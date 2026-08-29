from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from .errors import (
    AgentRuntimeV3Error,
    IdempotencyConflict,
    RuntimeConflict,
    RuntimeNotFound,
    RuntimeNotReady,
)
from .persistence.base import IdempotencyConflictError, NotFoundError
from .persistence.validation import validate_database_at_head
from .persistence.workspaces import WorkspaceRepository


DEFAULT_WORKSPACE_ID = str(uuid5(NAMESPACE_URL, "ade://workspace/default"))
DEFAULT_WORKSPACE_KEY = "default"


class RuntimeDatabase:
    """Owns readiness and error translation for the v3 persistence boundary."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self._ready = False
        self._ready_lock = asyncio.Lock()

    async def ensure_ready(self) -> None:
        if self._ready:
            return
        async with self._ready_lock:
            if self._ready:
                return
            try:
                async with self.engine.connect() as connection:
                    await connection.run_sync(validate_database_at_head)
            except Exception as exc:
                raise RuntimeNotReady(
                    "ADE-native runtime database is not at the reviewed migration head"
                ) from exc
            self._ready = True

    @asynccontextmanager
    async def translated_errors(self) -> AsyncIterator[None]:
        try:
            yield
        except AgentRuntimeV3Error:
            raise
        except NotFoundError as exc:
            raise RuntimeNotFound(str(exc)) from exc
        except IdempotencyConflictError as exc:
            raise IdempotencyConflict(str(exc)) from exc
        except IntegrityError as exc:
            raise RuntimeConflict("The requested v3 resource already exists") from exc

    async def ensure_workspace(self, connection: AsyncConnection) -> dict[str, Any]:
        return await WorkspaceRepository(connection).ensure(
            {
                "id": DEFAULT_WORKSPACE_ID,
                "workspace_key": DEFAULT_WORKSPACE_KEY,
                "name": "ADE Default Workspace",
            }
        )


def require_default_workspace(row: dict[str, Any]) -> None:
    if str(row.get("workspace_id", "")) != DEFAULT_WORKSPACE_ID:
        raise RuntimeNotFound("resource does not exist in the active workspace")
