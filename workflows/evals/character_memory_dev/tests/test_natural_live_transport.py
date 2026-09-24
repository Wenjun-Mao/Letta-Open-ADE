from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from ade_api.features.agent_runtime.request_budget import (
    BudgetedTransport,
    RequestLedger,
)
from workflows.evals.character_memory_dev.natural_live_transport import (
    NaturalLiveTransport,
    RequestScope,
)


class FakeRouter:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.ledger: RequestLedger | None = None

    async def catalog(self, *, timeout_seconds: float):
        return {"items": []}

    async def chat_completion(self, payload, *, timeout_seconds):
        assert self.ledger is not None
        assert self.ledger.counts()["generation"] == self.sent.count("generation") + 1
        self.sent.append("generation")
        return {
            "choices": [{"message": {"content": "ok", "reasoning_content": "private"}}]
        }

    async def embeddings(self, payload, *, timeout_seconds):
        assert self.ledger is not None
        assert self.ledger.counts()["embedding"] == 1
        self.sent.append("embedding")
        return {"data": [{"embedding": [1.0]}]}


def _transport(
    tmp_path: Path,
) -> tuple[NaturalLiveTransport, RequestLedger, FakeRouter]:
    router = FakeRouter()
    ledger = RequestLedger(
        tmp_path / "ledger.sqlite3", generation_limit=2, embedding_limit=1
    )
    router.ledger = ledger
    transport = NaturalLiveTransport(
        BudgetedTransport(router, ledger),
        capture_dir=tmp_path / "captures",
        generation_model="deepseek::deepseek-flash",
        embedding_model="dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
    )
    return transport, ledger, router


def test_all_outbound_paths_reserve_before_send_and_capture_redacted_raw_response(
    tmp_path: Path,
) -> None:
    transport, ledger, router = _transport(tmp_path)

    async def scenario() -> None:
        with pytest.raises(RuntimeError, match="unscoped"):
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )
        assert await transport.catalog() == {"items": []}
        with transport.scope(RequestScope("setup", 1, 1)):
            await transport.embeddings(
                {
                    "model": "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
                    "input": ["synthetic"],
                },
                timeout_seconds=180,
            )
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash", "messages": []},
                timeout_seconds=180,
            )
            with pytest.raises(RuntimeError, match="schedule exhausted"):
                await transport.chat_completion(
                    {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
                )
        with transport.scope(RequestScope("cell", 1, 0)):
            with pytest.raises(RuntimeError, match="route differs"):
                await transport.chat_completion(
                    {"model": "spark::chat"}, timeout_seconds=180
                )
            await transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )

    asyncio.run(scenario())
    assert router.sent == ["embedding", "generation", "generation"]
    assert ledger.counts() == {"generation": 2, "embedding": 1}
    captures = list((tmp_path / "captures").glob("*.json"))
    assert len(captures) == 3
    generation = json.loads(
        (tmp_path / "captures" / "setup-generation-001.json").read_text()
    )
    assert generation["ledger_before"]["generation"] == 0
    assert generation["ledger_after"]["generation"] == 1
    assert (
        generation["response"]["choices"][0]["message"]["reasoning_content"]
        == "[redacted]"
    )
    assert all(path.stat().st_mode & 0o077 == 0 for path in captures)


def test_failed_send_remains_spent_and_is_captured(tmp_path: Path) -> None:
    transport, ledger, router = _transport(tmp_path)

    async def failure(payload, *, timeout_seconds):
        assert ledger.counts()["generation"] == 1
        raise TimeoutError("synthetic")

    router.chat_completion = failure

    async def scenario() -> None:
        with transport.scope(RequestScope("cell", 1, 0)):
            with pytest.raises(TimeoutError):
                await transport.chat_completion(
                    {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
                )

    asyncio.run(scenario())
    assert ledger.counts()["generation"] == 1
    capture = json.loads(
        (tmp_path / "captures" / "cell-generation-001.json").read_text()
    )
    assert capture["outcome"] == "failed"
    assert capture["error_type"] == "TimeoutError"
