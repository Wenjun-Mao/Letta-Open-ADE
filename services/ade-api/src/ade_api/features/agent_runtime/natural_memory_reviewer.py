"""One-call mixed reviewer for the isolated natural-memory policy binding."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .context import estimate_tokens
from .errors import RuntimeValidationError
from .fact_registry import FACT_TYPE_REGISTRY
from .natural_memory_review import (
    NaturalReviewDecision,
    natural_review_json_schema,
    parse_natural_review_decision,
)
from .natural_memory_policy import PreparedNaturalReview, prepare_natural_memory_review
from .provider_tracing import AttemptTrace, safe_provider_request_id
from .reviewer import _combined_usage, _response_content
from .router_transport import RouterTransport


NATURAL_REVIEWER_SYSTEM = """You are ADE's durable-memory reviewer.
Return one JSON object matching the supplied schema. Review all supported claims
in the current user turn together: add, revise, end, reassert or forget, including
mixed turns. Give each proposal one unique claim_id and one typed disposition.
An allow disposition requires exact current-user authority. A prior assistant
message can resolve a referent only when the current user explicitly endorses it;
assistant words alone never authorize storage. Cite each exact source span by
message_id, quote and source role. The source must be in the supplied bundle.
Never infer or store fictional, quoted, hypothetical, uncertain, unconsented or
no-save details. Use defer for unresolved reference or scoped no-save claims.
If the visible candidate reply contradicts a proposed claim, cite one exact
candidate reply quote and mark contradiction. Do not silently omit an affected
claim to avoid reporting the conflict. One contradiction rejects the whole turn.
Match fact_id and expected_version exactly for target operations. Revise keeps
the same entity/type/qualifier slot and names enrich, supersede, correct or
unspecified only when the source cannot distinguish the reason.
End makes a former/invalidated assertion inactive; reassert activates only an
inactive assertion. Forget requires an explicit user request. Never target a
forgotten assertion or invent IDs. A new related entity requires a surviving
identity proposal. No proposal is valid merely because the assistant said it.
"""


@dataclass(frozen=True)
class NaturalReviewerResult:
    decision: NaturalReviewDecision
    usage: dict[str, int]
    model_request_count: int
    protocol_repaired: bool
    provider_request_ids: list[str | None]


class NaturalMemoryReviewer:
    def __init__(
        self, transport: RouterTransport, *, provider_adapter: str = ""
    ) -> None:
        self.transport = transport
        self.provider_adapter = provider_adapter

    async def review(
        self,
        *,
        model_key: str,
        current_user_message: dict[str, Any],
        source_messages: list[dict[str, Any]],
        facts: list[dict[str, Any]],
        entities: list[dict[str, Any]],
        candidate_reply: str,
        timeout_seconds: float,
        validate_decision: Callable[[NaturalReviewDecision], None],
        input_token_limit: int,
        observe_request: Callable[[dict[str, Any]], None] | None = None,
        observe_decision: Callable[[NaturalReviewDecision], None] | None = None,
    ) -> NaturalReviewerResult:
        schema = natural_review_json_schema()
        packet = {
            "current_user_message": {
                "id": str(current_user_message["id"]),
                "content": str(current_user_message["content"]),
            },
            "source_messages": [
                {
                    "id": str(item["id"]),
                    "role": str(item["role"]),
                    "content": str(item["content"]),
                }
                for item in source_messages
            ],
            "candidate_visible_reply": candidate_reply,
            "current_memory_targets": [
                {
                    "fact_id": str(item["id"]),
                    "fact_type": item["fact_type"],
                    "qualifier": item.get("qualifier"),
                    "entity_id": str(item["entity_id"]),
                    "value": item.get("value"),
                    "status": item["status"],
                    "version": item["version"],
                }
                for item in facts
                if item["status"] in {"active", "inactive"}
            ],
            "entities": [
                {
                    "entity_id": str(item["id"]),
                    "kind": item["kind"],
                    "label": item["label"],
                }
                for item in entities
            ],
            "allowed_fact_contracts": [
                {
                    "fact_type": spec.name,
                    "entity_kind": spec.entity_kind.value,
                    "qualifier_required": spec.qualifier_required,
                    "allowed_qualifiers": list(spec.allowed_qualifiers),
                    "defines_entity_identity": spec.defines_entity_identity,
                }
                for spec in FACT_TYPE_REGISTRY.values()
            ],
        }
        system = NATURAL_REVIEWER_SYSTEM
        if self.provider_adapter == "deepseek_openai":
            system += (
                "\nReturn JSON matching this exact schema: "
                f"{json.dumps(schema, ensure_ascii=False)}"
                '\nExample JSON: {"proposals":[],"claim_dispositions":[]}'
            )
        payload: dict[str, Any] = {
            "model": model_key,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
            ],
            "max_tokens": 1024,
            "stream": False,
        }
        if self.provider_adapter == "deepseek_openai":
            payload.update(
                {
                    "thinking": {"type": "enabled"},
                    "reasoning_effort": "high",
                    "response_format": {"type": "json_object"},
                }
            )
        else:
            payload.update(
                {
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "ade_natural_memory_review",
                            "strict": True,
                            "schema": schema,
                        },
                    },
                    "temperature": 0,
                    "chat_template_kwargs": {"enable_thinking": False},
                }
            )
        request_tokens = estimate_tokens(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        if request_tokens > input_token_limit:
            raise RuntimeValidationError(
                "Full natural reviewer request exceeds its input limit",
                detail_code="natural_reviewer_capacity",
            )
        if observe_request is not None:
            observe_request(payload)
        response = await self.transport.chat_completion(
            payload, timeout_seconds=timeout_seconds
        )
        try:
            decision = parse_natural_review_decision(
                json.loads(_response_content(response))
            )
            if observe_decision is not None:
                observe_decision(decision)
            validate_decision(decision)
        except RuntimeValidationError as exc:
            if exc.detail_code == "natural_memory_reply_conflict":
                raise
            raise RuntimeValidationError(
                f"Natural memory reviewer failed its closed schema: {exc}",
                detail_code="natural_review_validation",
            ) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeValidationError(
                f"Natural memory reviewer failed its closed schema: {exc}",
                detail_code="natural_review_validation",
            ) from exc
        return NaturalReviewerResult(
            decision=decision,
            usage=_combined_usage([response]),
            model_request_count=1,
            protocol_repaired=False,
            provider_request_ids=[safe_provider_request_id(response.get("id"))],
        )


def reviewer_suffix_limit(
    *,
    current_user_message: dict[str, Any],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    input_token_limit: int,
    candidate_reply_reserve: int,
) -> int:
    """Conservatively reserve full targets, schema and a maximum candidate reply."""

    required = {
        "system": NATURAL_REVIEWER_SYSTEM,
        "schema": natural_review_json_schema(),
        "current_user_message": current_user_message["content"],
        "full_targets": [
            (
                item["id"],
                item["fact_type"],
                item.get("qualifier"),
                item["value"],
                item["status"],
                item["version"],
            )
            for item in facts
            if item["status"] in {"active", "inactive"}
        ],
        "entities": [
            (item["id"], item["kind"], item.get("label")) for item in entities
        ],
    }
    fixed = estimate_tokens(
        json.dumps(required, ensure_ascii=False, separators=(",", ":"), default=str)
    )
    remaining = input_token_limit - fixed - candidate_reply_reserve - 320
    if remaining < 0:
        raise RuntimeValidationError(
            "Natural reviewer cannot fit its required targets and candidate reply",
            detail_code="natural_reviewer_capacity",
        )
    return remaining


async def execute_natural_review(
    *,
    trace: AttemptTrace,
    transport: RouterTransport,
    reviewer_deployment: dict[str, Any],
    provider_adapter: str,
    subject_id: str,
    current_user_message: dict[str, Any],
    source_messages: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    candidate_reply: str,
    timeout_seconds: float,
    input_token_limit: int,
) -> tuple[NaturalReviewerResult, PreparedNaturalReview]:
    """Bind one visible candidate and source bundle to one validated decision."""

    def prepare(decision: NaturalReviewDecision) -> PreparedNaturalReview:
        return prepare_natural_memory_review(
            decision=decision,
            subject_id=subject_id,
            current_user_message=current_user_message,
            available_messages=source_messages,
            facts=facts,
            entities=entities,
            candidate_reply=candidate_reply,
        )

    reviewer = NaturalMemoryReviewer(
        trace.transport(
            transport,
            stage="reviewer",
            model_fingerprint=str(reviewer_deployment["fingerprint"]),
        ),
        provider_adapter=provider_adapter,
    )
    evidence = trace.natural_evidence
    result = await reviewer.review(
        model_key=str(reviewer_deployment["route_alias"]),
        current_user_message=current_user_message,
        source_messages=source_messages,
        facts=facts,
        entities=entities,
        candidate_reply=candidate_reply,
        timeout_seconds=timeout_seconds,
        input_token_limit=input_token_limit,
        observe_request=evidence.capture_reviewer_request if evidence else None,
        observe_decision=evidence.capture_reviewer_decision if evidence else None,
        validate_decision=prepare,
    )
    return result, prepare(result.decision)
