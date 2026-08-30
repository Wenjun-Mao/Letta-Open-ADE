from __future__ import annotations

import asyncio
import signal

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings, get_settings

from .errors import RuntimeNotReady
from .flags import ensure_agent_runtime_v3_enabled
from .persistence.database import create_persistence_engine
from .persistence.validation import validate_database_at_head
from .provider_tracing import AttemptTrace
from .retry import execute_with_retries
from .router_transport import RouterTransport
from .turn_execution import AttemptResult, TurnExecution
from .worker_claims import ClaimedRun, RunClaimer
from .worker_control import (
    AttemptController,
    LeaseLost,
    RunCancelled,
    WorkerDraining,
)
from .worker_finalization import RunFinalizer
from .worker_health import WorkerPresence


class AgentRuntimeV3Worker:
    """Coordinates claimed runs; collaborators own each persistence boundary."""

    def __init__(
        self,
        *,
        engine: AsyncEngine,
        settings: AdeApiSettings,
        transport: RouterTransport,
    ) -> None:
        self.engine = engine
        self.settings = settings
        execution = TurnExecution(engine=engine, transport=transport, settings=settings)
        self.claimer = RunClaimer(engine=engine, settings=settings)
        self.attempts = AttemptController(
            engine=engine, settings=settings, execution=execution
        )
        self.finalizer = RunFinalizer(engine)
        self.presence = WorkerPresence(engine=engine, settings=settings)
        self._ready = False

    async def aclose(self) -> None:
        await self.engine.dispose()

    async def ensure_ready(self) -> None:
        if self._ready:
            return
        try:
            async with self.engine.connect() as connection:
                await connection.run_sync(validate_database_at_head)
        except Exception as exc:
            raise RuntimeNotReady(
                "ADE-native worker database is not at the reviewed migration head"
            ) from exc
        self._ready = True

    async def run_forever(self, stop_requested: asyncio.Event | None = None) -> None:
        await self.ensure_ready()
        stop_requested = stop_requested or asyncio.Event()
        heartbeat_stop = asyncio.Event()
        await self.presence.register()
        heartbeat_task = asyncio.create_task(
            self.presence.heartbeat_forever(heartbeat_stop),
            name="v3-worker-presence-heartbeat",
        )

        async def mark_draining_when_requested() -> None:
            await stop_requested.wait()
            await self.presence.mark_draining()

        draining_task = asyncio.create_task(
            mark_draining_when_requested(),
            name="v3-worker-presence-draining",
        )
        try:
            while not stop_requested.is_set():
                if heartbeat_task.done():
                    await heartbeat_task
                processed = await self.process_once(stop_requested)
                if processed:
                    continue
                stop_wait = asyncio.create_task(stop_requested.wait())
                try:
                    done, _ = await asyncio.wait(
                        {heartbeat_task, stop_wait},
                        timeout=self.settings.agent_runtime_v3_worker_poll_seconds,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    if heartbeat_task in done:
                        await heartbeat_task
                finally:
                    if not stop_wait.done():
                        stop_wait.cancel()
                    await asyncio.gather(stop_wait, return_exceptions=True)
        finally:
            if stop_requested.is_set():
                await self.presence.mark_draining()
            heartbeat_stop.set()
            await asyncio.gather(heartbeat_task, return_exceptions=True)
            if not draining_task.done():
                draining_task.cancel()
            await asyncio.gather(draining_task, return_exceptions=True)
            await self.presence.mark_stopped()

    async def process_once(self, stop_requested: asyncio.Event | None = None) -> bool:
        await self.ensure_ready()
        claim, handled = await self.claimer.claim()
        if claim is None:
            return handled
        await self._process_claim(claim, stop_requested or asyncio.Event())
        return True

    async def _process_claim(
        self, claim: ClaimedRun, stop_requested: asyncio.Event
    ) -> None:
        run_id = str(claim.run["id"])
        stop = asyncio.Event()
        cancelled = asyncio.Event()
        lease_lost = asyncio.Event()
        monitors = (
            asyncio.create_task(
                self.attempts.monitor_cancellation(run_id, cancelled, stop),
                name=f"v3-cancel-{run_id}",
            ),
            asyncio.create_task(
                self.attempts.heartbeat(claim, lease_lost, stop),
                name=f"v3-heartbeat-{run_id}",
            ),
        )
        prior_attempt_count = int(claim.run["attempt_count"])
        remaining_retries = int(claim.run["retry_count"]) - prior_attempt_count
        last_attempt_id: str | None = None
        last_attempt_started_event_id: str | None = None
        last_attempt_trace: AttemptTrace | None = None
        last_failure_event_id: str | None = None

        async def operation(local_attempt: int) -> AttemptResult:
            nonlocal last_attempt_id
            nonlocal last_attempt_started_event_id
            nonlocal last_attempt_trace
            nonlocal last_failure_event_id
            if stop_requested.is_set():
                raise WorkerDraining("worker is draining before the next attempt")
            attempt = prior_attempt_count + local_attempt
            last_attempt_trace = AttemptTrace(attempt=attempt)
            started = await self.attempts.start_attempt(claim, attempt)
            last_attempt_id = started.attempt_id
            last_attempt_started_event_id = started.started_event_id
            last_failure_event_id = None
            try:
                return await self.attempts.execute_attempt(
                    claim,
                    trace=last_attempt_trace,
                    cancelled=cancelled,
                    lease_lost=lease_lost,
                )
            except Exception as exc:
                last_failure_event_id = await self.attempts.finish_attempt_failure(
                    claim,
                    last_attempt_id,
                    last_attempt_started_event_id,
                    attempt,
                    last_attempt_trace,
                    exc,
                )
                last_attempt_id = None
                raise

        async def on_retry(
            completed_local: int,
            next_local: int,
            delay: float,
            exc: Exception,
        ) -> None:
            nonlocal last_failure_event_id
            completed = prior_attempt_count + completed_local
            next_attempt = prior_attempt_count + next_local
            if stop_requested.is_set():
                raise WorkerDraining("worker is draining before retry scheduling")
            last_failure_event_id = await self.attempts.schedule_retry(
                claim,
                completed_attempt=completed,
                next_attempt=next_attempt,
                delay=delay,
                exc=exc,
                causation_id=last_failure_event_id,
            )

        try:
            if remaining_retries < 0:
                raise RuntimeError("run attempt budget was already exhausted")
            result = await execute_with_retries(
                operation,
                retry_count=remaining_retries,
                on_retry=on_retry,
                sleep=lambda delay: self.attempts.backoff_sleep(
                    delay, cancelled, lease_lost, stop_requested
                ),
            )
            if last_attempt_id is None:
                raise RuntimeError("runtime produced no attempt")
            await self.finalizer.commit_success(claim, last_attempt_id, result)
        except RunCancelled:
            await self.finalizer.commit_cancellation(
                claim,
                last_attempt_id,
                causation_id=last_failure_event_id,
                trace=last_attempt_trace if last_attempt_id else None,
                trace_causation_id=last_attempt_started_event_id,
            )
        except LeaseLost:
            # Another worker owns recovery. This worker must never terminally commit.
            return
        except Exception as exc:
            await self.finalizer.commit_failure(
                claim,
                last_attempt_id,
                exc,
                causation_id=last_failure_event_id,
                trace=last_attempt_trace if last_attempt_id else None,
                trace_causation_id=last_attempt_started_event_id,
            )
        finally:
            stop.set()
            for monitor in monitors:
                monitor.cancel()
            await asyncio.gather(*monitors, return_exceptions=True)


def build_worker() -> AgentRuntimeV3Worker:
    ensure_agent_runtime_v3_enabled()
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeNotReady("ADE_API_DATABASE_URL is required for runtime v3")
    router_base_url = settings.model_router_v1_base_url()
    if not router_base_url:
        raise RuntimeNotReady(
            "ADE_API_MODEL_ROUTER_BASE_URL is required for runtime v3"
        )
    return AgentRuntimeV3Worker(
        engine=create_persistence_engine(settings.database_url),
        settings=settings,
        transport=RouterTransport(
            base_url=router_base_url,
            api_key=settings.resolve_model_router_api_key(),
        ),
    )


async def _main() -> None:
    worker = build_worker()
    stop_requested = asyncio.Event()
    loop = asyncio.get_running_loop()
    installed_signals = []
    for signal_name in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(signal_name, stop_requested.set)
        except (NotImplementedError, RuntimeError):
            continue
        installed_signals.append(signal_name)
    try:
        await worker.run_forever(stop_requested)
    finally:
        for signal_name in installed_signals:
            loop.remove_signal_handler(signal_name)
        await worker.aclose()


def main() -> int:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
