from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

import pytest

from ade_api.features.agent_runtime_v3.provider_tracing import (
    AttemptTrace,
    TracedRouterTransport,
)
from ade_api.features.agent_runtime_v3.router_transport import RouterRequestError


class _StubTransport:
    def __init__(
        self,
        operation: Callable[[], Awaitable[dict[str, Any]]],
    ) -> None:
        self.operation = operation

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self.operation()

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self.operation()

    async def catalog(self, *, timeout_seconds: float) -> dict[str, Any]:
        return await self.operation()


def _traced_transport(
    transport: _StubTransport,
    *,
    stage: str = "conversation",
) -> tuple[AttemptTrace, TracedRouterTransport]:
    trace = AttemptTrace(attempt=2)
    return trace, trace.transport(
        transport,
        stage=stage,
        model_fingerprint="f" * 64,
    )


def test_provider_failure_records_started_and_failed_events_without_raw_data() -> None:
    async def fail() -> dict[str, Any]:
        raise RouterRequestError(
            "secret provider response body",
            retryable=True,
            status_code=503,
            error_code="http_503",
        )

    trace, transport = _traced_transport(_StubTransport(fail))

    with pytest.raises(RouterRequestError, match="secret provider"):
        asyncio.run(
            transport.chat_completion(
                {
                    "model": "source::model",
                    "messages": [{"role": "user", "content": "private prompt"}],
                },
                timeout_seconds=12.5,
            )
        )

    events = trace.normalized_events()
    assert [event.event_type for event in events] == [
        "model.request.started",
        "model.request.failed",
    ]
    started, failed = events
    assert started.payload == {
        "request_id": started.payload["request_id"],
        "provider": "model_router",
        "operation": "chat_completion",
        "stage": "conversation",
        "request_number": 1,
        "model_key": "source::model",
        "model_fingerprint": "f" * 64,
        "timeout_seconds": 12.5,
    }
    assert failed.payload["request_id"] == started.payload["request_id"]
    assert failed.payload["error_code"] == "http_503"
    assert failed.payload["status_code"] == 503
    assert failed.payload["retryable"] is True
    rendered = repr(events)
    assert "private prompt" not in rendered
    assert "secret provider response body" not in rendered


def test_provider_success_records_provider_request_identity_and_stage_counter() -> None:
    responses = iter(
        [
            {"id": "provider-1", "choices": []},
            {"id": "provider-2", "choices": []},
        ]
    )

    async def succeed() -> dict[str, Any]:
        return next(responses)

    trace, transport = _traced_transport(_StubTransport(succeed))

    asyncio.run(
        transport.chat_completion(
            {"model": "source::model", "messages": []}, timeout_seconds=10
        )
    )
    asyncio.run(
        transport.chat_completion(
            {"model": "source::model", "messages": []}, timeout_seconds=9
        )
    )

    events = trace.normalized_events()
    assert [event.event_type for event in events] == [
        "model.request.started",
        "model.response.completed",
        "model.request.started",
        "model.response.completed",
    ]
    assert events[0].payload["request_number"] == 1
    assert events[2].payload["request_number"] == 2
    assert events[1].payload["provider_request_id"] == "provider-1"
    assert events[3].payload["provider_request_id"] == "provider-2"


def test_cancelled_provider_request_gets_a_terminal_trace() -> None:
    async def cancel() -> dict[str, Any]:
        raise asyncio.CancelledError

    trace, transport = _traced_transport(_StubTransport(cancel), stage="reviewer")

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(
            transport.chat_completion(
                {"model": "source::reviewer", "messages": []},
                timeout_seconds=8,
            )
        )

    events = trace.normalized_events()
    assert [event.event_type for event in events] == [
        "model.request.started",
        "model.request.cancelled",
    ]
    assert events[-1].payload["error_code"] == "request_cancelled"


def test_each_runtime_stage_has_an_independent_request_counter() -> None:
    async def succeed() -> dict[str, Any]:
        return {"id": "provider", "data": []}

    trace = AttemptTrace(attempt=1)
    retrieval = trace.transport(_StubTransport(succeed), stage="retrieval_query")
    memory = trace.transport(_StubTransport(succeed), stage="memory_embeddings")

    asyncio.run(
        retrieval.embeddings(
            {"model": "source::embedding", "input": ["query"]}, timeout_seconds=2
        )
    )
    asyncio.run(
        memory.embeddings(
            {"model": "source::embedding", "input": ["fact"]}, timeout_seconds=2
        )
    )

    started = [
        event
        for event in trace.normalized_events()
        if event.event_type == "model.request.started"
    ]
    assert [
        (event.payload["stage"], event.payload["request_number"]) for event in started
    ] == [
        ("retrieval_query", 1),
        ("memory_embeddings", 1),
    ]


def test_provider_trace_rejects_unbounded_identifiers_and_error_codes() -> None:
    async def unsafe_success() -> dict[str, Any]:
        return {"id": "private\nresponse-body", "choices": []}

    success_trace, success_transport = _traced_transport(_StubTransport(unsafe_success))
    asyncio.run(
        success_transport.chat_completion(
            {"model": "source::model", "messages": []}, timeout_seconds=2
        )
    )

    async def unsafe_failure() -> dict[str, Any]:
        raise RouterRequestError(
            "private response body",
            retryable=False,
            error_code="private response body!",
        )

    failure_trace, failure_transport = _traced_transport(_StubTransport(unsafe_failure))
    with pytest.raises(RouterRequestError):
        asyncio.run(
            failure_transport.chat_completion(
                {"model": "source::model", "messages": []}, timeout_seconds=2
            )
        )

    assert success_trace.normalized_events()[-1].payload["provider_request_id"] is None
    assert (
        failure_trace.normalized_events()[-1].payload["error_code"]
        == "router_request_error"
    )
    assert "private response body" not in repr(failure_trace.normalized_events())
