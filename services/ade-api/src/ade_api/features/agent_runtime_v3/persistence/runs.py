"""Repositories for idempotent runs, attempts, events, and outbox records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from datetime import datetime

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import IdempotencyConflictError, NotFoundError, fetch_one, values
from .metadata import conversation_leases, outbox, run_attempts, run_events, runs


class RunRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def accept(self, payload: Mapping[str, Any]) -> tuple[dict[str, Any], bool]:
        """Create an idempotent run or return its exact prior request.

        PostgreSQL performs the uniqueness decision, so concurrent API workers
        cannot accept two turns with the same conversation/idempotency pair.
        """

        run = values(payload)
        result = await self._connection.execute(
            pg_insert(runs)
            .values(**run)
            .on_conflict_do_nothing(
                index_elements=[runs.c.conversation_id, runs.c.idempotency_key]
            )
            .returning(*runs.c)
        )
        created = result.mappings().one_or_none()
        if created is not None:
            return dict(created), False

        existing = await fetch_one(
            self._connection,
            select(runs).where(
                and_(
                    runs.c.conversation_id == run["conversation_id"],
                    runs.c.idempotency_key == run["idempotency_key"],
                )
            ),
            "idempotent run disappeared before it could be read",
        )
        if existing["request_hash"] != run["request_hash"]:
            raise IdempotencyConflictError(
                "idempotency key is already bound to a different request hash"
            )
        return existing, True

    async def get(self, run_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(runs).where(runs.c.id == run_id),
            "run does not exist",
        )

    async def get_for_update(self, run_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(runs).where(runs.c.id == run_id).with_for_update(),
            "run does not exist",
        )

    async def get_by_idempotency(
        self, conversation_id: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(runs).where(
                and_(
                    runs.c.conversation_id == conversation_id,
                    runs.c.idempotency_key == idempotency_key,
                )
            )
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def active_for_conversation(
        self, conversation_id: str
    ) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(runs).where(
                and_(
                    runs.c.conversation_id == conversation_id,
                    runs.c.status.in_(("pending", "running")),
                )
            )
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def list_for_conversation(
        self, conversation_id: str, *, limit: int, offset: int
    ) -> tuple[int, list[dict[str, Any]]]:
        total = int(
            await self._connection.scalar(
                select(func.count())
                .select_from(runs)
                .where(runs.c.conversation_id == conversation_id)
            )
            or 0
        )
        result = await self._connection.execute(
            select(runs)
            .where(runs.c.conversation_id == conversation_id)
            .order_by(runs.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return total, [dict(row) for row in result.mappings().all()]

    async def claim_pending(self) -> dict[str, Any] | None:
        """Claim one pending run without holding the transaction during model I/O."""

        candidate = (
            select(runs.c.id)
            .where(runs.c.status == "pending")
            .order_by(runs.c.created_at, runs.c.id)
            .with_for_update(skip_locked=True)
            .limit(1)
            .scalar_subquery()
        )
        result = await self._connection.execute(
            update(runs)
            .where(runs.c.id == candidate)
            .values(status="running", started_at=func.now())
            .returning(*runs.c)
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def claim_abandoned(self) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(runs)
            .join(
                conversation_leases,
                conversation_leases.c.run_id == runs.c.id,
            )
            .where(
                and_(
                    runs.c.status == "running",
                    conversation_leases.c.released_at.is_(None),
                    conversation_leases.c.expires_at <= func.now(),
                )
            )
            .order_by(conversation_leases.c.expires_at, runs.c.id)
            .with_for_update(of=runs, skip_locked=True)
            .limit(1)
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def set_attempt_count(self, run_id: str, attempt_count: int) -> None:
        await self._connection.execute(
            update(runs)
            .where(
                and_(
                    runs.c.id == run_id,
                    runs.c.status.in_(("pending", "running")),
                )
            )
            .values(attempt_count=attempt_count)
        )

    async def requeue(self, run_id: str) -> None:
        await self._connection.execute(
            update(runs)
            .where(and_(runs.c.id == run_id, runs.c.status == "running"))
            .values(status="pending", started_at=None)
        )

    async def request_cancellation(self, run_id: str) -> dict[str, Any]:
        result = await self._connection.execute(
            update(runs)
            .where(runs.c.id == run_id)
            .values(
                cancellation_requested_at=func.coalesce(
                    runs.c.cancellation_requested_at, func.now()
                )
            )
            .returning(*runs.c)
        )
        row = result.mappings().one_or_none()
        if row is None:
            return await self.get(run_id)
        return dict(row)

    async def is_cancellation_requested(self, run_id: str) -> bool:
        result = await self._connection.execute(
            select(runs.c.cancellation_requested_at).where(runs.c.id == run_id)
        )
        return result.scalar_one_or_none() is not None

    async def finish(
        self,
        run_id: str,
        *,
        status: str,
        attempt_count: int,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        result = await self._connection.execute(
            update(runs)
            .where(
                and_(
                    runs.c.id == run_id,
                    runs.c.status.in_(("pending", "running")),
                )
            )
            .values(
                status=status,
                attempt_count=attempt_count,
                error_code=error_code,
                error_message=error_message,
                finished_at=func.now(),
            )
            .returning(*runs.c)
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else await self.get(run_id)

    async def create_attempt(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(run_attempts).values(**values(payload)).returning(*run_attempts.c),
            "run attempt was not created",
        )

    async def finish_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        provider_outcome: Mapping[str, Any],
        finished_at: datetime,
    ) -> None:
        await self._connection.execute(
            update(run_attempts)
            .where(run_attempts.c.id == attempt_id)
            .values(
                status=status,
                provider_outcome=values(provider_outcome),
                finished_at=finished_at,
            )
        )

    async def abandon_open_attempts(self, run_id: str) -> None:
        await self._connection.execute(
            update(run_attempts)
            .where(
                and_(
                    run_attempts.c.run_id == run_id,
                    run_attempts.c.status == "running",
                )
            )
            .values(
                status="failed",
                provider_outcome={"error_code": "worker_lease_expired"},
                finished_at=func.now(),
            )
        )

    async def append_event(
        self, event: Mapping[str, Any], outbox_record: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Store an event and optional publish record in the caller's transaction."""

        created = await fetch_one(
            self._connection,
            insert(run_events).values(**values(event)).returning(*run_events.c),
            "run event was not created",
        )
        if outbox_record is not None:
            record = values(outbox_record)
            record["run_event_id"] = created["id"]
            await self._connection.execute(insert(outbox).values(**record))
        return created

    async def append_ordered_event(
        self,
        *,
        event_id: str,
        run_id: str,
        event_type: str,
        correlation_id: str,
        payload: Mapping[str, Any],
        attempt: int | None = None,
        causation_id: str | None = None,
        visibility: str = "operator",
        outbox_id: str | None = None,
    ) -> dict[str, Any]:
        locked = await self._connection.execute(
            select(runs.c.id).where(runs.c.id == run_id).with_for_update()
        )
        if locked.scalar_one_or_none() is None:
            raise NotFoundError("run does not exist")
        sequence = int(
            await self._connection.scalar(
                select(func.coalesce(func.max(run_events.c.sequence), 0) + 1).where(
                    run_events.c.run_id == run_id
                )
            )
        )
        event = {
            "id": event_id,
            "run_id": run_id,
            "sequence": sequence,
            "schema_version": 1,
            "event_type": event_type,
            "attempt": attempt,
            "correlation_id": correlation_id,
            "causation_id": causation_id,
            "visibility": visibility,
            "payload": values(payload),
        }
        outbox_record = None
        if outbox_id:
            outbox_record = {
                "id": outbox_id,
                "run_id": run_id,
                "topic": "agent_runtime_v3.run_events",
                "payload": event,
            }
        return await self.append_event(event, outbox_record)

    async def list_events(
        self, run_id: str, after_sequence: int = 0
    ) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(run_events)
            .where(
                and_(
                    run_events.c.run_id == run_id,
                    run_events.c.sequence > after_sequence,
                )
            )
            .order_by(run_events.c.sequence)
        )
        return [dict(row) for row in result.mappings()]

    async def list_event_page(
        self, run_id: str, *, limit: int, after_sequence: int = 0
    ) -> tuple[int, list[dict[str, Any]]]:
        await self.get(run_id)
        total = int(
            await self._connection.scalar(
                select(func.count())
                .select_from(run_events)
                .where(run_events.c.run_id == run_id)
            )
            or 0
        )
        result = await self._connection.execute(
            select(run_events)
            .where(
                run_events.c.run_id == run_id,
                run_events.c.sequence > after_sequence,
            )
            .order_by(run_events.c.sequence)
            .limit(limit)
        )
        return total, [dict(row) for row in result.mappings().all()]
