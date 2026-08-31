from __future__ import annotations

from pathlib import Path

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from workflows.evals.agent_runtime_v3_acceptance.policy import (
    PROJECT_ROOT,
    PRODUCTION_POLICY_INPUTS,
    fingerprint_policy_hashes,
    production_policy_hashes,
)


def test_production_policy_inputs_are_explicit_existing_files() -> None:
    assert set(PRODUCTION_POLICY_INPUTS) == {"prompt", "tool", "schema", "retrieval"}
    for paths in PRODUCTION_POLICY_INPUTS.values():
        assert paths == tuple(sorted(paths))
        assert all((PROJECT_ROOT / path).is_file() for path in paths)


def test_checked_in_manifest_is_bound_to_current_production_policy() -> None:
    manifest = load_deployment_manifest(
        Path("config/model-router/deployment-manifest.json"),
        project_root=PROJECT_ROOT,
    )
    expected = production_policy_hashes()

    assert manifest.deployments
    assert all(
        fingerprint_policy_hashes(deployment.fingerprint) == expected
        for deployment in manifest.deployments
    )


def test_policy_hash_snapshot_cannot_mutate_the_cached_policy() -> None:
    first = production_policy_hashes()
    expected_prompt = first["prompt"]

    first["prompt"] = "0" * 64

    assert production_policy_hashes()["prompt"] == expected_prompt


def test_policy_scripts_are_available_inside_the_ade_api_image() -> None:
    dockerfile = (PROJECT_ROOT / "services/ade-api/Dockerfile").read_text(
        encoding="utf-8"
    )

    for relative_path in PRODUCTION_POLICY_INPUTS["schema"]:
        if relative_path.startswith("scripts/"):
            assert f"COPY {relative_path} ./{relative_path}" in dockerfile
