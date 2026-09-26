"""Subject-bound fact retrieval for automatic context and curated search."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from .embeddings import (
    AUTOMATIC_MAXIMUM_COSINE_DISTANCE,
    EmbeddingClient,
    qwen_query_text,
)
from .errors import RuntimeValidationError
from .turn_memory_snapshot import search_turn_memory
from .turn_memory_views import tool_fact


async def select_automatic_facts(
    *,
    engine: AsyncEngine,
    embeddings: EmbeddingClient,
    deployment: dict[str, Any],
    current_user_content: str,
    subject_id: str,
    fingerprint: str,
    expected_dimensions: int,
    accepted_memory_generation: int,
    natural: bool,
    deadline: float,
) -> list[dict[str, Any]]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("whole runtime attempt timed out")
    vector = (
        await embeddings.embed(
            model_key=str(deployment["route_alias"]),
            inputs=[qwen_query_text(current_user_content)],
            timeout_seconds=remaining,
        )
    )[0]
    if expected_dimensions and len(vector) != expected_dimensions:
        raise RuntimeValidationError(
            "Embedding query dimensions do not match the deployment fingerprint"
        )
    return await search_turn_memory(
        engine,
        subject_id=subject_id,
        query_vector=vector,
        fingerprint=fingerprint,
        limit=8,
        maximum_distance=AUTOMATIC_MAXIMUM_COSINE_DISTANCE,
        accepted_memory_generation=accepted_memory_generation,
        natural=natural,
    )


def search_memory_handler(
    *,
    engine: AsyncEngine,
    embeddings: EmbeddingClient,
    deployment: dict[str, Any],
    subject_id: str,
    fingerprint: str,
    expected_dimensions: int,
    accepted_memory_generation: int,
    natural: bool,
    deadline: float,
) -> Callable[[str, int], Awaitable[list[dict[str, Any]]]]:
    async def search(query: str, limit: int) -> list[dict[str, Any]]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("whole runtime attempt timed out")
        vector = (
            await embeddings.embed(
                model_key=str(deployment["route_alias"]),
                inputs=[qwen_query_text(query)],
                timeout_seconds=remaining,
            )
        )[0]
        if expected_dimensions and len(vector) != expected_dimensions:
            raise RuntimeValidationError(
                "Embedding tool-query dimensions do not match the deployment fingerprint"
            )
        rows = await search_turn_memory(
            engine,
            subject_id=subject_id,
            query_vector=vector,
            fingerprint=fingerprint,
            limit=limit,
            maximum_distance=None,
            accepted_memory_generation=accepted_memory_generation,
            natural=natural,
        )
        return [tool_fact(item) for item in rows]

    return search
