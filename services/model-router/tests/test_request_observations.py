"""Wire capture, private export and closed-lease behavior through the real Router."""

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import time

import httpx
import pytest

import model_router.app as router_app
import model_router.forwarding as forwarding
import model_router.request_observations as observations
from model_router.catalog import RoutedModel
from model_router.settings import ModelRouterSettings, RouterSourceConfig


MODEL = "deepseek::deepseek-flash"
AUTH = {"Authorization": "Bearer router-key"}


def lease_files(root: Path, *, expired=False):
    root.mkdir()
    now = int(time.time())
    value = {
        "activation_id": "7f186710-a26f-49b2-8496-61a7c60ecb2d",
        "source_revision": "a" * 40,
        "started_at": now - 60,
        "dispatch_deadline": now - 1 if expired else now + 3_600,
        "expires_at": now + 7_200,
    }
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    (root / "lease.json").write_bytes(encoded)
    (root / "lease.seal.json").write_text(
        json.dumps({"sha256": hashlib.sha256(encoded).hexdigest()})
    )
    (root / "checks").mkdir()
    (root / "checks" / "0001.json").write_text(
        json.dumps(
            {
                "time": time.time(),
                "issues": [],
                "activation_id": value["activation_id"],
                "source_revision": value["source_revision"],
            }
        )
    )


def configure(monkeypatch, tmp_path, *, activation_root=""):
    monkeypatch.setenv("MODEL_ROUTER_API_KEY", "router-key")
    monkeypatch.setenv("UPSTREAM_TEST_SECRET", "wire-secret")
    source = RouterSourceConfig(
        id="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        adapter="deepseek_openai",
        enabled_for=["agent_studio"],
        api_key_env="UPSTREAM_TEST_SECRET",
    )
    model = RoutedModel(
        router_model_id=MODEL,
        source_id="deepseek",
        source_label="DeepSeek",
        source_kind="openai-compatible",
        source_adapter="deepseek_openai",
        source_base_url=source.base_url,
        module_visibility=("agent_studio",),
        provider_model_id="deepseek-flash",
        model_type="llm",
        agent_studio_available=True,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode="json_object",
        thinking_default_enabled=True,
        reasoning_effort_default="high",
    )
    settings = ModelRouterSettings(
        _env_file=None,
        sources=[source],
        api_key="router-key",
        api_key_secret="",
        observation_root=str(tmp_path / "observations"),
        activation_root=activation_root,
    )
    monkeypatch.setattr(router_app, "get_settings", lambda: settings)
    monkeypatch.setattr(forwarding, "get_settings", lambda: settings)
    monkeypatch.setattr(observations, "get_settings", lambda: settings)
    monkeypatch.setattr(
        router_app,
        "catalog_service",
        SimpleNamespace(
            find_routed_model=lambda value: model if value == MODEL else None,
            source_config=lambda identity: source,
        ),
    )
    return settings


def exercise(monkeypatch, handler, scenario):
    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as upstream:
            monkeypatch.setattr(
                router_app.app.state, "upstream_client", upstream, raising=False
            )
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=router_app.app),
                base_url="http://router",
            ) as client:
                await scenario(client)

    asyncio.run(run())


def completion(**message):
    return httpx.Response(
        200,
        json={
            "id": "provider-1",
            "model": "DeepSeek-V4.1-Flash",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "无糖乌龙。",
                        **message,
                    },
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        },
    )


def test_capture_matches_final_sent_bytes_and_excludes_private_response_and_auth(
    monkeypatch, tmp_path
):
    settings = configure(monkeypatch, tmp_path)
    sent = []

    def provider(request):
        sent.append(request.content)
        assert request.headers["Authorization"] == "Bearer wire-secret"
        return completion(reasoning_content="private-model-reasoning")

    async def scenario(client):
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "替我挑杯茶。"}],
                "max_tokens": 0,
            },
            headers={
                **AUTH,
                "X-ADE-Run-Id": "run-a",
                "X-ADE-Observation-Role": "character",
            },
        )
        assert response.status_code == 200
        identity = response.headers["X-Model-Router-Request-Id"]
        record = (
            await client.get(f"/v1/router/observations/{identity}", headers=AUTH)
        ).json()
        assert record["request"]["raw_body_utf8"].encode() == sent[0]
        assert (
            record["request"]["request_sha256"] == hashlib.sha256(sent[0]).hexdigest()
        )
        assert record["request"]["body"]["model"] == "deepseek-flash"
        assert record["request"]["body"]["thinking"] == {"type": "enabled"}
        assert record["request"]["body"]["reasoning_effort"] == "high"
        assert "max_tokens" not in record["request"]["body"]
        assert record["request"]["metadata"] == {
            "run_id": "run-a",
            "role": "character",
            "router_model": MODEL,
        }
        assert (
            record["outcome"]["visible_response"]["choices"][0]["message"]["content"]
            == "无糖乌龙。"
        )
        assert (
            await client.get(f"/v1/router/observations/{identity}")
        ).status_code == 401
        index = (
            await client.get("/v1/router/observations?run_id=run-a", headers=AUTH)
        ).json()
        assert index["total"] == 1
        assert index["items"][0]["request_id"] == identity

    exercise(monkeypatch, provider, scenario)
    contents = "\n".join(
        path.read_text() for path in Path(settings.observation_root).glob("*.json")
    )
    assert "wire-secret" not in contents
    assert "router-key" not in contents
    assert "private-model-reasoning" not in contents


