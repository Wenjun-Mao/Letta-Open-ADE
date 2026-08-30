from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime_v3.worker_health import (
    RuntimeWorkerHealthService,
    WORKER_CONTRACT_VERSION,
    WorkerPresence,
    project_runtime_health,
    worker_compatibility_fingerprint,
)
from ade_api.features.agent_runtime_v3.errors import RuntimeNotReady


NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def _worker(
    *,
    heartbeat_age_seconds: int,
    contract_version: str = WORKER_CONTRACT_VERSION,
    stopped: bool = False,
) -> dict:
    return {
        "instance_id": "00000000-0000-0000-0000-000000000001",
        "worker_id": "worker-1",
        "runtime_version": "0.3.0",
        "compatibility_fingerprint": worker_compatibility_fingerprint(
            runtime_mode="development",
            contract_version=contract_version,
            migration_heads=("20260830_0004",),
        ),
        "source_revision": "a" * 40,
        "source_dirty": False,
        "source_fingerprint": "b" * 64,
        "state": "stopped" if stopped else "ready",
        "started_at": NOW - timedelta(minutes=2),
        "heartbeat_at": NOW - timedelta(seconds=heartbeat_age_seconds),
        "stopped_at": NOW if stopped else None,
    }


def test_fresh_compatible_worker_makes_runtime_ready() -> None:
    fingerprint = worker_compatibility_fingerprint(
        runtime_mode="development", migration_heads=("20260830_0004",)
    )
    result = project_runtime_health(
        [_worker(heartbeat_age_seconds=12)],
        checked_at=NOW,
        freshness_seconds=45,
        compatibility_fingerprint=fingerprint,
    )

    assert result["status"] == "ready"
    assert result["database_ready"] is True
    assert result["worker_ready"] is True
    assert result["compatible_worker_count"] == 1
    assert result["compatibility_fingerprint"] == fingerprint


def test_stale_stopped_and_incompatible_workers_do_not_satisfy_readiness() -> None:
    fingerprint = worker_compatibility_fingerprint(
        runtime_mode="development", migration_heads=("20260830_0004",)
    )
    result = project_runtime_health(
        [
            _worker(heartbeat_age_seconds=46),
            _worker(heartbeat_age_seconds=1, stopped=True),
            _worker(
                heartbeat_age_seconds=1,
                contract_version="agent-runtime-v3-old",
            ),
        ],
        checked_at=NOW,
        freshness_seconds=45,
        compatibility_fingerprint=fingerprint,
    )

    assert result["status"] == "not_ready"
    assert result["worker_ready"] is False
    assert result["compatible_worker_count"] == 0


def test_future_heartbeat_is_clamped_for_diagnostics() -> None:
    worker = _worker(heartbeat_age_seconds=-5)
    fingerprint = worker_compatibility_fingerprint(
        runtime_mode="development", migration_heads=("20260830_0004",)
    )
    result = project_runtime_health(
        [worker],
        checked_at=NOW,
        freshness_seconds=45,
        compatibility_fingerprint=fingerprint,
    )

    assert result["worker_ready"] is True
    assert result["compatible_worker_count"] == 1


def test_matching_build_requires_exact_source_content_fingerprint() -> None:
    fingerprint = worker_compatibility_fingerprint(
        runtime_mode="development", migration_heads=("20260830_0004",)
    )

    result = project_runtime_health(
        [_worker(heartbeat_age_seconds=1)],
        checked_at=NOW,
        freshness_seconds=45,
        compatibility_fingerprint=fingerprint,
        source_revision="a" * 40,
        source_dirty=False,
        source_fingerprint="c" * 64,
    )

    assert result["compatible_worker_count"] == 1
    assert result["matching_build_worker_count"] == 0
    assert result["worker_ready"] is False


def test_database_failure_returns_typed_not_ready_health(monkeypatch) -> None:
    class _UnavailableDatabase:
        async def ensure_ready(self) -> None:
            raise RuntimeNotReady("database unavailable")

    service = RuntimeWorkerHealthService(
        engine=SimpleNamespace(),  # type: ignore[arg-type]
        settings=SimpleNamespace(  # type: ignore[arg-type]
            agent_runtime_v3_mode="development",
            agent_runtime_v3_worker_stale_seconds=15.0,
        ),
    )
    service.database = _UnavailableDatabase()  # type: ignore[assignment]
    monkeypatch.setenv("ADE_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "b" * 64)

    result = asyncio.run(service.get_health())

    assert result["status"] == "not_ready"
    assert result["database_ready"] is False
    assert result["worker_ready"] is False
    assert result["matching_build_worker_count"] == 0
    assert result["source_fingerprint"] == "b" * 64


def test_worker_presence_rejects_unknown_or_truncated_source_identity(
    monkeypatch,
) -> None:
    monkeypatch.setenv("ADE_SOURCE_REVISION", "a" * 40)
    monkeypatch.setenv("ADE_SOURCE_DIRTY", "false")
    monkeypatch.setenv("ADE_SOURCE_FINGERPRINT", "b" * 64 + "secret")

    with pytest.raises(RuntimeNotReady, match="exact source"):
        WorkerPresence(
            engine=SimpleNamespace(),  # type: ignore[arg-type]
            settings=SimpleNamespace(  # type: ignore[arg-type]
                agent_runtime_v3_mode="development",
            ),
        )
