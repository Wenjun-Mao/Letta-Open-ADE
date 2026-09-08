from __future__ import annotations

from copy import deepcopy

import pytest

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)

from ade_api.features.agent_runtime.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS,
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
MANIFEST_SHA256 = "5" * 64
SOURCE = {"revision": "a" * 40, "dirty": False, "fingerprint": "b" * 64}


def _manifest() -> DeploymentManifest:
    deployments: list[dict[str, object]] = []
    for deployment_id, alias, roles in (
        ("chat", "router::chat", ["conversation", "reviewer"]),
        ("embedding", "router::embedding", ["retriever"]),
    ):
        fingerprint = {
            "provider": "test",
            "endpoint_role": "test-endpoint",
            "endpoint_identity": f"endpoint-{deployment_id}",
            "served_model": f"model-{deployment_id}",
            "artifact_reference": f"artifact-{deployment_id}",
            "artifact_revision": None,
            "artifact_sha256": None,
            "runtime_implementation": "test-runtime",
            "runtime_version": None,
            "runtime_image_digest": None,
            "prompt_policy_sha256": POLICY_HASHES["prompt"],
            "tool_policy_sha256": POLICY_HASHES["tool"],
            "schema_policy_sha256": POLICY_HASHES["schema"],
            "retrieval_policy_sha256": POLICY_HASHES["retrieval"],
            "sampling_settings": {},
            "context_settings": {},
            "hardware_metadata": {},
        }
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


def _refresh_digest(payload: dict[str, object]) -> None:
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )


def _payload(manifest: DeploymentManifest) -> dict[str, object]:
    aliases = {
        "conversation": "router::chat",
        "reviewer": "router::chat",
        "retriever": "router::embedding",
    }
    qualified_routes = {
        role: {
            "route_alias": alias,
            "deployment_id": manifest.for_route_alias(alias).deployment_id,
            "fingerprint_sha256": manifest.for_route_alias(alias).fingerprint.sha256,
        }
        for role, alias in aliases.items()
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
        "manifest_sha256": MANIFEST_SHA256,
        "policy_hashes": POLICY_HASHES,
        "qualified_routes": qualified_routes,
        "agent_bundle": {
            "prompt_key": "chat_v20260516",
            "persona_key": "chat_linxiaotang",
            "tool_names": ["search_memory"],
        },
        "qualification": {
            "run_id": "native-qualification",
            "passed": True,
            "proposal_sha256": "c" * 64,
            "canonical_case_keys_sha256": "d" * 64,
            "round_artifact_sha256s": ["e" * 64, "f" * 64, "0" * 64],
            "llama_compatibility": {"passed": True, "artifact_sha256": "9" * 64},
        },
        "conformance": {
            "passed": True,
            "receipt_sha256": "8" * 64,
            "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
        },
    }
    _refresh_digest(payload)
    return payload


def _validate(payload: dict[str, object], manifest: DeploymentManifest):
    return validate_agent_studio_release_evidence(
        payload,
        manifest=manifest,
        manifest_sha256=MANIFEST_SHA256,
        policy_hashes=POLICY_HASHES,
    )


def test_release_evidence_binds_the_steady_state_release_contract() -> None:
    manifest = _manifest()

    release = _validate(_payload(manifest), manifest)

    assert release.qualification_run_id == "native-qualification"
    assert release.route_aliases == {
        "conversation": "router::chat",
        "reviewer": "router::chat",
        "retriever": "router::embedding",
    }
    assert release.agent_bundle.tool_names == ("search_memory",)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda payload: payload.update(schema_version=2), "schema_version must be 3"),
        (
            lambda payload: payload["qualification"].update(
                round_artifact_sha256s=["e" * 64, "e" * 64, "f" * 64]
            ),
            "three distinct passing rounds",
        ),
        (
            lambda payload: payload["qualification"]["llama_compatibility"].update(
                passed=False
            ),
            "llama-server compatibility",
        ),
        (
            lambda payload: payload["build_identity"]["worker"].update(
                revision="0" * 40
            ),
            "worker build identity",
        ),
        (
            lambda payload: payload["qualified_routes"]["reviewer"].update(
                route_alias="router::missing"
            ),
            "route is absent for reviewer",
        ),
        (
            lambda payload: payload["agent_bundle"].update(tool_names=[]),
            "tool_names must be unique",
        ),
        (
            lambda payload: payload["conformance"].update(test_paths=[]),
            "conformance suite is incomplete",
        ),
    ],
)
def test_release_evidence_fails_closed_when_a_required_gate_is_invalid(
    mutate, message: str
) -> None:
    manifest = _manifest()
    payload = deepcopy(_payload(manifest))
    mutate(payload)
    _refresh_digest(payload)

    with pytest.raises(AgentStudioReleaseEvidenceError, match=message):
        _validate(payload, manifest)


def test_release_evidence_rejects_stale_manifest_or_policy_identity() -> None:
    manifest = _manifest()
    payload = _payload(manifest)

    with pytest.raises(AgentStudioReleaseEvidenceError, match="deployment manifest"):
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256="0" * 64,
            policy_hashes=POLICY_HASHES,
        )
    with pytest.raises(AgentStudioReleaseEvidenceError, match="stale runtime policies"):
        validate_agent_studio_release_evidence(
            payload,
            manifest=manifest,
            manifest_sha256=MANIFEST_SHA256,
            policy_hashes={**POLICY_HASHES, "tool": "0" * 64},
        )


def test_release_evidence_rejects_tampering_before_semantic_validation() -> None:
    manifest = _manifest()
    payload = _payload(manifest)
    payload["reviewed_by"] = "someone-else"

    with pytest.raises(AgentStudioReleaseEvidenceError, match="digest"):
        _validate(payload, manifest)
