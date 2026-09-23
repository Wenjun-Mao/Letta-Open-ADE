from __future__ import annotations

from copy import deepcopy

import pytest

from model_catalog_contracts.deployment_manifest import DeploymentManifest

from ade_api.features.agent_runtime.release_evidence import (
    AgentStudioReleaseEvidenceError,
    canonical_sha256,
    validate_agent_studio_release_evidence,
)


POLICY_HASHES = {
    "prompt": "1" * 64,
    "tool": "2" * 64,
    "schema": "3" * 64,
    "retrieval": "4" * 64,
}
SOURCE = {"revision": "a" * 40, "dirty": False, "fingerprint": "b" * 64}


def _fingerprint(seed: str) -> dict[str, object]:
    return {
        "provider": "test",
        "endpoint_role": "test-endpoint",
        "endpoint_identity": f"endpoint-{seed}",
        "served_model": f"model-{seed}",
        "artifact_reference": f"artifact-{seed}",
        "artifact_revision": None,
        "artifact_sha256": None,
        "runtime_implementation": "test-runtime",
        "runtime_version": None,
        "runtime_image_digest": None,
        "prompt_policy_sha256": POLICY_HASHES["prompt"],
        "tool_policy_sha256": POLICY_HASHES["tool"],
        "schema_policy_sha256": POLICY_HASHES["schema"],
        "retrieval_policy_sha256": POLICY_HASHES["retrieval"],
        "sampling_settings": (
            {"vector_space": {"id": "synthetic-space", "dimensions": 3}}
            if seed == "embedding"
            else {}
        ),
        "context_settings": (
            {
                "route_base_url": "https://embedding.test/v1",
                "vector_space_origin_url": "https://embedding.test/v1",
                "vector_space_origin_runtime": {
                    "implementation": "test-runtime",
                    "version": None,
                    "image_digest": None,
                },
            }
            if seed == "embedding"
            else {}
        ),
        "hardware_metadata": {},
    }


def _manifest() -> DeploymentManifest:
    deployments: list[dict[str, object]] = []
    for deployment_id, alias, roles, seed in (
        ("chat", "router::chat", ["conversation", "reviewer"], "chat"),
        ("embedding", "router::embedding", ["retriever"], "embedding"),
    ):
        fingerprint = _fingerprint(seed)
        from model_catalog_contracts.deployment_manifest import DeploymentFingerprint

        deployments.append(
            {
                "id": deployment_id,
                "route_aliases": [alias],
                "roles": roles,
                "lifecycle": "qualified",
                "fingerprint": fingerprint,
                "qualification": {
                    "fingerprint_sha256": DeploymentFingerprint.from_payload(
                        fingerprint
                    ).sha256,
                    "qualified": True,
                    "stale_round_count": 0,
                    "role_results": [
                        {
                            "role": role,
                            "observed_rounds": 3,
                            "consecutive_passing_rounds": 3,
                            "qualified": True,
                        }
                        for role in roles
                    ],
                },
            }
        )
    return DeploymentManifest.from_payload(
        {"schema_version": 1, "deployments": deployments}
    )


def _evidence(manifest: DeploymentManifest) -> dict[str, object]:
    routes = {
        role: {
            "route_alias": alias,
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
        for role, alias in {
            "conversation": "router::chat",
            "reviewer": "router::chat",
            "retriever": "router::embedding",
        }.items()
        if (deployment := manifest.for_route_alias(alias)) is not None
    }
    payload: dict[str, object] = {
        "schema_version": 3,
        "kind": "ade-agent-studio-release-evidence",
        "decision": "approved",
        "reviewed_by": "release-reviewer",
        "reviewed_at": "2026-09-07T00:00:00+00:00",
        "evaluated_source": SOURCE,
        "build_identity": {
            "api": {
                "revision": SOURCE["revision"],
                "fingerprint": SOURCE["fingerprint"],
            },
            "worker": {
                "revision": SOURCE["revision"],
                "fingerprint": SOURCE["fingerprint"],
            },
        },
        "manifest_sha256": "c" * 64,
        "policy_hashes": POLICY_HASHES,
        "qualified_routes": routes,
        "agent_bundle": {
            "prompt_key": "test_prompt",
            "persona_key": "test_persona",
            "tool_names": ["search_memory"],
        },
        "qualification": {
            "run_id": "native-run",
            "passed": True,
            "proposal_sha256": "d" * 64,
            "canonical_case_keys_sha256": "e" * 64,
            "round_artifact_sha256s": ["f" * 64, "0" * 64, "9" * 64],
            "llama_compatibility": {"passed": True, "artifact_sha256": "8" * 64},
        },
        "conformance": {
            "passed": True,
            "receipt_sha256": "7" * 64,
            "test_paths": [
                "services/ade-api/tests/agent_runtime/test_retry.py",
                "services/ade-api/tests/agent_runtime/test_provider_tracing.py",
                "services/ade-api/tests/agent_runtime/test_run_service.py",
                "services/ade-api/tests/agent_runtime/test_worker_events.py",
                "services/ade-api/tests/agent_runtime/persistence/test_repository_contracts.py",
            ],
        },
    }
    payload["evidence_sha256"] = canonical_sha256(payload)
    return payload


def _v4_evidence(manifest: DeploymentManifest) -> dict[str, object]:
    payload = _evidence(manifest)
    payload["schema_version"] = 4
    qualification = payload["qualification"]
    assert isinstance(qualification, dict)
    qualification.pop("llama_compatibility")
    qualification["compatibility_checks"] = []
    retriever = manifest.for_route_alias("router::embedding")
    assert retriever is not None
    qualification["embedding_space_compatibility"] = {
        "space_id": "synthetic-space",
        "route_alias": "router::embedding",
        "deployment_fingerprint": retriever.fingerprint.sha256,
        "mode": "origin",
    }
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )
    return payload


