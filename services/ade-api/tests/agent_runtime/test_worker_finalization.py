from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime import worker_control, worker_finalization
from ade_api.features.agent_runtime.persistence import run_lifecycle
from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.worker_claims import ClaimedRun
from ade_api.features.agent_runtime.provider_tracing import AttemptTrace
from ade_api.features.agent_runtime.worker_control import (
    AttemptController,
    LeaseLost,
    RunCancelled,
    WorkerDraining,
)
from ade_api.features.agent_runtime.worker_finalization import RunFinalizer


class _Transaction:
    def __init__(self, runs):
        self.runs = runs

    async def __aenter__(self):
        return SimpleNamespace(runs=self.runs)

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _Engine:
    def __init__(self, runs):
        self.runs = runs

    def begin(self):
        return _Transaction(self.runs)


class _Conversations:
    async def get_for_update(self, identity):
        return {"id": identity}


@pytest.fixture(autouse=True)
def current_conversation_first_lock(monkeypatch):
    monkeypatch.setattr(
        run_lifecycle, "ConversationRepository", lambda _: _Conversations()
    )
    monkeypatch.setattr(
        run_lifecycle, "RunRepository", lambda connection: connection.runs
    )


def test_finalization_and_attempts_use_the_shared_conversation_first_lock():
    from ade_api.features.agent_runtime.persistence.run_lifecycle import lock_run

    assert worker_finalization.lock_run is lock_run
    assert worker_control.lock_run is lock_run


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

    async def get(self, run_id):
        return {
            "conversation_id": "conversation-1",
            **await self.get_for_update(run_id),
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

    async def release_owned(self, _lease_token, _run_id):
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
    finalizer = RunFinalizer(_Engine(runs))  # type: ignore[arg-type]

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
        engine=_Engine(runs),  # type: ignore[arg-type]
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
                claim,
                "attempt-1",
                "attempt-started-event",
                1,
                AttemptTrace(attempt=1),
                RuntimeError("provider failed"),
            )
        )

    assert runs.finished is False


def test_retry_scheduling_is_fenced_by_the_claimed_lease(
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
        engine=_Engine(runs),  # type: ignore[arg-type]
        settings=object(),  # type: ignore[arg-type]
        execution=object(),  # type: ignore[arg-type]
    )
    claim = ClaimedRun(
        run={"id": "run-1"},
        lease_token="stale-token",
        recovered=False,
    )

    with pytest.raises(LeaseLost, match="before retry scheduling"):
        asyncio.run(
            controller.schedule_retry(
                claim,
                completed_attempt=1,
                next_attempt=2,
                delay=0.5,
                exc=TimeoutError("provider timeout"),
                causation_id="attempt-failed-event",
            )
        )


@pytest.mark.parametrize(
    "trigger,error", [(0, RunCancelled), (1, LeaseLost), (2, WorkerDraining)]
)
def test_backoff_reacts_to_the_first_control_signal(trigger, error):
    async def check():
        signals = [asyncio.Event() for _ in range(3)]
        signals[trigger].set()
        await asyncio.wait_for(
            AttemptController.backoff_sleep(30, *signals), timeout=0.5
        )

    with pytest.raises(error):
        asyncio.run(check())


class _TerminalRuns:
    def __init__(self) -> None:
        self.events: list[dict] = []
        self.finished_attempts: list[dict] = []
        self.finished_run: dict | None = None

    async def get_for_update(self, run_id: str):
        return {
            "id": run_id,
            "status": "running",
            "attempt_count": 1,
            "cancellation_requested_at": None,
        }

    async def get(self, run_id):
        return {
            "conversation_id": "conversation-1",
            **await self.get_for_update(run_id),
        }

    async def finish_attempt(self, attempt_id: str, **kwargs):
        self.finished_attempts.append({"attempt_id": attempt_id, **kwargs})

    async def finish(self, run_id: str, **kwargs):
        self.finished_run = {"id": run_id, **kwargs}
        return self.finished_run

    async def append_ordered_event(self, **event):
        row = {**event, "id": event["event_id"]}
        self.events.append(row)
        return row


class _OwnedLeases:
    def __init__(self) -> None:
        self.released = False

    async def owns(self, _lease_token: str, _run_id: str) -> bool:
        return True

    async def release_owned(self, _lease_token: str, _run_id: str) -> bool:
        self.released = True
        return True


class _SuccessfulTransport:
    async def chat_completion(self, _payload, *, timeout_seconds):
        return {"id": "provider-safe", "choices": []}


def test_terminal_fallback_persists_trace_and_redacts_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _TerminalRuns()
    leases = _OwnedLeases()
    monkeypatch.setattr(worker_finalization, "RunRepository", lambda _connection: runs)
    monkeypatch.setattr(
        worker_finalization,
        "ConversationLeaseRepository",
        lambda _connection: leases,
    )
    trace = AttemptTrace(attempt=1)
    asyncio.run(
        trace.transport(_SuccessfulTransport(), stage="conversation").chat_completion(
            {"model": "source::model", "messages": []}, timeout_seconds=5
        )
    )
    finalizer = RunFinalizer(_Engine(runs))  # type: ignore[arg-type]
    claim = ClaimedRun(
        run={"id": "run-1"},
        lease_token="owned-token",
        recovered=False,
    )

    asyncio.run(
        finalizer.commit_failure(
            claim,
            "attempt-1",
            RuntimeError("secret database payload"),
            trace=trace,
            trace_causation_id="attempt-started-event",
        )
    )

    assert [event["event_type"] for event in runs.events] == [
        "model.request.started",
        "model.response.completed",
        "run.failed",
    ]
    assert runs.events[0]["causation_id"] == "attempt-started-event"
    assert runs.events[2]["causation_id"] == runs.events[1]["id"]
    assert runs.finished_run is not None
    assert runs.finished_run["error_message"] == ("ADE reply failed (runtime_error)")
    assert "secret" not in str(runs.finished_run)
    assert leases.released is True


def test_terminal_failure_persists_safe_validation_detail_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runs = _TerminalRuns()
    leases = _OwnedLeases()
    monkeypatch.setattr(worker_finalization, "RunRepository", lambda _connection: runs)
    monkeypatch.setattr(
        worker_finalization,
        "ConversationLeaseRepository",
        lambda _connection: leases,
    )
    finalizer = RunFinalizer(_Engine(runs))  # type: ignore[arg-type]
    claim = ClaimedRun(
        run={"id": "run-1"},
        lease_token="owned-token",
        recovered=False,
    )

    asyncio.run(
        finalizer.commit_failure(
            claim,
            "attempt-1",
            RuntimeValidationError(
                "private provider-derived detail",
                detail_code="conversation_output_empty",
            ),
        )
    )

    expected_error = {
        "error_code": "runtime_validation_error",
        "error_detail_code": "conversation_output_empty",
    }
    assert runs.finished_attempts[0]["provider_outcome"] == expected_error
    assert runs.events[-1]["payload"] == {"attempt_count": 1, **expected_error}
    assert runs.finished_run is not None
    assert runs.finished_run["error_message"] == (
        "ADE reply failed (runtime_validation_error)"
    )
    assert "private provider-derived detail" not in repr(runs.finished_attempts)
    assert "private provider-derived detail" not in repr(runs.events)
