from __future__ import annotations

import asyncio
import ast
from contextlib import asynccontextmanager
import importlib
import inspect
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
import ade_api.features.agent_runtime.worker_claims as worker_claims_module
from ade_api.features.agent_runtime.worker_claims import ClaimedRun
from ade_api.features.agent_runtime.worker_claims import RunClaimer
from ade_api.features.agent_runtime.worker_control import (
    StartedAttempt,
    WorkerDraining,
)


@pytest.mark.parametrize(
    "name", ["worker", "worker_control", "worker_events", "worker_finalization"]
)
def test_worker_consumers_import_attempt_result_from_its_owner(name: str) -> None:
    module = importlib.import_module(f"ade_api.features.agent_runtime.{name}")
    imports = [
        node.module
        for node in ast.walk(ast.parse(inspect.getsource(module)))
        if isinstance(node, ast.ImportFrom)
        and any(alias.name == "AttemptResult" for alias in node.names)
    ]
    assert imports == ["turn_result"]


class _Attempts:
    def __init__(self) -> None:
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.start_count = 0

    async def monitor_cancellation(self, _run_id, _cancelled, stop):
        await stop.wait()

    async def heartbeat(self, _claim, _lease_lost, stop):
        await stop.wait()

    async def start_attempt(self, _claim, _attempt):
        self.start_count += 1
        return StartedAttempt("attempt-1", "attempt-started-event")

    async def execute_attempt(self, _claim, **_kwargs):
        self.started.set()
        await self.release.wait()
        return SimpleNamespace()

    async def finish_attempt_failure(self, *_args, **_kwargs):
        raise AssertionError("the active attempt must finish successfully")


class _Finalizer:
    def __init__(self) -> None:
        self.succeeded = False
        self.failure: Exception | None = None

    async def commit_success(self, _claim, _attempt_id, _result, *, trace=None):
        self.succeeded = True

    async def commit_failure(self, _claim, _attempt_id, exc, **_kwargs):
        self.failure = exc

    async def commit_cancellation(self, *_args, **_kwargs):
        raise AssertionError("draining is not user cancellation")


def _worker(attempts: _Attempts, finalizer: _Finalizer) -> AgentRuntimeWorker:
    worker = AgentRuntimeWorker.__new__(AgentRuntimeWorker)
    worker.attempts = attempts
    worker.finalizer = finalizer
    worker.settings = SimpleNamespace()
    return worker


def _claim() -> ClaimedRun:
    return ClaimedRun(
        run={
            "id": "run-1",
            "workspace_id": "workspace-1",
            "conversation_id": "conversation-1",
            "attempt_count": 0,
            "retry_count": 0,
            "retry_attempt_base": 0,
        },
        lease_token="lease-1",
        recovered=False,
    )


def test_drain_allows_one_active_attempt_to_finish() -> None:
    async def scenario() -> tuple[_Attempts, _Finalizer]:
        attempts = _Attempts()
        finalizer = _Finalizer()
        stop_requested = asyncio.Event()
        task = asyncio.create_task(
            _worker(attempts, finalizer)._process_claim(_claim(), stop_requested)
        )
        await asyncio.wait_for(attempts.started.wait(), timeout=1)
        stop_requested.set()
        attempts.release.set()
        await task
        return attempts, finalizer

    attempts, finalizer = asyncio.run(scenario())

    assert attempts.start_count == 1
    assert finalizer.succeeded is True
    assert finalizer.failure is None


def test_drain_before_attempt_fails_claim_without_starting_provider_work() -> None:
    async def scenario() -> tuple[_Attempts, _Finalizer]:
        attempts = _Attempts()
        finalizer = _Finalizer()
        stop_requested = asyncio.Event()
        stop_requested.set()
        await _worker(attempts, finalizer)._process_claim(_claim(), stop_requested)
        return attempts, finalizer

    attempts, finalizer = asyncio.run(scenario())

    assert attempts.start_count == 0
    assert isinstance(finalizer.failure, WorkerDraining)


