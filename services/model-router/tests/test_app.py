from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

import model_router.app as router_app
import model_router.forwarding as router_forwarding
from model_router.catalog import (
    RoutedModel,
    RouterCatalogSnapshot,
    RouterSourceSnapshot,
)
from model_router.settings import RouterSourceConfig


class _FakeSettings:
    sources: list[RouterSourceConfig] = []
    request_timeout_seconds = 600.0

    def resolve_api_key(self) -> str:
        return "router-token"


class _FakeCatalog:
    def __init__(
        self,
        *,
        source: RouterSourceConfig | None = None,
        model: RoutedModel | None = None,
    ) -> None:
        self.source = source or RouterSourceConfig(
            id="local_llama_server",
            label="Local llama-server",
            base_url="http://127.0.0.1:8081/v1",
            adapter="llama_cpp_server",
            enabled_for=["agent_studio", "comment_lab", "label_lab"],
        )
        self.model = model or RoutedModel(
            router_model_id="local_llama_server::gemma4",
            source_id=self.source.id,
            source_label=self.source.label,
            source_kind="openai-compatible",
            source_adapter=self.source.adapter,
            source_base_url=self.source.base_url,
            module_visibility=("agent_studio", "comment_lab", "label_lab"),
            provider_model_id="gemma4",
            model_type="llm",
            letta_handle="openai-proxy/local_llama_server::gemma4",
            agent_studio_available=True,
            comment_lab_available=True,
            label_lab_available=True,
            structured_output_mode="json_schema",
        )

    def snapshot(self, *, force_refresh: bool = False) -> RouterCatalogSnapshot:
        return RouterCatalogSnapshot(
            generated_at=123.0,
            sources=(
                RouterSourceSnapshot(
                    id=self.source.id,
                    label=self.source.label,
                    kind="openai-compatible",
                    adapter=self.source.adapter,
                    base_url=self.source.base_url,
                    module_visibility=("agent_studio", "comment_lab", "label_lab"),
                    status="healthy",
                    detail="ok",
                    models=(),
                    raw_model_count=1,
                    filtered_model_count=1,
                ),
            ),
        )

    def flatten(self, snapshot: RouterCatalogSnapshot) -> list[RoutedModel]:
        return [self.model]

    def find_routed_model(
        self, router_model_id: str, *, force_refresh: bool = False
    ) -> RoutedModel | None:
        if router_model_id.endswith(self.model.router_model_id):
            return self.model
        return None

    def source_config(self, source_id: str) -> RouterSourceConfig | None:
        return self.source if source_id == self.source.id else None

    def source_status(self, source_id: str) -> SimpleNamespace:
        return SimpleNamespace(status="healthy", detail="ok")


def test_router_requires_api_key(monkeypatch) -> None:
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    client = TestClient(router_app.app)

    response = client.get("/v1/models")

    assert response.status_code == 401


