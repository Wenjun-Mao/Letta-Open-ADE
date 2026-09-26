"""Frozen native ranking dispatches only after fresh source authorization."""

from __future__ import annotations

import asyncio
import time

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.history_native_rank import (
    HISTORY_EMBEDDING_ROUTE,
    rank_native_history,
)
from ade_api.features.agent_runtime.router_transport import RouterRequestError


def _exchange(run_id: str, text: str) -> dict:
    return {
        "run_id": run_id,
        "messages": [
            {"content": text},
            {"content": "记得。", "created_at": "2026-09-01T12:00:00Z"},
        ],
    }


def test_native_qwen_guards_both_dispatches_and_retains_source_identity() -> None:
    corpus = [_exchange("r1", "早晨手磨咖啡"), _exchange("r2", "晚上泡茶")]
    guards: list[list[str]] = []
    requests: list[list[str]] = []
    exposed: list[bool] = []

    async def authorize(exchanges):
        guards.append([item["run_id"] for item in exchanges])
        return set()

    class Embeddings:
        async def embed(self, *, model_key, inputs, timeout_seconds):
            assert model_key == HISTORY_EMBEDDING_ROUTE
            assert timeout_seconds > 0
            assert exposed
            requests.append(list(inputs))
            return [[1.0] * 1024 for _ in inputs]

    result = asyncio.run(
        rank_native_history(
            exchanges=corpus,
            current_user="起床后喝什么？",
            local_suffix=[{"role": "assistant", "content": "继续聊。"}],
            recipe="probe_local_qwen_cosine",
            embeddings=Embeddings(),
            model_key=HISTORY_EMBEDDING_ROUTE,
            deadline=time.monotonic() + 30,
            authorize_sources=authorize,
            mark_exposed=lambda: exposed.append(True),
        )
    )
    assert guards == [["r1", "r2"], ["r1", "r2"]]
    assert requests[0] == [
        "User: 早晨手磨咖啡\nAssistant: 记得。",
        "User: 晚上泡茶\nAssistant: 记得。",
    ]
    assert '"current_user":"起床后喝什么？"' in requests[1][0]
    assert len(requests) == result.embedding_dispatches == 2
    assert set(result.document_hashes) == {"r1", "r2"}
    assert [item["id"] for item in result.ranked] == ["r1", "r2"]
    assert result.recipe_identity and result.query_sha256


def test_native_qwen_omits_preexposure_purge_without_dispatch() -> None:
    calls = []

    async def authorize(exchanges):
        calls.append([item["run_id"] for item in exchanges])
        return {"r1"} if len(calls) == 1 else set()

    class Embeddings:
        async def embed(self, *, model_key, inputs, timeout_seconds):
            return [[1.0] * 1024 for _ in inputs]

    result = asyncio.run(
        rank_native_history(
            exchanges=[_exchange("r1", "早晨咖啡"), _exchange("r2", "晚上茶")],
            current_user="喝什么？",
            local_suffix=[],
            recipe="probe_local_qwen_cosine",
            embeddings=Embeddings(),
            model_key=HISTORY_EMBEDDING_ROUTE,
            deadline=time.monotonic() + 30,
            authorize_sources=authorize,
            mark_exposed=lambda: None,
        )
    )
    assert calls == [["r1", "r2"], ["r2"], ["r2"]]
    assert result.status == "purged"
    assert [item["id"] for item in result.ranked] == ["r2"]


def test_native_qwen_never_sends_query_after_postexposure_loss() -> None:
    calls = 0
    dispatches = 0

    async def authorize(_exchanges):
        nonlocal calls
        calls += 1
        return set() if calls == 1 else {"r1"}

    class Embeddings:
        async def embed(self, *, model_key, inputs, timeout_seconds):
            nonlocal dispatches
            dispatches += 1
            return [[1.0] * 1024 for _ in inputs]

    with pytest.raises(RuntimeValidationError) as lost:
        asyncio.run(
            rank_native_history(
                exchanges=[_exchange("r1", "早晨咖啡")],
                current_user="喝什么？",
                local_suffix=[],
                recipe="probe_local_qwen_cosine",
                embeddings=Embeddings(),
                model_key=HISTORY_EMBEDDING_ROUTE,
                deadline=time.monotonic() + 30,
                authorize_sources=authorize,
                mark_exposed=lambda: None,
            )
        )
    assert lost.value.detail_code == "natural_history_missing"
    assert (calls, dispatches) == (2, 1)


def test_native_qwen_transport_failure_has_no_retry_or_fallback() -> None:
    dispatches = 0

    async def authorize(_exchanges):
        return set()

    class Embeddings:
        async def embed(self, *, model_key, inputs, timeout_seconds):
            nonlocal dispatches
            dispatches += 1
            raise RouterRequestError("synthetic retryable failure", retryable=True)

    with pytest.raises(RuntimeValidationError) as failure:
        asyncio.run(
            rank_native_history(
                exchanges=[_exchange("r1", "早晨咖啡")],
                current_user="喝什么？",
                local_suffix=[],
                recipe="probe_local_qwen_cosine",
                embeddings=Embeddings(),
                model_key=HISTORY_EMBEDDING_ROUTE,
                deadline=time.monotonic() + 30,
                authorize_sources=authorize,
                mark_exposed=lambda: None,
            )
        )
    assert failure.value.detail_code == "natural_history_embedding_unavailable"
    assert dispatches == 1
