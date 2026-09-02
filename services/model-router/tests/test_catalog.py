from __future__ import annotations

import json
import threading
from types import SimpleNamespace

import httpx

from model_router.catalog import (
    RouterCatalogService,
    RouterModelRecord,
    build_router_model_id,
    normalize_router_model_id,
    parse_router_model_id,
)
from model_router.settings import RouterSourceConfig
from model_catalog_contracts.deployment_manifest import DeploymentFingerprint
from model_catalog_contracts.model_allowlist import SourceAllowlistLoadResult
import model_router.catalog as router_catalog_module


def _settings_with_sources(
    *sources: RouterSourceConfig,
    model_profiles_file: str = "missing-model-profiles.json",
    deployment_manifest_file: str = "missing-deployment-manifest.json",
) -> SimpleNamespace:
    return SimpleNamespace(
        sources=list(sources),
        cache_ttl_seconds=30,
        discovery_timeout_seconds=5.0,
        model_profiles_file=model_profiles_file,
        deployment_manifest_file=deployment_manifest_file,
    )


def test_router_catalog_unions_healthy_sources_and_visibility(monkeypatch) -> None:
    llama = RouterSourceConfig(
        id="local_llama_server",
        label="Local llama-server",
        base_url="http://127.0.0.1:8081/v1",
        adapter="llama_cpp_server",
        enabled_for=["agent_studio", "comment_lab", "label_lab"],
    )
    ark = RouterSourceConfig(
        id="ark",
        label="Ark",
        base_url="https://ark.example/api/v3",
        adapter="ark_openai",
        enabled_for=["agent_studio", "comment_lab"],
    )
    service = RouterCatalogService(
        settings_factory=lambda: _settings_with_sources(llama, ark)
    )
    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: None,
    )

    def fake_fetch(source: RouterSourceConfig, *, settings) -> dict[str, object]:
        if source.id == "local_llama_server":
            return {"data": [{"id": "gemma4"}]}
        return {"data": [{"id": "doubao-seed-1-8-251228"}]}

    monkeypatch.setattr(service, "_fetch_models_payload", fake_fetch)

    snapshot = service.snapshot(force_refresh=True)
    models = service.flatten(snapshot)

    assert [source.status for source in snapshot.sources] == ["healthy", "healthy"]
    assert [model.router_model_id for model in models] == [
        "local_llama_server::gemma4",
        "ark::doubao-seed-1-8-251228",
    ]
    assert models[0].letta_handle == "openai-proxy/local_llama_server::gemma4"
    assert models[0].label_lab_available is True
    assert models[0].structured_output_mode == "json_schema"
    assert models[1].label_lab_available is False


def test_router_catalog_filters_ark_through_chat_allowlist(monkeypatch) -> None:
    ark = RouterSourceConfig(
        id="ark",
        label="Ark",
        base_url="https://ark.example/api/v3",
        adapter="ark_openai",
        enabled_for=["agent_studio", "comment_lab"],
    )
    service = RouterCatalogService(settings_factory=lambda: _settings_with_sources(ark))
    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: SourceAllowlistLoadResult(
            source_id="ark",
            path=SimpleNamespace(),
            applied=True,
            checked_at="2026-04-22T12:00:00+00:00",
            probe_mode="chat-probe",
            raw_model_count=3,
            usable_models=frozenset({"doubao-seed-1-8-251228"}),
            detail="ok",
        ),
    )
    monkeypatch.setattr(
        service,
        "_fetch_models_payload",
        lambda source, *, settings: {
            "data": [
                {"id": "doubao-seed-1-8-251228"},
                {"id": "deepseek-v3-250324"},
                {"id": "doubao-embedding-text-240715"},
            ]
        },
    )

    snapshot = service.snapshot(force_refresh=True)
    ark_source = snapshot.sources[0]
    models = service.flatten(snapshot)

    assert ark_source.allowlist_applied is True
    assert ark_source.raw_model_count == 3
    assert ark_source.filtered_model_count == 2
    assert [model.router_model_id for model in models] == [
        "ark::doubao-seed-1-8-251228",
        "ark::doubao-embedding-text-240715",
    ]
    assert models[1].model_type == "embedding"


