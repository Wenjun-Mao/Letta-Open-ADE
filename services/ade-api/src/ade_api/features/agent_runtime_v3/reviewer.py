from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .errors import RuntimeValidationError
from .fact_registry import FACT_TYPE_REGISTRY
from .memory_intent import is_explicit_forgetting_request
from .memory_review import ReviewDecision, parse_review_decision, review_json_schema
from .router_transport import RouterTransport


REVIEWER_SYSTEM = """You are ADE's dedicated durable-memory reviewer.
Return only the requested JSON object. Propose only durable facts explicitly stated
or corrected in the CURRENT user message. evidence_quote must be an exact current
message excerpt and value must preserve the user's wording. Prior user messages and
active facts may resolve references but are not evidence for a new write. Never use
assistant prose, guesses, hypotheticals, or temporary plans. Questions about memory
produce no proposal. Use add when no matching active fact exists. Use correct only
when replacing a listed active fact, copying its fact_id and version exactly. Use
forget only for an explicit request to remove retained information. Never output a
subject ID or free-form key.
Choose the operation before filling any proposal fields, following
operation_contracts and worked_examples. An explicit request to forget or remove a
matching active fact is never an add. It must use forget, copy that active fact's
fact_id and version, and set value to JSON null rather than the string "null".
Use only the exact fact types and qualifiers in allowed_fact_contracts. A
qualifier is required only when that fact contract says so. Qualifiers are
canonical categories, not free-form labels: for example, a favorite museum is
person.preference with qualifier place, never favorite_place.
For subject facts leave entity_ref null. Existing non-subject entities use
existing:<id>; related facts for one new entity reuse new:<local-ref>. Correct and
forget must not provide type, qualifier, entity, or key metadata; ADE derives all
of it from their fact IDs. Expected versions must exactly match the
provided active facts. Example: after pet.name=Rocky, "it is a Husky" adds
pet.breed=Husky against Rocky's existing entity and preserves both facts.
"""

OPERATION_CONTRACTS = {
    "add": {
        "when": "the current message states a durable fact with no matching active fact",
        "excludes": ["explicit_forgetting"],
    },
    "correct": {
        "when": "the current message replaces or corrects a matching active fact",
        "uses_active_fact_id_and_version": True,
    },
    "forget": {
        "when": "the current message explicitly asks to remove an active fact",
        "value": None,
        "uses_active_fact_id_and_version": True,
    },
}

WORKED_EXAMPLES = {
    "explicit_forgetting": {
        "current_message": "请忘掉我喜欢蓝色这件事。",
        "matching_active_fact": {
            "fact_type": "person.preference",
            "qualifier": "color",
            "value": "蓝色",
        },
        "operation": "forget",
        "rule": (
            "Copy the matching active fact_id and version, set value to JSON null, "
            "and never emit add."
        ),
    }
}


@dataclass(frozen=True)
class ReviewerResult:
    decision: ReviewDecision
    usage: dict[str, int]
    model_request_count: int
    protocol_repaired: bool
    provider_request_ids: list[str | None]


