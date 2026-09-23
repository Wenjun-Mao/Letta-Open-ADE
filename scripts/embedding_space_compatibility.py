"""Validate synthetic paired-vector evidence before reusing a relocated space."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from typing import Any

from ade_api.features.agent_runtime.release_evidence import canonical_sha256


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_MAX_COSINE_DISTANCE = 0.001


class EmbeddingCompatibilityError(ValueError):
    pass


def validate_embedding_compatibility_receipt(
    payload: Mapping[str, Any],
    *,
    source_revision: str,
    source_fingerprint: str,
    space_id: str,
    route_alias: str,
    deployment_fingerprint: str,
    origin_url: str,
    candidate_url: str,
    dimensions: int,
) -> str:
    digest = payload.get("artifact_sha256")
    material = {
        key: value for key, value in payload.items() if key != "artifact_sha256"
    }
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise EmbeddingCompatibilityError("embedding receipt digest is invalid")
    if canonical_sha256(material) != digest:
        raise EmbeddingCompatibilityError("embedding receipt content digest differs")
    expected = {
        "schema_version": 1,
        "kind": "ade-embedding-space-compatibility",
        "source_revision": source_revision,
        "source_dirty": False,
        "source_fingerprint": source_fingerprint,
        "space_id": space_id,
        "route_alias": route_alias,
        "deployment_fingerprint": deployment_fingerprint,
        "origin_url": origin_url,
        "candidate_url": candidate_url,
    }
    if any(payload.get(key) != value for key, value in expected.items()):
        raise EmbeddingCompatibilityError(
            "embedding receipt does not bind the evaluated source and routes"
        )
    canaries = payload.get("canaries")
    if not isinstance(canaries, list) or len(canaries) != 2:
        raise EmbeddingCompatibilityError(
            "embedding receipt requires query and document canaries"
        )
    purposes: set[str] = set()
    for canary in canaries:
        if not isinstance(canary, Mapping):
            raise EmbeddingCompatibilityError("embedding canary must be an object")
        purpose = canary.get("purpose")
        if purpose not in {"query", "document"} or purpose in purposes:
            raise EmbeddingCompatibilityError("embedding canary purposes differ")
        purposes.add(purpose)
        input_digest = canary.get("input_sha256")
        if not isinstance(input_digest, str) or not _DIGEST.fullmatch(input_digest):
            raise EmbeddingCompatibilityError(
                "embedding canary input digest is invalid"
            )
        for field in ("origin_request_id", "candidate_request_id"):
            if not isinstance(canary.get(field), str) or not canary[field].strip():
                raise EmbeddingCompatibilityError(
                    "embedding canary request provenance is missing"
                )
        baseline = _vector(canary.get("origin_vector"), dimensions)
        candidate = _vector(canary.get("candidate_vector"), dimensions)
        cosine = sum(a * b for a, b in zip(baseline, candidate, strict=True))
        cosine /= math.sqrt(sum(a * a for a in baseline)) * math.sqrt(
            sum(b * b for b in candidate)
        )
        if 1.0 - min(1.0, cosine) > _MAX_COSINE_DISTANCE:
            raise EmbeddingCompatibilityError(
                "embedding canary vectors are not numerically compatible"
            )
    return digest


def _vector(value: object, dimensions: int) -> list[float]:
    if not isinstance(value, list) or len(value) != dimensions:
        raise EmbeddingCompatibilityError("embedding canary dimensions differ")
    if any(type(item) not in {int, float} for item in value):
        raise EmbeddingCompatibilityError("embedding canary must contain numbers")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result) or not any(result):
        raise EmbeddingCompatibilityError("embedding canary vector is invalid")
    return result
