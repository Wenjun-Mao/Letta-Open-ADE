from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest

from ade_api.features.agent_runtime.errors import RuntimeValidationError
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
import ade_api.features.agent_runtime.worker as worker_module
from ade_api.features.agent_runtime.natural_attempt_evidence import (
    NaturalAttemptEvidence,
)
import ade_api.features.agent_runtime.worker_claims as worker_claims_module
from ade_api.features.agent_runtime.worker_claims import ClaimedRun
from ade_api.features.agent_runtime.worker_claims import RunClaimer
from ade_api.features.agent_runtime.worker_control import (
    StartedAttempt,
    WorkerDraining,
)


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

    async def commit_success(self, _claim, _attempt_id, _result):
        self.succeeded = True

    async def commit_failure(self, _claim, _attempt_id, exc, **_kwargs):
        self.failure = exc

    async def commit_cancellation(self, *_args, **_kwargs):
        raise AssertionError("draining is not user cancellation")


def _worker(attempts: _Attempts, finalizer: _Finalizer) -> AgentRuntimeWorker:
    worker = AgentRuntimeWorker.__new__(AgentRuntimeWorker)
    worker.attempts = attempts
    worker.finalizer = finalizer
    return worker


def _claim() -> ClaimedRun:
    return ClaimedRun(
        run={"id": "run-1", "attempt_count": 0, "retry_count": 0},
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
        await attempts.started.wait()
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


def test_artifact_retention_fault_cannot_undo_committed_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _EvidenceAttempts(_Attempts):
        async def execute_attempt(self, _claim, **kwargs):
            kwargs["trace"].natural_evidence = NaturalAttemptEvidence(
                run_id="run-1", attempt=1, policy_binding="natural-user-assertions-v2-b"
            )
            return SimpleNamespace()

    async def fail_retention(_engine, _evidence):
        raise OSError("synthetic disk fault")

    monkeypatch.setattr(worker_module, "retain_attempt_evidence", fail_retention)

    async def scenario() -> _Finalizer:
        attempts = _EvidenceAttempts()
        finalizer = _Finalizer()
        worker = _worker(attempts, finalizer)
        worker.engine = object()
        await worker._process_claim(_claim(), asyncio.Event())
        return finalizer

    finalizer = asyncio.run(scenario())
    assert finalizer.succeeded is True
    assert finalizer.failure is None


def test_rejected_candidate_is_retained_after_worker_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[NaturalAttemptEvidence] = []

    class _RejectedAttempts(_Attempts):
        async def execute_attempt(self, _claim, **kwargs):
            evidence = NaturalAttemptEvidence(
                run_id="run-1", attempt=1, policy_binding="natural-user-assertions-v2-b"
            )
            evidence.capture_candidate("Okay, Toronto.", [])
            evidence.reviewer_decision = {
                "claim_dispositions": [
                    {"claim_id": "residence", "outcome": "contradiction"}
                ]
            }
            kwargs["trace"].natural_evidence = evidence
            raise RuntimeValidationError(
                "synthetic false veto", detail_code="natural_memory_reply_conflict"
            )

        async def finish_attempt_failure(self, *_args, **_kwargs):
            return "failed-event"

    async def retain(_engine, evidence):
        observed.append(evidence)

    monkeypatch.setattr(worker_module, "retain_attempt_evidence", retain)

    async def scenario() -> _Finalizer:
        attempts = _RejectedAttempts()
        finalizer = _Finalizer()
        worker = _worker(attempts, finalizer)
        worker.engine = object()
        await worker._process_claim(_claim(), asyncio.Event())
        return finalizer

    finalizer = asyncio.run(scenario())
    assert finalizer.succeeded is False
    assert isinstance(finalizer.failure, RuntimeValidationError)
    assert observed[0].candidate_visible_reply == "Okay, Toronto."
    assert (
        observed[0].reviewer_decision["claim_dispositions"][0]["outcome"]
        == "contradiction"
    )


def test_run_claimer_only_claims_work_accepted_in_its_runtime_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[tuple[str, str]] = []

    class _Engine:
        @asynccontextmanager
        async def begin(self):
            yield object()

    class _Runs:
        def __init__(self, _connection) -> None:
            pass

        async def claim_pending(self, *, runtime_mode: str):
            seen.append(("pending", runtime_mode))
            return None

        async def claim_abandoned(self, *, runtime_mode: str):
            seen.append(("abandoned", runtime_mode))
            return None

    monkeypatch.setattr(worker_claims_module, "RunRepository", _Runs)
    monkeypatch.setattr(
        worker_claims_module,
        "ConversationLeaseRepository",
        lambda _connection: object(),
    )
    claimer = RunClaimer(
        engine=_Engine(),
        settings=SimpleNamespace(agent_runtime_mode="release"),
    )

    assert asyncio.run(claimer.claim()) == (None, False)
    assert seen == [("pending", "release"), ("abandoned", "release")]
