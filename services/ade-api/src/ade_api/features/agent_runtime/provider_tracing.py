from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .router_transport import RouterRequestError
from .tool_policy import ToolRequirement


@dataclass(frozen=True)
class NormalizedTraceEvent:
    event_type: str
    payload: dict[str, Any]


class AttemptTrace:
    """Collect safe provider lifecycle evidence for one ADE-owned attempt."""

    def __init__(self, *, attempt: int) -> None:
        if attempt < 1:
            raise ValueError("attempt must be positive")
        self.attempt = attempt
        self._events: list[NormalizedTraceEvent] = []
        self._request_counts: dict[str, int] = defaultdict(int)

    def transport(
        self,
        transport: Any,
        *,
        stage: str,
        model_fingerprint: str | None = None,
    ) -> TracedRouterTransport:
        return TracedRouterTransport(
            transport=transport,
            trace=self,
            stage=_validate_stage(stage),
            model_fingerprint=model_fingerprint,
        )

    def normalized_events(self) -> tuple[NormalizedTraceEvent, ...]:
        return tuple(self._events)

    def record_tool_requirement_resolved(self, requirement: ToolRequirement) -> None:
        self._events.append(
            NormalizedTraceEvent(
                event_type="tool.requirement.resolved",
                payload=requirement.safe_payload(),
            )
        )

    def record_tool_requirement_satisfied(self, requirement: ToolRequirement) -> None:
        self._events.append(
            NormalizedTraceEvent(
                event_type="tool.requirement.satisfied",
                payload=requirement.safe_payload(),
            )
        )

    def record_tool_requirement_unmet(
        self, requirement: ToolRequirement, *, detail_code: str
    ) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,127}", detail_code):
            raise ValueError("detail_code must be a bounded snake-case identifier")
        self._events.append(
            NormalizedTraceEvent(
                event_type="tool.requirement.unmet",
                payload={
                    **requirement.safe_payload(),
                    "error_detail_code": detail_code,
                },
            )
        )

    def _start(
        self,
        *,
        operation: str,
        stage: str,
        model_key: str | None,
        model_fingerprint: str | None,
        timeout_seconds: float,
    ) -> tuple[str, int, float]:
        self._request_counts[stage] += 1
        request_number = self._request_counts[stage]
        request_id = str(uuid4())
        payload: dict[str, Any] = {
            "request_id": request_id,
            "provider": "model_router",
            "operation": operation,
            "stage": stage,
            "request_number": request_number,
            "model_key": model_key,
            "model_fingerprint": model_fingerprint,
            "timeout_seconds": round(float(timeout_seconds), 6),
        }
        self._events.append(
            NormalizedTraceEvent(event_type="model.request.started", payload=payload)
        )
        return request_id, request_number, time.monotonic()

    def _complete(
        self,
        *,
        request_id: str,
        operation: str,
        stage: str,
        request_number: int,
        response: dict[str, Any],
        started_at: float,
    ) -> None:
        payload = {
            "request_id": request_id,
            "provider": "model_router",
            "operation": operation,
            "stage": stage,
            "request_number": request_number,
            "provider_request_id": _provider_request_id(response),
            "latency_ms": _elapsed_ms(started_at),
        }
        payload.update(_safe_response_shape(operation, response))
        self._events.append(
            NormalizedTraceEvent(
                event_type="model.response.completed",
                payload=payload,
            )
        )

    def _fail(
        self,
        *,
        request_id: str,
        operation: str,
        stage: str,
        request_number: int,
        exc: Exception,
        started_at: float,
    ) -> None:
        retryable = bool(
            exc.retryable if isinstance(exc, RouterRequestError) else False
        )
        status_code = exc.status_code if isinstance(exc, RouterRequestError) else None
        retry_after_seconds = (
            exc.retry_after_seconds if isinstance(exc, RouterRequestError) else None
        )
        payload = {
            "request_id": request_id,
            "provider": "model_router",
            "operation": operation,
            "stage": stage,
            "request_number": request_number,
            "error_code": _safe_error_code(exc),
            "status_code": status_code,
            "retryable": retryable,
            "retry_after_seconds": retry_after_seconds,
            "latency_ms": _elapsed_ms(started_at),
        }
        self._events.append(
            NormalizedTraceEvent(event_type="model.request.failed", payload=payload)
        )

    def _cancel(
        self,
        *,
        request_id: str,
        operation: str,
        stage: str,
        request_number: int,
        started_at: float,
    ) -> None:
        self._events.append(
            NormalizedTraceEvent(
                event_type="model.request.cancelled",
                payload={
                    "request_id": request_id,
                    "provider": "model_router",
                    "operation": operation,
                    "stage": stage,
                    "request_number": request_number,
                    "error_code": "request_cancelled",
                    "latency_ms": _elapsed_ms(started_at),
                },
            )
        )


