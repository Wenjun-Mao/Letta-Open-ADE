from __future__ import annotations

import asyncio

import pytest

from ade_api.features.agent_runtime_v3.embeddings import EmbeddingClient
from ade_api.features.agent_runtime_v3.errors import RuntimeValidationError


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
