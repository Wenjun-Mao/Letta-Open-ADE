"""Temporary HTTP fault mechanics, without a real provider or native Memory."""

import asyncio
import hashlib
import json
import time
from uuid import uuid4

import httpx
import pytest

from ..fault_proxy import ProxyConfig, create_app
from ..operations import Lease, create_record


AUTH = {"Authorization": "Bearer fault-control"}


def config(root):
    now = int(time.time())
    activation = root / "activation"
    lease = Lease(
        "ade-hindsight-integration-fault-test",
        str(uuid4()),
        "a" * 40,
        now - 1,
        now + 3600,
        now + 7200,
        "/mnt/projects",
        (),
    )
    lease.save(activation)
    create_record(
        activation / "checks/001.json",
        {
            "time": time.time(),
            "activation_id": lease.activation_id,
            "source_revision": lease.source_revision,
            "issues": [],
        },
    )
    return ProxyConfig(activation, root / "records", "fault-control")


def plan(conversation, mode, target="router_chat"):
    return {
        "id": str(uuid4()),
        "conversation_id": conversation,
        "target": target,
        "mode": mode,
        "hold_seconds": 3,
    }


async def matched(client, identity, *, received=False):
    for _ in range(100):
        value = (await client.get(f"/control/rules/{identity}", headers=AUTH)).json()
        if value["matched"] and (not received or "upstream_status" in value["outcome"]):
            return value
        await asyncio.sleep(0.001)
    raise AssertionError("Controlled fault did not match")


def test_idle_forwarding_preserves_bytes_headers_and_correlation_without_recording_secrets(
    tmp_path,
):
    async def check():
        sent = []

        def upstream(request):
            sent.append(request)
            return httpx.Response(
                200,
                headers={"X-Model-Router-Request-Id": "router-original"},
                json={"ok": True},
            )

        cfg = config(tmp_path)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(upstream)
        ) as provider:
            app = create_app(cfg, client=provider)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://proxy"
            ) as client:
                raw = b' {"messages": [{"role":"user", "content":"unchanged"}]} '
                response = await client.post(
                    "/router/v1/chat/completions",
                    content=raw,
                    headers={
                        "Authorization": "Bearer router-secret",
                        "Content-Type": "application/json",
                        "X-ADE-Run-Id": "actual-run",
                    },
                )
                assert response.status_code == 200
                assert (
                    response.headers["X-Model-Router-Request-Id"] == "router-original"
                )
                assert (
                    sent[0].content == raw
                    and sent[0].headers["X-ADE-Run-Id"] == "actual-run"
                )
                assert (
                    str(sent[0].url) == "http://model-router:8010/v1/chat/completions"
                )
                response = await client.patch(
                    "/hindsight/v1/default/banks/owned/config",
                    content=b'{"updates":{}}',
                    headers={"Authorization": "Bearer native-secret"},
                )
                assert response.status_code == 200
                assert (
                    sent[1].method == "PATCH" and sent[1].content == b'{"updates":{}}'
                )
                assert not list(cfg.record_root.glob("*.json"))
                assert (
                    await client.post(
                        "/control/rules", json=plan(str(uuid4()), "fail_before_send")
                    )
                ).status_code == 401

    asyncio.run(check())


