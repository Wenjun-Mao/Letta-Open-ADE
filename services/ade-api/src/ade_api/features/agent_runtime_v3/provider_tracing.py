from __future__ import annotations

import asyncio
import re
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .router_transport import RouterRequestError


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
        self._events.append(
            NormalizedTraceEvent(
                event_type="model.response.completed",
                payload={
                    "request_id": request_id,
                    "provider": "model_router",
                    "operation": operation,
                    "stage": stage,
                    "request_number": request_number,
                    "provider_request_id": _provider_request_id(response),
                    "latency_ms": _elapsed_ms(started_at),
                },
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
