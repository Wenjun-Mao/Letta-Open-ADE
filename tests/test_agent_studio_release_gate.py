from __future__ import annotations

from types import SimpleNamespace

import pytest

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)

from ade_api.features.agent_runtime.release_evidence import (
    REQUIRED_CONFORMANCE_TESTS,
    AgentStudioReleaseEvidenceError,
    canonical_sha256,
)
from scripts import check_agent_studio_release_gate as release_gate


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
            "endpoint_identity": deployment_id,
            "served_model": deployment_id,
            "artifact_reference": deployment_id,
            "artifact_revision": None,
            "artifact_sha256": None,
            "runtime_implementation": "test-runtime",
            "runtime_version": None,
            "runtime_image_digest": None,
            **{
                f"{name}_policy_sha256": digest
                for name, digest in POLICY_HASHES.items()
            },
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


def _evidence(manifest: DeploymentManifest) -> dict[str, object]:
    aliases = {
        "conversation": "router::chat",
        "reviewer": "router::chat",
        "retriever": "router::embedding",
    }
    payload: dict[str, object] = {
        "schema_version": 3,
        "kind": "ade-agent-studio-release-evidence",
        "decision": "approved",
        "reviewed_by": "release-reviewer",
        "reviewed_at": "2026-09-07T00:00:00+00:00",
        "evaluated_source": SOURCE,
        "build_identity": {
            component: {
                "revision": SOURCE["revision"],
                "fingerprint": SOURCE["fingerprint"],
            }
            for component in ("api", "worker")
        },
        "manifest_sha256": MANIFEST_SHA256,
        "policy_hashes": POLICY_HASHES,
        "qualified_routes": {
            role: {
                "route_alias": alias,
                "deployment_id": manifest.for_route_alias(alias).deployment_id,
                "fingerprint_sha256": manifest.for_route_alias(
                    alias
                ).fingerprint.sha256,
            }
            for role, alias in aliases.items()
        },
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
    payload["evidence_sha256"] = canonical_sha256(payload)
    return payload


def test_release_gate_accepts_a_complete_steady_state_release() -> None:
    manifest = _manifest()

    release = release_gate.validate_agent_studio_release_gate(
        manifest,
        policy_hashes=POLICY_HASHES,
        source_clean=True,
        evidence_payload=_evidence(manifest),
        manifest_sha256=MANIFEST_SHA256,
    )

    assert release.qualification_run_id == "native-qualification"


def test_release_gate_fails_closed_for_dirty_source_or_stale_policy() -> None:
    manifest = _manifest()
    evidence = _evidence(manifest)

    with pytest.raises(
        release_gate.AgentStudioReleaseGateError, match="clean Git-visible"
    ):
        release_gate.validate_agent_studio_release_gate(
            manifest,
            policy_hashes=POLICY_HASHES,
            source_clean=False,
            evidence_payload=evidence,
            manifest_sha256=MANIFEST_SHA256,
        )
    with pytest.raises(AgentStudioReleaseEvidenceError, match="stale runtime policies"):
        release_gate.validate_agent_studio_release_gate(
            manifest,
            policy_hashes={**POLICY_HASHES, "schema": "0" * 64},
            source_clean=True,
            evidence_payload=evidence,
            manifest_sha256=MANIFEST_SHA256,
        )


def test_source_lineage_rejects_governed_changes_but_not_unrelated_docs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        release_gate.subprocess,
        "run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0),
    )
    monkeypatch.setattr(
        release_gate.subprocess,
        "check_output",
        lambda *_args, **_kwargs: "docs/architecture/overview.md\n",
    )
    release_gate._validate_source_lineage(SOURCE["revision"])

    monkeypatch.setattr(
        release_gate.subprocess,
        "check_output",
        lambda *_args, **_kwargs: (
            "services/ade-api/src/ade_api/features/agent_runtime/worker.py\n"
        ),
    )
    with pytest.raises(
        release_gate.AgentStudioReleaseGateError, match="runtime changed"
    ):
        release_gate._validate_source_lineage(SOURCE["revision"])
