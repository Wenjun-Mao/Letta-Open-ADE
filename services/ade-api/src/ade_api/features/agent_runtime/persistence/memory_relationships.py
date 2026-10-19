"""Persisted character-local bank identity and fenced one-time initialization."""

from datetime import timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.integrations.hindsight_bank import (
    bank_configuration,
    bank_configuration_sha256,
)
from ade_api.integrations.hindsight_sources import MemoryRelationship

from .base import LeaseUnavailableError, PersistenceError, fetch_one
from .metadata import memory_relationships, workspaces


class MemoryRelationshipRepository:
    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def ensure(self, scope: MemoryRelationship) -> dict:
        authority = await self.connection.scalar(
            select(workspaces.c.memory_backend).where(
                workspaces.c.id == scope.workspace_id,
            )
        )
        if authority != "hindsight":
            raise PersistenceError("Hindsight requires an explicitly fresh workspace")
        configuration = bank_configuration()
        configuration_sha256 = bank_configuration_sha256()
        await self.connection.execute(
            insert(memory_relationships)
            .values(
                bank_id=scope.bank_id,
                **scope.as_dict(),
                configuration=configuration,
                configuration_sha256=configuration_sha256,
            )
            .on_conflict_do_nothing(index_elements=[memory_relationships.c.bank_id])
        )
        row = await self.get(
            scope.bank_id, workspace_id=scope.workspace_id, for_update=True
        )
        if any(str(row[key]) != value for key, value in scope.as_dict().items()) or (
            row["configuration_sha256"] != configuration_sha256
            or row["configuration"] != configuration
        ):
            raise PersistenceError(
                "Frozen Hindsight relationship/configuration changed"
            )
        return row

    async def get(self, bank_id: str, *, workspace_id: str, for_update=False) -> dict:
        statement = select(memory_relationships).where(
            memory_relationships.c.bank_id == bank_id,
            memory_relationships.c.workspace_id == workspace_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return await fetch_one(
            self.connection, statement, "Memory relationship does not exist"
        )

    async def allocate_sequence(self, bank_id: str, *, workspace_id: str) -> int:
        result = await self.connection.execute(
            update(memory_relationships)
            .where(
                memory_relationships.c.bank_id == bank_id,
                memory_relationships.c.workspace_id == workspace_id,
            )
            .values(next_sequence=memory_relationships.c.next_sequence + 1)
            .returning(memory_relationships.c.next_sequence)
        )
        return int(result.scalar_one()) - 1

    async def claim_initialization(
        self, bank_id: str, *, workspace_id: str, token: str, lease_seconds: int
    ) -> dict | None:
        result = await self.connection.execute(
            update(memory_relationships)
            .where(
                memory_relationships.c.bank_id == bank_id,
                memory_relationships.c.workspace_id == workspace_id,
                or_(
                    memory_relationships.c.state == "new",
                    (memory_relationships.c.state == "initializing")
                    & (
                        memory_relationships.c.initialization_expires_at
                        <= func.clock_timestamp()
                    ),
                ),
            )
            .values(
                state="initializing",
                initialization_token=token,
                initialization_expires_at=func.clock_timestamp()
                + timedelta(seconds=lease_seconds),
            )
            .returning(*memory_relationships.c)
        )
        row = result.mappings().one_or_none()
        return dict(row) if row else None

    async def finish_initialization(
        self,
        bank_id: str,
        *,
        workspace_id: str,
        token: str,
        state: str,
        error: str | None = None,
    ) -> None:
        if state not in {"ready", "new", "failed"}:
            raise ValueError("Invalid initialization outcome")
        values = {
            "state": state,
            "initialization_token": None,
            "initialization_expires_at": None,
            "last_error_code": error,
        }
        if state == "ready":
            values["initialized_at"] = func.coalesce(
                memory_relationships.c.initialized_at, func.now()
            )
        result = await self.connection.execute(
            update(memory_relationships)
            .where(
                memory_relationships.c.bank_id == bank_id,
                memory_relationships.c.workspace_id == workspace_id,
                memory_relationships.c.state == "initializing",
                memory_relationships.c.initialization_token == token,
                memory_relationships.c.initialization_expires_at
                > func.clock_timestamp(),
            )
            .values(**values)
        )
        if result.rowcount != 1:
            raise LeaseUnavailableError(
                "Memory initialization lease no longer belongs to this worker"
            )

    async def mark_missing(self, bank_id: str, *, workspace_id: str) -> None:
        await self.connection.execute(
            update(memory_relationships)
            .where(
                memory_relationships.c.bank_id == bank_id,
                memory_relationships.c.workspace_id == workspace_id,
                memory_relationships.c.state == "ready",
            )
            .values(state="missing", last_error_code="established_memory_bank_missing")
        )

    async def mark_configuration_changed(
        self, bank_id: str, *, workspace_id: str
    ) -> None:
        await self.connection.execute(
            update(memory_relationships)
            .where(
                memory_relationships.c.bank_id == bank_id,
                memory_relationships.c.workspace_id == workspace_id,
                memory_relationships.c.state == "ready",
            )
            .values(state="failed", last_error_code="memory_bank_configuration_changed")
        )
