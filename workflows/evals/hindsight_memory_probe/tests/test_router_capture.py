import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
import model_router.app as shared
from model_router.catalog import RouterCatalogService
from model_router.settings import ModelRouterSettings

from workflows.evals.hindsight_memory_probe.receipts import CaptureFailure, ReceiptStore
from workflows.evals.hindsight_memory_probe.router_entrypoint import build_app

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "


@pytest.fixture
def observed(tmp_path, monkeypatch):
    settings = ModelRouterSettings(
        _env_file=None,
        sources_file=str(ROOT / "config/sources.json"),
        model_profiles_file=str(ROOT / "config/model-profiles.json"),
        deployment_manifest_file=str(
            ROOT / "config/unqualified-deployment-manifest.absent.json"
        ),
        api_key="synthetic-router",
        api_key_secret="",
    )
    monkeypatch.setattr(
        settings.__class__, "resolve_api_key", lambda *_: "synthetic-router"
    )
    catalog = RouterCatalogService(settings_factory=lambda: settings)
    # Only discovery I/O is synthetic. Real config/profile/deployment-binding path is exercised.
    monkeypatch.setattr(
        catalog,
        "_fetch_models_payload",
        lambda source, **_: {
            "data": [
                {
                    "id": "deepseek-flash"
                    if source.id == "deepseek"
                    else "Qwen/Qwen3-Embedding-0.6B"
                }
            ]
        },
    )
    monkeypatch.setattr(shared, "get_settings", lambda: settings)
    monkeypatch.setattr(
        "workflows.evals.hindsight_memory_probe.router_entrypoint.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(shared, "catalog_service", catalog)
    phase = tmp_path / "phase.json"
    phase.write_text(json.dumps({"phase": "retain", "operation_id": "synthetic-op"}))
    store = ReceiptStore(tmp_path / "wire")
    requests = []

    def dispatch(request):
        raw = request.content
        payload = json.loads(raw)
        outbound = list(store.directory.glob("*.outbound.body.json"))
        assert any(p.read_bytes() == raw for p in outbound), (
            "durable actual bytes precede dispatch"
        )
        requests.append(payload)
        if request.url.path.endswith("embeddings"):
            body = {
                "data": [{"index": 0, "embedding": [0.0] * 1024}],
                "usage": {"prompt_tokens": 3},
            }
        else:
            body = {
                "choices": [
                    {
                        "message": {
                            "content": "synthetic",
                            "reasoning_content": "private-reasoning",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                "secret": "provider-secret",
            }
        return httpx.Response(200, json=body)

    original = shared.app.router.lifespan_context
    app = build_app(store, phase, httpx.MockTransport(dispatch))
    try:
        with TestClient(app) as client:
            yield client, store, phase, requests, catalog
    finally:
        shared.app.router.lifespan_context = original


def post(client, path, payload):
    return client.post(
        "/v1/" + path,
        headers={"Authorization": "Bearer synthetic-router"},
        json=payload,
    )


def test_real_catalog_profile_and_unqualified_binding(observed):
    client, _, _, _, catalog = observed
    model = catalog.find_routed_model("deepseek::deepseek-flash")
    assert model.profile_applied and model.thinking_default_enabled
    assert model.reasoning_effort_default == "high" and model.deployment is None
    result = client.get(
        "/v1/router/model-catalog", headers={"Authorization": "Bearer synthetic-router"}
    )
    assert result.status_code == 200
    assert len(result.json()["items"]) == 2


def test_real_memory_adapter_and_character_frozen_defaults(observed):
    client, store, phase, requests, _ = observed
    assert (
        post(
            client,
            "chat/completions",
            {
                "model": "deepseek::deepseek-flash",
                "messages": [{"role": "user", "content": "中文 JSON schema"}],
                "thinking": {"type": "disabled"},
                "response_format": {"type": "json_object"},
                "max_tokens": 128,
            },
        ).status_code
        == 200
    )
    assert requests[-1]["model"] == "deepseek-flash"
    assert requests[-1]["thinking"] == {"type": "disabled"}
    assert requests[-1]["response_format"] == {"type": "json_object"}
    assert "reasoning_effort" not in requests[-1]
    phase.write_text(json.dumps({"phase": "character", "operation_id": "arm-empty"}))
    assert (
        post(
            client,
            "chat/completions",
            {
                "model": "deepseek::deepseek-flash",
                "messages": [{"role": "user", "content": "你好"}],
            },
        ).status_code
        == 200
    )
    assert (
        requests[-1]["thinking"] == {"type": "enabled"}
        and requests[-1]["reasoning_effort"] == "high"
    )
    text = "\n".join(p.read_text() for p in store.directory.iterdir())
    assert (
        "private-reasoning" not in text
        and "provider-secret" not in text
        and "Authorization" not in text
    )
    assert "arm-empty" in text and "character" in text and "request_id" in text


def test_qwen_actual_wire_retains_exact_prefix_without_router_additions(observed):
    client, store, phase, requests, _ = observed
    phase.write_text(json.dumps({"phase": "recall", "operation_id": "query-1"}))
    assert (
        post(
            client,
            "embeddings",
            {
                "model": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                "input": [PREFIX + "中文问题"],
            },
        ).status_code
        == 200
    )
    assert requests[-1]["model"] == "Qwen/Qwen3-Embedding-0.6B"
    assert requests[-1]["input"] == [PREFIX + "中文问题"]
    assert (
        post(
            client,
            "embeddings",
            {
                "model": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                "input": ["中文原文"],
            },
        ).status_code
        == 200
    )
    assert requests[-1]["input"] == ["中文原文"]
    receipts = [
        json.loads(p.read_text()) for p in store.directory.glob("*.response.json")
    ]
    assert all(
        r["embedding_dimensions"] == [1024] and r["input_count"] == 1 for r in receipts
    )


def test_outbound_capture_failure_blocks_forward_and_latches_qualification(
    observed, monkeypatch
):
    client, store, _, requests, _ = observed
    original = store.write_bytes

    def fail(name, value):
        if ".outbound.body." in name:
            raise CaptureFailure()
        original(name, value)

    monkeypatch.setattr(store, "write_bytes", fail)
    assert (
        post(
            client,
            "chat/completions",
            {"model": "deepseek::deepseek-flash", "messages": []},
        ).status_code
        == 502
    )
    assert requests == []
    assert client.get("/probe/qualification").status_code == 503
    receipt = json.loads(next(store.directory.glob("*.failure.json")).read_text())
    assert receipt["code"] == "outbound_capture_failed"
    assert (
        post(
            client,
            "chat/completions",
            {"model": "deepseek::deepseek-flash", "messages": []},
        ).status_code
        == 503
    )


@pytest.mark.parametrize(
    "payload",
    [{"stream": True}, {"reasoning_content": "private"}, {"api_key": "secret"}],
)
def test_unobservable_request_contract_fails_before_upstream(observed, payload):
    client, _, _, requests, _ = observed
    assert (
        post(
            client, "chat/completions", {"model": "deepseek::deepseek-flash", **payload}
        ).status_code
        == 503
    )
    assert not requests


def test_credentials_from_headers_are_never_captured(observed):
    client, store, _, requests, _ = observed
    assert (
        client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer secret"},
            json={"password": "secret"},
        ).status_code
        == 401
    )
    assert not list(store.directory.iterdir()) and not requests


def test_safe_failure_never_retains_or_returns_transport_exception_text(
    observed, monkeypatch
):
    client, store, _, _, _ = observed

    async def fail_dispatch(_self, _request):
        raise RuntimeError("synthetic-secret-bearing-diagnostic")

    monkeypatch.setattr(httpx.MockTransport, "handle_async_request", fail_dispatch)
    result = post(
        client,
        "chat/completions",
        {"model": "deepseek::deepseek-flash", "messages": []},
    )
    assert result.status_code == 502
    assert "synthetic-secret-bearing-diagnostic" not in result.text
    assert all(
        "synthetic-secret-bearing-diagnostic" not in p.read_text()
        for p in store.directory.iterdir()
    )


def test_response_capture_failure_marks_qualification_without_second_dispatch(
    observed, monkeypatch
):
    client, store, _, requests, _ = observed
    original = store.write

    def fail(name, value):
        if name.endswith(".response.json"):
            raise CaptureFailure()
        original(name, value)

    monkeypatch.setattr(store, "write", fail)
    assert (
        post(
            client,
            "chat/completions",
            {"model": "deepseek::deepseek-flash", "messages": []},
        ).status_code
        == 502
    )
    assert len(requests) == 1 and client.get("/probe/qualification").status_code == 503
