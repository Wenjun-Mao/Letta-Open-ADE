"""Database-backed conversation lease repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import LeaseUnavailableError
from .metadata import conversation_leases


class ConversationLeaseRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def acquire(
        self,
        *,
        lease_id: str,
        conversation_id: str,
        run_id: str,
        lease_token: str,
        holder_id: str,
        expires_at: datetime,
    ) -> dict[str, object]:
        """Acquire or reclaim only an expired active lease in one PostgreSQL statement."""

        result = await self._connection.execute(
            pg_insert(conversation_leases)
            .values(
                id=lease_id,
                conversation_id=conversation_id,
                run_id=run_id,
                lease_token=lease_token,
                holder_id=holder_id,
                expires_at=expires_at,
            )
            .on_conflict_do_update(
                index_elements=[conversation_leases.c.conversation_id],
                index_where=conversation_leases.c.released_at.is_(None),
                set_={
                    "run_id": run_id,
                    "lease_token": lease_token,
                    "holder_id": holder_id,
                    "heartbeat_at": func.now(),
                    "expires_at": expires_at,
                    "released_at": None,
                },
                where=conversation_leases.c.expires_at <= func.now(),
            )
            .returning(*conversation_leases.c)
        )
        lease = result.mappings().one_or_none()
        if lease is None:
            raise LeaseUnavailableError("conversation already has an active lease")
        return dict(lease)

    async def create_pending(
        self,
        *,
        lease_id: str,
        conversation_id: str,
        run_id: str,
        lease_token: str,
        expires_at: datetime,
    ) -> dict[str, object]:
        result = await self._connection.execute(
            insert(conversation_leases)
            .values(
                id=lease_id,
                conversation_id=conversation_id,
                run_id=run_id,
                lease_token=lease_token,
                holder_id="pending",
                expires_at=expires_at,
            )
            .returning(*conversation_leases.c)
        )
        row = result.mappings().one()
        return dict(row)

    async def get_active(self, conversation_id: str) -> dict[str, object] | None:
        result = await self._connection.execute(
            select(conversation_leases).where(
                and_(
                    conversation_leases.c.conversation_id == conversation_id,
                    conversation_leases.c.released_at.is_(None),
                )
            )
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def owns(self, lease_token: str, run_id: str) -> bool:
        result = await self._connection.execute(
            select(conversation_leases.c.id).where(
                and_(
                    conversation_leases.c.lease_token == lease_token,
                    conversation_leases.c.run_id == run_id,
                    conversation_leases.c.released_at.is_(None),
                    conversation_leases.c.expires_at > func.now(),
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def heartbeat(self, lease_token: str, expires_at: datetime) -> bool:
        result = await self._connection.execute(
            update(conversation_leases)
            .where(
                and_(
                    conversation_leases.c.lease_token == lease_token,
                    conversation_leases.c.released_at.is_(None),
                    conversation_leases.c.expires_at > func.now(),
                )
            )
            .values(heartbeat_at=func.now(), expires_at=expires_at)
        )
        return result.rowcount == 1

    async def release(self, lease_token: str) -> bool:
        result = await self._connection.execute(
            update(conversation_leases)
            .where(
                and_(
                    conversation_leases.c.lease_token == lease_token,
                    conversation_leases.c.released_at.is_(None),
                )
            )
            .values(released_at=func.now())
        )
        return result.rowcount == 1

    async def release_for_run(self, run_id: str) -> bool:
        result = await self._connection.execute(
            update(conversation_leases)
            .where(
                and_(
                    conversation_leases.c.run_id == run_id,
                    conversation_leases.c.released_at.is_(None),
                )
            )
            .values(released_at=func.now())
        )
        return result.rowcount == 1
