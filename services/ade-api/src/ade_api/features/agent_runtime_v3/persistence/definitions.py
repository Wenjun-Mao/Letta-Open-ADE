"""Logical agent definitions and immutable version persistence."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection

from .base import OptimisticLockError, PersistenceError, fetch_one, values
from .metadata import agent_definition_versions, agent_definitions, workspaces


class AgentDefinitionRepository:
    def __init__(self, connection: AsyncConnection) -> None:
        self._connection = connection

    async def get(self, definition_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(agent_definitions).where(agent_definitions.c.id == definition_id),
            "agent definition does not exist",
        )

    async def get_for_update(self, definition_id: str) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            select(agent_definitions)
            .where(agent_definitions.c.id == definition_id)
            .with_for_update(),
            "agent definition does not exist",
        )

    async def find_by_key(
        self, workspace_id: str, definition_key: str, *, for_update: bool = False
    ) -> dict[str, Any] | None:
        statement = select(agent_definitions).where(
            agent_definitions.c.workspace_id == workspace_id,
            agent_definitions.c.definition_key == definition_key,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self._connection.execute(statement)
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    async def list_current(
        self,
        workspace_id: str,
        *,
        purpose: str,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> tuple[int, list[dict[str, Any]]]:
        conditions = [
            agent_definitions.c.workspace_id == workspace_id,
            agent_definitions.c.purpose == purpose,
        ]
        if not include_archived:
            conditions.append(agent_definitions.c.archived_at.is_(None))
        total = int(
            await self._connection.scalar(
                select(func.count()).select_from(agent_definitions).where(*conditions)
            )
            or 0
        )
        result = await self._connection.execute(
            select(
                *agent_definition_versions.c,
                agent_definitions.c.archived_at.label("definition_archived_at"),
                agent_definitions.c.updated_at.label("definition_updated_at"),
            )
            .join(
                agent_definition_versions,
                agent_definition_versions.c.id
                == agent_definitions.c.current_version_id,
            )
            .where(*conditions)
            .order_by(agent_definitions.c.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return total, [dict(row) for row in result.mappings().all()]

    async def set_archived(
        self, definition_id: str, *, archived: bool
    ) -> dict[str, Any]:
        return await fetch_one(
            self._connection,
            update(agent_definitions)
            .where(agent_definitions.c.id == definition_id)
            .values(
                archived_at=func.now() if archived else None,
                updated_at=func.now(),
            )
            .returning(*agent_definitions.c),
            "agent definition does not exist",
        )


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

    async def list_versions(self, agent_definition_id: str) -> list[dict[str, Any]]:
        result = await self._connection.execute(
            select(agent_definition_versions)
            .where(
                agent_definition_versions.c.agent_definition_id == agent_definition_id
            )
            .order_by(agent_definition_versions.c.version.desc())
        )
        return [dict(row) for row in result.mappings().all()]

    async def create_next(
        self,
        workspace_id: str,
        payload: Mapping[str, Any],
        *,
        purpose: str = "development",
        expected_current_version: int | None = None,
    ) -> dict[str, Any]:
        """Serialize root/version allocation and advance the current pointer."""

        await fetch_one(
            self._connection,
            select(workspaces).where(workspaces.c.id == workspace_id).with_for_update(),
            "workspace does not exist",
        )
        definition = values(payload)
        root_repository = AgentDefinitionRepository(self._connection)
        root = await root_repository.find_by_key(
            workspace_id, str(definition["definition_key"]), for_update=True
        )
        if root is None:
            if expected_current_version not in {None, 0}:
                raise OptimisticLockError(
                    "agent definition current version does not match"
                )
            root_id = str(definition.pop("agent_definition_id", "") or uuid4())
            root = await fetch_one(
                self._connection,
                insert(agent_definitions)
                .values(
                    id=root_id,
                    workspace_id=workspace_id,
                    definition_key=definition["definition_key"],
                    name=definition["name"],
                    purpose=purpose,
                )
                .returning(*agent_definitions.c),
                "agent definition was not created",
            )
            current_version = 0
        else:
            if str(root["purpose"]) != purpose:
                raise PersistenceError(
                    "agent definition purpose cannot change between versions"
                )
            if root.get("archived_at") is not None:
                raise PersistenceError(
                    "archived agent definitions cannot receive new versions"
                )
            current_version = int(
                await self._connection.scalar(
                    select(
                        func.coalesce(func.max(agent_definition_versions.c.version), 0)
                    ).where(
                        agent_definition_versions.c.agent_definition_id == root["id"]
                    )
                )
                or 0
            )
            if (
                expected_current_version is not None
                and current_version != expected_current_version
            ):
                raise OptimisticLockError(
                    "agent definition current version does not match"
                )

        definition["workspace_id"] = workspace_id
        definition["agent_definition_id"] = root["id"]
        definition["purpose"] = purpose
        definition["version"] = current_version + 1
        version = await self.create(definition)
        await self._connection.execute(
            update(agent_definitions)
            .where(agent_definitions.c.id == root["id"])
            .values(
                current_version_id=version["id"],
                name=version["name"],
                updated_at=func.now(),
            )
        )
        return version
