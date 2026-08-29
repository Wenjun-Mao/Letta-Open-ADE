from __future__ import annotations

from collections.abc import Sequence

from .errors import RuntimeValidationError
from .router_transport import RouterTransport


RETRIEVAL_POLICY_VERSION = "qwen3-semantic-facts-v1"
AUTOMATIC_MAXIMUM_COSINE_DISTANCE = 1.0 - 0.6311


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
