from __future__ import annotations

from pathlib import Path

from model_catalog_contracts.deployment_manifest import load_deployment_manifest

from workflows.evals.agent_runtime_acceptance.policy import (
    PROJECT_ROOT,
    fingerprint_policy_hashes,
    production_policy_hashes,
)
from ade_api.features.agent_runtime.release_policy import (
    POLICY_INPUT_FILES,
    POLICY_INPUT_ROOTS,
)


def test_production_policy_inputs_are_existing_roots_and_files() -> None:
    assert set(POLICY_INPUT_ROOTS) == {"prompt", "tool", "schema", "retrieval"}
    assert set(POLICY_INPUT_FILES) == set(POLICY_INPUT_ROOTS)
    for paths in POLICY_INPUT_ROOTS.values():
        assert paths == tuple(sorted(paths))
        assert all((PROJECT_ROOT / path).is_dir() for path in paths)
    for paths in POLICY_INPUT_FILES.values():
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


def test_governed_policy_sources_are_available_inside_the_ade_api_image() -> None:
    dockerfile = (PROJECT_ROOT / "services/ade-api/Dockerfile").read_text(
        encoding="utf-8"
    )

    assert "COPY scripts ./scripts" in dockerfile
    assert "COPY config ./config" in dockerfile
    assert "COPY content ./content" in dockerfile
    assert "COPY services/ade-api ./services/ade-api" in dockerfile
    assert (
        "COPY services/model-router/src/model_router "
        "./services/model-router/src/model_router"
    ) in dockerfile