@dataclass(frozen=True)
class TracedRouterTransport:
    transport: Any
    trace: AttemptTrace
    stage: str
    model_fingerprint: str | None = None

    async def catalog(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        return await self._invoke(
            operation="catalog",
            model_key=None,
            timeout_seconds=timeout_seconds,
            call=lambda: self.transport.catalog(timeout_seconds=timeout_seconds),
        )

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._invoke(
            operation="chat_completion",
            model_key=_model_key(payload),
            timeout_seconds=timeout_seconds,
            call=lambda: self.transport.chat_completion(
                payload, timeout_seconds=timeout_seconds
            ),
        )

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._invoke(
            operation="embeddings",
            model_key=_model_key(payload),
            timeout_seconds=timeout_seconds,
            call=lambda: self.transport.embeddings(
                payload, timeout_seconds=timeout_seconds
            ),
        )

    async def _invoke(
        self,
        *,
        operation: str,
        model_key: str | None,
        timeout_seconds: float,
        call,
    ) -> dict[str, Any]:
        request_id, request_number, started_at = self.trace._start(
            operation=operation,
            stage=self.stage,
            model_key=model_key,
            model_fingerprint=self.model_fingerprint,
            timeout_seconds=timeout_seconds,
        )
        try:
            response = await call()
        except asyncio.CancelledError:
            self.trace._cancel(
                request_id=request_id,
                operation=operation,
                stage=self.stage,
                request_number=request_number,
                started_at=started_at,
            )
            raise
        except Exception as exc:
            self.trace._fail(
                request_id=request_id,
                operation=operation,
                stage=self.stage,
                request_number=request_number,
                exc=exc,
                started_at=started_at,
            )
            raise
        self.trace._complete(
            request_id=request_id,
            operation=operation,
            stage=self.stage,
            request_number=request_number,
            response=response,
            started_at=started_at,
        )
        return response


def _validate_stage(value: str) -> str:
    stage = str(value or "").strip()
    allowed = {
        "catalog",
        "compaction",
        "retrieval_query",
        "conversation",
        "tool_retrieval",
        "reviewer",
        "memory_embeddings",
    }
    if stage not in allowed:
        raise ValueError(f"unsupported provider trace stage: {stage}")
    return stage


def _model_key(payload: dict[str, Any]) -> str | None:
    value = payload.get("model")
    return str(value) if isinstance(value, str) and value else None


def _provider_request_id(response: dict[str, Any]) -> str | None:
    return safe_provider_request_id(response.get("id"))


def _safe_response_shape(operation: str, response: dict[str, Any]) -> dict[str, Any]:
    if operation != "chat_completion":
        return {}
    choices = response.get("choices")
    choices_state = _choices_state(response, choices)
    raw_choice_count = len(choices) if isinstance(choices, list) else 0
    choice = choices[0] if raw_choice_count and isinstance(choices[0], dict) else None
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    reasoning = message.get("reasoning_content") if isinstance(message, dict) else None
    tool_calls = message.get("tool_calls") if isinstance(message, dict) else None
    raw_tool_call_count = len(tool_calls) if isinstance(tool_calls, list) else 0
    finish_reason = choice.get("finish_reason") if isinstance(choice, dict) else None
    return {
        "response_shape_version": 1,
        "choices_state": choices_state,
        "choice_count": min(raw_choice_count, 32),
        "choice_count_overflow": raw_choice_count > 32,
        "message_state": _object_state(choice, "message", message),
        "content_state": _text_state(message, "content", content),
        "reasoning_content_state": _text_state(message, "reasoning_content", reasoning),
        "tool_calls_state": _list_state(message, "tool_calls", tool_calls),
        "tool_call_count": min(raw_tool_call_count, 32),
        "tool_call_count_overflow": raw_tool_call_count > 32,
        "finish_reason": _safe_finish_reason(finish_reason),
        "usage": _safe_usage(response.get("usage")),
    }


def _choices_state(response: dict[str, Any], value: object) -> str:
    if "choices" not in response or value is None:
        return "missing_or_null"
    if not isinstance(value, list):
        return "non_list"
    if not value:
        return "empty"
    return "present" if isinstance(value[0], dict) else "first_not_object"


def _object_state(container: object, key: str, value: object) -> str:
    if not isinstance(container, dict) or key not in container or value is None:
        return "missing_or_null"
    return "present" if isinstance(value, dict) else "non_object"


def _text_state(container: object, key: str, value: object) -> str:
    if not isinstance(container, dict) or key not in container or value is None:
        return "missing_or_null"
    if not isinstance(value, str):
        return "non_string"
    return "present" if value.strip() else "empty"


def _list_state(container: object, key: str, value: object) -> str:
    if not isinstance(container, dict) or key not in container or value is None:
        return "missing_or_null"
    if not isinstance(value, list):
        return "non_list"
    return "present" if value else "empty"


def _safe_finish_reason(value: object) -> str:
    if value is None:
        return "missing"
    if not isinstance(value, str):
        return "other"
    candidate = value.strip().casefold()
    allowed = {"stop", "length", "tool_calls", "content_filter", "function_call"}
    return candidate if candidate in allowed else "other"


def _safe_usage(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    allowed = {"prompt_tokens", "completion_tokens", "total_tokens"}
    return {
        key: min(item, 1_000_000_000)
        for key in allowed
        if isinstance((item := value.get(key)), int)
        and not isinstance(item, bool)
        and item >= 0
    }


def safe_provider_request_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,256}", candidate):
        return None
    return candidate


def _safe_error_code(exc: Exception) -> str:
    if isinstance(exc, RouterRequestError):
        return exc.error_code
    name = re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()
    return re.sub(r"[^a-z0-9_]+", "_", name).strip("_")[:128] or "provider_error"


def _elapsed_ms(started_at: float) -> float:
    return round(max(0.0, (time.monotonic() - started_at) * 1000.0), 3)
