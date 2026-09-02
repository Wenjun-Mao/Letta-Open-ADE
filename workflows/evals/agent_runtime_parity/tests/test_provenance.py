from __future__ import annotations

from typing import Any

from workflows.evals.agent_runtime_parity.provenance import (
    OPTION_IDENTITY_FIELDS,
    _catalog_identity_sha256,
    _option_snapshot,
    capture_source_identity,
    evaluate_comparability,
)


def _definition() -> dict[str, Any]:
    return {
        "prompt_key": "chat_v20260516",
        "prompt_sha256": "a" * 64,
        "persona_key": "chat_linxiaotang",
        "persona_sha256": "b" * 64,
        "deployments": [
            {"role": "conversation", "route_alias": "dgx_vllm::qwen3.6-35b-a3b-fp8"},
            {"role": "reviewer", "route_alias": "dgx_vllm::qwen3.6-35b-a3b-fp8"},
            {
                "role": "retriever",
                "route_alias": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
            },
        ],
    }


def _spec() -> dict[str, Any]:
    return {
        "fixture": {"sha256": "f" * 64},
        "controls": {"rounds": 3},
        "requested_inputs": {
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "legacy": {"model_router_key": "dgx_vllm::qwen3.6-35b-a3b-fp8"},
            "native": {
                "conversation_model": "dgx_vllm::qwen3.6-35b-a3b-fp8",
                "reviewer_model": "dgx_vllm::qwen3.6-35b-a3b-fp8",
                "embedding_model": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
            },
        },
    }


def _legacy() -> dict[str, Any]:
    return {
        "prompt": {"content_sha256": "a" * 64},
        "persona": {"content_sha256": "b" * 64},
    }


def test_comparability_requires_equivalent_inputs_for_all_rounds() -> None:
    result = evaluate_comparability(
        parity_spec_sha256="p" * 64,
        parity_spec=_spec(),
        legacy_inputs=_legacy(),
        native_health={
            "database_ready": True,
            "worker_ready": True,
            "source_revision": "r" * 40,
            "source_dirty": False,
            "source_fingerprint": "s" * 64,
        },
        native_rounds=[{"native_definition": _definition()} for _ in range(3)],
        source_identity={"revision": "r" * 40, "fingerprint": "s" * 64, "dirty": False},
    )

    assert result["pass"] is True


def test_comparability_fails_closed_when_native_persona_differs() -> None:
    definition = _definition()
    definition["persona_sha256"] = "c" * 64
    result = evaluate_comparability(
        parity_spec_sha256="p" * 64,
        parity_spec=_spec(),
        legacy_inputs=_legacy(),
        native_health={
            "database_ready": True,
            "worker_ready": True,
            "source_revision": "r" * 40,
            "source_dirty": False,
            "source_fingerprint": "s" * 64,
        },
        native_rounds=[{"native_definition": definition} for _ in range(3)],
        source_identity={"revision": "r" * 40, "fingerprint": "s" * 64, "dirty": False},
    )

    assert result["pass"] is False
    assert result["checks"]["persona_snapshots_match"] is False


def test_catalog_snapshot_verifies_the_public_catalog_hash_format() -> None:
    option = {field: None for field in OPTION_IDENTITY_FIELDS}
    option["key"] = "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8"
    option["identity_sha256"] = _catalog_identity_sha256(
        {field: option.get(field) for field in OPTION_IDENTITY_FIELDS}
    )

    snapshot = _option_snapshot(option)

    assert snapshot["identity_sha256"] == option["identity_sha256"]


def test_source_identity_prefers_build_bound_environment(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADE_SOURCE_REVISION", "r" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "s" * 64)

    identity = capture_source_identity()

    assert identity == {
        "revision": "r" * 40,
        "dirty": False,
        "fingerprint": "s" * 64,
    }
