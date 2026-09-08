from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from workflows.evals.agent_runtime_acceptance.client import (
    ApiResponseError,
    RuntimeClient,
    RuntimeClientError,
    SseEvent,
    parse_sse,
)


def test_evaluation_session_lifecycle_uses_only_supported_routes() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if (
            request.url.path == "/api/v3/evaluation-sessions"
            and request.method == "POST"
        ):
            return httpx.Response(
                201,
                json={
                    "session_id": "session-1",
                    "agent_definition": {"id": "definition-1", "deployments": []},
                    "memory_subject": {"id": "subject-1"},
                    "conversation": {"id": "conversation-1"},
                },
            )
        if request.url.path.endswith("/turns"):
            return httpx.Response(
                202,
                json={
                    "run_id": "run-1",
                    "status": "pending",
                    "events_url": "/api/v3/runs/run-1/events",
                    "idempotent_replay": False,
                },
            )
        if request.url.path.endswith("/state"):
            return httpx.Response(
                200,
                json={
                    "conversation": {"id": "conversation-1", "messages": []},
                    "memory_subject": {"id": "subject-1"},
                    "memories": {"facts": []},
                    "latest_run": {"id": "run-1"},
                },
            )
        if request.url.path == "/api/v3/evaluation-sessions/conversation-1":
            return httpx.Response(
                200,
                json={
                    "conversation_id": "conversation-1",
                    "already_purged": False,
                    "deleted_counts": {"conversations": 1},
                },
            )
        raise AssertionError(f"unexpected route: {request.method} {request.url.path}")

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = RuntimeClient("https://ade.test", "operator-key", client=raw)
            session = await client.create_evaluation_session(
                idempotency_key="case-a",
                title="Case A",
                model_key="router::chat",
                reviewer_model_key="router::reviewer",
                embedding_model_key="router::embedding",
                prompt_key="chat_prompt",
                persona_key="chat_persona",
                tool_names=("search_memory",),
                subject_external_key="subject-a",
                subject_display_name="Subject A",
            )
            await client.accept_turn(
                session["conversation"]["id"],
                "hello",
                "turn-a",
                timeout_seconds=180,
                retry_count=0,
            )
            state = await client.get_evaluation_session_state("conversation-1")
            purge = await client.purge_evaluation_session("conversation-1")

        assert state["memories"] == {"facts": []}
        assert purge["deleted_counts"] == {"conversations": 1}

    asyncio.run(scenario())

    create_request = requests[0]
    assert create_request.headers["authorization"] == "Bearer operator-key"
    assert json.loads(create_request.content) == {
        "idempotency_key": "case-a",
        "title": "Case A",
        "model_key": "router::chat",
        "reviewer_model_key": "router::reviewer",
        "embedding_model_key": "router::embedding",
        "prompt_key": "chat_prompt",
        "persona_key": "chat_persona",
        "tool_names": ["search_memory"],
        "subject_external_key": "subject-a",
        "subject_display_name": "Subject A",
    }
    assert all(
        "/agent-definitions" not in str(request.url)
        and "/memory-subjects" not in str(request.url)
        for request in requests
    )


def test_shared_session_binding_omits_new_resource_configuration() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            201,
            json={
                "session_id": "session-2",
                "agent_definition": {"id": "definition-1", "deployments": []},
                "memory_subject": {"id": "subject-1"},
                "conversation": {"id": "conversation-2"},
            },
        )

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = RuntimeClient("https://ade.test", "key", client=raw)
            await client.create_evaluation_session(
                idempotency_key="case-b",
                title="Case B",
                agent_definition_id="definition-1",
                memory_subject_id="subject-1",
            )

    asyncio.run(scenario())
    assert captured == {
        "idempotency_key": "case-b",
        "title": "Case B",
        "agent_definition_id": "definition-1",
        "memory_subject_id": "subject-1",
    }


def test_sse_normalization_and_origin_protection() -> None:
    events = list(
        parse_sse(
            [
                "id: 4\n",
                "event: model.response\n",
                'data: {"run_id":"run-1",\n',
                'data: "sequence":4,"type":"model.response","payload":{}}\n\n',
            ]
        )
    )
    assert events == [
        SseEvent(
            event_id="4",
            event_type="model.response",
            data={
                "run_id": "run-1",
                "sequence": 4,
                "type": "model.response",
                "payload": {},
            },
        )
    ]

    async def scenario() -> None:
        client = RuntimeClient("https://ade.test", "operator-key")
        try:
            with pytest.raises(RuntimeClientError, match="configured API origin"):
                async for _event in client.stream_events(
                    "https://attacker.test/api/v3/runs/run-1/events"
                ):
                    pass
        finally:
            await client.aclose()

    asyncio.run(scenario())


def test_http_errors_keep_a_safe_status_and_code() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": {"code": "conversation_busy"}})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = RuntimeClient("https://ade.test", "key", client=raw)
            with pytest.raises(ApiResponseError) as raised:
                await client.get_run("run-1")
        assert raised.value.status_code == 409
        assert raised.value.code == "conversation_busy"

    asyncio.run(scenario())
