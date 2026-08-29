from __future__ import annotations

from copy import deepcopy

import pytest

from model_catalog_contracts.deployment_manifest import (
    DeploymentFingerprint,
    DeploymentManifest,
    DeploymentManifestError,
)


def _fingerprint() -> dict[str, object]:
    return {
        "provider": "embedding-source",
        "endpoint_role": "openai-compatible-embeddings",
        "endpoint_identity": "embedding-host:8001",
        "served_model": "provider-embedding-model",
        "artifact_reference": "org/embedding-model",
        "artifact_revision": "a" * 40,
        "artifact_sha256": None,
        "runtime_implementation": "vllm",
        "runtime_version": "0.12.0",
        "runtime_image_digest": "b" * 64,
        "prompt_policy_sha256": "c" * 64,
        "tool_policy_sha256": "d" * 64,
        "schema_policy_sha256": "e" * 64,
        "retrieval_policy_sha256": "f" * 64,
        "sampling_settings": {"dimensions": 1024},
        "context_settings": {"request_timeout_seconds": 15},
        "hardware_metadata": {"accelerator": "test-gpu"},
    }


def _manifest_payload(*, alias: str = "source::embedding-model") -> dict[str, object]:
    fingerprint = _fingerprint()
    fingerprint_sha256 = DeploymentFingerprint.from_payload(fingerprint).sha256
    return {
        "schema_version": 1,
        "deployments": [
            {
                "id": "embedding-deployment",
                "route_aliases": [alias],
                "roles": ["retriever"],
                "lifecycle": "candidate",
                "fingerprint": fingerprint,
                "qualification": {
                    "fingerprint_sha256": fingerprint_sha256,
                    "qualified": False,
                    "stale_round_count": 0,
                    "role_results": [
                        {
                            "role": "retriever",
                            "observed_rounds": 2,
                            "consecutive_passing_rounds": 2,
                            "qualified": False,
                        }
                    ],
                },
            }
        ],
    }


def test_manifest_uses_alias_only_as_a_lookup_selector() -> None:
    original = DeploymentManifest.from_payload(_manifest_payload())
    renamed_payload = _manifest_payload(alias="source::renamed-embedding-model")
    renamed = DeploymentManifest.from_payload(renamed_payload)

    deployment = original.for_route_alias("source::embedding-model")

    assert deployment is not None
    assert deployment.fingerprint.sha256 == renamed.deployments[0].fingerprint.sha256
    assert renamed.for_route_alias("source::embedding-model") is None
    assert renamed.for_route_alias("source::renamed-embedding-model") is not None
    assert deployment.as_catalog_dict() == {
        "deployment_id": "embedding-deployment",
        "roles": ["retriever"],
        "lifecycle": "candidate",
        "fingerprint": {
            **deployment.fingerprint.as_dict(),
            "sha256": deployment.fingerprint.sha256,
        },
        "qualification": deployment.qualification.as_dict(),
    }
    assert "route_aliases" not in deployment.as_catalog_dict()


def test_manifest_rejects_qualification_for_a_different_fingerprint() -> None:
    payload = deepcopy(_manifest_payload())
    payload["deployments"][0]["qualification"]["fingerprint_sha256"] = "0" * 64  # type: ignore[index]

    with pytest.raises(DeploymentManifestError, match="exact fingerprint"):
        DeploymentManifest.from_payload(payload)
