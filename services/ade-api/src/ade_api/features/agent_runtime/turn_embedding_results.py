"""Embed only the accepted review's value-bearing memory operations."""

from __future__ import annotations

from typing import Any

from .embeddings import EmbeddingClient
from .errors import RuntimeValidationError
from .memory_policy import PreparedMemoryReview
from .natural_memory_policy import PreparedNaturalReview
from .natural_attempt_evidence import NaturalAttemptEvidence
from .turn_memory_views import fact_document


async def embed_review_operations(
    *,
    client: EmbeddingClient,
    deployment: dict[str, Any],
    review: PreparedMemoryReview | PreparedNaturalReview,
    expected_dimensions: int,
    timeout_seconds: float,
    evidence: NaturalAttemptEvidence | None,
) -> tuple[tuple[list[float] | None, ...], int]:
    embeddable = [
        operation for operation in review.operations if operation.value is not None
    ]
    vectors = await client.embed(
        model_key=str(deployment["route_alias"]),
        inputs=[fact_document(item) for item in embeddable],
        timeout_seconds=timeout_seconds,
    )
    vector_iterator = iter(vectors)
    operation_embeddings = tuple(
        None if operation.value is None else next(vector_iterator)
        for operation in review.operations
    )
    dimensions = len(vectors[0]) if vectors else expected_dimensions
    if expected_dimensions and vectors and dimensions != expected_dimensions:
        raise RuntimeValidationError(
            "Embedding dimensions do not match the deployment fingerprint"
        )
    if evidence is not None:
        try:
            evidence.capture_embeddings(len(vectors), dimensions)
        except Exception:
            pass
    return operation_embeddings, dimensions
