from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings

from .events import append_run_event
from .persistence.base import LeaseUnavailableError
from .persistence.leases import ConversationLeaseRepository
from .persistence.runs import RunRepository


@dataclass(frozen=True)
class ClaimedRun:
    run: dict[str, Any]
    lease_token: str
    recovered: bool


class RunClaimer:
    """Claims pending work or recovers work whose lease expired."""

    def __init__(self, *, engine: AsyncEngine, settings: AdeApiSettings) -> None:
        self.engine = engine
        self.settings = settings

    async def claim(self) -> tuple[ClaimedRun | None, bool]:
        async with self.engine.begin() as connection:
            runs = RunRepository(connection)
            leases = ConversationLeaseRepository(connection)
            run = await runs.claim_pending()
            recovered = False
            if run is None:
                run = await runs.claim_abandoned()
                recovered = run is not None
            if run is None:
                return None, False
            if recovered:
                await runs.abandon_open_attempts(str(run["id"]))
                if int(run["attempt_count"]) >= int(run["retry_count"]) + 1:
                    await runs.finish(
                        str(run["id"]),
                        status="failed",
                        attempt_count=int(run["attempt_count"]),
                        error_code="worker_lease_expired",
                        error_message="Worker lease expired after the attempt budget",
                    )
                    await leases.release_for_run(str(run["id"]))
                    await append_run_event(
                        runs,
                        run_id=str(run["id"]),
                        event_type="run.failed",
                        payload={
                            "attempt_count": int(run["attempt_count"]),
                            "error_code": "worker_lease_expired",
                        },
                    )
                    return None, True
            lease_token = str(uuid4())
            try:
                await leases.acquire(
                    lease_id=str(uuid4()),
                    conversation_id=str(run["conversation_id"]),
                    run_id=str(run["id"]),
                    lease_token=lease_token,
                    holder_id=self.settings.agent_runtime_v3_worker_id,
                    expires_at=_utc_now()
                    + timedelta(seconds=self.settings.agent_runtime_v3_lease_seconds),
                )
            except LeaseUnavailableError:
                if not recovered:
                    await runs.requeue(str(run["id"]))
                return None, True
            await append_run_event(
                runs,
                run_id=str(run["id"]),
                event_type="run.recovered" if recovered else "run.started",
                payload={
                    "worker_id": self.settings.agent_runtime_v3_worker_id,
                    "prior_attempt_count": int(run["attempt_count"]),
                },
            )
            return ClaimedRun(
                run=run, lease_token=lease_token, recovered=recovered
            ), True


def _utc_now() -> datetime:
    return datetime.now(UTC)
