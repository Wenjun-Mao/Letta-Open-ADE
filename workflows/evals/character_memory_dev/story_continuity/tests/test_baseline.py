"""Real manifest identity, without provider discovery or hash substitution."""

from copy import deepcopy
import json

import pytest

from model_catalog_contracts.deployment_manifest import DeploymentManifest

from ..baseline import (
    MANIFEST,
    SOURCES,
    expected_catalog,
    manifest,
    preparation_binding,
    validate_catalog,
)
from ..schedule import ROOT


def test_exact_baseline_is_unqualified_and_not_a_live_receipt():
    entries = manifest().deployments
    assert {entry.fingerprint.sha256 for entry in entries} == {
        "870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe",
        "c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086",
    }
    for entry in entries:
        assert entry.lifecycle == "candidate"
        assert not entry.qualification.qualified
        assert all(
            result.observed_rounds == 0 for result in entry.qualification.role_results
        )
    assert not any(
        "base_url_env" in source for source in json.loads(SOURCES.read_text())
    )
    assert (
        preparation_binding()["catalog_status"]
        == "expected_configuration_not_live_observation"
    )
    assert len(validate_catalog(expected_catalog())) == 3


@pytest.mark.parametrize(
    "change", ["payload", "digest", "url", "adapter", "missing", "duplicate"]
)
def test_catalog_drift_is_rejected(change):
    catalog = expected_catalog()
    item = catalog["items"][-1]
    if change == "payload":
        item["deployment"]["fingerprint"]["sampling_settings"]["dimensions"] = 512
    elif change == "digest":
        item["deployment"]["fingerprint"]["sha256"] = "0" * 64
    elif change == "url":
        item["source_base_url"] = "http://another-endpoint.invalid/v1"
    elif change == "adapter":
        item["source_adapter"] = "generic_openai"
    elif change == "missing":
        catalog["items"].pop()
    else:
        catalog["items"].append(deepcopy(item))
    with pytest.raises(ValueError):
        validate_catalog(catalog)


def test_vector_space_id_is_not_a_deployment_fingerprint():
    current = DeploymentManifest.from_payload(
        json.loads((ROOT / "config/model-router/deployment-manifest.json").read_text())
    )
    qwen = next(entry for entry in current.deployments if "retriever" in entry.roles)
    baseline = next(
        entry for entry in manifest().deployments if "retriever" in entry.roles
    )
    assert qwen.fingerprint.sha256 != baseline.fingerprint.sha256
    assert (
        qwen.fingerprint.sampling_settings["vector_space"]["id"]
        == baseline.fingerprint.sha256
    )
    # Neither using the new payload nor overwriting its digest is a baseline.
    catalog = expected_catalog()
    catalog["items"][-1]["deployment"] = qwen.as_catalog_dict()
    with pytest.raises(ValueError):
        validate_catalog(catalog)
    catalog["items"][-1]["deployment"]["fingerprint"]["sha256"] = (
        baseline.fingerprint.sha256
    )
    with pytest.raises(ValueError):
        validate_catalog(catalog)


def test_config_file_drift_is_rejected(tmp_path, monkeypatch):
    from .. import baseline

    changed = tmp_path / "manifest.json"
    changed.write_bytes(MANIFEST.read_bytes() + b"\n")
    monkeypatch.setattr(baseline, "MANIFEST", changed)
    with pytest.raises(ValueError, match="configuration changed"):
        baseline.manifest()