@pytest.mark.parametrize(
    "mode", ["fail_before_send", "hold_before_send", "hold_after_response"]
)
def test_fault_is_one_shot_conversation_scoped_and_does_not_block_unrelated_calls(
    tmp_path, mode
):
    async def check():
        sent = []

        def upstream(request):
            sent.append(request.content)
            return httpx.Response(200, json={"ok": True})

        cfg = config(tmp_path)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(upstream)
        ) as provider:
            app = create_app(cfg, client=provider)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://proxy"
            ) as client:
                conversation = str(uuid4())
                fault = plan(conversation, mode)
                assert (
                    await client.post("/control/rules", headers=AUTH, json=fault)
                ).status_code == 200
                assert (
                    await client.post("/control/rules", headers=AUTH, json=fault)
                ).status_code == 200
                assert (
                    await client.post(
                        "/control/rules",
                        headers=AUTH,
                        json=dict(fault, mode="lose_ack"),
                    )
                ).status_code == 409
                task = asyncio.create_task(
                    client.post(
                        "/router/v1/chat/completions",
                        content=b"original-body",
                        headers={"X-ADE-Conversation-Id": conversation},
                    )
                )
                await matched(
                    client, fault["id"], received=mode == "hold_after_response"
                )
                unrelated = await client.post(
                    "/router/v1/chat/completions",
                    content=b"other",
                    headers={"X-ADE-Conversation-Id": str(uuid4())},
                )
                assert unrelated.status_code == 200
                if mode != "fail_before_send":
                    assert not task.done()
                    assert (
                        await client.post(
                            f"/control/rules/{fault['id']}/release", headers=AUTH
                        )
                    ).status_code == 200
                response = await task
                assert response.status_code == (
                    400 if mode == "fail_before_send" else 200
                )
                assert (
                    await client.post(
                        "/router/v1/chat/completions",
                        content=b"second",
                        headers={"X-ADE-Conversation-Id": conversation},
                    )
                ).status_code == 200
                assert sent.count(b"original-body") == (
                    0 if mode == "fail_before_send" else 1
                )

    asyncio.run(check())


def test_lost_native_ack_records_actual_acceptance_and_immutable_operation_without_raw_source(
    tmp_path,
):
    async def check():
        sent = []

        def upstream(request):
            sent.append(request.content)
            return httpx.Response(
                200, json={"operation_id": operation, "status": "pending"}
            )

        cfg = config(tmp_path)
        conversation, operation = str(uuid4()), str(uuid4())
        raw = json.dumps(
            {
                "operation_id": operation,
                "items": [
                    {
                        "content": "PRIVATE-SYNTHETIC-SOURCE",
                        "metadata": {"conversation_id": conversation},
                    }
                ],
            }
        ).encode()
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(upstream)
        ) as provider:
            app = create_app(cfg, client=provider)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://proxy"
            ) as client:
                fault = plan(conversation, "lose_ack", "memory_retain")
                await client.post("/control/rules", headers=AUTH, json=fault)
                response = await client.post(
                    "/hindsight/v1/default/banks/owned/memories",
                    content=raw,
                    headers={"Authorization": "Bearer native-secret"},
                )
                assert response.status_code == 503
                status = await matched(client, fault["id"], received=True)
                assert status["outcome"]["operation_id"] == operation
                assert status["outcome"]["upstream_status"] == 200
                assert (
                    status["outcome"]["request_sha256"]
                    == hashlib.sha256(raw).hexdigest()
                )
                assert sent == [raw]
                records = "".join(
                    path.read_text() for path in cfg.record_root.glob("*.json")
                )
                assert "PRIVATE-SYNTHETIC-SOURCE" not in records
                assert "native-secret" not in records and "fault-control" not in records

    asyncio.run(check())


def test_closed_activation_cannot_release_held_work_into_upstream(tmp_path):
    async def check():
        sent = []
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: sent.append(request) or httpx.Response(200, json={})
            )
        ) as provider:
            cfg = config(tmp_path)
            app = create_app(cfg, client=provider)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://proxy"
            ) as client:
                conversation = str(uuid4())
                fault = plan(conversation, "hold_before_send")
                await client.post("/control/rules", headers=AUTH, json=fault)
                task = asyncio.create_task(
                    client.post(
                        "/router/v1/chat/completions",
                        headers={"X-ADE-Conversation-Id": conversation},
                        json={},
                    )
                )
                await matched(client, fault["id"])
                create_record(cfg.activation_root / "closed.json", {})
                assert (
                    await client.post(
                        f"/control/rules/{fault['id']}/release", headers=AUTH
                    )
                ).status_code == 503
                assert (await task).status_code == 503
                assert not sent

    asyncio.run(check())
