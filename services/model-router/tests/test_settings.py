from __future__ import annotations

import json

import pytest

from model_router.settings import RouterSourceConfig, clear_settings_cache, get_settings


def test_router_settings_parse_sources_and_module_visibility(monkeypatch) -> None:
    monkeypatch.setenv(
        "MODEL_ROUTER_SOURCES",
        json.dumps(
            [
                {
                    "id": "local_llama_server",
                    "label": "Local llama-server",
                    "base_url": "http://127.0.0.1:8081/v1",
                    "kind": "openai-compatible",
                    "adapter": "llama_cpp_server",
                    "enabled": True,
                    "enabled_for": ["agent_studio", "comment_lab", "label_lab"],
                    "api_key_env": "LLAMA_SERVER_API_KEY",
                    "api_key_secret": "llama-server-api-key",
                },
                {
                    "id": "ark",
                    "label": "Ark",
                    "base_url": "https://ark.example/api/v3",
                    "kind": "openai-compatible",
                    "adapter": "ark_openai",
                    "enabled_for": ["chat", "comment"],
                    "module_visibility": ["agent_studio", "comment_lab"],
                    "api_key_env": "OPENAI_API_KEY",
                    "api_key_secret": "ark-api-key",
                },
                {
                    "id": "dgx_vllm",
                    "label": "DGX Spark vLLM",
                    "base_url": "http://100.64.35.71:8000/v1",
                    "kind": "openai-compatible",
                    "adapter": "vllm_openai",
                    "enabled_for": ["agent_studio", "comment_lab", "label_lab"],
                    "api_key_env": "DGX_VLLM_API_KEY",
                    "api_key_secret": "dgx-vllm-api-key",
                },
            ]
        ),
    )
    clear_settings_cache()
    try:
        settings = get_settings()
        assert [source.id for source in settings.sources] == [
            "local_llama_server",
            "ark",
            "dgx_vllm",
        ]
        assert settings.sources[0].visible_modules() == (
            "agent_studio",
            "comment_lab",
            "label_lab",
        )
        assert settings.sources[1].visible_modules() == ("agent_studio", "comment_lab")
        assert (
            settings.sources[1].models_endpoint() == "https://ark.example/api/v3/models"
        )
        assert (
            settings.sources[0].embeddings_url()
            == "http://127.0.0.1:8081/v1/embeddings"
        )
        assert settings.sources[2].adapter == "vllm_openai"
        assert settings.sources[2].visible_modules() == (
            "agent_studio",
            "comment_lab",
            "label_lab",
        )
    finally:
        clear_settings_cache()


