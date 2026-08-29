from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from workflows.evals.agent_runtime_v3_acceptance.client import (
    ApiResponseError,
    RuntimeV3Client,
    SseEvent,
    parse_sse,
)


def test_authenticated_resource_lifecycle_and_sse_normalization() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v3/agent-definitions":
            return httpx.Response(201, json={"id": "definition-1", "deployments": []})
        if request.url.path == "/api/v3/memory-subjects":
            return httpx.Response(201, json={"id": "subject-1"})
        if request.url.path == "/api/v3/conversations":
            return httpx.Response(201, json={"id": "conversation-1"})
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
        if request.url.path.endswith("/events"):
            body = (
                b": heartbeat\n\n"
                b'id: 1\nevent: run.started\ndata: {"run_id":"run-1","sequence":1,"type":"run.started","payload":{}}\n\n'
                b'id: 2\nevent: run.completed\ndata: {"run_id":"run-1","sequence":2,"type":"run.completed","payload":{}}\n\n'
            )
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=body
            )
        if request.url.path == "/api/v3/runs/run-1":
            return httpx.Response(
                200,
                json={"id": "run-1", "status": "succeeded", "attempt_count": 1},
            )
        raise AssertionError(request.url.path)

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as raw:
            client = RuntimeV3Client("https://ade.test", "operator-key", client=raw)
            definition = await client.create_definition(
                definition_key="acceptance-a",
                name="Acceptance",
                model_key="chat",
                reviewer_model_key="reviewer",
                embedding_model_key="embedding",
            )
            subject = await client.create_subject("acceptance-a", "Acceptance")
            conversation = await client.create_conversation(
                definition["id"], subject["id"]
            )
            accepted = await client.accept_turn(
                conversation["id"],
                "hello",
                "turn-key",
                timeout_seconds=180,
                retry_count=0,
            )
            events = [
                event async for event in client.stream_events(accepted["events_url"])
            ]
            run = await client.get_run(accepted["run_id"])
        assert [event.event_type for event in events] == [
            "run.started",
            "run.completed",
        ]
        assert run["status"] == "succeeded"

    asyncio.run(scenario())
    assert all(
        request.headers["authorization"] == "Bearer operator-key"
        for request in requests
    )


def test_sse_parser_joins_multiline_data_and_rejects_non_object() -> None:
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


def test_http_errors_preserve_status_and_safe_detail() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"detail": {"code": "conversation_busy"}})

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = RuntimeV3Client("https://ade.test", "key", client=raw)
            with pytest.raises(ApiResponseError) as raised:
                await client.get_run("run-1")
        assert raised.value.status_code == 409
        assert raised.value.code == "conversation_busy"

    asyncio.run(scenario())


def test_fake_transport_covers_idempotency_concurrency_and_cancellation() -> None:
    seen_keys: set[str] = set()
    active = False

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active
        if request.url.path.endswith("/turns"):
            body = json.loads(request.content)
            key = body["idempotency_key"]
            if key in seen_keys:
                return httpx.Response(
                    202,
                    json={
                        "run_id": "run-1",
                        "status": "pending",
                        "events_url": "/api/v3/runs/run-1/events",
                        "idempotent_replay": True,
                    },
                )
            if active:
                return httpx.Response(
                    409, json={"detail": {"code": "conversation_busy"}}
                )
            active = True
            seen_keys.add(key)
            return httpx.Response(
                202,
                json={
                    "run_id": "run-1",
                    "status": "pending",
                    "events_url": "/api/v3/runs/run-1/events",
                    "idempotent_replay": False,
                },
            )
        if request.url.path.endswith("/cancel"):
            active = False
            return httpx.Response(200, json={"id": "run-1", "status": "cancelled"})
        raise AssertionError(request.url.path)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = RuntimeV3Client("https://ade.test", "key", client=raw)
            first = await client.accept_turn(
                "conversation-1", "hello", "key-a", timeout_seconds=180, retry_count=0
            )
            replay = await client.accept_turn(
                "conversation-1", "hello", "key-a", timeout_seconds=180, retry_count=0
            )
            with pytest.raises(ApiResponseError) as raised:
                await client.accept_turn(
                    "conversation-1",
                    "other",
                    "key-b",
                    timeout_seconds=180,
                    retry_count=0,
                )
            cancelled = await client.cancel_run(first["run_id"])
        assert replay["idempotent_replay"] is True
        assert raised.value.code == "conversation_busy"
        assert cancelled["status"] == "cancelled"

    asyncio.run(scenario())


def test_terminal_wait_times_out_when_sse_never_finishes() -> None:
    async def never_finishes(_url: str):
        await asyncio.sleep(60)
        yield None

    async def scenario() -> None:
        client = RuntimeV3Client("https://ade.test", "key")
        client.stream_events = never_finishes  # type: ignore[method-assign]
        with pytest.raises(Exception, match="did not finish"):
            await client.await_terminal(
                {"run_id": "run-1", "events_url": "/api/v3/runs/run-1/events"},
                timeout_seconds=0.001,
            )
        await client.aclose()

    asyncio.run(scenario())
