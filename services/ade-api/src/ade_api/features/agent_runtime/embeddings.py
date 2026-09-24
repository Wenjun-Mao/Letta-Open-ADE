from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping

from .errors import RuntimeValidationError
from .router_transport import RouterTransport


RETRIEVAL_POLICY_VERSION = "qwen3-semantic-facts-v1"
NATURAL_RETRIEVAL_POLICY_VERSION = "qwen3-lifecycle-facts-v2"
AUTOMATIC_MAXIMUM_COSINE_DISTANCE = 1.0 - 0.6311
# This opaque legacy ID is already present on stored Qwen fact vectors. Keeping
# it as the semantic-space key avoids rewriting vectors when only the endpoint
# or deployment policy fingerprint changes.
QWEN_FACT_SPACE = {
    "id": "c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086",
    "artifact_reference": "Qwen/Qwen3-Embedding-0.6B",
    "artifact_revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
    "dimensions": 1024,
    "query_format": "qwen3-instruct-query-v1",
    "document_format": "typed-fact-lines-v1",
    "pooling": "provider-served",
    "normalization": "provider-served",
    "comparison": "pgvector-cosine-v1",
    "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
}


def embedding_space_key(deployment: Mapping[str, Any]) -> str:
    """Choose a validated vector-space key, or preserve a legacy binding."""

    deployment_fingerprint = str(deployment["fingerprint"])
    fingerprint = deployment.get("fingerprint_payload")
    if not isinstance(fingerprint, Mapping):
        raise RuntimeValidationError("Retriever deployment fingerprint is missing")
    sampling = fingerprint.get("sampling_settings")
    if not isinstance(sampling, Mapping):
        raise RuntimeValidationError("Retriever sampling settings are missing")
    space = sampling.get("vector_space")
    if space is None:
        return deployment_fingerprint
    if space != QWEN_FACT_SPACE:
        raise RuntimeValidationError("Retriever vector space is not supported")
    if (
        fingerprint.get("artifact_reference") != space["artifact_reference"]
        or fingerprint.get("artifact_revision") != space["artifact_revision"]
        or fingerprint.get("served_model") != space["artifact_reference"]
        or sampling.get("dimensions") != space["dimensions"]
        or sampling.get("query_instruction_enabled") is not True
        or sampling.get("strategy") != "semantic"
    ):
        raise RuntimeValidationError("Retriever deployment changed vector semantics")
    return str(space["id"])


def qwen_query_text(query: str) -> str:
    return (
        "Instruct: Retrieve durable user facts relevant to the conversation.\n"
        f"Query: {query.strip()}"
    )


class EmbeddingClient:
    def __init__(self, transport: RouterTransport) -> None:
        self.transport = transport

    async def embed(
        self,
        *,
        model_key: str,
        inputs: Sequence[str],
        timeout_seconds: float,
    ) -> list[list[float]]:
        if not inputs:
            return []
        response = await self.transport.embeddings(
            {"model": model_key, "input": list(inputs)},
            timeout_seconds=timeout_seconds,
        )
        raw_data = response.get("data")
        if not isinstance(raw_data, list) or len(raw_data) != len(inputs):
            raise RuntimeValidationError(
                "Embedding response count did not match the request"
            )
        ordered: list[list[float] | None] = [None] * len(inputs)
        for raw_item in raw_data:
            if not isinstance(raw_item, dict):
                raise RuntimeValidationError(
                    "Embedding response item must be an object"
                )
            index = raw_item.get("index")
            vector = raw_item.get("embedding")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(inputs)
                or not isinstance(vector, list)
                or not vector
            ):
                raise RuntimeValidationError("Embedding response item is malformed")
            try:
                values = [float(value) for value in vector]
            except (TypeError, ValueError) as exc:
                raise RuntimeValidationError(
                    "Embedding vector must contain numbers"
                ) from exc
            if ordered[index] is not None:
                raise RuntimeValidationError("Embedding response index was duplicated")
            ordered[index] = values
        if any(item is None for item in ordered):
            raise RuntimeValidationError("Embedding response omitted an index")
        return [item for item in ordered if item is not None]
