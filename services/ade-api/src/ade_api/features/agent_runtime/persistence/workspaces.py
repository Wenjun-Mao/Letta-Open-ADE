"""Workspace repository."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import fetch_one, values
from .metadata import workspaces


class WorkspaceRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            insert(workspaces).values(**values(payload)).returning(*workspaces.c),
            "workspace was not created",
        )

    async def get(self, workspace_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(workspaces).where(workspaces.c.id == workspace_id),
            "workspace does not exist",
        )

    async def ensure(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        workspace = values(payload)
        await self._connection.execute(
            pg_insert(workspaces)
            .values(**workspace)
            .on_conflict_do_nothing(index_elements=[workspaces.c.workspace_key])
        )
        return await fetch_one(
            self._connection,
            select(workspaces).where(
                workspaces.c.workspace_key == workspace["workspace_key"]
            ),
            "workspace was not created",
        )
