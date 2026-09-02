from __future__ import annotations

import asyncio
import json

import httpx

from workflows.evals.agent_runtime_parity.clients import (
    LegacyV2Client,
    NativeV3Client,
)


def test_legacy_adapter_uses_only_public_v2_message_contract() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path.endswith("/messages"):
            return httpx.Response(200, json={"sequence": [], "memory_diff": {}})
        if request.url.path.endswith("/archive"):
            return httpx.Response(200, json={"archived": True})
        if request.url.path.endswith("/purge"):
            return httpx.Response(200, json={"ok": True})
        raise AssertionError(request.url.path)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = LegacyV2Client("https://legacy.test", "key", client=raw)
            await client.send_message(
                agent_id="agent-1",
                message="hello",
                timeout_seconds=180,
                retry_count=0,
            )
            await client.archive_agent("agent-1")
            await client.purge_agent("agent-1")

    asyncio.run(scenario())
    message = seen[0]
    assert message.url.path == "/api/v2/agent-studio/agents/agent-1/messages"
    assert json.loads(message.content) == {
        "message": "hello",
        "timeout_seconds": 180,
        "retry_count": 0,
    }
    assert all(request.headers["authorization"] == "Bearer key" for request in seen)


def test_native_adapter_uses_agent_studio_session_turn_and_event_contracts() -> None:
    seen: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/v3/agent-studio/sessions":
            return httpx.Response(201, json={"session_id": "conversation-1"})
        if request.url.path == "/api/v3/agent-studio/sessions/conversation-1":
            return httpx.Response(200, json={"conversation": {"archived_at": "now"}})
        if request.url.path == "/api/v3/agent-studio/sessions/conversation-1/restore":
            return httpx.Response(200, json={"conversation": {"archived_at": None}})
        if request.url.path == "/api/v3/conversations/conversation-1/turns":
            return httpx.Response(
                202,
                json={
                    "run_id": "run-1",
                    "status": "pending",
                    "events_url": "/api/v3/runs/run-1/events",
                },
            )
        if request.url.path == "/api/v3/runs/run-1/events":
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=(
                    b"event: run.started\n"
                    b'data: {"sequence":1,"type":"run.started","attempt":1}\n\n'
                    b"event: run.completed\n"
                    b'data: {"sequence":2,"type":"run.completed","attempt":1}\n\n'
                ),
            )
        if request.url.path == "/api/v3/runs/run-1":
            return httpx.Response(
                200,
                json={
                    "id": "run-1",
                    "status": "succeeded",
                    "timeout_seconds": 180,
                    "retry_count": 0,
                    "attempt_count": 1,
                },
            )
        raise AssertionError(request.url.path)

    async def scenario() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as raw:
            client = NativeV3Client("https://native.test", "key", client=raw)
            await client.create_agent_studio_session(
                idempotency_key="parity-test-session",
                definition_key="parity-test-definition",
                name="Parity",
                subject_external_key="parity-test-subject",
                subject_display_name="Parity subject",
                title="Parity conversation",
                model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
                reviewer_model_key="dgx_vllm::qwen3.6-35b-a3b-fp8",
                embedding_model_key="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                prompt_key="chat_v20260516",
                persona_key="chat_linxiaotang",
            )
            accepted = await client.accept_turn(
                conversation_id="conversation-1",
                content="hello",
                idempotency_key="parity-test-turn",
                timeout_seconds=180,
                retry_count=0,
            )
            run, events = await client.await_terminal(accepted, timeout_seconds=210)
            await client.archive_agent_studio_session("conversation-1")
            await client.restore_agent_studio_session("conversation-1")
        assert run["status"] == "succeeded"
        assert [event.event_type for event in events] == [
            "run.started",
            "run.completed",
        ]

    asyncio.run(scenario())
    session = json.loads(seen[0].content)
    assert session["new_definition"]["prompt_key"] == "chat_v20260516"
    assert session["new_definition"]["persona_key"] == "chat_linxiaotang"
    assert session["new_subject"]["external_key"] == "parity-test-subject"
    turn = json.loads(seen[1].content)
    assert turn["timeout_seconds"] == 180
    assert turn["retry_count"] == 0
    assert seen[-2].method == "DELETE"
    assert seen[-1].url.path.endswith("/restore")
