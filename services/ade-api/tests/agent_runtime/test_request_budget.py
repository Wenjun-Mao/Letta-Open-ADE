from __future__ import annotations

import asyncio
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime.errors import RuntimeNotReady
from ade_api.features.agent_runtime.provider_tracing import AttemptTrace
from ade_api.features.agent_runtime.request_budget import (
    BudgetedTransport,
    RequestLedger,
    build_runtime_router_transport,
)
from ade_api.platform.settings import AdeApiSettings


def _reserve_from_process(path: str) -> bool:
    ledger = RequestLedger(
        Path(path), generation_limit=5, embedding_limit=1, binding={"stage": "test"}
    )
    try:
        ledger.reserve("generation", "synthetic::model")
    except RuntimeError:
        return False
    return True


def _settings(tmp_path: Path) -> AdeApiSettings:
    return AdeApiSettings(
        _env_file=None,
        model_router_base_url="http://router.test",
        model_router_api_key_env="",
        model_router_api_key_secret="",
        runtime_data_dir=str(tmp_path),
        agent_runtime_budget_ledger_path=str(tmp_path / "stage.sqlite3"),
        agent_runtime_budget_stage="preflight",
        agent_runtime_budget_generation_limit=2,
        agent_runtime_budget_embedding_limit=1,
    )


def _source(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ADE_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "b" * 64)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")


def test_concurrent_processes_reserve_one_shared_cap(tmp_path: Path) -> None:
    path = tmp_path / "shared.sqlite3"
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context("spawn")) as pool:
        results = list(pool.map(_reserve_from_process, [str(path)] * 12))
    assert sum(results) == 5
    reopened = RequestLedger(
        path, generation_limit=5, embedding_limit=1, binding={"stage": "test"}
    )
    assert reopened.counts() == {"generation": 5, "embedding": 0}
    with pytest.raises(ValueError, match="limits differ"):
        RequestLedger(
            path, generation_limit=6, embedding_limit=1, binding={"stage": "test"}
        )
    with pytest.raises(ValueError, match="binding differs"):
        RequestLedger(
            path, generation_limit=5, embedding_limit=1, binding={"stage": "reroll"}
        )


def test_unfinished_reservation_stays_spent_after_restart(tmp_path: Path) -> None:
    path = tmp_path / "interrupted.sqlite3"
    first = RequestLedger(path, generation_limit=1, embedding_limit=1)
    first.reserve("generation", "synthetic::model")
    reopened = RequestLedger(path, generation_limit=1, embedding_limit=1)
    assert reopened.counts()["generation"] == 1
    with pytest.raises(RuntimeError, match="budget exhausted"):
        reopened.reserve("generation", "synthetic::model")


def test_budgeted_transport_counts_failed_timed_out_and_tool_requests(
    tmp_path: Path,
) -> None:
    class FakeRouter:
        def __init__(self) -> None:
            self.requests: list[str] = []

        async def catalog(self, *, timeout_seconds):
            return {"data": []}

        async def chat_completion(self, payload, *, timeout_seconds):
            self.requests.append("generation")
            assert timeout_seconds == 180
            raise TimeoutError("synthetic timeout")

        async def embeddings(self, payload, *, timeout_seconds):
            self.requests.append("embedding")
            return {"data": [], "purpose": payload["purpose"]}

    ledger = RequestLedger(
        tmp_path / "stage.sqlite3", generation_limit=1, embedding_limit=2
    )
    router = FakeRouter()
    transport = BudgetedTransport(router, ledger)

    async def scenario() -> None:
        await transport.catalog()
        with pytest.raises(TimeoutError, match="synthetic timeout"):
            await transport.chat_completion(
                {"model": "synthetic::chat"}, timeout_seconds=500
            )
        with pytest.raises(RuntimeError, match="budget exhausted"):
            await transport.chat_completion(
                {"model": "synthetic::chat"}, timeout_seconds=5
            )
        for purpose in ("automatic", "tool"):
            await transport.embeddings(
                {"model": "synthetic::embedding", "purpose": purpose},
                timeout_seconds=5,
            )
        with pytest.raises(RuntimeError, match="budget exhausted"):
            await transport.embeddings(
                {"model": "synthetic::embedding", "purpose": "document"},
                timeout_seconds=5,
            )

    asyncio.run(scenario())
    assert ledger.counts() == {"generation": 1, "embedding": 2}
    assert router.requests == ["generation", "embedding", "embedding"]