class MemoryReviewer:
    def __init__(self, transport: RouterTransport) -> None:
        self.transport = transport

    async def review(
        self,
        *,
        model_key: str,
        current_user_message: dict[str, Any],
        recent_user_messages: list[dict[str, Any]],
        active_facts: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        timeout_seconds: float,
        validate_decision: Callable[[ReviewDecision], None],
    ) -> ReviewerResult:
        entity_kinds = {str(item.get("id")): item.get("kind") for item in entities}
        review_mode = (
            "forget"
            if is_explicit_forgetting_request(
                str(current_user_message.get("content") or "")
            )
            else "all"
        )
        packet = {
            "current_user_message": {
                "id": current_user_message.get("id"),
                "content": current_user_message.get("content"),
            },
            "recent_user_messages_for_reference_only": [
                {"id": item.get("id"), "content": item.get("content")}
                for item in recent_user_messages[-8:]
            ],
            "active_facts": [
                {
                    "fact_id": item.get("id"),
                    "fact_type": item.get("fact_type"),
                    "entity_ref": (
                        None
                        if entity_kinds.get(str(item.get("entity_id"))) == "subject"
                        else f"existing:{item.get('entity_id')}"
                    ),
                    "qualifier": item.get("qualifier"),
                    "value": item.get("value"),
                    "version": item.get("version"),
                }
                for item in active_facts
            ],
            "entities": [
                {
                    "entity_ref": f"existing:{item.get('id')}",
                    "kind": item.get("kind"),
                    "label": item.get("label"),
                }
                for item in entities
                if item.get("kind") != "subject"
            ],
            "review_mode": (
                "explicit_forgetting" if review_mode == "forget" else "general"
            ),
            "operation_contracts": (
                {"forget": OPERATION_CONTRACTS["forget"]}
                if review_mode == "forget"
                else OPERATION_CONTRACTS
            ),
            "worked_examples": WORKED_EXAMPLES,
            "allowed_fact_contracts": [
                {
                    "fact_type": spec.name,
                    "entity_kind": spec.entity_kind.value,
                    "qualifier_required": spec.qualifier_required,
                    "allowed_qualifiers": list(spec.allowed_qualifiers),
                }
                for spec in FACT_TYPE_REGISTRY.values()
            ],
        }
        messages: list[dict[str, str]] = [
            {"role": "system", "content": REVIEWER_SYSTEM},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
        ]
        responses: list[dict[str, Any]] = []
        for request_number in (1, 2):
            response = await self.transport.chat_completion(
                {
                    "model": model_key,
                    "messages": messages,
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "ade_memory_review",
                            "strict": True,
                            "schema": review_json_schema(mode=review_mode),
                        },
                    },
                    "temperature": 0,
                    "max_tokens": 2048,
                    "stream": False,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
                timeout_seconds=timeout_seconds,
            )
            responses.append(response)
            try:
                content = _response_content(response)
                decision = parse_review_decision(json.loads(content), mode=review_mode)
                validate_decision(decision)
            except (RuntimeValidationError, json.JSONDecodeError, ValueError) as exc:
                if request_number == 2:
                    raise RuntimeValidationError(
                        f"Memory reviewer failed its closed schema after repair: {exc}"
                    ) from exc
                messages.extend(
                    [
                        {
                            "role": "assistant",
                            "content": _safe_response_content(response),
                        },
                        {
                            "role": "user",
                            "content": (
                                "Repair the response to satisfy both the JSON schema "
                                f"and memory policy. Validation error: {str(exc)[:1000]}"
                            ),
                        },
                    ]
                )
                continue
            return ReviewerResult(
                decision=decision,
                usage=_combined_usage(responses),
                model_request_count=request_number,
                protocol_repaired=request_number == 2,
                provider_request_ids=[
                    str(item.get("id", "") or "") or None for item in responses
                ],
            )
        raise AssertionError("review loop did not return")


def _response_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeValidationError("Reviewer response did not contain a choice")
    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise RuntimeValidationError("Reviewer response did not contain a message")
    content = str(message.get("content", "") or "").strip()
    if not content:
        raise RuntimeValidationError("Reviewer response content was empty")
    return content


def _safe_response_content(response: dict[str, Any]) -> str:
    try:
        return _response_content(response)[:10_000]
    except RuntimeValidationError:
        return "{}"


def _combined_usage(responses: list[dict[str, Any]]) -> dict[str, int]:
    total: dict[str, int] = {}
    for response in responses:
        usage = response.get("usage")
        if not isinstance(usage, dict):
            continue
        for key, value in usage.items():
            if isinstance(value, int) and not isinstance(value, bool):
                total[str(key)] = total.get(str(key), 0) + value
    return total