def test_router_settings_load_sources_from_file_when_env_sources_absent(
    monkeypatch, tmp_path
) -> None:
    sources_path = tmp_path / "router_sources.json"
    sources_path.write_text(
        json.dumps(
            [
                {
                    "id": "local_llama_server",
                    "label": "Local llama-server",
                    "base_url": "http://127.0.0.1:8081/v1",
                    "kind": "openai-compatible",
                    "adapter": "llama_cpp_server",
                    "enabled_for": ["agent_studio", "comment_lab"],
                }
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("MODEL_ROUTER_SOURCES", raising=False)
    monkeypatch.setenv("MODEL_ROUTER_SOURCES_FILE", str(sources_path))
    clear_settings_cache()
    try:
        settings = get_settings()
        assert [source.id for source in settings.sources] == ["local_llama_server"]
        assert settings.sources[0].visible_modules() == ("agent_studio", "comment_lab")
    finally:
        clear_settings_cache()


def test_router_source_auth_prefers_secret_file_over_env(tmp_path) -> None:
    source = RouterSourceConfig(
        id="local",
        label="Local",
        base_url="http://127.0.0.1:8081/v1",
        enabled_for=["label_lab"],
        api_key_env="LLAMA_SERVER_API_KEY",
        api_key_secret="llama-server-api-key",
    )
    (tmp_path / "llama-server-api-key").write_text("secret-token\n", encoding="utf-8")

    assert (
        source.resolve_api_key(
            secrets_dir=tmp_path,
            environ={"LLAMA_SERVER_API_KEY": "env-token"},
        )
        == "secret-token"
    )

    (tmp_path / "llama-server-api-key").unlink()
    assert (
        source.resolve_api_key(
            secrets_dir=tmp_path,
            environ={"LLAMA_SERVER_API_KEY": "env-token"},
        )
        == "env-token"
    )


def test_llama_router_source_falls_back_to_unsloth_key(tmp_path) -> None:
    source = RouterSourceConfig(
        id="local_llama_server",
        label="Local llama-server",
        base_url="http://127.0.0.1:8081/v1",
        adapter="llama_cpp_server",
        enabled_for=["label_lab"],
        api_key_env="LLAMA_SERVER_API_KEY",
        api_key_secret="llama-server-api-key",
    )

    assert (
        source.resolve_api_key(
            secrets_dir=tmp_path,
            environ={"LLAMA_SERVER_API_KEY": "", "UNSLOTH_API_KEY": "fallback-token"},
        )
        == "fallback-token"
    )


def test_dgx_vllm_router_source_auth_is_optional(tmp_path) -> None:
    source = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://100.64.35.71:8000/v1",
        adapter="vllm_openai",
        enabled_for=["agent_studio", "comment_lab", "label_lab"],
        api_key_env="DGX_VLLM_API_KEY",
        api_key_secret="dgx-vllm-api-key",
    )

    assert (
        source.resolve_api_key(secrets_dir=tmp_path, environ={"DGX_VLLM_API_KEY": ""})
        == ""
    )
    assert (
        source.resolve_api_key(
            secrets_dir=tmp_path, environ={"DGX_VLLM_API_KEY": "spark-token"}
        )
        == "spark-token"
    )


def test_deepseek_source_resolves_configured_base_and_key_without_v1_suffix(
    monkeypatch, tmp_path
) -> None:
    source = RouterSourceConfig(
        id="deepseek",
        label="DeepSeek",
        base_url="https://api.deepseek.com",
        base_url_env="DEEPSEEK_API_BASE",
        adapter="deepseek_openai",
        enabled_for=["agent_studio", "comment_lab", "label_lab"],
        api_key_env="DEEPSEEK_API_KEY",
    )
    monkeypatch.setenv("DEEPSEEK_API_BASE", "https://api.deepseek.com/")
    assert source.models_endpoint() == "https://api.deepseek.com/models"
    assert source.chat_completions_url() == "https://api.deepseek.com/chat/completions"
    assert (
        source.resolve_api_key(
            secrets_dir=tmp_path, environ={"DEEPSEEK_API_KEY": "synthetic-key"}
        )
        == "synthetic-key"
    )
    monkeypatch.setenv(
        "DEEPSEEK_API_BASE", "https://api.deepseek.com/v1/chat/completions"
    )
    assert (
        source.chat_completions_url() == "https://api.deepseek.com/v1/chat/completions"
    )
    assert source.models_endpoint() == "https://api.deepseek.com/v1/models"
    for unsafe_base in (
        "http://api.deepseek.com",
        "https://other.example/v1",
        "https://api.deepseek.com/v1?key=secret",
        "https://user:secret@api.deepseek.com/v1",
    ):
        monkeypatch.setenv("DEEPSEEK_API_BASE", unsafe_base)
        with pytest.raises(ValueError, match="official API endpoint"):
            source.normalized_base_url()


def test_embedding_endpoint_can_relocate_without_leaking_credentials(
    monkeypatch, tmp_path
) -> None:
    source = RouterSourceConfig(
        id="dgx_embedding_sidecar",
        label="Qwen embedding service",
        base_url="http://dgx-spark:8001/v1",
        base_url_env="QWEN_EMBEDDING_API_BASE",
        adapter="vllm_openai",
        enabled_for=["embedding"],
        api_key_env="DGX_EMBEDDING_API_KEY",
    )
    monkeypatch.setenv("QWEN_EMBEDDING_API_BASE", "https://embedding.example/v1/")
    assert source.embeddings_url() == "https://embedding.example/v1/embeddings"
    assert "secret" not in source.embeddings_url()
    assert (
        source.resolve_api_key(
            secrets_dir=tmp_path, environ={"DGX_EMBEDDING_API_KEY": "synthetic-secret"}
        )
        == "synthetic-secret"
    )
    monkeypatch.setenv(
        "QWEN_EMBEDDING_API_BASE", "https://user:secret@embedding.example/v1"
    )
    with pytest.raises(ValueError, match="without credentials"):
        source.normalized_base_url()
