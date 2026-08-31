from __future__ import annotations

from dataclasses import replace

import pytest

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from scripts.check_native_preview_gate import (
    DEFAULT_CONVERSATION_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    NativePreviewGateError,
    PROJECT_ROOT,
    validate_native_preview_gate,
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


def test_native_preview_gate_requires_all_exact_promoted_roles() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)

    validate_native_preview_gate(
        manifest,
        conversation_model=DEFAULT_CONVERSATION_MODEL,
        reviewer_model=DEFAULT_CONVERSATION_MODEL,
        embedding_model=DEFAULT_EMBEDDING_MODEL,
        policy_hashes=policies,
        source_clean=True,
    )


def test_native_preview_gate_fails_closed_on_stale_policy() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)

    with pytest.raises(NativePreviewGateError, match="stale policy"):
        validate_native_preview_gate(
            manifest,
            conversation_model=DEFAULT_CONVERSATION_MODEL,
            reviewer_model=DEFAULT_CONVERSATION_MODEL,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            policy_hashes={**policies, "prompt": "0" * 64},
            source_clean=True,
        )


def test_native_preview_gate_fails_closed_on_dirty_source() -> None:
    manifest, policies = _qualified_manifest(PROJECT_ROOT)

    with pytest.raises(NativePreviewGateError, match="clean Git-visible source"):
        validate_native_preview_gate(
            manifest,
            conversation_model=DEFAULT_CONVERSATION_MODEL,
            reviewer_model=DEFAULT_CONVERSATION_MODEL,
            embedding_model=DEFAULT_EMBEDDING_MODEL,
            policy_hashes=policies,
            source_clean=False,
        )