def test_private_observation_failure_cannot_undo_committed_success() -> None:
    class BrokenObserver:
        def record(self, *_args):
            raise OSError("synthetic disk fault")

    class ObservedAttempts(_Attempts):
        async def execute_attempt(self, _claim, **kwargs):
            self.trace = kwargs["trace"]
            self.trace.private_observer = BrokenObserver()
            return SimpleNamespace()

    async def scenario():
        attempts, finalizer = ObservedAttempts(), _Finalizer()
        await _worker(attempts, finalizer)._process_claim(_claim(), asyncio.Event())
        return attempts, finalizer

    attempts, finalizer = asyncio.run(scenario())
    assert finalizer.succeeded and finalizer.failure is None
    assert attempts.trace.observation_incomplete is True


def test_lost_commit_ack_does_not_run_the_candidate_again() -> None:
    class Attempts(_Attempts):
        async def execute_attempt(self, _claim, **kwargs):
            self.trace = kwargs["trace"]
            return SimpleNamespace()

    class LostAckFinalizer(_Finalizer):
        async def commit_success(self, claim, attempt_id, result, *, trace=None):
            await super().commit_success(claim, attempt_id, result, trace=trace)
            raise ConnectionError("synthetic acknowledgment loss")

        async def commit_failure(self, claim, attempt_id, exc, **kwargs):
            # The real finalizer separately verifies authoritative terminal state.
            assert self.succeeded
            self.failure_calls = getattr(self, "failure_calls", 0) + 1

    async def scenario():
        attempts, finalizer = Attempts(), LostAckFinalizer()
        await _worker(attempts, finalizer)._process_claim(_claim(), asyncio.Event())
        return attempts, finalizer

    attempts, finalizer = asyncio.run(scenario())
    assert attempts.start_count == 1
    assert finalizer.succeeded and finalizer.failure is None
    assert finalizer.failure_calls == 1


def test_execution_failure_keeps_private_capture_and_never_commits_candidate() -> None:
    records = []

    class Observer:
        def record(self, event_type, value):
            records.append((event_type, value))
            return True

    class RejectedAttempts(_Attempts):
        async def execute_attempt(self, _claim, **kwargs):
            trace = kwargs["trace"]
            trace.private_observer = Observer()
            trace.record_private("controlled_candidate", {"reply": "candidate only"})
            raise RuntimeValidationError(
                "controlled invalid candidate",
                detail_code="synthetic_invalid_candidate",
            )

        async def finish_attempt_failure(self, *_args, **_kwargs):
            return "failed-event"

    async def scenario():
        finalizer = _Finalizer()
        await _worker(RejectedAttempts(), finalizer)._process_claim(
            _claim(), asyncio.Event()
        )
        return finalizer

    finalizer = asyncio.run(scenario())
    assert not finalizer.succeeded
    assert isinstance(finalizer.failure, RuntimeValidationError)
    assert records[0] == ("controlled_candidate", {"reply": "candidate only"})
    assert records[-1][0] == "attempt_execution.finished"
    assert records[-1][1]["status"] == "RuntimeValidationError"


def test_run_claimer_only_claims_work_accepted_in_its_runtime_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen = []

    class _Engine:
        @asynccontextmanager
        async def begin(self):
            yield object()

    class _Lifecycle:
        def __init__(self, _connection) -> None:
            pass

        async def claim(self, *, runtime_mode, workspace_id, abandoned=False):
            seen.append(
                ("abandoned" if abandoned else "pending", runtime_mode, workspace_id)
            )
            return None

    monkeypatch.setattr(worker_claims_module, "RunRepository", lambda _: object())
    monkeypatch.setattr(worker_claims_module, "RunLifecycleRepository", _Lifecycle)
    monkeypatch.setattr(
        worker_claims_module,
        "ConversationLeaseRepository",
        lambda _connection: object(),
    )
    claimer = RunClaimer(
        engine=_Engine(),
        settings=SimpleNamespace(
            agent_runtime_mode="release",
            agent_runtime_workspace_key="synthetic-claim-workspace",
        ),
    )

    assert asyncio.run(claimer.claim()) == (None, False)
    assert seen == [
        ("pending", "release", claimer.database.workspace_id),
        ("abandoned", "release", claimer.database.workspace_id),
    ]
