from __future__ import annotations

from dataclasses import replace

import pytest

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from ade_api.features.agent_runtime_v3.release_evidence import (
    REQUIRED_CAPABILITY_EVIDENCE,
    REQUIRED_CONFORMANCE_TESTS,
    AgentStudioReleaseEvidenceError,
    canonical_sha256,
    validate_agent_studio_release_evidence,
)
from ade_api.features.agent_runtime_v3.release_policy import (
    AGENT_STUDIO_RELEASE_ROUTES,
)
from scripts.check_agent_studio_release_gate import PROJECT_ROOT
from workflows.evals.agent_runtime_v3_acceptance.policy import (
    production_policy_hashes,
)


def _qualified_manifest():
    manifest = load_deployment_manifest(
        PROJECT_ROOT / "config/model-router/deployment-manifest.json"
    )
    policies = production_policy_hashes(PROJECT_ROOT)
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


def _payload(manifest, policies):
    qualified_routes = {}
    for role, route_alias in AGENT_STUDIO_RELEASE_ROUTES.items():
        deployment = manifest.for_route_alias(route_alias)
        assert deployment is not None
        qualified_routes[role] = {
            "route_alias": route_alias,
            "deployment_id": deployment.deployment_id,
            "fingerprint_sha256": deployment.fingerprint.sha256,
        }
    payload = {
        "schema_version": 2,
        "kind": "ade-agent-studio-cutover-evidence",
        "decision": "approved",
        "reviewed_by": "release-reviewer",
        "reviewed_at": "2026-09-03T00:00:00Z",
        "evaluated_source": {
            "revision": "a" * 40,
            "dirty": False,
            "fingerprint": "b" * 64,
        },
        "manifest_sha256": "c" * 64,
        "policy_hashes": policies,
        "qualified_routes": qualified_routes,
        "qualification": {
            "run_id": "qualification-1",
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
            "run_id": "parity-1",
            "passed": True,
            "inputs_comparable": True,
            "cleanup_complete": True,
            "rounds_requested": 3,
            "rounds_completed": 3,
            "rounds_passed": 3,
            "native_rounds_passed": 3,
            "legacy_rounds_passed": 0,
            "native_not_worse_than_legacy": True,
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
            capability: {
                "status": "passed",
                "evidence_kind": (
                    "paired-parity"
                    if capability == "memory_correctness"
                    else (
                        "deterministic-contract"
                        if capability in {"timeout_retry_ownership", "cancellation"}
                        else "native-qualification"
                    )
                ),
                "artifact_sha256": (
                    "a" * 64
                    if capability == "memory_correctness"
                    else (
                        "b" * 64
                        if capability in {"timeout_retry_ownership", "cancellation"}
                        else "d" * 64
                    )
                ),
                "references": ["chat_memory_baseline"],
            }
            for capability in REQUIRED_CAPABILITY_EVIDENCE
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


def _validate(payload, manifest, policies):
    return validate_agent_studio_release_evidence(
        payload,
        manifest=manifest,
        manifest_sha256="c" * 64,
        policy_hashes=policies,
        release_routes=AGENT_STUDIO_RELEASE_ROUTES,
    )


def test_release_evidence_binds_every_cutover_gate() -> None:
    manifest, policies = _qualified_manifest()
    payload = _payload(manifest, policies)
    evidence = _validate(payload, manifest, policies)

    assert evidence.qualification_run_id == "qualification-1"
    assert evidence.parity_run_id == "parity-1"
    assert payload["paired_parity"]["legacy_rounds_passed"] == 0


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload["paired_parity"].update(native_rounds_passed=2),
            "native_rounds_passed=3",
        ),
        (
            lambda payload: payload["paired_parity"].update(rounds_passed=2),
            "rounds_passed must equal native_rounds_passed",
        ),
        (
            lambda payload: payload["paired_parity"].update(rounds_completed=3.0),
            "rounds_completed must be an integer from 0 to 3",
        ),
        (
            lambda payload: payload["paired_parity"].update(legacy_rounds_passed=4),
            "legacy_rounds_passed must be an integer from 0 to 3",
        ),
        (
            lambda payload: payload["paired_parity"].update(legacy_rounds_passed=True),
            "legacy_rounds_passed must be an integer from 0 to 3",
        ),
        (
            lambda payload: payload["paired_parity"].update(
                native_not_worse_than_legacy=False
            ),
            "native_not_worse_than_legacy=true",
        ),
        (
            lambda payload: payload.update(schema_version=1),
            "schema_version must be 2",
        ),
        (
            lambda payload: payload["qualification"]["llama_compatibility"].update(
                passed=False
            ),
            "llama-server compatibility",
        ),
        (
            lambda payload: payload["capability_evidence"].pop("cancellation"),
            "capability evidence is incomplete",
        ),
        (
            lambda payload: payload["capability_evidence"][
                "timeout_retry_ownership"
            ].update(artifact_sha256="f" * 64),
            "not bound to its reviewed artifact",
        ),
        (
            lambda payload: payload["conformance"].update(test_paths=[]),
            "conformance suite is incomplete",
        ),
        (
            lambda payload: payload["rollback_rehearsal"].update(
                native_state_preserved=False
            ),
            "native_state_preserved=true",
        ),
        (
            lambda payload: payload["rollback_rehearsal"].update(
                legacy_web_api_write_passed=False
            ),
            "legacy_web_api_write_passed=true",
        ),
    ],
)
def test_release_evidence_fails_closed_on_missing_gate(mutate, message) -> None:
    manifest, policies = _qualified_manifest()
    payload = _payload(manifest, policies)
    mutate(payload)
    payload["evidence_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "evidence_sha256"}
    )

    with pytest.raises(AgentStudioReleaseEvidenceError, match=message):
        _validate(payload, manifest, policies)


def test_release_evidence_rejects_tampering_before_semantic_validation() -> None:
    manifest, policies = _qualified_manifest()
    payload = _payload(manifest, policies)
    payload["reviewed_by"] = "someone-else"

    with pytest.raises(AgentStudioReleaseEvidenceError, match="digest"):
        _validate(payload, manifest, policies)
