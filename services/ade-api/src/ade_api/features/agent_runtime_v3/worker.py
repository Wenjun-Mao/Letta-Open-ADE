from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings, get_settings

from .errors import RuntimeNotReady
from .events import append_run_event
from .flags import ensure_agent_runtime_v3_enabled
from .persistence.database import create_persistence_engine
from .persistence.runs import RunRepository
from .persistence.validation import validate_database_at_head
from .retry import execute_with_retries
from .router_transport import RouterTransport
from .turn_execution import AttemptResult, TurnExecution
from .worker_claims import ClaimedRun, RunClaimer
from .worker_control import (
    AttemptController,
    LeaseLost,
    RunCancelled,
    worker_error_code,
)
from .worker_finalization import RunFinalizer


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
        execution = TurnExecution(engine=engine, transport=transport)
        self.claimer = RunClaimer(engine=engine, settings=settings)
        self.attempts = AttemptController(
            engine=engine, settings=settings, execution=execution
        )
        self.finalizer = RunFinalizer(engine)
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

    async def run_forever(self) -> None:
        await self.ensure_ready()
        while True:
            processed = await self.process_once()
            if not processed:
                await asyncio.sleep(self.settings.agent_runtime_v3_worker_poll_seconds)

    async def process_once(self) -> bool:
        await self.ensure_ready()
        claim, handled = await self.claimer.claim()
        if claim is None:
            return handled
        await self._process_claim(claim)
        return True

    async def _process_claim(self, claim: ClaimedRun) -> None:
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

        async def operation(local_attempt: int) -> AttemptResult:
            nonlocal last_attempt_id
            attempt = prior_attempt_count + local_attempt
            last_attempt_id = await self.attempts.start_attempt(claim, attempt)
            try:
                return await self.attempts.execute_attempt(
                    claim,
                    cancelled=cancelled,
                    lease_lost=lease_lost,
                )
            except Exception as exc:
                await self.attempts.finish_attempt_failure(
                    claim, last_attempt_id, attempt, exc
                )
                last_attempt_id = None
                raise

        async def on_retry(
            completed_local: int,
            next_local: int,
            delay: float,
            exc: Exception,
        ) -> None:
            completed = prior_attempt_count + completed_local
            next_attempt = prior_attempt_count + next_local
            async with self.engine.begin() as connection:
                await append_run_event(
                    RunRepository(connection),
                    run_id=run_id,
                    event_type="retry.scheduled",
                    payload={
                        "completed_attempt": completed,
                        "next_attempt": next_attempt,
                        "delay_seconds": round(delay, 6),
                        "error_code": worker_error_code(exc),
                    },
                    attempt=completed,
                )

        try:
            if remaining_retries < 0:
                raise RuntimeError("run attempt budget was already exhausted")
            result = await execute_with_retries(
                operation,
                retry_count=remaining_retries,
                on_retry=on_retry,
                sleep=lambda delay: self.attempts.backoff_sleep(
                    delay, cancelled, lease_lost
                ),
            )
            if last_attempt_id is None:
                raise RuntimeError("runtime produced no attempt")
            await self.finalizer.commit_success(claim, last_attempt_id, result)
        except RunCancelled:
            await self.finalizer.commit_cancellation(claim, last_attempt_id)
        except LeaseLost:
            # Another worker owns recovery. This worker must never terminally commit.
            return
        except Exception as exc:
            await self.finalizer.commit_failure(claim, last_attempt_id, exc)
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
    try:
        await worker.run_forever()
    finally:
        await worker.aclose()


def main() -> int:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