def test_traced_runtime_stages_share_one_generation_and_embedding_cap(
    tmp_path: Path,
) -> None:
    class FakeRouter:
        async def chat_completion(self, payload, *, timeout_seconds):
            return {"id": "synthetic-response", "choices": []}

        async def embeddings(self, payload, *, timeout_seconds):
            return {"data": []}

    ledger = RequestLedger(
        tmp_path / "stage.sqlite3", generation_limit=3, embedding_limit=3
    )
    transport = BudgetedTransport(FakeRouter(), ledger)
    trace = AttemptTrace(attempt=1)

    async def scenario() -> None:
        for stage in ("conversation", "reviewer", "compaction"):
            await trace.transport(transport, stage=stage).chat_completion(
                {"model": "synthetic::chat"}, timeout_seconds=5
            )
        for stage in ("retrieval_query", "tool_retrieval", "memory_embeddings"):
            await trace.transport(transport, stage=stage).embeddings(
                {"model": "synthetic::embedding"}, timeout_seconds=5
            )
        with pytest.raises(RuntimeError, match="budget exhausted"):
            await trace.transport(transport, stage="conversation").chat_completion(
                {"model": "synthetic::chat"}, timeout_seconds=5
            )
        with pytest.raises(RuntimeError, match="budget exhausted"):
            await trace.transport(transport, stage="tool_retrieval").embeddings(
                {"model": "synthetic::embedding"}, timeout_seconds=5
            )

    asyncio.run(scenario())
    assert ledger.counts() == {"generation": 3, "embedding": 3}


def test_standard_api_and_worker_builders_share_budgeted_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ade_api.features.agent_runtime.application as application
    import ade_api.features.agent_runtime.worker as worker

    _source(monkeypatch)
    settings = _settings(tmp_path)
    monkeypatch.setattr(application, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "ensure_agent_runtime_enabled", lambda: None)
    monkeypatch.setattr(application, "create_persistence_engine", lambda _url: object())
    monkeypatch.setattr(worker, "create_persistence_engine", lambda _url: object())
    monkeypatch.setattr(
        application, "build_prompt_template_reader", lambda *_a, **_k: object()
    )
    monkeypatch.setattr(
        application,
        "AgentRuntimeApplication",
        lambda **kwargs: SimpleNamespace(**kwargs),
    )
    monkeypatch.setattr(
        worker, "AgentRuntimeWorker", lambda **kwargs: SimpleNamespace(**kwargs)
    )
    settings.database_url = "postgresql+psycopg://synthetic/test"

    api = application.build_agent_runtime_service()
    runtime_worker = worker.build_worker()
    assert isinstance(api.router_transport, BudgetedTransport)
    assert isinstance(runtime_worker.transport, BudgetedTransport)
    assert api.router_transport.ledger.path == runtime_worker.transport.ledger.path
    assert api.router_transport.ledger.limits == {"generation": 2, "embedding": 1}


def test_budgeted_standard_transport_requires_clean_build_and_runtime_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source(monkeypatch)
    settings = _settings(tmp_path)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "true")
    with pytest.raises(RuntimeNotReady, match="clean build identity"):
        build_runtime_router_transport(settings)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    settings.agent_runtime_budget_ledger_path = str(tmp_path.parent / "outside.sqlite3")
    with pytest.raises(RuntimeNotReady, match="runtime data"):
        build_runtime_router_transport(settings)


def test_standard_transport_rejects_reopening_ledger_with_changed_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _source(monkeypatch)
    settings = _settings(tmp_path)
    first = build_runtime_router_transport(settings)
    assert isinstance(first, BudgetedTransport)
    first.ledger.reserve("generation", "synthetic::model")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "c" * 64)
    with pytest.raises(ValueError, match="binding differs"):
        build_runtime_router_transport(settings)


def test_partial_budget_configuration_is_rejected() -> None:
    with pytest.raises(ValueError, match="runtime budget requires"):
        AdeApiSettings(
            _env_file=None,
            agent_runtime_budget_ledger_path="data/runtime/stage.sqlite3",
        )
