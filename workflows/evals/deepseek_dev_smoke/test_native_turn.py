from __future__ import annotations

import asyncio

import pytest

from workflows.evals.deepseek_dev_smoke.native_turn import CappedNativeTransport


class _Transport:
    def __init__(self) -> None:
        self.chat_count = 0
        self.embedding_count = 0

    async def chat_completion(self, payload, *, timeout_seconds):
        self.chat_count += 1
        assert timeout_seconds <= 180
        return {}

    async def embeddings(self, payload, *, timeout_seconds):
        self.embedding_count += 1
        assert timeout_seconds <= 180
        return {}


def test_native_probe_reserves_and_caps_outbound_calls_before_transport() -> None:
    async def scenario() -> None:
        inner = _Transport()
        transport = CappedNativeTransport(inner)
        for _ in range(2):
            await transport.chat_completion({}, timeout_seconds=600)
        for _ in range(3):
            await transport.embeddings({}, timeout_seconds=600)
        with pytest.raises(RuntimeError, match="generation reservation exhausted"):
            await transport.chat_completion({}, timeout_seconds=600)
        with pytest.raises(RuntimeError, match="embedding reservation exhausted"):
            await transport.embeddings({}, timeout_seconds=600)
        assert (inner.chat_count, inner.embedding_count) == (2, 3)

    asyncio.run(scenario())
