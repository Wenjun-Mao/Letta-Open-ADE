from __future__ import annotations

import asyncio

import pytest

from ade_api.features.agent_runtime_v3 import worker_control, worker_finalization
from ade_api.features.agent_runtime_v3.worker_claims import ClaimedRun
from ade_api.features.agent_runtime_v3.worker_control import (
    AttemptController,
    LeaseLost,
)
from ade_api.features.agent_runtime_v3.worker_finalization import RunFinalizer


class _Transaction:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Engine:
    def begin(self):
        return _Transaction()


class _Runs:
    def __init__(self) -> None:
        self.finished = False

    async def get_for_update(self, run_id: str):
        return {
            "id": run_id,
            "status": "running",
            "attempt_count": 1,
            "cancellation_requested_at": None,
        }

    async def finish(self, *args, **kwargs):
        self.finished = True
        raise AssertionError("a stale worker must not finish the recovered run")


class _Leases:
    def __init__(self) -> None:
        self.released = False

    async def owns(self, lease_token: str, run_id: str) -> bool:
        return False

    async def release(self, lease_token: str) -> None:
        self.released = True
        raise AssertionError("a stale worker must not release another worker's lease")


@pytest.mark.parametrize("terminal_method", ["commit_failure", "commit_cancellation"])
def test_terminal_finalization_is_fenced_by_the_claimed_lease(
    monkeypatch: pytest.MonkeyPatch, terminal_method: str
) -> None:
    runs = _Runs()
    leases = _Leases()
    monkeypatch.setattr(worker_finalization, "RunRepository", lambda _connection: runs)
    monkeypatch.setattr(
        worker_finalization,
        "ConversationLeaseRepository",
        lambda _connection: leases,
    )
    claim = ClaimedRun(
        run={"id": "run-1"},
        lease_token="stale-token",
        recovered=False,
    )
    finalizer = RunFinalizer(_Engine())  # type: ignore[arg-type]

    async def execute() -> None:
        method = getattr(finalizer, terminal_method)
        if terminal_method == "commit_failure":
            await method(claim, "attempt-1", RuntimeError("provider failed"))
        else:
            await method(claim, "attempt-1")

    with pytest.raises(LeaseLost, match="lease was lost"):
        asyncio.run(execute())

    assert runs.finished is False
    assert leases.released is False


def test_failed_attempt_record_is_fenced_by_the_claimed_lease(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _Runs()
    leases = _Leases()
    monkeypatch.setattr(worker_control, "RunRepository", lambda _connection: runs)
    monkeypatch.setattr(
        worker_control,
        "ConversationLeaseRepository",
        lambda _connection: leases,
    )
    controller = AttemptController(
        engine=_Engine(),  # type: ignore[arg-type]
        settings=object(),  # type: ignore[arg-type]
        execution=object(),  # type: ignore[arg-type]
    )
    claim = ClaimedRun(
        run={"id": "run-1"},
        lease_token="stale-token",
        recovered=False,
    )

    with pytest.raises(LeaseLost, match="lease was lost"):
        asyncio.run(
            controller.finish_attempt_failure(
                claim, "attempt-1", 1, RuntimeError("provider failed")
            )
        )

    assert runs.finished is False
