"""Immutable agent definition-version repository."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import fetch_one, values
from .metadata import agent_definition_versions, workspaces


class DefinitionVersionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Insert a definition version; database uniqueness preserves immutability."""

        return await fetch_one(
            self._connection,
            insert(agent_definition_versions)
            .values(**values(payload))
            .returning(*agent_definition_versions.c),
            "definition version was not created",
        )

    async def get(self, definition_version_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(agent_definition_versions).where(
                agent_definition_versions.c.id == definition_version_id
            ),
            "definition version does not exist",
        )

    async def find(self, definition_version_id: str) -> dict[str, Any] | None:
        result = await self._connection.execute(
            select(agent_definition_versions).where(
                agent_definition_versions.c.id == definition_version_id
            )
        )
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def create_next(
        self, workspace_id: str, payload: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Serialize version allocation on the owning workspace row."""

        await fetch_one(
            self._connection,
            select(workspaces).where(workspaces.c.id == workspace_id).with_for_update(),
            "workspace does not exist",
        )
        definition = values(payload)
        definition["workspace_id"] = workspace_id
        definition["version"] = int(
            await self._connection.scalar(
                select(
                    func.coalesce(func.max(agent_definition_versions.c.version), 0) + 1
                ).where(
                    agent_definition_versions.c.workspace_id == workspace_id,
                    agent_definition_versions.c.definition_key
                    == definition["definition_key"],
                )
            )
        )
        return await self.create(definition)
