from __future__ import annotations

import asyncio
import re
import time
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings

from .events import append_run_event
from .persistence.leases import ConversationLeaseRepository
from .persistence.runs import RunRepository
from .turn_execution import AttemptResult, TurnExecution
from .worker_claims import ClaimedRun


class RunCancelled(RuntimeError):
    pass


class LeaseLost(RuntimeError):
    pass


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

    async def start_attempt(self, claim: ClaimedRun, attempt: int) -> str:
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
            await append_run_event(
                runs,
                run_id=str(claim.run["id"]),
                event_type="attempt.started",
                payload={"timeout_seconds": float(claim.run["timeout_seconds"])},
                attempt=attempt,
            )
        return attempt_id

    async def execute_attempt(
        self,
        claim: ClaimedRun,
        *,
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
            self.execution.execute(claim.run, deadline=deadline)
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
        attempt: int,
        exc: Exception,
    ) -> None:
        if isinstance(exc, LeaseLost):
            return
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            await runs.finish_attempt(
                attempt_id,
                status="cancelled" if isinstance(exc, RunCancelled) else "failed",
                provider_outcome={"error_code": worker_error_code(exc)},
                finished_at=utc_now(),
            )
            await append_run_event(
                runs,
                run_id=str(claim.run["id"]),
                event_type=(
                    "attempt.cancelled"
                    if isinstance(exc, RunCancelled)
                    else "attempt.failed"
                ),
                payload={"error_code": worker_error_code(exc)},
                attempt=attempt,
            )

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
        delay: float, cancelled: asyncio.Event, lease_lost: asyncio.Event
    ) -> None:
        cancellation_task = asyncio.create_task(cancelled.wait())
        lease_task = asyncio.create_task(lease_lost.wait())
        try:
            done, _ = await asyncio.wait({cancellation_task, lease_task}, timeout=delay)
            if cancellation_task in done:
                raise RunCancelled("run cancellation was requested")
            if lease_task in done:
                raise LeaseLost("conversation lease was lost")
        finally:
            for task in (cancellation_task, lease_task):
                task.cancel()
            await asyncio.gather(cancellation_task, lease_task, return_exceptions=True)


def worker_error_code(exc: Exception) -> str:
    name = type(exc).__name__
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()[:128]


def utc_now() -> datetime:
    return datetime.now(UTC)
