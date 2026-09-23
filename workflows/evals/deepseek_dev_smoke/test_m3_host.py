import asyncio
from pathlib import Path

import pytest

from workflows.evals.deepseek_dev_smoke.m3_host import BudgetedTransport, RequestLedger


def test_m3_ledger_reserves_before_calls_and_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "m3.sqlite3"
    first = RequestLedger(path, generation_limit=2, embedding_limit=1)
    call_id = first.reserve("generation", "deepseek::deepseek-flash")
    assert first.counts() == {"generation": 1, "embedding": 0}
    reopened = RequestLedger(path, generation_limit=2, embedding_limit=1)
    assert reopened.counts() == {"generation": 1, "embedding": 0}
    reopened.finish(call_id, "failed:TimeoutError")
    reopened.reserve("generation", "deepseek::deepseek-flash")
    reopened.reserve("embedding", "dgx_embedding_sidecar::qwen")
    with pytest.raises(RuntimeError, match="generation provider budget exhausted"):
        reopened.reserve("generation", "deepseek::deepseek-flash")
    with pytest.raises(RuntimeError, match="embedding provider budget exhausted"):
        reopened.reserve("embedding", "dgx_embedding_sidecar::qwen")
    assert reopened.counts() == {"generation": 2, "embedding": 1}
    with pytest.raises(ValueError, match="limits differ"):
        RequestLedger(path, generation_limit=3, embedding_limit=1)


def test_m3_transport_caps_timeout_and_counts_a_failed_send(tmp_path: Path) -> None:
    class FailingRouter:
        def __init__(self) -> None:
            self.calls: list[float] = []

        async def chat_completion(self, payload, *, timeout_seconds):
            self.calls.append(timeout_seconds)
            raise TimeoutError("synthetic provider timeout")

    ledger = RequestLedger(
        tmp_path / "m3.sqlite3", generation_limit=1, embedding_limit=1
    )
    router = FailingRouter()
    transport = BudgetedTransport(router, ledger)

    with pytest.raises(TimeoutError, match="synthetic provider timeout"):
        asyncio.run(
            transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=300
            )
        )
    assert router.calls == [180.0]
    assert ledger.counts()["generation"] == 1
    with pytest.raises(RuntimeError, match="generation provider budget exhausted"):
        asyncio.run(
            transport.chat_completion(
                {"model": "deepseek::deepseek-flash"}, timeout_seconds=180
            )
        )
    assert router.calls == [180.0]
