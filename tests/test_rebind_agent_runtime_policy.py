from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)

from scripts.rebind_agent_runtime_policy import rebind_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "config/model-router/deployment-manifest.json"
POLICY_HASHES = {
    "prompt": "1" * 64,
    "tool": "2" * 64,
    "schema": "3" * 64,
    "retrieval": "4" * 64,
}


def _manifest_payload() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _mark_first_deployment_qualified(payload: dict[str, Any]) -> None:
    deployment = payload["deployments"][0]
    deployment["lifecycle"] = "qualified"
    deployment["qualification"]["qualified"] = True
    for result in deployment["qualification"]["role_results"]:
        result.update(
            observed_rounds=3,
            consecutive_passing_rounds=3,
            qualified=True,
        )


def test_rebind_invalidates_every_qualification_when_policy_identity_changes() -> None:
    payload = _manifest_payload()
    _mark_first_deployment_qualified(payload)
    DeploymentManifest.from_payload(payload)

    rebound = rebind_manifest(payload, POLICY_HASHES)
    manifest = DeploymentManifest.from_payload(rebound)

    for deployment in manifest.deployments:
        assert deployment.fingerprint.prompt_policy_sha256 == POLICY_HASHES["prompt"]
        assert deployment.fingerprint.tool_policy_sha256 == POLICY_HASHES["tool"]
        assert deployment.fingerprint.schema_policy_sha256 == POLICY_HASHES["schema"]
        assert (
            deployment.fingerprint.retrieval_policy_sha256 == POLICY_HASHES["retrieval"]
        )
        assert not deployment.qualification.qualified
        assert deployment.qualification.stale_round_count == 0
        assert all(
            result.observed_rounds == 0
            and result.consecutive_passing_rounds == 0
            and not result.qualified
            for result in deployment.qualification.role_results
        )
    assert manifest.deployments[0].lifecycle == "candidate"


def test_rebind_is_idempotent_when_the_policy_identity_is_already_current() -> None:
    payload = _manifest_payload()
    for deployment in payload["deployments"]:
        fingerprint = deployment["fingerprint"]
        fingerprint.update(
            {
                "prompt_policy_sha256": POLICY_HASHES["prompt"],
                "tool_policy_sha256": POLICY_HASHES["tool"],
                "schema_policy_sha256": POLICY_HASHES["schema"],
                "retrieval_policy_sha256": POLICY_HASHES["retrieval"],
            }
        )
        deployment["qualification"]["fingerprint_sha256"] = (
            DeploymentFingerprint.from_payload(fingerprint).sha256
        )

    assert rebind_manifest(payload, POLICY_HASHES) == payload


def test_rebind_rejects_an_incomplete_policy_hash_set() -> None:
    with pytest.raises(ValueError, match="prompt, tool, schema, and retrieval"):
        rebind_manifest(_manifest_payload(), {"prompt": "1" * 64})
