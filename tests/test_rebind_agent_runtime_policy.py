from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
)

from scripts.rebind_agent_runtime_policy import rebind_manifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "config/model-router/deployment-manifest.json"


def _manifest_payload() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_rebind_updates_policy_identity_and_invalidates_qualification() -> None:
    payload = _manifest_payload()
    first = payload["deployments"][0]
    first["lifecycle"] = "qualified"
    first["qualification"]["qualified"] = True
    for result in first["qualification"]["role_results"]:
        result.update(
            observed_rounds=3,
            consecutive_passing_rounds=3,
            qualified=True,
        )
    DeploymentManifest.from_payload(payload)

    policy_hashes = {
        "prompt": "1" * 64,
        "tool": "2" * 64,
        "schema": "3" * 64,
        "retrieval": "4" * 64,
    }
    rebound = rebind_manifest(payload, policy_hashes)
    manifest = DeploymentManifest.from_payload(rebound)

    assert manifest.deployments[0].lifecycle == "candidate"
    assert manifest.deployments[-1].lifecycle == "discovered"
    for deployment in manifest.deployments:
        assert deployment.fingerprint.prompt_policy_sha256 == "1" * 64
        assert deployment.fingerprint.tool_policy_sha256 == "2" * 64
        assert deployment.fingerprint.schema_policy_sha256 == "3" * 64
        assert deployment.fingerprint.retrieval_policy_sha256 == "4" * 64
        assert not deployment.qualification.qualified
        assert deployment.qualification.stale_round_count == 0
        assert all(
            result.observed_rounds == 0
            and result.consecutive_passing_rounds == 0
            and not result.qualified
            for result in deployment.qualification.role_results
        )


def test_rebind_is_idempotent_for_an_unqualified_manifest() -> None:
    policy_hashes = {
        "prompt": "a" * 64,
        "tool": "b" * 64,
        "schema": "c" * 64,
        "retrieval": "d" * 64,
    }
    rebound = rebind_manifest(_manifest_payload(), policy_hashes)

    assert rebind_manifest(rebound, policy_hashes) == rebound


def test_rebind_preserves_qualification_when_policy_identity_is_current() -> None:
    payload = _manifest_payload()
    first = payload["deployments"][0]
    first["lifecycle"] = "qualified"
    first["qualification"]["qualified"] = True
    for result in first["qualification"]["role_results"]:
        result.update(
            observed_rounds=3,
            consecutive_passing_rounds=3,
            qualified=True,
        )
    policy_hashes = {
        "prompt": first["fingerprint"]["prompt_policy_sha256"],
        "tool": first["fingerprint"]["tool_policy_sha256"],
        "schema": first["fingerprint"]["schema_policy_sha256"],
        "retrieval": first["fingerprint"]["retrieval_policy_sha256"],
    }
    policy_fields = {
        "prompt": "prompt_policy_sha256",
        "tool": "tool_policy_sha256",
        "schema": "schema_policy_sha256",
        "retrieval": "retrieval_policy_sha256",
    }
    for deployment in payload["deployments"][1:]:
        for policy_name, field in policy_fields.items():
            deployment["fingerprint"][field] = policy_hashes[policy_name]
        deployment["qualification"]["fingerprint_sha256"] = (
            DeploymentFingerprint.from_payload(deployment["fingerprint"]).sha256
        )
    DeploymentManifest.from_payload(payload)

    assert rebind_manifest(payload, policy_hashes) == payload
