"""Idempotent operator-action receipts, separate from conversation runs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import and_, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import fetch_one, values
from .metadata import memory_actions


class MemoryActionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def find_by_key(
        self, subject_id: str, idempotency_key: str
    ) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(memory_actions).where(
                and_(
                    memory_actions.c.subject_id == subject_id,
                    memory_actions.c.idempotency_key == idempotency_key,
                )
            )
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(memory_actions)
            .values(**values(payload))
            .returning(*memory_actions.c),
            "memory action receipt was not created",
        )
