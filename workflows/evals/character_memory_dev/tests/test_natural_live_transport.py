from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from workflows.evals.character_memory_dev.natural_live_transport import (
    NaturalLiveTransport,
    RequestScope,
)


class FakeRouter:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def catalog(self, *, timeout_seconds: float):
        return {"items": []}

    async def chat_completion(self, payload, *, timeout_seconds):
        self.sent.append("generation")
        return {
            "choices": [{"message": {"content": "ok", "reasoning_content": "private"}}]
        }

    async def embeddings(self, payload, *, timeout_seconds):
        self.sent.append("embedding")
        return {"data": [{"embedding": [1.0]}]}


def _transport(tmp_path: Path) -> tuple[NaturalLiveTransport, FakeRouter]:
    router = FakeRouter()
    transport = NaturalLiveTransport(
        router,
        capture_dir=tmp_path / "captures",
        generation_model="deepseek::deepseek-flash",
        embedding_model="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
    )
    return transport, router


def test_setup_and_run_calls_count_without_caps_and_capture_redacts(
    tmp_path: Path,
) -> None:
    transport, router = _transport(tmp_path)

    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="unscoped"):
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )
        assert await transport.catalog() == {"items": []}
        with transport.scope(RequestScope("setup")):
            await transport.embeddings(
                {
                    "model": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                    "input": ["x"],
                },
                timeout_seconds=180,
            )
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )
        with transport.scope(RequestScope("cell")):
            with pytest.raises(RuntimeError, match="route differs"):
                await transport.chat_completion(
                    {"model": "spark::chat"}, timeout_seconds=180
                )
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )

    asyncio.run(scenario())
    assert router.sent == ["embedding", "generation", "generation", "generation"]
    assert sum(group["attempted"] for group in transport.counts()["groups"]) == 4
    capture = json.loads(
        (tmp_path / "captures" / "setup-generation-001.json").read_text()
    )
    assert (
        capture["response"]["choices"][0]["message"]["reasoning_content"]
        == "[redacted]"
    )


def test_capture_failure_preserves_success_and_original_exception(
    tmp_path: Path,
) -> None:
    transport, router = _transport(tmp_path)
    # A path occupied by a directory makes the optional capture fail.
    (transport.capture_dir / "cell-generation-001.json").mkdir()

    async def scenario() -> None:
        with transport.scope(RequestScope("cell")):
            assert await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=300
            )

        async def failure(payload, *, timeout_seconds):
            raise TimeoutError("original provider failure")

        router.chat_completion = failure
        with transport.scope(RequestScope("cell")):
            with pytest.raises(TimeoutError, match="original provider failure"):
                await transport.chat_completion(
                    {"model": "deepseek::deepseek-flash"}, timeout_seconds=300
                )

    asyncio.run(scenario())
    groups = transport.counts()["groups"]
    assert sum(group["completed"] for group in groups) == 1
    assert sum(group["failed"] for group in groups) == 1


def test_event_capture_failure_never_changes_provider_outcome(tmp_path: Path) -> None:
    transport, router = _transport(tmp_path)

    class BrokenEvents:
        def append(self, _event):
            raise OSError("observation is unavailable")

        def __iter__(self):
            return iter(())

    transport._events = BrokenEvents()

    async def scenario() -> None:
        with transport.scope(RequestScope("cell")):
            assert await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=30
            )

        async def failure(payload, *, timeout_seconds):
            raise TimeoutError("original provider failure")

        router.chat_completion = failure
        with transport.scope(RequestScope("cell")):
            with pytest.raises(TimeoutError, match="original provider failure"):
                await transport.chat_completion(
                    {"model": "deepseek::deepseek-flash"}, timeout_seconds=30
                )

    asyncio.run(scenario())
    assert transport.counts() == {"complete": False, "groups": []}
