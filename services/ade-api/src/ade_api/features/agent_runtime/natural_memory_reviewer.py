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
from .natural_memory_binding import NaturalBindingMap, build_natural_binding_map
from .provider_tracing import AttemptTrace, safe_provider_request_id
from .reviewer import _combined_usage, _response_content
from .router_transport import RouterTransport


NATURAL_REVIEWER_SYSTEM = """You are ADE's one-call durable-memory reviewer.
Return exactly one JSON object with required decisions array, at most 20 items.
An empty decisions array means an explicit checked no-change.
Use subject_add for subject facts without any entity field; related_add needs an
E handle or new:local identity reference. Targets use F handles only. ADE owns all
persistent IDs, versions, roles and source offsets. Preserve scope, time,
frequency, condition and negation in supported values.
Every write has one exact current-user quote and one evidence mode:
direct (current assertion), resolve_user (earlier U assertion/request completed by
current answer), endorse_assistant (current explicit assent to one A proposition
or action). Earlier text is support, never independent current authority. Bare
names do not endorse assistant-introduced properties. Uncertainty, hypothetical,
quotation, withdrawal and no-save restrictions inherited from antecedents remain
binding. Forget needs explicit removal assent; a factual ending is not forgetting.
Use defer for unresolved/uncertain/nonasserted/no-save claims without executable
fields. No-save on a claim blocks an equivalent write in either order; unrelated
supported writes survive. Use conflict with exact candidate quote and read-only
F/E grounding when the visible reply contradicts held memory, even with no write.
A conflict rejects the whole attempt. Never invent an assertion to ground it.
Do not repair malformed output or silently omit a contradictory sibling.
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
        max_output_tokens: int = 1024,
        observe_request: Callable[[dict[str, Any]], None] | None = None,
        observe_decision: Callable[[NaturalReviewDecision], None] | None = None,
        binding_map: NaturalBindingMap | None = None,
    ) -> NaturalReviewerResult:
        payload = natural_review_request(
            model_key=model_key,
            provider_adapter=self.provider_adapter,
            current_user_message=current_user_message,
            source_messages=source_messages,
            facts=facts,
            entities=entities,
            candidate_reply=candidate_reply,
            max_output_tokens=max_output_tokens,
            binding_map=binding_map,
        )
        request_tokens = serialized_review_tokens(payload)
        if request_tokens > input_token_limit:
            raise RuntimeValidationError(
                "Full natural reviewer request exceeds its input limit",
                detail_code="natural_reviewer_capacity",
            )
        if observe_request is not None:
            try:
                observe_request(payload)
            except Exception:
                pass
        response = await self.transport.chat_completion(
            payload, timeout_seconds=timeout_seconds
        )
        choices = response.get("choices")
        choice = (
            choices[0]
            if isinstance(choices, list) and choices and isinstance(choices[0], dict)
            else {}
        )
        finish = choice.get("finish_reason")
        if finish == "length":
            raise RuntimeValidationError(
                "Natural reviewer output was truncated",
                detail_code="natural_review_truncated",
            )
        if finish != "stop":
            raise RuntimeValidationError(
                "Natural reviewer did not finish normally",
                detail_code="natural_review_refusal",
            )
        try:
            decision = parse_natural_review_decision(
                json.loads(_response_content(response))
            )
            if observe_decision is not None:
                try:
                    observe_decision(decision)
                except Exception:
                    pass
            validate_decision(decision)
        except RuntimeValidationError as exc:
            if exc.detail_code in {
                "natural_memory_reply_conflict",
                "natural_review_schema",
                "natural_review_binding",
            }:
                raise
            raise RuntimeValidationError(
                f"Natural memory reviewer decision was rejected: {exc}",
                detail_code="natural_review_semantic",
            ) from exc
        except (json.JSONDecodeError, ValueError) as exc:
            raise RuntimeValidationError(
                f"Natural memory reviewer returned malformed JSON: {exc}",
                detail_code="natural_review_json",
            ) from exc
        return NaturalReviewerResult(
            decision=decision,
            usage=_combined_usage([response]),
            model_request_count=1,
            protocol_repaired=False,
            provider_request_ids=[safe_provider_request_id(response.get("id"))],
        )


def natural_review_request(
    *,
    model_key: str,
    provider_adapter: str,
    current_user_message: dict[str, Any],
    source_messages: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    candidate_reply: str,
    max_output_tokens: int = 1024,
    binding_map: NaturalBindingMap | None = None,
) -> dict[str, Any]:
    """Build the sole reviewer wire shape used by preflight and execution."""

    schema = natural_review_json_schema()
    binding = binding_map or build_natural_binding_map(
        current_user_message=current_user_message,
        source_messages=source_messages,
        facts=facts,
        entities=entities,
    )
    packet = binding.packet(candidate_reply)
    packet["allowed_fact_contracts"] = [
        {
            "fact_type": spec.name,
            "entity_kind": spec.entity_kind.value,
            "qualifier_required": spec.qualifier_required,
            "allowed_qualifiers": list(spec.allowed_qualifiers),
            "defines_entity_identity": spec.defines_entity_identity,
        }
        for spec in FACT_TYPE_REGISTRY.values()
    ]
    system = NATURAL_REVIEWER_SYSTEM
    if provider_adapter == "deepseek_openai":
        system += (
            "\nReturn JSON matching this exact schema: "
            f"{json.dumps(schema, ensure_ascii=False)}"
            '\nExample JSON: {"decisions":[]}'
        )
    payload: dict[str, Any] = {
        "model": model_key,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
        ],
        "max_tokens": max_output_tokens,
        "stream": False,
    }
    if provider_adapter == "deepseek_openai":
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
    return payload


def serialized_review_tokens(payload: dict[str, Any]) -> int:
    return estimate_tokens(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )


def reviewer_suffix_limit(
    *,
    model_key: str,
    provider_adapter: str,
    current_user_message: dict[str, Any],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    input_token_limit: int,
    candidate_reply_reserve: int,
) -> int:
    """Reserve the serialized reviewer base and its full candidate reply."""

    projected = natural_review_request(
        model_key=model_key,
        provider_adapter=provider_adapter,
        current_user_message=current_user_message,
        source_messages=[current_user_message],
        facts=facts,
        entities=entities,
        candidate_reply="x" * (4 * candidate_reply_reserve),
    )
    remaining = input_token_limit - serialized_review_tokens(projected) - 320
    if remaining < 0:
        raise RuntimeValidationError(
            "Natural reviewer cannot fit its required targets and candidate reply",
            detail_code="natural_reviewer_capacity",
        )
    return remaining


def preflight_reviewer_bundle(
    *,
    model_key: str,
    provider_adapter: str,
    current_user_message: dict[str, Any],
    source_messages: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    candidate_reply_reserve: int,
    input_token_limit: int,
    max_output_tokens: int = 1024,
) -> int:
    """Fail before generation if the selected shared bundle cannot be reviewed."""

    projected = natural_review_request(
        model_key=model_key,
        provider_adapter=provider_adapter,
        current_user_message=current_user_message,
        source_messages=source_messages,
        facts=facts,
        entities=entities,
        candidate_reply="x" * (4 * candidate_reply_reserve),
        max_output_tokens=max_output_tokens,
    )
    tokens = serialized_review_tokens(projected)
    if tokens > input_token_limit:
        raise RuntimeValidationError(
            "Selected natural source bundle exceeds the full reviewer input limit",
            detail_code="natural_reviewer_capacity",
        )
    return tokens


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
    max_output_tokens: int = 1024,
) -> tuple[NaturalReviewerResult, PreparedNaturalReview]:
    """Bind one visible candidate and source bundle to one validated decision."""

    binding_map = build_natural_binding_map(
        current_user_message=current_user_message,
        source_messages=source_messages,
        facts=facts,
        entities=entities,
    )
    prepared: PreparedNaturalReview | None = None

    def prepare(decision: NaturalReviewDecision) -> PreparedNaturalReview:
        nonlocal prepared
        prepared = prepare_natural_memory_review(
            decision=decision,
            subject_id=subject_id,
            current_user_message=current_user_message,
            available_messages=source_messages,
            facts=facts,
            entities=entities,
            candidate_reply=candidate_reply,
            binding_map=binding_map,
        )
        return prepared

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
        max_output_tokens=max_output_tokens,
        observe_request=evidence.capture_reviewer_request if evidence else None,
        observe_decision=evidence.capture_reviewer_decision if evidence else None,
        validate_decision=prepare,
        binding_map=binding_map,
    )
    if prepared is None:
        raise RuntimeValidationError("Natural review was not prepared")
    return result, prepared
