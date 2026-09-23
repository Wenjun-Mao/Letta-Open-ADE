from __future__ import annotations

import asyncio
from copy import deepcopy

import pytest

from model_catalog_contracts.deployment_manifest import DeploymentFingerprint

from ade_api.features.agent_runtime.embeddings import (
    QWEN_FACT_SPACE,
    EmbeddingClient,
    embedding_space_key,
    qwen_query_text,
)
from ade_api.features.agent_runtime.errors import RuntimeValidationError


class _Transport:
    def __init__(self, response):
        self.response = response
        self.payload = None

    async def embeddings(self, payload, *, timeout_seconds):
        self.payload = payload
        assert timeout_seconds == 5
        return self.response


def test_embedding_response_is_restored_to_input_order() -> None:
    transport = _Transport(
        {
            "data": [
                {"index": 1, "embedding": [0, 1]},
                {"index": 0, "embedding": [1, 0]},
            ]
        }
    )
    result = asyncio.run(
        EmbeddingClient(transport).embed(
            model_key="source::embedding", inputs=["a", "b"], timeout_seconds=5
        )
    )
    assert result == [[1.0, 0.0], [0.0, 1.0]]
    assert transport.payload["model"] == "source::embedding"


def test_embedding_response_rejects_duplicate_indexes() -> None:
    transport = _Transport(
        {
            "data": [
                {"index": 0, "embedding": [1]},
                {"index": 0, "embedding": [2]},
            ]
        }
    )
    with pytest.raises(RuntimeValidationError, match="duplicated"):
        asyncio.run(
            EmbeddingClient(transport).embed(
                model_key="source::embedding",
                inputs=["a", "b"],
                timeout_seconds=5,
            )
        )


def _retriever_deployment(endpoint: str) -> dict[str, object]:
    fingerprint = {
        "provider": "embedding-service",
        "endpoint_role": "openai-compatible-embeddings",
        "endpoint_identity": endpoint,
        "served_model": QWEN_FACT_SPACE["artifact_reference"],
        "artifact_reference": QWEN_FACT_SPACE["artifact_reference"],
        "artifact_revision": QWEN_FACT_SPACE["artifact_revision"],
        "artifact_sha256": None,
        "runtime_implementation": "vllm",
        "runtime_version": "test",
        "runtime_image_digest": None,
        "prompt_policy_sha256": "1" * 64,
        "tool_policy_sha256": "2" * 64,
        "schema_policy_sha256": "3" * 64,
        "retrieval_policy_sha256": "4" * 64,
        "sampling_settings": {
            "dimensions": 1024,
            "query_instruction_enabled": True,
            "strategy": "semantic",
            "vector_space": deepcopy(QWEN_FACT_SPACE),
        },
        "context_settings": {},
        "hardware_metadata": {},
    }
    return {
        "fingerprint": DeploymentFingerprint.from_payload(fingerprint).sha256,
        "fingerprint_payload": fingerprint,
    }


def test_same_semantic_space_survives_endpoint_change_but_deployment_does_not() -> None:
    original = _retriever_deployment("spark:8001")
    relocated = _retriever_deployment("embedding.example:443")

    assert original["fingerprint"] != relocated["fingerprint"]
    assert embedding_space_key(original) == embedding_space_key(relocated)
    assert embedding_space_key(original) == QWEN_FACT_SPACE["id"]
    assert qwen_query_text(" tea ") == (
        "Instruct: Retrieve durable user facts relevant to the conversation.\n"
        "Query: tea"
    )


def test_old_snapshot_keeps_existing_vector_key_without_rewriting_history() -> None:
    original = _retriever_deployment("spark:8001")
    fingerprint = original["fingerprint_payload"]
    assert isinstance(fingerprint, dict)
    del fingerprint["sampling_settings"]["vector_space"]
    assert embedding_space_key(original) == original["fingerprint"]


@pytest.mark.parametrize("change", ["dimensions", "artifact", "query_format"])
def test_changed_semantic_space_cannot_reuse_old_vectors(change: str) -> None:
    deployment = _retriever_deployment("embedding.example:443")
    fingerprint = deployment["fingerprint_payload"]
    assert isinstance(fingerprint, dict)
    if change == "dimensions":
        fingerprint["sampling_settings"]["dimensions"] = 768
    elif change == "artifact":
        fingerprint["artifact_revision"] = "new-revision"
    else:
        fingerprint["sampling_settings"]["vector_space"]["query_format"] = "other"
    with pytest.raises(RuntimeValidationError, match="vector|semantics"):
        embedding_space_key(deployment)
