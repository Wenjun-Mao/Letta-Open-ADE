from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .errors import RuntimeValidationError
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
For subject facts leave entity_ref null. Existing non-subject entities use
existing:<id>; related facts for one new entity reuse new:<local-ref>. Correct,
forget, and merge derive their entity from fact IDs. Expected versions must exactly
match the provided active facts. Example: after pet.name=Rocky, "it is a Husky"
adds pet.breed=Husky against Rocky's existing entity and preserves both facts.
"""


@dataclass(frozen=True)
class ReviewerResult:
    decision: ReviewDecision
    usage: dict[str, int]
    model_request_count: int
    protocol_repaired: bool
    provider_request_ids: list[str]


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
            "allowed_fact_types": [
                "person.name",
                "person.current_location",
                "person.preference",
                "person.shoe_size",
                "pet.name",
                "pet.breed",
                "relationship.person",
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
                            "schema": review_json_schema(),
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
                decision = parse_review_decision(json.loads(content))
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
                    str(item.get("id")) for item in responses if item.get("id")
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
