"""H4 uses official DeepSeek and the exact H2 configured Qwen deployment."""

from __future__ import annotations

from typing import Any

from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE

from .history_h2_router import ContainerEmbeddingClient


class SplitHistoryTransport:
    """One catalog, two pinned providers, with observational dispatch counts."""

    def __init__(
        self,
        deepseek,
        qwen: ContainerEmbeddingClient,
    ) -> None:
        self.deepseek = deepseek
        self.qwen = qwen
        self.generation_dispatches = 0
        self.embedding_dispatches = 0

    async def catalog(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        deepseek = await self.deepseek.catalog(timeout_seconds=timeout_seconds)
        qwen = await self.qwen.catalog()
        items = [
            item
            for item in deepseek.get("items", [])
            if item.get("model_key") == "deepseek::deepseek-flash"
        ] + qwen.get("items", [])
        if [item.get("model_key") for item in items] != [
            "deepseek::deepseek-flash",
            HISTORY_EMBEDDING_ROUTE,
        ]:
            raise RuntimeError("H4 provider catalog route set changed")
        return {"items": items}

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        if payload.get("model") != "deepseek::deepseek-flash":
            raise RuntimeError("H4 generation route differs")
        self.generation_dispatches += 1
        return await self.deepseek.chat_completion(
            payload, timeout_seconds=timeout_seconds
        )

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        if payload.get("model") != HISTORY_EMBEDDING_ROUTE:
            raise RuntimeError("H4 embedding route differs")
        self.embedding_dispatches += 1
        vectors = await self.qwen.embed(
            inputs=payload["input"], timeout_seconds=timeout_seconds
        )
        return {
            "data": [
                {"index": index, "embedding": vector}
                for index, vector in enumerate(vectors)
            ]
        }
