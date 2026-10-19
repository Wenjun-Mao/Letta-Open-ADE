"""New candidate identities never rewrite or inherit native release results."""

import hashlib
import json

from workflows.evals.hindsight_integration.deployment_config import (
    PROJECT_ROOT,
    OUTPUT,
    candidate_manifest,
)
from model_catalog_contracts.deployment_manifest import DeploymentManifest


def test_stage1_configuration_is_current_unqualified_and_preserves_incumbent():
    original = PROJECT_ROOT / "config/model-router/deployment-manifest.json"
    before = hashlib.sha256(original.read_bytes()).hexdigest()
    payload = candidate_manifest()
    manifest = DeploymentManifest.from_payload(payload)
    assert len(manifest.deployments) == 1
    entry = manifest.deployments[0]
    assert entry.roles == ("conversation", "compaction")
    assert entry.lifecycle == "candidate" and not entry.qualification.qualified
    assert all(
        item.observed_rounds == item.consecutive_passing_rounds == 0
        for item in entry.qualification.role_results
    )
    assert hashlib.sha256(original.read_bytes()).hexdigest() == before
    assert json.loads((PROJECT_ROOT / OUTPUT).read_text()) == payload
