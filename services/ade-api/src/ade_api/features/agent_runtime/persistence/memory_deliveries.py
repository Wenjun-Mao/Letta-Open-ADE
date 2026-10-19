"""Immutable message outbox with ordered claims and token-fenced readbacks."""

from datetime import timedelta

from sqlalchemy import case, exists, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.integrations.hindsight_sources import (
    MemoryDelivery,
    MemorySourceMessage,
    prepare_memory_delivery,
)

from .base import (
    IdempotencyConflictError,
    LeaseUnavailableError,
    OptimisticLockError,
    fetch_one,
)
from .memory_relationships import MemoryRelationshipRepository
from .metadata import memory_deliveries


MAX_RECONCILIATION_ERRORS = 5


def verified_delivery(row: dict) -> MemoryDelivery:
    delivery = MemoryDelivery(
        bank_id=row["bank_id"],
        message_id=str(row["message_id"]),
        operation_id=str(row["operation_id"]),
        document_id=row["document_id"],
        payload=bytes(row["payload"]),
        payload_sha256=row["payload_sha256"],
    )
    delivery.verify()
    return delivery


class MemoryDeliveryRepository:
    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def enqueue(
        self,
        source: MemorySourceMessage,
        *,
        earlier_messages: tuple[MemorySourceMessage, ...] = (),
    ) -> dict:
        delivery = prepare_memory_delivery(source, earlier_messages=earlier_messages)
        relationships = MemoryRelationshipRepository(self.connection)
        relationship = await relationships.ensure(source.relationship)
        prior = (
            (
                await self.connection.execute(
                    select(memory_deliveries).where(
                        memory_deliveries.c.message_id == source.message_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if prior:
            previous = verified_delivery(dict(prior))
            if previous != delivery:
                raise IdempotencyConflictError(
                    "Message already owns a different immutable delivery"
                )
            return dict(prior)
        sequence = await relationships.allocate_sequence(
            delivery.bank_id, workspace_id=source.relationship.workspace_id
        )
        return await fetch_one(
            self.connection,
            insert(memory_deliveries)
            .values(
                operation_id=delivery.operation_id,
                workspace_id=source.relationship.workspace_id,
                bank_id=delivery.bank_id,
                configuration_sha256=relationship["configuration_sha256"],
                message_id=source.message_id,
                relationship_sequence=sequence,
                document_id=delivery.document_id,
                payload=delivery.payload,
                payload_sha256=delivery.payload_sha256,
            )
            .returning(*memory_deliveries.c),
            "Memory delivery was not created",
        )

    async def get(self, operation_id: str, *, bank_id: str) -> dict:
        return await fetch_one(
            self.connection,
            select(memory_deliveries).where(
                memory_deliveries.c.operation_id == operation_id,
                memory_deliveries.c.bank_id == bank_id,
            ),
            "Memory delivery does not exist in this relationship",
        )

    async def list(
        self, bank_id: str, *, limit: int = 100, offset: int = 0
    ) -> tuple[int, list[dict]]:
        conditions = [memory_deliveries.c.bank_id == bank_id]
        total = await self.connection.scalar(
            select(func.count()).select_from(memory_deliveries).where(*conditions)
        )
        rows = await self.connection.execute(
            select(memory_deliveries)
            .where(*conditions)
            .order_by(memory_deliveries.c.relationship_sequence)
            .limit(limit)
            .offset(offset)
        )
        return int(total or 0), [dict(row) for row in rows.mappings()]

    async def claim(
        self, *, workspace_id: str, token: str, lease_seconds: int
    ) -> dict | None:
        earlier = memory_deliveries.alias("earlier_delivery")
        blocked = exists(
            select(1).where(
                earlier.c.bank_id == memory_deliveries.c.bank_id,
                earlier.c.relationship_sequence
                < memory_deliveries.c.relationship_sequence,
                earlier.c.status != "retained",
            )
        )
        candidate = (
            (
                await self.connection.execute(
                    select(memory_deliveries)
                    .where(
                        memory_deliveries.c.workspace_id == workspace_id,
                        memory_deliveries.c.status.in_(
                            ("queued", "submitting", "processing", "uncertain")
                        ),
                        memory_deliveries.c.consecutive_errors
                        < MAX_RECONCILIATION_ERRORS,
                        memory_deliveries.c.next_attempt_at <= func.now(),
                        or_(
                            memory_deliveries.c.lease_token.is_(None),
                            memory_deliveries.c.lease_expires_at <= func.now(),
                        ),
                        ~blocked,
                    )
                    .order_by(
                        memory_deliveries.c.next_attempt_at,
                        memory_deliveries.c.created_at,
                    )
                    .with_for_update(skip_locked=True)
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        if candidate is None:
            return None
        return await fetch_one(
            self.connection,
            update(memory_deliveries)
            .where(
                memory_deliveries.c.operation_id == candidate["operation_id"],
            )
            .values(
                lease_token=token,
                lease_expires_at=func.now() + timedelta(seconds=lease_seconds),
                check_count=memory_deliveries.c.check_count + 1,
                status=case(
                    (
                        memory_deliveries.c.status.in_(("queued", "uncertain")),
                        "submitting",
                    ),
                    else_=memory_deliveries.c.status,
                ),
                updated_at=func.now(),
            )
            .returning(*memory_deliveries.c),
            "Memory delivery claim disappeared",
        )

    def owned(self, operation_id: str, token: str):
        return update(memory_deliveries).where(
            memory_deliveries.c.operation_id == operation_id,
            memory_deliveries.c.lease_token == token,
            memory_deliveries.c.lease_expires_at > func.now(),
        )

    async def heartbeat(
        self, operation_id: str, token: str, *, lease_seconds: int
    ) -> bool:
        result = await self.connection.execute(
            self.owned(operation_id, token).values(
                lease_expires_at=func.now() + timedelta(seconds=lease_seconds),
                updated_at=func.now(),
            )
        )
        return result.rowcount == 1

    async def start_dispatch(self, operation_id: str, token: str) -> None:
        result = await self.connection.execute(
            self.owned(operation_id, token).values(
                attempt_count=memory_deliveries.c.attempt_count + 1,
                retry_requested=False,
                first_dispatch_at=func.coalesce(
                    memory_deliveries.c.first_dispatch_at, func.now()
                ),
                updated_at=func.now(),
            )
        )
        self.require_owned(result.rowcount)

    async def record_native(
        self,
        operation_id: str,
        token: str,
        *,
        status: str,
        native_status: str,
        progress: dict,
        acknowledgement: str | None = None,
        poll_seconds: float = 1,
    ) -> None:
        if status not in {"processing", "retained", "failed"}:
            raise ValueError("Invalid native delivery outcome")
        values = {
            "status": status,
            "native_status": native_status,
            "native_progress": progress,
            "last_checked_at": func.now(),
            "updated_at": func.now(),
            "consecutive_errors": 0,
            "retry_requested": False,
            "last_error_code": "native_operation_failed"
            if status == "failed"
            else None,
            "lease_token": None,
            "lease_expires_at": None,
            "next_attempt_at": func.now() + timedelta(seconds=poll_seconds),
        }
        if acknowledgement:
            values.update(
                accepted_at=func.coalesce(memory_deliveries.c.accepted_at, func.now()),
                accepted_via=func.coalesce(
                    memory_deliveries.c.accepted_via, acknowledgement
                ),
            )
        if status == "retained":
            values.update(retained_at=func.now(), retry_requested=False)
        result = await self.connection.execute(
            self.owned(operation_id, token).values(**values)
        )
        self.require_owned(result.rowcount)

    async def record_error(
        self, operation_id: str, token: str, *, error_code: str, permanent: bool = False
    ) -> None:
        row = (
            (
                await self.connection.execute(
                    select(memory_deliveries)
                    .where(
                        memory_deliveries.c.operation_id == operation_id,
                        memory_deliveries.c.lease_token == token,
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise LeaseUnavailableError("Memory delivery lease is not owned")
        failures = int(row["consecutive_errors"]) + 1
        result = await self.connection.execute(
            self.owned(operation_id, token).values(
                status="failed" if permanent else "uncertain",
                consecutive_errors=failures,
                last_error_code=error_code,
                last_checked_at=func.now(),
                updated_at=func.now(),
                next_attempt_at=func.now()
                + timedelta(seconds=min(60, 2 ** min(failures, 6))),
                lease_token=None,
                lease_expires_at=None,
            )
        )
        self.require_owned(result.rowcount)

    async def request_retry(
        self, operation_id: str, *, bank_id: str, expected_check_count: int
    ) -> dict:
        row = await fetch_one(
            self.connection,
            select(memory_deliveries)
            .where(
                memory_deliveries.c.operation_id == operation_id,
                memory_deliveries.c.bank_id == bank_id,
            )
            .with_for_update(),
            "Memory delivery does not exist in this relationship",
        )
        if int(row["check_count"]) != expected_check_count:
            raise OptimisticLockError("Memory delivery changed; reload before Retry")
        if row["status"] == "queued" and row["retry_requested"]:
            return row
        if row["status"] not in {"failed", "uncertain"}:
            raise OptimisticLockError("Only failed/uncertain delivery can be retried")
        return await fetch_one(
            self.connection,
            update(memory_deliveries)
            .where(
                memory_deliveries.c.operation_id == operation_id,
            )
            .values(
                status="queued",
                retry_requested=True,
                consecutive_errors=0,
                next_attempt_at=func.now(),
                updated_at=func.now(),
            )
            .returning(*memory_deliveries.c),
            "Memory delivery Retry disappeared",
        )

    @staticmethod
    def require_owned(affected: int) -> None:
        if affected != 1:
            raise LeaseUnavailableError(
                "Memory delivery lease no longer belongs to this worker"
            )