def test_router_catalog_enriches_matching_model_from_deployment_manifest(
    monkeypatch, tmp_path
) -> None:
    fingerprint = {
        "provider": "dgx_vllm",
        "endpoint_role": "openai-compatible-chat",
        "endpoint_identity": "dgx-spark-vllm-chat:8000",
        "served_model": "qwen3.6-35b-a3b-fp8",
        "artifact_reference": "Qwen/Qwen3.6-35B-A3B-FP8",
        "artifact_revision": "a" * 40,
        "artifact_sha256": None,
        "runtime_implementation": "vLLM",
        "runtime_version": "0.19.2",
        "runtime_image_digest": "b" * 64,
        "prompt_policy_sha256": "c" * 64,
        "tool_policy_sha256": "d" * 64,
        "schema_policy_sha256": "e" * 64,
        "retrieval_policy_sha256": "f" * 64,
        "sampling_settings": {"temperature": 1.0},
        "context_settings": {"total_tokens": 16384},
        "hardware_metadata": {"accelerator": "NVIDIA GB10"},
    }
    manifest_path = tmp_path / "deployment-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "deployments": [
                    {
                        "id": "dgx-qwen-chat",
                        "route_aliases": ["dgx_vllm::qwen3.6-35b-a3b-fp8"],
                        "roles": ["conversation", "reviewer"],
                        "lifecycle": "candidate",
                        "fingerprint": fingerprint,
                        "qualification": {
                            "fingerprint_sha256": DeploymentFingerprint.from_payload(
                                fingerprint
                            ).sha256,
                            "qualified": False,
                            "stale_round_count": 1,
                            "role_results": [
                                {
                                    "role": "conversation",
                                    "observed_rounds": 1,
                                    "consecutive_passing_rounds": 1,
                                    "qualified": False,
                                },
                                {
                                    "role": "reviewer",
                                    "observed_rounds": 2,
                                    "consecutive_passing_rounds": 2,
                                    "qualified": False,
                                },
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://127.0.0.1:8000/v1",
        adapter="vllm_openai",
        enabled_for=["agent_studio"],
    )
    service = RouterCatalogService(
        settings_factory=lambda: _settings_with_sources(
            source, deployment_manifest_file=str(manifest_path)
        )
    )
    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: None,
    )
    monkeypatch.setattr(
        service,
        "_fetch_models_payload",
        lambda source, *, settings: {"data": [{"id": "qwen3.6-35b-a3b-fp8"}]},
    )

    model = service.flatten(service.snapshot(force_refresh=True))[0]
    deployment = model.as_dict()["deployment"]

    assert deployment == {
        "deployment_id": "dgx-qwen-chat",
        "roles": ["conversation", "reviewer"],
        "lifecycle": "candidate",
        "fingerprint": {
            **fingerprint,
            "artifact_sha256": None,
            "runtime_image_digest": "b" * 64,
            "sha256": DeploymentFingerprint.from_payload(fingerprint).sha256,
        },
        "qualification": {
            "fingerprint_sha256": DeploymentFingerprint.from_payload(
                fingerprint
            ).sha256,
            "qualified": False,
            "stale_round_count": 1,
            "role_results": [
                {
                    "role": "conversation",
                    "observed_rounds": 1,
                    "consecutive_passing_rounds": 1,
                    "qualified": False,
                },
                {
                    "role": "reviewer",
                    "observed_rounds": 2,
                    "consecutive_passing_rounds": 2,
                    "qualified": False,
                },
            ],
        },
    }
    assert "route_aliases" not in deployment


def test_router_resolves_stable_alias_through_the_discovered_deployment(
    monkeypatch, tmp_path
) -> None:
    fingerprint = {
        "provider": "embedding-source",
        "endpoint_role": "openai-compatible-embeddings",
        "endpoint_identity": "embedding:8001",
        "served_model": "Qwen/Qwen3-Embedding-0.6B",
        "artifact_reference": "Qwen/Qwen3-Embedding-0.6B",
        "artifact_revision": "a" * 40,
        "artifact_sha256": None,
        "runtime_implementation": "vLLM",
        "runtime_version": "0.19.2",
        "runtime_image_digest": "b" * 64,
        "prompt_policy_sha256": "c" * 64,
        "tool_policy_sha256": "d" * 64,
        "schema_policy_sha256": "e" * 64,
        "retrieval_policy_sha256": "f" * 64,
        "sampling_settings": {"dimensions": 1024},
        "context_settings": {"request_timeout_seconds": 15},
        "hardware_metadata": {},
    }
    manifest_path = tmp_path / "deployment-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "deployments": [
                    {
                        "id": "embedding-deployment",
                        "route_aliases": [
                            "embedding-source::stable",
                            "embedding-source::Qwen/Qwen3-Embedding-0.6B",
                        ],
                        "roles": ["retriever"],
                        "lifecycle": "candidate",
                        "fingerprint": fingerprint,
                        "qualification": {
                            "fingerprint_sha256": DeploymentFingerprint.from_payload(
                                fingerprint
                            ).sha256,
                            "qualified": False,
                            "stale_round_count": 0,
                            "role_results": [
                                {
                                    "role": "retriever",
                                    "observed_rounds": 0,
                                    "consecutive_passing_rounds": 0,
                                    "qualified": False,
                                }
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    source = RouterSourceConfig(
        id="embedding-source",
        label="Embedding source",
        base_url="http://127.0.0.1:8001/v1",
        adapter="vllm_openai",
        enabled_for=["embedding"],
    )
    service = RouterCatalogService(
        settings_factory=lambda: _settings_with_sources(
            source, deployment_manifest_file=str(manifest_path)
        )
    )
    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: None,
    )
    monkeypatch.setattr(
        service,
        "_fetch_models_payload",
        lambda source, *, settings: {"data": [{"id": "Qwen/Qwen3-Embedding-0.6B"}]},
    )

    model = service.find_routed_model("embedding-source::stable")

    assert model is not None
    assert model.provider_model_id == "Qwen/Qwen3-Embedding-0.6B"
    assert model.deployment is not None
    assert model.deployment.deployment_id == "embedding-deployment"
    assert model.as_dict()["route_aliases"] == [
        "embedding-source::stable",
        "embedding-source::Qwen/Qwen3-Embedding-0.6B",
    ]


def test_router_catalog_enriches_models_from_profiles_and_gates_agent_studio(
    monkeypatch, tmp_path
) -> None:
    profiles_path = tmp_path / "model_profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "dgx_vllm::gemma4-31b-nvfp4": {
                    "base_model": "nvidia/Gemma-4-31B-IT-NVFP4",
                    "profile_source": "https://huggingface.co/google/gemma-4-31B-it",
                    "supports_top_k": True,
                    "supports_thinking": True,
                    "thinking_default_enabled": False,
                    "agent_studio_candidate": True,
                    "agent_studio_compatible": False,
                    "sampling_defaults": {
                        "temperature": 1.0,
                        "top_p": 0.95,
                        "top_k": 64,
                    },
                    "scenario_sampling_defaults": {
                        "comment_lab": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
                        "label_lab": {"temperature": 0.0, "top_p": 0.95, "top_k": 64},
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    dgx = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://100.64.35.71:8000/v1",
        adapter="vllm_openai",
        enabled_for=["agent_studio", "comment_lab", "label_lab"],
    )
    service = RouterCatalogService(
        settings_factory=lambda: _settings_with_sources(
            dgx, model_profiles_file=str(profiles_path)
        )
    )
    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: None,
    )
    monkeypatch.setattr(
        service,
        "_fetch_models_payload",
        lambda source, *, settings: {"data": [{"id": "gemma4-31b-nvfp4"}]},
    )

    models = service.flatten(service.snapshot(force_refresh=True))

    assert len(models) == 1
    model = models[0]
    assert model.router_model_id == "dgx_vllm::gemma4-31b-nvfp4"
    assert model.profile_applied is True
    assert model.supports_top_k is True
    assert model.supports_thinking is True
    assert model.thinking_default_enabled is False
    assert model.sampling_defaults == {"temperature": 1.0, "top_p": 0.95, "top_k": 64}
    assert model.scenario_sampling_defaults["label_lab"]["temperature"] == 0.0
    assert model.agent_studio_candidate is True
    assert model.agent_studio_compatible is False
    assert model.agent_studio_available is False
    assert model.letta_handle is None
    assert model.comment_lab_available is True
    assert model.label_lab_available is True


def test_router_catalog_exposes_qwen_vllm_profile_to_all_modules(
    monkeypatch, tmp_path
) -> None:
    profiles_path = tmp_path / "model_profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "dgx_vllm::qwen3.6-35b-a3b-fp8": {
                    "base_model": "Qwen/Qwen3.6-35B-A3B-FP8",
                    "profile_source": (
                        "docs/adr/0015-model-scoped-tool-call-thinking-mode.md"
                    ),
                    "supports_top_k": True,
                    "supports_thinking": True,
                    "thinking_default_enabled": True,
                    "tool_call_thinking_default_enabled": False,
                    "agent_studio_candidate": True,
                    "agent_studio_compatible": True,
                    "sampling_defaults": {
                        "temperature": 1.0,
                        "top_p": 0.95,
                        "top_k": 20,
                        "min_p": 0.0,
                        "presence_penalty": 1.5,
                        "repetition_penalty": 1.0,
                    },
                    "scenario_sampling_defaults": {
                        "agent_studio": {
                            "temperature": 1.0,
                            "top_p": 0.95,
                            "top_k": 20,
                            "min_p": 0.0,
                            "presence_penalty": 1.5,
                            "repetition_penalty": 1.0,
                        },
                        "comment_lab": {
                            "temperature": 1.0,
                            "top_p": 0.95,
                            "top_k": 20,
                            "min_p": 0.0,
                            "presence_penalty": 1.5,
                            "repetition_penalty": 1.0,
                        },
                        "label_lab": {
                            "temperature": 1.0,
                            "top_p": 0.95,
                            "top_k": 20,
                            "min_p": 0.0,
                            "presence_penalty": 1.5,
                            "repetition_penalty": 1.0,
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    dgx = RouterSourceConfig(
        id="dgx_vllm",
        label="DGX Spark vLLM",
        base_url="http://100.64.35.71:8000/v1",
        adapter="vllm_openai",
        enabled_for=["agent_studio", "comment_lab", "label_lab"],
    )
    service = RouterCatalogService(
        settings_factory=lambda: _settings_with_sources(
            dgx, model_profiles_file=str(profiles_path)
        )
    )
    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: None,
    )
    monkeypatch.setattr(
        service,
        "_fetch_models_payload",
        lambda source, *, settings: {"data": [{"id": "qwen3.6-35b-a3b-fp8"}]},
    )

    models = service.flatten(service.snapshot(force_refresh=True))

    assert len(models) == 1
    model = models[0]
    assert model.router_model_id == "dgx_vllm::qwen3.6-35b-a3b-fp8"
    assert model.letta_handle == "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8"
    assert model.agent_studio_available is True
    assert model.comment_lab_available is True
    assert model.label_lab_available is True
    assert model.thinking_default_enabled is True
    assert model.tool_call_thinking_default_enabled is False
    assert model.as_dict()["tool_call_thinking_default_enabled"] is False
    assert model.sampling_defaults == {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 1.5,
        "repetition_penalty": 1.0,
    }


def test_router_model_id_helpers() -> None:
    assert build_router_model_id("local", "gemma4") == "local::gemma4"
    assert normalize_router_model_id("openai-proxy/local::gemma4") == "local::gemma4"
    assert parse_router_model_id("openai-proxy/local::gemma4") == ("local", "gemma4")


def test_extract_model_records_normalizes_gguf_paths() -> None:
    records = RouterCatalogService._extract_model_records(
        {"data": [{"id": r"F:\LM Studio\models\gemma-4-26B-it-Q4_K_M.gguf"}]}
    )

    assert records == [
        RouterModelRecord(provider_model_id="gemma-4-26B-it-Q4_K_M", model_type="llm")
    ]


def test_catalog_discovers_enabled_sources_concurrently(monkeypatch) -> None:
    sources = tuple(
        RouterSourceConfig(
            id=f"source_{index}",
            label=f"Source {index}",
            base_url=f"http://source-{index}.test/v1",
            enabled_for=["agent_studio"],
        )
        for index in range(2)
    )
    service = RouterCatalogService(
        settings_factory=lambda: _settings_with_sources(*sources)
    )
    barrier = threading.Barrier(2)
    thread_ids: set[int] = set()

    def fake_fetch(source, *, settings):
        del settings
        thread_ids.add(threading.get_ident())
        barrier.wait(timeout=1)
        return {"data": [{"id": f"{source.id}-model"}]}

    monkeypatch.setattr(
        router_catalog_module,
        "load_configured_source_allowlist",
        lambda source_id: None,
    )
    monkeypatch.setattr(service, "_fetch_models_payload", fake_fetch)

    snapshot = service.snapshot(force_refresh=True)

    assert [source.status for source in snapshot.sources] == ["healthy", "healthy"]
    assert len(thread_ids) == 2


def test_catalog_discovery_does_not_hide_transport_retries(monkeypatch) -> None:
    source = RouterSourceConfig(
        id="source_one",
        label="Source One",
        base_url="http://source-one.test/v1",
        enabled_for=["agent_studio"],
    )
    settings = _settings_with_sources(source)
    service = RouterCatalogService(settings_factory=lambda: settings)
    calls = 0

    def fail_once(source, *, settings):
        nonlocal calls
        del source, settings
        calls += 1
        raise httpx.ReadTimeout("catalog unavailable")

    monkeypatch.setattr(service, "_fetch_models_payload_once", fail_once)

    snapshot = service.snapshot(force_refresh=True)

    assert calls == 1
    assert snapshot.sources[0].status == "unreachable"
