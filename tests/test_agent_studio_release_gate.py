from __future__ import annotations

from dataclasses import replace

import pytest

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from scripts.check_agent_studio_release_gate import (
    DEFAULT_CONVERSATION_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    AgentStudioReleaseGateError,
    PROJECT_ROOT,
    validate_agent_studio_release_gate,
)
from ade_api.features.agent_runtime_v3.release_evidence import (
    REQUIRED_CAPABILITY_EVIDENCE,
    REQUIRED_CONFORMANCE_TESTS,
    AgentStudioReleaseEvidenceError,
    canonical_sha256,
)
from workflows.evals.agent_runtime_v3_acceptance.policy import (
    production_policy_hashes,
)


def _qualified_manifest(project_root):
    manifest = load_deployment_manifest(
        project_root / "config/model-router/deployment-manifest.json"
    )
    policies = production_policy_hashes(project_root)
    deployments = []
    for deployment in manifest.deployments:
        fingerprint = replace(
            deployment.fingerprint,
            prompt_policy_sha256=policies["prompt"],
            tool_policy_sha256=policies["tool"],
            schema_policy_sha256=policies["schema"],
            retrieval_policy_sha256=policies["retrieval"],
        )
        role_results = tuple(
            replace(
                result,
                observed_rounds=3,
                consecutive_passing_rounds=3,
                qualified=True,
            )
            for result in deployment.qualification.role_results
        )
        deployments.append(
            replace(
                deployment,
                lifecycle="qualified",
                fingerprint=fingerprint,
                qualification=replace(
                    deployment.qualification,
                    fingerprint_sha256=fingerprint.sha256,
                    qualified=True,
                    stale_round_count=0,
                    role_results=role_results,
                ),
            )
        )
    return replace(manifest, deployments=tuple(deployments)), policies


def _release_evidence(manifest, policies):
    routes = {}
    for role, route_alias in {
        "conversation": DEFAULT_CONVERSATION_MODEL,
        "reviewer": DEFAULT_CONVERSATION_MODEL,
        "retriever": DEFAULT_EMBEDDING_MODEL,
    }.items():
        deployment = manifest.for_route_alias(route_alias)
        routes[role] = {
            "route_alias": route_alias,
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
    payload = {
        "schema_version": 1,
        "kind": "ade-agent-studio-cutover-evidence",
        "decision": "approved",
        "reviewed_by": "test",
        "reviewed_at": "2026-09-03T00:00:00Z",
        "evaluated_source": {
            "revision": "a" * 40,
            "dirty": False,
            "fingerprint": "b" * 64,
        },
        "manifest_sha256": "c" * 64,
        "policy_hashes": policies,
        "qualified_routes": routes,
        "qualification": {
            "run_id": "qualification",
            "passed": True,
            "proposal_sha256": "d" * 64,
            "canonical_case_keys_sha256": "e" * 64,
            "round_artifact_sha256s": ["1" * 64, "2" * 64, "3" * 64],
            "llama_compatibility": {
                "passed": True,
                "artifact_sha256": "4" * 64,
            },
        },
        "paired_parity": {
            "run_id": "parity",
            "passed": True,
            "inputs_comparable": True,
            "cleanup_complete": True,
            "rounds_requested": 3,
            "rounds_completed": 3,
            "rounds_passed": 3,
            "native_product_api": "/api/v3/agent-studio/sessions",
            "artifact_digests": {
                "parity_spec_sha256": "5" * 64,
                "provenance_sha256": "6" * 64,
                "normalized_turns_sha256": "7" * 64,
                "comparison_sha256": "8" * 64,
                "summary_sha256": "9" * 64,
                "evidence_sha256": "a" * 64,
            },
        },
        "conformance": {
            "passed": True,
            "receipt_sha256": "b" * 64,
            "test_paths": list(REQUIRED_CONFORMANCE_TESTS),
        },
        "capability_evidence": {
            key: {
                "status": "passed",
                "evidence_kind": (
                    "paired-parity"
                    if key == "memory_correctness"
                    else (
                        "deterministic-contract"
                        if key in {"timeout_retry_ownership", "cancellation"}
                        else "native-qualification"
                    )
                ),
                "artifact_sha256": (
                    "a" * 64
                    if key == "memory_correctness"
                    else (
                        "b" * 64
                        if key in {"timeout_retry_ownership", "cancellation"}
                        else "d" * 64
                    )
                ),
                "references": ["case"],
            }
            for key in REQUIRED_CAPABILITY_EVIDENCE
        },
        "rollback_rehearsal": {
            "rehearsed": True,
            "legacy_source_verified": True,
            "legacy_web_image_built": True,
            "legacy_web_smoke_passed": True,
            "legacy_web_api_read_passed": True,
            "legacy_web_api_write_passed": True,
            "legacy_web_api_cleanup_passed": True,
            "legacy_health_passed": True,
            "native_state_preserved": True,
            "legacy_revision": "0" * 40,
            "rehearsed_at": "2026-09-03T00:00:00Z",
            "receipt_sha256": "b" * 64,
        },
    }
    payload["evidence_sha256"] = canonical_sha256(payload)
    return payload


def test_agent_studio_release_gate_requires_all_exact_promoted_roles() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)

    validate_agent_studio_release_gate(
        manifest,
        conversation_model=DEFAULT_CONVERSATION_MODEL,
        reviewer_model=DEFAULT_CONVERSATION_MODEL,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        policy_hashes=policies,
        source_clean=True,
        evidence_payload=_release_evidence(manifest, policies),
        manifest_sha256="c" * 64,
    )


def test_agent_studio_release_gate_fails_closed_on_stale_policy() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)

    with pytest.raises(AgentStudioReleaseGateError, match="stale policy"):
        validate_agent_studio_release_gate(
            manifest,
            conversation_model=DEFAULT_CONVERSATION_MODEL,
            reviewer_model=DEFAULT_CONVERSATION_MODEL,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            policy_hashes={**policies, "prompt": "0" * 64},
            source_clean=True,
            evidence_payload=_release_evidence(manifest, policies),
            manifest_sha256="c" * 64,
        )


def test_agent_studio_release_gate_fails_closed_on_dirty_source() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)

    with pytest.raises(AgentStudioReleaseGateError, match="clean Git-visible source"):
        validate_agent_studio_release_gate(
            manifest,
            conversation_model=DEFAULT_CONVERSATION_MODEL,
            reviewer_model=DEFAULT_CONVERSATION_MODEL,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            policy_hashes=policies,
            source_clean=False,
            evidence_payload=_release_evidence(manifest, policies),
            manifest_sha256="c" * 64,
        )


def test_agent_studio_release_gate_requires_reviewed_cutover_evidence() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)
    evidence = _release_evidence(manifest, policies)
    evidence["decision"] = "pending"
    evidence["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in evidence.items() if key != "evidence_sha256"}
    )

    with pytest.raises(AgentStudioReleaseEvidenceError, match="not approved"):
        validate_agent_studio_release_gate(
            manifest,
            conversation_model=DEFAULT_CONVERSATION_MODEL,
            reviewer_model=DEFAULT_CONVERSATION_MODEL,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            policy_hashes=policies,
            source_clean=True,
            evidence_payload=evidence,
            manifest_sha256="c" * 64,
        )
