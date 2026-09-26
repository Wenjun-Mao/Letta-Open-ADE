"""H4 dispatch counts are observations, while provider routes stay pinned."""

from __future__ import annotations

import asyncio

import pytest

from ade_api.features.agent_runtime.history_native_rank import HISTORY_EMBEDDING_ROUTE
from workflows.evals.character_memory_dev.history_h4_transport import (
    SplitHistoryTransport,
)


class FakeDeepSeek:
    def __init__(self) -> None:
        self.calls = 0

    async def chat_completion(self, payload, *, timeout_seconds):
        self.calls += 1
        return {"choices": []}


class FakeQwen:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, *, inputs, timeout_seconds):
        self.calls += 1
        return [[1.0] for _ in inputs]


def test_h4_dispatch_counts_do_not_gate_provider_calls() -> None:
    async def scenario() -> None:
        deepseek, qwen = FakeDeepSeek(), FakeQwen()
        transport = SplitHistoryTransport(deepseek, qwen)
        for _ in range(97):
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=1
            )
        for _ in range(161):
            await transport.embeddings(
                {"model": HISTORY_EMBEDDING_ROUTE, "input": ["fixture"]},
                timeout_seconds=1,
            )
        assert (transport.generation_dispatches, deepseek.calls) == (97, 97)
        assert (transport.embedding_dispatches, qwen.calls) == (161, 161)

    asyncio.run(scenario())


def test_h4_wrong_routes_still_fail_before_dispatch() -> None:
    async def scenario() -> None:
        deepseek, qwen = FakeDeepSeek(), FakeQwen()
        transport = SplitHistoryTransport(deepseek, qwen)
        with pytest.raises(RuntimeError, match="generation route differs"):
            await transport.chat_completion(
                {"model": "another::model"}, timeout_seconds=1
            )
        with pytest.raises(RuntimeError, match="embedding route differs"):
            await transport.embeddings(
                {"model": "another::embedding", "input": ["fixture"]},
                timeout_seconds=1,
            )
        assert (transport.generation_dispatches, deepseek.calls) == (0, 0)
        assert (transport.embedding_dispatches, qwen.calls) == (0, 0)

    asyncio.run(scenario())
