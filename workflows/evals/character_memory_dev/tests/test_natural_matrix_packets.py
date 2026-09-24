"""Execute each frozen cell through the real serializers with a fake transport.

These packets prove admission, pairing and reviewer visibility. They do not score
the semantic correctness of scripted replies or writes.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from uuid import UUID

from ade_api.features.agent_runtime.context import (
    ContextBudget,
    ConversationHistoryMetadata,
)
from ade_api.features.agent_runtime.executor import ConversationExecutor
from ade_api.features.agent_runtime.natural_context import build_natural_context
from ade_api.features.agent_runtime.natural_memory_reviewer import (
    NaturalMemoryReviewer,
    preflight_reviewer_bundle,
)
from workflows.evals.character_memory_dev.natural_memory_contract import (
    eligible_local_turn_ids,
    expanded_cells,
    load_cases,
    load_matrix,
)


class PacketRouter:
    async def chat_completion(self, payload, *, timeout_seconds):
        content = (
            json.dumps({"proposals": [], "claim_dispositions": []})
            if payload["model"] == "fake::reviewer"
            else "Okay."
        )
        return {
            "id": "synthetic-packet-request",
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }


def _branch(cases: dict, cell: dict) -> dict:
    return next(
        branch
        for arc in cases["arcs"]
        if arc["id"] == cell["arc"]
        for branch in arc["branches"]
        if branch["id"] == cell["branch"]
    )


def _history(branch: dict, cutoff: str) -> tuple[list[dict], dict, dict[str, int]]:
    source_turns = branch["turns"]
    selected = source_turns[
        : next(i for i, turn in enumerate(source_turns) if turn[0] == cutoff) + 1
    ]
    messages: list[dict] = []
    label_sequence: dict[str, int] = {}
    run_number = 0
    for index, (label, role, content) in enumerate(selected):
        if role == "user":
            run_number += 1
        message = {
            "id": str(UUID(int=2000 + len(messages))),
            "label": label,
            "run_id": str(UUID(int=3000 + run_number)),
            "sequence": len(messages) + 1,
            "role": role,
            "content": content,
        }
        label_sequence[label] = message["sequence"]
        messages.append(message)
        if (
            role == "user"
            and index < len(selected) - 1
            and selected[index + 1][1] != "assistant"
        ):
            messages.append(
                {
                    "id": str(UUID(int=2000 + len(messages))),
                    "label": f"synthetic-ack-after-{label}",
                    "run_id": message["run_id"],
                    "sequence": len(messages) + 1,
                    "role": "assistant",
                    "content": "Acknowledged (synthetic fixture completion).",
                }
            )
    return messages[:-1], messages[-1], label_sequence


def _facts(cell: dict, *, size: str) -> list[dict]:
    count = int(cell.get("record_count", 0))
    repetitions = 15 if size == "short" else 100
    facts = [
        {
            "id": str(UUID(int=1000 + index)),
            "entity_id": str(UUID(int=1)),
            "fact_type": "person.preference",
            "normalized_key": f"person.preference|subject|{index:03d}",
            "qualifier": "other",
            "value": f"unrelated-{index:03d}" + " x" * repetitions,
            "status": "inactive" if index % 3 == 0 else "active",
            "version": 2 if index % 3 == 0 else 1,
        }
        for index in range(count)
    ]
    special = {
        "response-residence-visit": ("person.current_location", "Toronto", "active"),
        "response-ended-recall": ("relationship.person", "Xiao Wang", "inactive"),
        "mutation-end": ("relationship.person", "Xiao Wang", "active"),
        "mutation-explicit-removal": ("person.preference", "milk tea", "active"),
        "mutation-no-save": ("person.preference", "morning coffee", "active"),
        "summary-after-change": ("relationship.person", "Xiao Wang", "inactive"),
        "summary-end-forget": ("relationship.person", "Xiao Wang", "forgotten"),
    }.get(cell["id"])
    if special:
        fact_type, value, status = special
        facts.append(
            {
                "id": str(UUID(int=9000)),
                "entity_id": str(UUID(int=2))
                if fact_type == "relationship.person"
                else str(UUID(int=1)),
                "fact_type": fact_type,
                "normalized_key": f"{fact_type}|subject|primary",
                "qualifier": "drink"
                if fact_type == "person.preference"
                else "partner"
                if fact_type == "relationship.person"
                else None,
                "value": value,
                "status": status,
                "version": 3
                if status == "forgotten"
                else 2
                if status == "inactive"
                else 1,
            }
        )
    return facts


async def _execute_cell(cell: dict, variant: str, branch: dict, matrix: dict) -> dict:
    prior, current, labels = _history(branch, cell["cutoff"])
    boundary = labels[cell["summary_through"]] if "summary_through" in cell else 0
    local = [message for message in prior if message["sequence"] > boundary]
    facts = _facts(cell, size=cell.get("size_class", "short"))
    primary = next((fact for fact in facts if fact["id"] == str(UUID(int=9000))), None)
    retrieved = [primary] if primary and primary["status"] != "forgotten" else facts[:1]
    generation_budget = ContextBudget(
        context_window=matrix["budgets"]["generation"]["context_window"],
        max_output_tokens=matrix["budgets"]["generation"]["output_reserve"],
        tool_schema_tokens=matrix["budgets"]["generation"]["tool_schema"],
    )
    reviewer_limit = matrix["budgets"]["reviewer"]["input_limit"]
    system_prompt = (
        "Policy " + "P" * matrix["budgets"]["pressure"]["synthetic_prompt_repeat_bytes"]
        if cell["id"].startswith("pressure-")
        else "Policy"
    )
    summary = (
        "Earlier report: Xiao Wang and the user were dating. "
        "An afternoon 2pm product-role opening was chosen."
        if boundary
        else ""
    )
    entities = [{"id": str(UUID(int=1)), "kind": "subject", "label": ""}]
    if primary and primary["fact_type"] == "relationship.person":
        entities.append(
            {"id": str(UUID(int=2)), "kind": "related_person", "label": "Xiao Wang"}
        )
    built = build_natural_context(
        variant="B" if variant == "native" else variant,
        system_prompt=system_prompt,
        persona="Companion",
        current_user=current,
        eligible_recent_messages=local,
        lifecycle_facts=facts,
        retrieved_facts=retrieved,
        entities=entities,
        summary_content=summary,
        history_metadata=ConversationHistoryMetadata(
            completed_user_turns=sum(message["role"] == "user" for message in prior),
            summary_through_sequence=boundary,
        ),
        budget=generation_budget,
        reviewer_suffix_limit=matrix["budgets"]["reviewer"]["shared_suffix_max"],
    )
    reviewer_preflight = preflight_reviewer_bundle(
        model_key="fake::reviewer",
        provider_adapter="synthetic",
        current_user_message=current,
        source_messages=list(built.source_messages),
        facts=facts,
        entities=entities,
        candidate_reply_reserve=generation_budget.max_output_tokens,
        input_token_limit=reviewer_limit,
    )
    router = PacketRouter()
    generation_requests: list[dict] = []
    generated = await ConversationExecutor(router).execute(
        model_key="fake::conversation",
        messages=built.context.messages,
        timeout_seconds=30,
        max_output_tokens=generation_budget.max_output_tokens,
        input_token_limit=generation_budget.input_limit,
        observe_request=generation_requests.append,
    )
    reviewer_requests: list[dict] = []
    reviewed = await NaturalMemoryReviewer(router).review(
        model_key="fake::reviewer",
        current_user_message=current,
        source_messages=list(built.source_messages),
        facts=facts,
        entities=entities,
        candidate_reply=generated.assistant_text,
        timeout_seconds=30,
        validate_decision=lambda decision: None,
        input_token_limit=reviewer_limit,
        observe_request=reviewer_requests.append,
    )
    assert len(generation_requests) == len(reviewer_requests) == 1
    reviewer_packet = json.loads(reviewer_requests[0]["messages"][1]["content"])
    source = [
        {"id": row["id"], "role": row["role"], "content": row["content"]}
        for row in built.source_messages
    ]
    assert reviewer_packet["source_messages"] == source
    assert generation_requests[0]["messages"] == built.context.messages
    assert built.context.estimated_input_tokens <= generation_budget.input_limit
    assert reviewer_preflight <= reviewer_limit
    assert reviewer_packet["current_user_message"]["id"] == current["id"]
    assert all(
        target["status"] != "forgotten"
        for target in reviewer_packet["current_memory_targets"]
    )
    return {
        "cell_id": cell["id"],
        "variant": variant,
        "kind": cell["kind"],
        "cutoff": cell["cutoff"],
        "eligible_local_turn_ids": eligible_local_turn_ids(cell, branch),
        "summary_through_sequence": boundary,
        "summary_content": summary if variant == "A" else "",
        "lifecycle_withheld": built.lifecycle_withheld,
        "facts": [
            {
                "id": f["id"],
                "status": f["status"],
                "version": f["version"],
                "value": f["value"],
            }
            for f in facts
        ],
        "source_messages": [
            {
                "id": row["id"],
                "label": row["label"],
                "role": row["role"],
                "content": row["content"],
            }
            for row in built.source_messages
        ],
        "selected_fact_ids": built.context.retrieved_fact_ids,
        "omitted_message_ids": built.context.omitted_message_ids,
        "section_tokens": built.context.section_tokens,
        "generation_input_tokens": built.context.estimated_input_tokens,
        "generation_input_limit": generation_budget.input_limit,
        "reviewer_preflight_tokens": reviewer_preflight,
        "reviewer_input_limit": reviewer_limit,
        "generation_request": generation_requests[0],
        "reviewer_request": reviewer_requests[0],
        "provider_counts": {
            "conversation": generated.model_request_count,
            "reviewer": reviewed.model_request_count,
        },
        "outcome": "scripted_packet_only_no_database_commit",
    }


def test_every_frozen_cell_executes_paired_serialized_packets(tmp_path: Path) -> None:
    cases, matrix = load_cases(), load_matrix()
    receipts = asyncio.run(
        _execute_all(cases=cases, matrix=matrix, output=tmp_path / "packets")
    )
    assert set(receipts) == {name for name, _, _ in expanded_cells(matrix)}
    assert len(receipts) == 30
    for cell in matrix["cells"]:
        variants = {
            variant: receipts[f"{cell['id']}::{variant}"]
            for variant in cell["variants"]
        }
        if "A" in variants and "A0" in variants:
            a, a0 = variants["A"], variants["A0"]
            assert a["source_messages"] == a0["source_messages"]
            assert a["selected_fact_ids"] == a0["selected_fact_ids"]
            assert a["omitted_message_ids"] == a0["omitted_message_ids"]
            summary_section = (
                "\n\nConversation summary (attributed, not certified current):\n"
                + a["summary_content"]
            )
            a_messages = a["generation_request"]["messages"]
            a0_messages = a0["generation_request"]["messages"]
            assert (
                a_messages[0]["content"].replace(summary_section, "")
                == a0_messages[0]["content"]
            )
            assert a_messages[1:] == a0_messages[1:]
        if "A0" in variants and "B" in variants:
            assert (
                variants["A0"]["eligible_local_turn_ids"]
                == variants["B"]["eligible_local_turn_ids"]
            )
        if cell["id"] in {"pressure-dog", "pressure-interview"}:
            assert variants["A"]["lifecycle_withheld"]
            assert variants["B"]["source_messages"][:-1]
            assert len(variants["B"]["reviewer_request"]["messages"]) == 2
        if cell["id"] == "summary-end-forget":
            for receipt in variants.values():
                assert str(UUID(int=9000)) not in receipt["selected_fact_ids"]
                targets = json.loads(
                    receipt["reviewer_request"]["messages"][1]["content"]
                )["current_memory_targets"]
                assert str(UUID(int=9000)) not in {
                    target["fact_id"] for target in targets
                }
        if cell["id"] == "response-residence-visit":
            for receipt in variants.values():
                assert str(UUID(int=9000)) in receipt["selected_fact_ids"]
                assert "巴黎" in json.dumps(
                    receipt["generation_request"]["messages"], ensure_ascii=False
                )


async def _execute_all(*, cases: dict, matrix: dict, output: Path) -> dict[str, dict]:
    output.mkdir(parents=True)
    receipts = {}
    for name, cell, variant in expanded_cells(matrix):
        receipt = await _execute_cell(cell, variant, _branch(cases, cell), matrix)
        receipts[name] = receipt
        (output / f"{name.replace('::', '--')}.json").write_text(
            json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        )
    return receipts
