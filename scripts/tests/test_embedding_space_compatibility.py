from __future__ import annotations

from copy import deepcopy

import pytest

from ade_api.features.agent_runtime.release_evidence import canonical_sha256
from scripts.embedding_space_compatibility import (
    EmbeddingCompatibilityError,
    validate_embedding_compatibility_receipt,
)


BOUND = {
    "source_revision": "a" * 40,
    "source_fingerprint": "b" * 64,
    "space_id": "synthetic-space",
    "route_alias": "embedding::model",
    "deployment_fingerprint": "c" * 64,
    "origin_url": "https://origin.example/v1",
    "candidate_url": "https://candidate.example/v1",
    "dimensions": 3,
}


def _receipt() -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "ade-embedding-space-compatibility",
        "source_revision": BOUND["source_revision"],
        "source_dirty": False,
        "source_fingerprint": BOUND["source_fingerprint"],
        "space_id": BOUND["space_id"],
        "route_alias": BOUND["route_alias"],
        "deployment_fingerprint": BOUND["deployment_fingerprint"],
        "origin_url": BOUND["origin_url"],
        "candidate_url": BOUND["candidate_url"],
        "canaries": [
            {
                "purpose": purpose,
                "input_sha256": index * 64,
                "origin_request_id": f"origin-{purpose}",
                "candidate_request_id": f"candidate-{purpose}",
                "origin_vector": [1.0, 0.0, 0.0],
                "candidate_vector": [1.0, 0.001, 0.0],
            }
            for purpose, index in (("query", "d"), ("document", "e"))
        ],
    }
    payload["artifact_sha256"] = canonical_sha256(payload)
    return payload


def test_relocation_requires_bound_paired_query_and_document_vectors() -> None:
    receipt = _receipt()
    assert (
        validate_embedding_compatibility_receipt(receipt, **BOUND)
        == receipt["artifact_sha256"]
    )


@pytest.mark.parametrize(
    "failure",
    ["different_endpoint", "different_vector", "wrong_dimensions", "tampered_digest"],
)
def test_relocation_receipt_fails_closed(failure: str) -> None:
    receipt = deepcopy(_receipt())
    if failure == "different_endpoint":
        receipt["candidate_url"] = "https://other.example/v1"
    elif failure == "different_vector":
        receipt["canaries"][0]["candidate_vector"] = [0.0, 1.0, 0.0]
    elif failure == "wrong_dimensions":
        receipt["canaries"][0]["candidate_vector"] = [1.0, 0.0]
    else:
        receipt["canaries"][0]["origin_request_id"] = "modified"
    if failure != "tampered_digest":
        receipt["artifact_sha256"] = canonical_sha256(
            {key: value for key, value in receipt.items() if key != "artifact_sha256"}
        )
    with pytest.raises(EmbeddingCompatibilityError):
        validate_embedding_compatibility_receipt(receipt, **BOUND)
