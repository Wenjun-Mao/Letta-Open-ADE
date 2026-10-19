"""SQL-owned inspection projections, scoped before any native HTTP request."""

from sqlalchemy import func, select

from ade_api.integrations.hindsight_sources import MemoryRelationship

from .base import fetch_one
from .memory_deliveries import MemoryDeliveryRepository
from .memory_relationships import MemoryRelationshipRepository
from .metadata import memory_deliveries, messages


class MemoryInspectionRepository:
    def __init__(self, connection):
        self.connection = connection

    async def relationship(self, *, workspace_id, subject_id, character_root_id):
        scope = MemoryRelationship(workspace_id, subject_id, character_root_id)
        return await MemoryRelationshipRepository(self.connection).get(
            scope.bank_id, workspace_id=workspace_id
        )

    def deliveries(self, bank_id):
        return (
            select(
                memory_deliveries,
                messages.c.conversation_id,
                messages.c.role,
                messages.c.sequence.label("message_sequence"),
            )
            .join(messages, messages.c.id == memory_deliveries.c.message_id)
            .where(memory_deliveries.c.bank_id == bank_id)
        )

    async def list(self, bank_id, *, limit, offset):
        grouped = await self.connection.execute(
            select(memory_deliveries.c.status, func.count())
            .where(memory_deliveries.c.bank_id == bank_id)
            .group_by(memory_deliveries.c.status)
        )
        counts = dict(grouped.tuples().all())
        first = (
            (
                await self.connection.execute(
                    select(
                        memory_deliveries.c.operation_id,
                        memory_deliveries.c.relationship_sequence,
                    )
                    .where(
                        memory_deliveries.c.bank_id == bank_id,
                        memory_deliveries.c.status != "retained",
                    )
                    .order_by(memory_deliveries.c.relationship_sequence)
                    .limit(1)
                )
            )
            .mappings()
            .one_or_none()
        )
        result = await self.connection.execute(
            self.deliveries(bank_id)
            .order_by(memory_deliveries.c.relationship_sequence)
            .limit(limit)
            .offset(offset)
        )
        return (
            counts,
            dict(first) if first else None,
            [dict(row) for row in result.mappings()],
        )

    async def source(self, bank_id, document_id):
        return await fetch_one(
            self.connection,
            self.deliveries(bank_id)
            .add_columns(messages.c.content, messages.c.created_at.label("occurred_at"))
            .where(memory_deliveries.c.document_id == document_id),
            "Source does not exist in this relationship",
        )

    async def retry(self, bank_id, operation_id, *, expected_check_count):
        await MemoryDeliveryRepository(self.connection).request_retry(
            operation_id, bank_id=bank_id, expected_check_count=expected_check_count
        )
        return await fetch_one(
            self.connection,
            self.deliveries(bank_id).where(
                memory_deliveries.c.operation_id == operation_id
            ),
            "Delivery does not exist in this relationship",
        )
