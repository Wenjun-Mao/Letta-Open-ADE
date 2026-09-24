"""Whole-record, paired offline context recipes for natural-memory evaluation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal

from .context import (
    BuiltContext,
    ContextBudget,
    ConversationHistoryMetadata,
    MEMORY_CONTROL_INSTRUCTIONS,
    estimate_tokens,
)
from .errors import RuntimeValidationError


NaturalVariant = Literal["A", "A0", "B"]
NATURAL_POLICY_BINDINGS: dict[str, NaturalVariant] = {
    "natural-user-assertions-v2-a": "A",
    "natural-user-assertions-v2-a0": "A0",
    "natural-user-assertions-v2-b": "B",
}


@dataclass(frozen=True)
class NaturalContextBundle:
    context: BuiltContext
    source_messages: tuple[dict[str, Any], ...]
    variant: NaturalVariant
    lifecycle_withheld: bool


def build_natural_context(
    *,
    variant: NaturalVariant,
    system_prompt: str,
    persona: str,
    current_user: dict[str, Any],
    eligible_recent_messages: list[dict[str, Any]],
    lifecycle_facts: list[dict[str, Any]],
    retrieved_facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    summary_content: str,
    history_metadata: ConversationHistoryMetadata,
    budget: ContextBudget,
    reviewer_suffix_limit: int,
    shared_suffix_token_limit: int = 640,
    selective_fact_limit: int = 8,
    exact_entity_expansion_limit: int = 2,
) -> NaturalContextBundle:
    if variant not in {"A", "A0", "B"}:
        raise ValueError("unknown natural context variant")
    mandatory = (
        f"{system_prompt}\n\nPersona:\n{persona}\n\n{MEMORY_CONTROL_INSTRUCTIONS}"
    )
    current_content = str(current_user["content"])
    metadata = (
        "Conversation history metadata (authoritative):\n"
        f"- Completed rounds before current: {history_metadata.completed_user_turns}\n"
        f"- Summary through sequence: {history_metadata.summary_through_sequence}\n"
        "- This excludes the current request and unfinished runs."
    )
    base_sections = [mandatory, metadata]
    if _request_tokens(base_sections, [], current_content) > budget.input_limit:
        raise RuntimeValidationError(
            "Mandatory natural context exceeds the generation input limit",
            detail_code="natural_context_mandatory_overflow",
        )
    suffix = _complete_exchange_suffix(
        eligible_recent_messages,
        max_user_turns=8,
        token_limit=min(shared_suffix_token_limit, reviewer_suffix_limit),
    )
    facts = sorted(
        (fact for fact in lifecycle_facts if fact["status"] in {"active", "inactive"}),
        key=lambda item: (str(item["normalized_key"]), str(item["id"])),
    )
    full_snapshot = _section("Current lifecycle snapshot", facts)
    lifecycle_withheld = False
    selected_facts: list[dict[str, Any]] = []
    summary = ""

    if variant in {"A", "A0"}:
        if (
            _request_tokens([*base_sections, full_snapshot], [], current_content)
            > budget.input_limit
        ):
            lifecycle_withheld = True
            fact_section = (
                "Current lifecycle snapshot WITHHELD: complete snapshot exceeds "
                "the input limit. Do not infer omitted memory or prior dialogue."
            )
            suffix = []
        else:
            selected_facts = facts
            fact_section = full_snapshot
            suffix = _fit_suffix(
                suffix,
                [*base_sections, fact_section],
                current_content,
                budget.input_limit,
            )
            if variant == "A" and summary_content:
                proposed_summary = (
                    "Conversation summary (attributed, not certified current):\n"
                    f"{summary_content}"
                )
                if (
                    _request_tokens(
                        [*base_sections, fact_section, proposed_summary],
                        suffix,
                        current_content,
                    )
                    <= budget.input_limit
                ):
                    summary = proposed_summary
    else:
        suffix = _fit_suffix(suffix, base_sections, current_content, budget.input_limit)
        selected_facts = _select_relevant_facts(
            facts=facts,
            retrieved=retrieved_facts,
            entities=entities,
            current_content=current_content,
            suffix=suffix,
            limit=selective_fact_limit,
            expansion_limit=exact_entity_expansion_limit,
        )
        while (
            selected_facts
            and _request_tokens(
                [
                    *base_sections,
                    _section("Selected current lifecycle views", selected_facts),
                ],
                suffix,
                current_content,
            )
            > budget.input_limit
        ):
            selected_facts.pop()
        fact_section = _section("Selected current lifecycle views", selected_facts)
        if (
            _request_tokens([*base_sections, fact_section], suffix, current_content)
            > budget.input_limit
        ):
            raise RuntimeValidationError(
                "Natural context cannot fit its shared suffix",
                detail_code="natural_context_suffix_overflow",
            )

    sections = [*base_sections, fact_section]
    if summary:
        sections.append(summary)
    messages = [
        {"role": "system", "content": "\n\n".join(sections)},
        *[
            {"role": str(message["role"]), "content": str(message["content"])}
            for message in suffix
        ],
        {"role": "user", "content": current_content},
    ]
    actual = estimate_tokens(
        json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    )
    if actual > budget.input_limit:
        raise RuntimeValidationError(
            "Natural context exceeded the actual serialized input limit",
            detail_code="natural_context_serialized_overflow",
        )
    selected_ids = {str(message["id"]) for message in suffix}
    return NaturalContextBundle(
        context=BuiltContext(
            messages=messages,
            section_tokens={
                "prompt_persona": estimate_tokens(mandatory),
                "conversation_history_metadata": estimate_tokens(metadata),
                "lifecycle_views": estimate_tokens(fact_section),
                "conversation_summary": estimate_tokens(summary),
                "recent_messages": sum(
                    estimate_tokens(str(message["content"])) for message in suffix
                ),
                "current_user_message": estimate_tokens(current_content),
            },
            omitted_message_ids=[
                str(message["id"])
                for message in eligible_recent_messages
                if str(message["id"]) not in selected_ids
            ],
            retrieved_fact_ids=[str(fact["id"]) for fact in selected_facts],
            estimated_input_tokens=actual,
        ),
        source_messages=tuple([*suffix, current_user]),
        variant=variant,
        lifecycle_withheld=lifecycle_withheld,
    )


def _complete_exchange_suffix(
    messages: list[dict[str, Any]], *, max_user_turns: int, token_limit: int
) -> list[dict[str, Any]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    pending: dict[str, Any] | None = None
    for message in sorted(messages, key=lambda item: int(item["sequence"])):
        if message["role"] == "user":
            pending = message
        elif (
            message["role"] == "assistant"
            and pending is not None
            and str(message.get("run_id")) == str(pending.get("run_id"))
        ):
            pairs.append((pending, message))
            pending = None
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for pair in reversed(pairs):
        if len(selected) >= max_user_turns:
            break
        candidate = [item for group in [pair, *selected] for item in group]
        cost = estimate_tokens(
            json.dumps(
                [
                    {"role": str(item["role"]), "content": str(item["content"])}
                    for item in candidate
                ],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
        if cost > token_limit:
            break
        selected.insert(0, pair)
    return [item for pair in selected for item in pair]


def _fit_suffix(
    suffix: list[dict[str, Any]],
    sections: list[str],
    current_content: str,
    input_limit: int,
) -> list[dict[str, Any]]:
    result = list(suffix)
    while result and _request_tokens(sections, result, current_content) > input_limit:
        result = result[2:]
    return result


def _select_relevant_facts(
    *,
    facts: list[dict[str, Any]],
    retrieved: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    current_content: str,
    suffix: list[dict[str, Any]],
    limit: int,
    expansion_limit: int,
) -> list[dict[str, Any]]:
    facts_by_id = {str(fact["id"]): fact for fact in facts}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in retrieved:
        fact_id = str(hit["id"])
        if fact_id in facts_by_id and fact_id not in seen and len(selected) < limit:
            selected.append(facts_by_id[fact_id])
            seen.add(fact_id)
    text = " ".join([current_content, *[str(item["content"]) for item in suffix]])
    matching_entities = [
        entity
        for entity in entities
        if entity["kind"] != "subject"
        and str(entity.get("label") or "").strip()
        and str(entity["label"]).casefold() in text.casefold()
    ]
    if len(matching_entities) == 1:
        entity_id = str(matching_entities[0]["id"])
        expanded = 0
        for fact in facts:
            if (
                str(fact["entity_id"]) == entity_id
                and str(fact["id"]) not in seen
                and len(selected) < limit
                and expanded < expansion_limit
            ):
                selected.append(fact)
                seen.add(str(fact["id"]))
                expanded += 1
    return selected


def _section(title: str, facts: list[dict[str, Any]]) -> str:
    lines = [f"{title} (only active is current; inactive is historical):"]
    for fact in facts:
        status = str(fact["status"]).upper()
        lines.append(
            f"- [{fact['id']} v{fact['version']}] {status} "
            f"{fact['normalized_key']}: {fact['value']}"
        )
    if len(lines) == 1:
        lines.append("- None supplied")
    return "\n".join(lines)


def _request_tokens(
    sections: list[str], suffix: list[dict[str, Any]], current_content: str
) -> int:
    messages = [
        {"role": "system", "content": "\n\n".join(sections)},
        *[
            {"role": str(item["role"]), "content": str(item["content"])}
            for item in suffix
        ],
        {"role": "user", "content": current_content},
    ]
    return estimate_tokens(
        json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    )
