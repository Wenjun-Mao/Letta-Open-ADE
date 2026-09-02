from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings

from .events import append_run_event
from .persistence.leases import ConversationLeaseRepository
from .persistence.runs import RunRepository
from .provider_tracing import AttemptTrace
from .turn_execution import AttemptResult, TurnExecution
from .worker_claims import ClaimedRun
from .worker_events import append_attempt_trace


class RunCancelled(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


class WorkerDraining(RuntimeError):
    pass


@dataclass(frozen=True)
class StartedAttempt:
    attempt_id: str
    started_event_id: str


class AttemptController:
    """Owns attempt lifecycle, timeout, cancellation, and lease monitoring."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        settings: AdeApiSettings,
        execution: TurnExecution,
    ) -> None:
        self.engine = engine
        self.settings = settings
        self.execution = execution

    async def start_attempt(self, claim: ClaimedRun, attempt: int) -> StartedAttempt:
        attempt_id = str(uuid4())
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            current = await runs.get_for_update(str(claim.run["id"]))
            if current["cancellation_requested_at"] is not None:
                raise RunCancelled("run cancellation was requested")
            if not await ConversationLeaseRepository(connection).owns(
                claim.lease_token, str(claim.run["id"])
            ):
                raise LeaseLost("conversation lease is no longer owned")
            await runs.set_attempt_count(str(claim.run["id"]), attempt)
            await runs.create_attempt(
                {
                    "id": attempt_id,
                    "run_id": str(claim.run["id"]),
                    "attempt_number": attempt,
                    "status": "running",
                    "timeout_seconds": claim.run["timeout_seconds"],
                }
            )
            started = await append_run_event(
                runs,
                run_id=str(claim.run["id"]),
                event_type="attempt.started",
                payload={"timeout_seconds": float(claim.run["timeout_seconds"])},
                attempt=attempt,
            )
        return StartedAttempt(
            attempt_id=attempt_id,
            started_event_id=str(started["id"]),
        )

    async def execute_attempt(
        self,
        claim: ClaimedRun,
        *,
        trace: AttemptTrace,
        cancelled: asyncio.Event,
        lease_lost: asyncio.Event,
    ) -> AttemptResult:
        if cancelled.is_set():
            raise RunCancelled("run cancellation was requested")
        if lease_lost.is_set():
            raise LeaseLost("conversation lease was lost")
        timeout = float(claim.run["timeout_seconds"])
        deadline = time.monotonic() + timeout
        execution_task = asyncio.create_task(
            self.execution.execute(claim.run, deadline=deadline, trace=trace)
        )
        cancellation_task = asyncio.create_task(cancelled.wait())
        lease_task = asyncio.create_task(lease_lost.wait())
        try:
            done, _ = await asyncio.wait(
                {execution_task, cancellation_task, lease_task},
                timeout=timeout,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if cancellation_task in done:
                raise RunCancelled("run cancellation was requested")
            if lease_task in done:
                raise LeaseLost("conversation lease was lost")
            if execution_task not in done:
                raise TimeoutError("whole runtime attempt timed out")
            return await execution_task
        finally:
            for task in (execution_task, cancellation_task, lease_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(
                execution_task, cancellation_task, lease_task, return_exceptions=True
            )

    async def finish_attempt_failure(
        self,
        claim: ClaimedRun,
        attempt_id: str,
        started_event_id: str,
        attempt: int,
        trace: AttemptTrace,
        exc: Exception,
    ) -> str | None:
        if isinstance(exc, LeaseLost):
            return None
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            if not await ConversationLeaseRepository(connection).owns(
                claim.lease_token, str(claim.run["id"])
            ):
                raise LeaseLost("conversation lease was lost before attempt failure")
            await runs.finish_attempt(
                attempt_id,
                status="cancelled" if isinstance(exc, RunCancelled) else "failed",
                provider_outcome=worker_error_payload(exc),
                finished_at=utc_now(),
            )
            trace_event_id = await append_attempt_trace(
                runs,
                run_id=str(claim.run["id"]),
                attempt=attempt,
                trace=trace,
                causation_id=started_event_id,
            )
            failed = await append_run_event(
                runs,
                run_id=str(claim.run["id"]),
                event_type=(
                    "attempt.cancelled"
                    if isinstance(exc, RunCancelled)
                    else "attempt.failed"
                ),
                payload=worker_error_payload(exc),
                attempt=attempt,
                causation_id=trace_event_id or started_event_id,
            )
            return str(failed["id"])

    async def schedule_retry(
        self,
        claim: ClaimedRun,
        *,
        completed_attempt: int,
        next_attempt: int,
        delay: float,
        exc: Exception,
        causation_id: str | None,
    ) -> str:
        run_id = str(claim.run["id"])
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            current = await runs.get_for_update(run_id)
            if current["cancellation_requested_at"] is not None:
                raise RunCancelled("run cancellation was requested")
            if not await ConversationLeaseRepository(connection).owns(
                claim.lease_token, run_id
            ):
                raise LeaseLost("conversation lease was lost before retry scheduling")
            event = await append_run_event(
                runs,
                run_id=run_id,
                event_type="retry.scheduled",
                payload={
                    "completed_attempt": completed_attempt,
                    "next_attempt": next_attempt,
                    "delay_seconds": round(delay, 6),
                    **worker_error_payload(exc),
                },
                attempt=completed_attempt,
                causation_id=causation_id,
            )
        return str(event["id"])

    async def monitor_cancellation(
        self, run_id: str, cancelled: asyncio.Event, stop: asyncio.Event
    ) -> None:
        while not stop.is_set():
            async with self.engine.connect() as connection:
                if await RunRepository(connection).is_cancellation_requested(run_id):
                    cancelled.set()
                    return
            await asyncio.sleep(0.25)

    async def heartbeat(
        self, claim: ClaimedRun, lease_lost: asyncio.Event, stop: asyncio.Event
    ) -> None:
        interval = min(
            self.settings.agent_runtime_v3_heartbeat_seconds,
            max(1, self.settings.agent_runtime_v3_lease_seconds // 3),
        )
        while not stop.is_set():
            await asyncio.sleep(interval)
            async with self.engine.begin() as connection:
                owned = await ConversationLeaseRepository(connection).heartbeat(
                    claim.lease_token,
                    utc_now()
                    + timedelta(seconds=self.settings.agent_runtime_v3_lease_seconds),
                )
            if not owned:
                lease_lost.set()
                return

    @staticmethod
    async def backoff_sleep(
        delay: float,
        cancelled: asyncio.Event,
        lease_lost: asyncio.Event,
        stop_requested: asyncio.Event | None = None,
    ) -> None:
        cancellation_task = asyncio.create_task(cancelled.wait())
        lease_task = asyncio.create_task(lease_lost.wait())
        draining_task = (
            asyncio.create_task(stop_requested.wait()) if stop_requested else None
        )
        try:
            waiters = {cancellation_task, lease_task}
            if draining_task is not None:
                waiters.add(draining_task)
            done, _ = await asyncio.wait(waiters, timeout=delay)
            if cancellation_task in done:
                raise RunCancelled("run cancellation was requested")
            if lease_task in done:
                raise LeaseLost("conversation lease was lost")
            if draining_task is not None and draining_task in done:
                raise WorkerDraining("worker is draining before retry")
        finally:
            tasks = tuple(
                task
                for task in (cancellation_task, lease_task, draining_task)
                if task is not None
            )
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def worker_error_code(exc: Exception) -> str:
    explicit = str(getattr(exc, "error_code", "") or "")
    if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", explicit):
        return explicit
    name = type(exc).__name__
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()[:128]


def worker_error_payload(exc: Exception) -> dict[str, str]:
    payload = {"error_code": worker_error_code(exc)}
    detail_code = str(getattr(exc, "detail_code", "") or "")
    if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", detail_code):
        payload["error_detail_code"] = detail_code
    return payload


def utc_now() -> datetime:
    return datetime.now(UTC)