def test_v3_evidence_binds_native_qualification_routes_and_agent_bundle() -> None:
    manifest = _manifest()
    payload = _evidence(manifest)

    release = validate_agent_studio_release_evidence(
        payload,
        manifest=manifest,
        manifest_sha256="c" * 64,
        policy_hashes=POLICY_HASHES,
    )

    assert release.route_aliases == {
        "conversation": "router::chat",
        "reviewer": "router::chat",
        "retriever": "router::embedding",
    }
    assert release.agent_bundle.prompt_key == "test_prompt"
    assert release.agent_bundle.persona_key == "test_persona"
    assert release.agent_bundle.tool_names == ("search_memory",)


def test_v3_evidence_does_not_require_legacy_parity_or_rollback_receipts() -> None:
    manifest = _manifest()

    validate_agent_studio_release_evidence(
        _evidence(manifest),
        manifest=manifest,
        manifest_sha256="c" * 64,
        policy_hashes=POLICY_HASHES,
    )


def test_v4_selected_routes_need_no_unselected_compatibility_provider() -> None:
    manifest = _manifest()
    payload = _v4_evidence(manifest)

    release = validate_agent_studio_release_evidence(
        payload,
        manifest=manifest,
        manifest_sha256="c" * 64,
        policy_hashes=POLICY_HASHES,
    )

    assert release.route_aliases["conversation"] == "router::chat"


@pytest.mark.parametrize(
    "checks",
    [
        None,
        [
            {
                "route_alias": "router::other",
                "passed": False,
                "artifact_sha256": "8" * 64,
            }
        ],
    ],
)
def test_v4_rejects_missing_or_failed_selected_compatibility(checks: object) -> None:
    manifest = _manifest()
    payload = _v4_evidence(manifest)
    qualification = payload["qualification"]
    assert isinstance(qualification, dict)
    qualification.pop("compatibility_checks")
    if checks is not None:
        qualification["compatibility_checks"] = checks
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )

    with pytest.raises(AgentStudioReleaseEvidenceError, match="compatibility"):
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256="c" * 64,
            policy_hashes=POLICY_HASHES,
        )


def test_v4_cannot_relabel_a_v3_llama_receipt_as_generic() -> None:
    manifest = _manifest()
    payload = _v4_evidence(manifest)
    qualification = payload["qualification"]
    assert isinstance(qualification, dict)
    qualification["llama_compatibility"] = {"passed": True, "artifact_sha256": "8" * 64}
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )
    with pytest.raises(AgentStudioReleaseEvidenceError, match="legacy llama"):
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256="c" * 64,
            policy_hashes=POLICY_HASHES,
        )


def test_v4_relocation_requires_exact_verified_embedding_receipt() -> None:
    manifest = _manifest()
    payload = _v4_evidence(manifest)
    qualification = payload["qualification"]
    assert isinstance(qualification, dict)
    qualification["embedding_space_compatibility"] = {
        **qualification["embedding_space_compatibility"],
        "mode": "verified",
        "passed": True,
        "artifact_sha256": "8" * 64,
    }
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )
    with pytest.raises(AgentStudioReleaseEvidenceError, match="Origin embedding"):
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256="c" * 64,
            policy_hashes=POLICY_HASHES,
        )


def test_v3_evidence_rejects_nonmatching_api_or_worker_build_identity() -> None:
    manifest = _manifest()
    payload = deepcopy(_evidence(manifest))
    payload["build_identity"] = {
        "api": {"revision": SOURCE["revision"], "fingerprint": SOURCE["fingerprint"]},
        "worker": {"revision": "0" * 40, "fingerprint": SOURCE["fingerprint"]},
    }
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )

    with pytest.raises(AgentStudioReleaseEvidenceError, match="worker build identity"):
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256="c" * 64,
            policy_hashes=POLICY_HASHES,
        )