def test_private_input_is_sent_unchanged_but_cannot_claim_a_complete_capture(
    monkeypatch, tmp_path
):
    configure(monkeypatch, tmp_path)

    def provider(request):
        assert (
            json.loads(request.content)["messages"][1]["reasoning_content"]
            == "private-input"
        )
        return completion()

    async def scenario(client):
        response = await client.post(
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": "tea"},
                    {
                        "role": "assistant",
                        "content": "",
                        "reasoning_content": "private-input",
                    },
                ],
            },
        )
        assert response.status_code == 200
        record = (
            await client.get(
                "/v1/router/observations/"
                + response.headers["X-Model-Router-Request-Id"],
                headers=AUTH,
            )
        ).json()["request"]
        assert record["input_complete"] is False
        assert record["limitation"] == "private_fields_excluded"
        assert "raw_body_utf8" not in record
        assert "body" not in record

    exercise(monkeypatch, provider, scenario)


@pytest.mark.parametrize("closed", ["expired", "marker", "tampered", "stale-heartbeat"])
def test_expired_closed_or_changed_activation_never_reaches_provider(
    monkeypatch, tmp_path, closed
):
    root = tmp_path / "activation"
    lease_files(root, expired=closed == "expired")
    if closed == "marker":
        (root / "closed.json").write_text("{}")
    if closed == "tampered":
        (root / "lease.json").write_text("{}")
    if closed == "stale-heartbeat":
        heartbeat = json.loads((root / "checks/0001.json").read_text())
        heartbeat["time"] -= 120
        (root / "checks/0001.json").write_text(json.dumps(heartbeat))
    configure(monkeypatch, tmp_path, activation_root=str(root))

    def provider(request):
        pytest.fail("Closed activation must not dispatch")

    async def scenario(client):
        response = await client.post(
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "activation_unavailable_or_closed"

    exercise(monkeypatch, provider, scenario)


def test_transport_failure_is_recorded_and_correlated_without_retry(
    monkeypatch, tmp_path
):
    configure(monkeypatch, tmp_path)
    attempts = []

    def provider(request):
        attempts.append(request)
        raise httpx.ConnectError("injected network failure", request=request)

    async def scenario(client):
        response = await client.post(
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "test"}],
            },
        )
        assert response.status_code == 502
        identity = response.headers["X-Model-Router-Request-Id"]
        record = (
            await client.get(f"/v1/router/observations/{identity}", headers=AUTH)
        ).json()
        assert record["outcome"]["status"] == "transport_failed"
        assert record["outcome"]["error_type"] == "ConnectError"

    exercise(monkeypatch, provider, scenario)
    assert len(attempts) == 1


def test_tool_continuation_keeps_both_actual_requests_and_visible_tool_response(
    monkeypatch, tmp_path
):
    configure(monkeypatch, tmp_path)
    tool = {
        "id": "call-1",
        "type": "function",
        "function": {"name": "search_memory", "arguments": "{}"},
    }
    sent = []

    def provider(request):
        sent.append(request.content)
        return (
            completion(content=None, tool_calls=[tool])
            if len(sent) == 1
            else completion()
        )

    async def scenario(client):
        messages = [{"role": "user", "content": "记得我喝什么吗？"}]
        headers = {**AUTH, "X-ADE-Run-Id": "run-tools", "X-ADE-Attempt-Id": "attempt-1"}
        first = await client.post(
            "/v1/chat/completions",
            headers=headers,
            json={"model": MODEL, "messages": messages},
        )
        first_message = first.json()["choices"][0]["message"]
        second = await client.post(
            "/v1/chat/completions",
            headers=headers,
            json={
                "model": MODEL,
                "messages": [
                    *messages,
                    first_message,
                    {"role": "tool", "tool_call_id": "call-1", "content": "乌龙"},
                ],
            },
        )
        assert second.status_code == 200
        index = (
            await client.get("/v1/router/observations?run_id=run-tools", headers=AUTH)
        ).json()
        assert index["total"] == 2
        records = [
            (
                await client.get(
                    f"/v1/router/observations/{item['request_id']}", headers=AUTH
                )
            ).json()
            for item in index["items"]
        ]
        assert [
            record["request"]["raw_body_utf8"].encode() for record in records
        ] == sent
        assert records[0]["outcome"]["visible_response"]["choices"][0]["message"][
            "tool_calls"
        ] == [tool]
        assert all(record["request"]["input_complete"] for record in records)

    exercise(monkeypatch, provider, scenario)


@pytest.mark.parametrize(
    "field", ["body", "raw_body_utf8", "request_sha256", "request_id"]
)
def test_private_export_rejects_corrupt_hash_body_or_identity(
    monkeypatch, tmp_path, field
):
    settings = configure(monkeypatch, tmp_path)

    async def scenario(client):
        response = await client.post(
            "/v1/chat/completions",
            headers=AUTH,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "original"}],
            },
        )
        identity = response.headers["X-Model-Router-Request-Id"]
        path = Path(settings.observation_root) / f"{identity}.request.json"
        record = json.loads(path.read_bytes())
        record[field] = {} if field == "body" else "changed"
        path.write_text(json.dumps(record))
        assert (
            await client.get(f"/v1/router/observations/{identity}", headers=AUTH)
        ).status_code == 503
        assert (
            await client.get("/v1/router/observations", headers=AUTH)
        ).status_code == 503

    exercise(monkeypatch, lambda request: completion(), scenario)