def test_router_health_remains_public(monkeypatch) -> None:
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())

    response = TestClient(router_app.app).get("/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_router_warms_catalog_before_lifespan_reports_ready(monkeypatch) -> None:
    class _WarmCatalog(_FakeCatalog):
        snapshot_calls = 0

        def snapshot(self, *, force_refresh: bool = False) -> RouterCatalogSnapshot:
            self.snapshot_calls += 1
            return super().snapshot(force_refresh=force_refresh)

    catalog = _WarmCatalog()
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", catalog)

    with TestClient(router_app.app):
        assert catalog.snapshot_calls == 1


def test_upstream_connections_expire_before_common_server_timeout() -> None:
    limits = router_forwarding.upstream_http_limits()

    assert limits.keepalive_expiry == 2.0


def test_router_lists_agent_studio_models(monkeypatch) -> None:
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    client = TestClient(router_app.app)

    response = client.get(
        "/v1/models", headers={"Authorization": "Bearer router-token"}
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "local_llama_server::gemma4"


def test_router_lists_embedding_models(monkeypatch) -> None:
    source = RouterSourceConfig(
        id="embedding_source",
        label="Embedding source",
        base_url="http://127.0.0.1:8001/v1",
        adapter="vllm_openai",
        enabled_for=["embedding"],
    )
    embedding_model = RoutedModel(
        router_model_id="embedding_source::embedding-model",
        source_id=source.id,
        source_label=source.label,
        source_kind="openai-compatible",
        source_adapter=source.adapter,
        source_base_url=source.base_url,
        module_visibility=("embedding",),
        provider_model_id="embedding-model",
        model_type="embedding",
        letta_handle=None,
        agent_studio_available=False,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode=None,
    )
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app,
        "catalog_service",
        _FakeCatalog(source=source, model=embedding_model),
    )

    response = TestClient(router_app.app).get(
        "/v1/models", headers={"Authorization": "Bearer router-token"}
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["id"] == "embedding_source::embedding-model"


def test_router_rewrites_model_and_preserves_payload(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_forward(
        _application, source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["source_id"] = source.id
        captured["payload"] = payload
        return JSONResponse({"ok": True, "model": payload["model"]})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    client = TestClient(router_app.app)

    payload = {
        "model": "openai-proxy/local_llama_server::gemma4",
        "messages": [{"role": "user", "content": "hi"}],
        "tools": [{"type": "function", "function": {"name": "ping"}}],
        "tool_choice": "auto",
        "response_format": {"type": "json_object"},
        "stream": False,
        "reasoning": {"effort": "low"},
    }
    response = client.post(
        "/v1/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert captured["source_id"] == "local_llama_server"
    assert captured["payload"]["model"] == "gemma4"
    assert captured["payload"]["tools"] == payload["tools"]
    assert captured["payload"]["tool_choice"] == "auto"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["payload"]["reasoning"] == {"effort": "low"}


def test_router_preserves_exact_named_tool_selection_for_vllm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    source = RouterSourceConfig(
        id="dgx_vllm",
        label="Local model",
        base_url="http://provider.invalid/v1",
        adapter="vllm_openai",
        enabled_for=["agent_studio"],
    )
    model = RoutedModel(
        router_model_id="dgx_vllm::model",
        source_id="dgx_vllm",
        source_label=source.label,
        source_kind="openai-compatible",
        source_adapter="vllm_openai",
        source_base_url=source.base_url,
        module_visibility=("agent_studio",),
        provider_model_id="model",
        model_type="llm",
        letta_handle="openai-proxy/dgx_vllm::model",
        agent_studio_available=True,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode="json_schema",
    )

    async def fake_forward(
        _application, _source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["payload"] = payload
        return JSONResponse({"ok": True})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app, "catalog_service", _FakeCatalog(source=source, model=model)
    )
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    selection = {
        "type": "function",
        "function": {"name": "get_weather"},
    }

    response = TestClient(router_app.app).post(
        "/v1/chat/completions",
        json={
            "model": "dgx_vllm::model",
            "messages": [{"role": "user", "content": "weather"}],
            "tools": [{"type": "function", "function": {"name": "get_weather"}}],
            "tool_choice": selection,
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert captured["payload"]["tool_choice"] == selection


def test_router_adapts_named_tool_selection_for_llama_cpp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}
    source = RouterSourceConfig(
        id="local_llama_server",
        label="Local llama-server",
        base_url="http://provider.invalid/v1",
        adapter="llama_cpp_server",
        enabled_for=["agent_studio"],
    )
    model = RoutedModel(
        router_model_id="local_llama_server::model",
        source_id=source.id,
        source_label=source.label,
        source_kind="openai-compatible",
        source_adapter=source.adapter,
        source_base_url=source.base_url,
        module_visibility=("agent_studio",),
        provider_model_id="model",
        model_type="llm",
        letta_handle="openai-proxy/local_llama_server::model",
        agent_studio_available=True,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode="json_schema",
    )

    async def fake_forward(
        _application, _source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["payload"] = payload
        return JSONResponse({"ok": True})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app, "catalog_service", _FakeCatalog(source=source, model=model)
    )
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    tools = [
        {"type": "function", "function": {"name": "search_memory"}},
        {"type": "function", "function": {"name": "get_weather"}},
    ]

    response = TestClient(router_app.app).post(
        "/v1/chat/completions",
        json={
            "model": model.router_model_id,
            "messages": [{"role": "user", "content": "weather"}],
            "tools": tools,
            "tool_choice": {
                "type": "function",
                "function": {"name": "get_weather"},
            },
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert captured["payload"]["tool_choice"] == "required"
    assert captured["payload"]["tools"] == [tools[1]]


def test_router_rejects_unbound_llama_cpp_named_tool_choice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forwarded = False

    async def fake_forward(*_args, **_kwargs):
        nonlocal forwarded
        forwarded = True
        return JSONResponse({"ok": True})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)

    response = TestClient(router_app.app).post(
        "/v1/chat/completions",
        json={
            "model": "local_llama_server::gemma4",
            "messages": [{"role": "user", "content": "weather"}],
            "tools": [{"type": "function", "function": {"name": "search_memory"}}],
            "tool_choice": {
                "type": "function",
                "function": {"name": "get_weather"},
            },
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_tool_choice"
    assert forwarded is False


def test_router_injects_profile_sampling_defaults_for_vllm_when_omitted(
    monkeypatch,
) -> None:
    captured: dict[str, Any] = {}
    source = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://100.64.35.71:8000/v1",
        adapter="vllm_openai",
        enabled_for=["comment_lab", "label_lab"],
    )
    model = RoutedModel(
        router_model_id="dgx_vllm::gemma4-31b-nvfp4",
        source_id="dgx_vllm",
        source_label="DGX Spark vLLM",
        source_kind="openai-compatible",
        source_adapter="vllm_openai",
        source_base_url="http://100.64.35.71:8000/v1",
        module_visibility=("comment_lab", "label_lab"),
        provider_model_id="gemma4-31b-nvfp4",
        model_type="llm",
        letta_handle=None,
        agent_studio_available=False,
        comment_lab_available=True,
        label_lab_available=True,
        structured_output_mode="json_schema",
        sampling_defaults={
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 1.5,
            "repetition_penalty": 1.0,
        },
        supports_top_k=True,
        supports_thinking=True,
        thinking_default_enabled=True,
        profile_applied=True,
    )

    async def fake_forward(
        _application, _source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["payload"] = payload
        return JSONResponse({"ok": True, "model": payload["model"]})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app, "catalog_service", _FakeCatalog(source=source, model=model)
    )
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    client = TestClient(router_app.app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "dgx_vllm::gemma4-31b-nvfp4",
            "messages": [{"role": "user", "content": "hi"}],
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert captured["payload"]["model"] == "gemma4-31b-nvfp4"
    assert captured["payload"]["temperature"] == 1.0
    assert captured["payload"]["top_p"] == 0.95
    assert captured["payload"]["top_k"] == 20
    assert captured["payload"]["min_p"] == 0.0
    assert captured["payload"]["presence_penalty"] == 1.5
    assert captured["payload"]["repetition_penalty"] == 1.0
    assert captured["payload"]["chat_template_kwargs"] == {"enable_thinking": True}


def test_router_uses_model_tool_call_thinking_default_without_overriding_caller(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict[str, Any]] = []
    source = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://100.64.35.71:8000/v1",
        adapter="vllm_openai",
        enabled_for=["agent_studio"],
    )
    model = RoutedModel(
        router_model_id="dgx_vllm::qwen3.6-35b-a3b-fp8",
        source_id="dgx_vllm",
        source_label=source.label,
        source_kind="openai-compatible",
        source_adapter=source.adapter,
        source_base_url=source.base_url,
        module_visibility=("agent_studio",),
        provider_model_id="qwen3.6-35b-a3b-fp8",
        model_type="llm",
        letta_handle="openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
        agent_studio_available=True,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode="json_schema",
        supports_thinking=True,
        thinking_default_enabled=True,
        tool_call_thinking_default_enabled=False,
        profile_applied=True,
    )

    async def fake_forward(
        _application, _source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured.append(payload)
        return JSONResponse({"ok": True})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app, "catalog_service", _FakeCatalog(source=source, model=model)
    )
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    client = TestClient(router_app.app)
    tool_payload = {
        "model": model.router_model_id,
        "messages": [{"role": "user", "content": "check the weather"}],
        "tools": [{"type": "function", "function": {"name": "get_weather"}}],
        "tool_choice": {
            "type": "function",
            "function": {"name": "get_weather"},
        },
    }

    assert (
        client.post(
            "/v1/chat/completions",
            json=tool_payload,
            headers={"Authorization": "Bearer router-token"},
        ).status_code
        == 200
    )
    assert captured[-1]["chat_template_kwargs"] == {"enable_thinking": False}

    explicit = {
        **tool_payload,
        "chat_template_kwargs": {"enable_thinking": True, "tokenize": False},
    }
    assert (
        client.post(
            "/v1/chat/completions",
            json=explicit,
            headers={"Authorization": "Bearer router-token"},
        ).status_code
        == 200
    )
    assert captured[-1]["chat_template_kwargs"] == {
        "enable_thinking": True,
        "tokenize": False,
    }

    no_tools = {
        "model": model.router_model_id,
        "messages": [{"role": "user", "content": "hello"}],
    }
    assert (
        client.post(
            "/v1/chat/completions",
            json=no_tools,
            headers={"Authorization": "Bearer router-token"},
        ).status_code
        == 200
    )
    assert captured[-1]["chat_template_kwargs"] == {"enable_thinking": True}


def test_router_preserves_explicit_sampling_values(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    source = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://100.64.35.71:8000/v1",
        adapter="vllm_openai",
        enabled_for=["comment_lab", "label_lab"],
    )
    model = RoutedModel(
        router_model_id="dgx_vllm::gemma4-31b-nvfp4",
        source_id="dgx_vllm",
        source_label="DGX Spark vLLM",
        source_kind="openai-compatible",
        source_adapter="vllm_openai",
        source_base_url="http://100.64.35.71:8000/v1",
        module_visibility=("comment_lab", "label_lab"),
        provider_model_id="gemma4-31b-nvfp4",
        model_type="llm",
        letta_handle=None,
        agent_studio_available=False,
        comment_lab_available=True,
        label_lab_available=True,
        structured_output_mode="json_schema",
        sampling_defaults={
            "temperature": 1.0,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "presence_penalty": 1.5,
            "repetition_penalty": 1.0,
        },
        supports_top_k=True,
        supports_thinking=True,
        thinking_default_enabled=True,
    )

    async def fake_forward(
        _application, _source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["payload"] = payload
        return JSONResponse({"ok": True, "model": payload["model"]})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app, "catalog_service", _FakeCatalog(source=source, model=model)
    )
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    client = TestClient(router_app.app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "dgx_vllm::gemma4-31b-nvfp4",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0.4,
            "top_p": 0.8,
            "top_k": 16,
            "min_p": 0.2,
            "presence_penalty": 0.3,
            "repetition_penalty": 1.1,
            "chat_template_kwargs": {"enable_thinking": False, "tokenize": False},
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert captured["payload"]["temperature"] == 0.4
    assert captured["payload"]["top_p"] == 0.8
    assert captured["payload"]["top_k"] == 16
    assert captured["payload"]["min_p"] == 0.2
    assert captured["payload"]["presence_penalty"] == 0.3
    assert captured["payload"]["repetition_penalty"] == 1.1
    assert captured["payload"]["chat_template_kwargs"] == {
        "enable_thinking": False,
        "tokenize": False,
    }


def test_router_drops_non_positive_max_tokens_before_forwarding(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    async def fake_forward(
        _application, source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["source_id"] = source.id
        captured["payload"] = payload
        return JSONResponse({"ok": True, "model": payload["model"]})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    client = TestClient(router_app.app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "local_llama_server::gemma4",
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 0,
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert "max_tokens" not in captured["payload"]


def test_router_does_not_inject_top_k_for_generic_sources(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    source = RouterSourceConfig(
        id="generic",
        label="Generic",
        base_url="https://generic.example/v1",
        adapter="generic_openai",
        enabled_for=["comment_lab"],
    )
    model = RoutedModel(
        router_model_id="generic::model-a",
        source_id="generic",
        source_label="Generic",
        source_kind="openai-compatible",
        source_adapter="generic_openai",
        source_base_url="https://generic.example/v1",
        module_visibility=("comment_lab",),
        provider_model_id="model-a",
        model_type="llm",
        letta_handle=None,
        agent_studio_available=False,
        comment_lab_available=True,
        label_lab_available=False,
        structured_output_mode=None,
        sampling_defaults={"temperature": 0.7, "top_p": 0.9, "top_k": 64, "min_p": 0.0},
        supports_top_k=False,
    )

    async def fake_forward(
        _application, _source: RouterSourceConfig, payload: dict[str, Any]
    ):
        captured["payload"] = payload
        return JSONResponse({"ok": True, "model": payload["model"]})

    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(
        router_app, "catalog_service", _FakeCatalog(source=source, model=model)
    )
    monkeypatch.setattr(router_app, "forward_chat_completion", fake_forward)
    client = TestClient(router_app.app)

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "generic::model-a",
            "messages": [{"role": "user", "content": "hi"}],
        },
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 200
    assert captured["payload"]["temperature"] == 0.7
    assert captured["payload"]["top_p"] == 0.9
    assert "top_k" not in captured["payload"]
    assert "min_p" not in captured["payload"]
    assert "chat_template_kwargs" not in captured["payload"]


def test_router_unknown_model_reports_source_status(monkeypatch) -> None:
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    client = TestClient(router_app.app)

    response = client.post(
        "/v1/chat/completions",
        json={"model": "local_llama_server::missing", "messages": []},
        headers={"Authorization": "Bearer router-token"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "unknown_or_unavailable_model"
    assert response.json()["error"]["source_status"] == "healthy"


@pytest.mark.parametrize(
    "path", ["/v1/models", "/v1/router/model-catalog", "/v1/router/sources"]
)
def test_router_protects_catalog_endpoints(monkeypatch, path: str) -> None:
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())

    response = TestClient(router_app.app).get(path)

    assert response.status_code == 401


def test_router_catalog_endpoints_accept_valid_api_key(monkeypatch) -> None:
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    client = TestClient(router_app.app)

    catalog_response = client.get(
        "/v1/router/model-catalog", headers={"Authorization": "Bearer router-token"}
    )
    sources_response = client.get(
        "/v1/router/sources", headers={"Authorization": "Bearer router-token"}
    )

    assert catalog_response.status_code == 200
    assert (
        catalog_response.json()["items"][0]["router_model_id"]
        == "local_llama_server::gemma4"
    )
    assert sources_response.status_code == 200
    assert sources_response.json()["sources"][0]["id"] == "local_llama_server"


def test_router_forwards_once_with_lifespan_managed_async_client(monkeypatch) -> None:
    attempts = 0
    captured: dict[str, Any] = {}

    async def upstream_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        captured["url"] = str(request.url)
        captured["model"] = json.loads(request.content)["model"]
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(201, json={"id": "completion-1"})

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setenv("UPSTREAM_API_KEY", "source-token")
    monkeypatch.setattr(
        router_app,
        "catalog_service",
        _FakeCatalog(
            source=RouterSourceConfig(
                id="local_llama_server",
                label="Local llama-server",
                base_url="http://127.0.0.1:8081/v1",
                adapter="llama_cpp_server",
                enabled_for=["agent_studio", "comment_lab", "label_lab"],
                api_key_env="UPSTREAM_API_KEY",
            )
        ),
    )
    monkeypatch.setattr(
        router_forwarding, "create_upstream_client", lambda: upstream_client
    )

    with TestClient(router_app.app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "local_llama_server::gemma4",
                "messages": [{"role": "user", "content": "hi"}],
            },
            headers={"Authorization": "Bearer router-token"},
        )

        assert response.status_code == 201
        assert response.json() == {"id": "completion-1"}
        assert attempts == 1
        assert captured == {
            "url": "http://127.0.0.1:8081/v1/chat/completions",
            "model": "gemma4",
            "authorization": "Bearer source-token",
        }
        assert router_app.app.state.upstream_client is upstream_client
        assert not upstream_client.is_closed

    assert upstream_client.is_closed
    assert not hasattr(router_app.app.state, "upstream_client")


def test_router_does_not_retry_failed_upstream_request(monkeypatch) -> None:
    attempts = 0

    async def upstream_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ConnectError("connection refused")

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(
        router_forwarding, "create_upstream_client", lambda: upstream_client
    )

    with TestClient(router_app.app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "local_llama_server::gemma4", "messages": []},
            headers={"Authorization": "Bearer router-token"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "type": "model_router_error",
            "code": "upstream_unreachable",
            "message": "Source 'local_llama_server' could not be reached: connection refused",
            "source_id": "local_llama_server",
        }
    }
    assert attempts == 1
    assert upstream_client.is_closed


def test_router_forwards_embeddings_once_with_source_auth(monkeypatch) -> None:
    attempts = 0
    captured: dict[str, Any] = {}

    async def upstream_handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        captured["authorization"] = request.headers.get("authorization")
        return httpx.Response(200, json={"object": "list", "data": []})

    source = RouterSourceConfig(
        id="embedding_source",
        label="Embedding source",
        base_url="http://127.0.0.1:8001/v1",
        adapter="vllm_openai",
        enabled_for=["embedding"],
        api_key_env="EMBEDDING_SOURCE_API_KEY",
    )
    embedding_model = RoutedModel(
        router_model_id="embedding_source::qwen3-embedding-0.6b",
        source_id=source.id,
        source_label=source.label,
        source_kind="openai-compatible",
        source_adapter=source.adapter,
        source_base_url=source.base_url,
        module_visibility=("embedding",),
        provider_model_id="qwen3-embedding-0.6b",
        model_type="embedding",
        letta_handle=None,
        agent_studio_available=False,
        comment_lab_available=False,
        label_lab_available=False,
        structured_output_mode=None,
    )
    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setenv("EMBEDDING_SOURCE_API_KEY", "embedding-token")
    monkeypatch.setattr(
        router_app,
        "catalog_service",
        _FakeCatalog(source=source, model=embedding_model),
    )
    monkeypatch.setattr(
        router_forwarding, "create_upstream_client", lambda: upstream_client
    )

    with TestClient(router_app.app) as client:
        response = client.post(
            "/v1/embeddings",
            json={
                "model": "embedding_source::qwen3-embedding-0.6b",
                "input": ["hello", "bonjour"],
                "dimensions": 1024,
                "encoding_format": "float",
            },
            headers={"Authorization": "Bearer router-token"},
        )

    assert response.status_code == 200
    assert response.json() == {"object": "list", "data": []}
    assert attempts == 1
    assert captured == {
        "url": "http://127.0.0.1:8001/v1/embeddings",
        "payload": {
            "model": "qwen3-embedding-0.6b",
            "input": ["hello", "bonjour"],
            "dimensions": 1024,
            "encoding_format": "float",
        },
        "authorization": "Bearer embedding-token",
    }
    assert upstream_client.is_closed


class _TrackedAsyncStream(httpx.AsyncByteStream):
    def __init__(self) -> None:
        self.closed = False

    async def __aiter__(self):
        yield b"data: first\\n\\n"
        yield b"data: [DONE]\\n\\n"

    async def aclose(self) -> None:
        self.closed = True


def test_router_streams_async_upstream_response_and_closes_stream(monkeypatch) -> None:
    attempts = 0
    stream = _TrackedAsyncStream()

    async def upstream_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            202,
            headers={"content-type": "text/event-stream"},
            stream=stream,
        )

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(
        router_forwarding, "create_upstream_client", lambda: upstream_client
    )

    with TestClient(router_app.app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "local_llama_server::gemma4",
                "messages": [],
                "stream": True,
            },
            headers={"Authorization": "Bearer router-token"},
        )

        assert response.status_code == 202
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.content == b"data: first\\n\\ndata: [DONE]\\n\\n"
        assert attempts == 1
        assert stream.closed

    assert upstream_client.is_closed


def test_router_stream_failure_preserves_existing_error_payload(monkeypatch) -> None:
    attempts = 0

    async def upstream_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        raise httpx.ReadError("stream interrupted")

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(
        router_forwarding, "create_upstream_client", lambda: upstream_client
    )

    with TestClient(router_app.app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "local_llama_server::gemma4",
                "messages": [],
                "stream": True,
            },
            headers={"Authorization": "Bearer router-token"},
        )

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "type": "model_router_error",
            "code": "upstream_unreachable",
            "message": "Source 'local_llama_server' could not be reached: stream interrupted",
        }
    }
    assert attempts == 1
    assert upstream_client.is_closed


def test_router_preserves_upstream_json_error_payload(monkeypatch) -> None:
    attempts = 0
    provider_error = {
        "error": {
            "message": "rate limited",
            "type": "rate_limit_error",
            "code": "rate_limited",
        }
    }

    async def upstream_handler(_request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(429, json=provider_error)

    upstream_client = httpx.AsyncClient(transport=httpx.MockTransport(upstream_handler))
    monkeypatch.setattr(router_app, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(router_app, "catalog_service", _FakeCatalog())
    monkeypatch.setattr(
        router_forwarding, "create_upstream_client", lambda: upstream_client
    )

    with TestClient(router_app.app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={"model": "local_llama_server::gemma4", "messages": []},
            headers={"Authorization": "Bearer router-token"},
        )

    assert response.status_code == 429
    assert response.json() == provider_error
    assert attempts == 1
    assert upstream_client.is_closed
