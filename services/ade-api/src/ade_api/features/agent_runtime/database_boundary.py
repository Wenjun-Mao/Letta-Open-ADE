from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from .errors import (
    AgentRuntimeError,
    IdempotencyConflict,
    RuntimeConflict,
    RuntimeNotFound,
    RuntimeNotReady,
)
from .persistence.base import (
    IdempotencyConflictError,
    NotFoundError,
    OptimisticLockError,
    PersistenceError,
)
from .persistence.validation import validate_database_at_head
from .persistence.workspaces import WorkspaceRepository
from .persistence.metadata import workspaces


DEFAULT_WORKSPACE_ID = str(uuid5(NAMESPACE_URL, "ade://workspace/default"))
DEFAULT_WORKSPACE_KEY = "default"


class RuntimeDatabase:
    """Owns readiness and error translation for the v3 persistence boundary."""

    def __init__(self, engine: AsyncEngine, *, workspace_key: str) -> None:
        self.engine = engine
        if not workspace_key.strip() or workspace_key.strip() == DEFAULT_WORKSPACE_KEY:
            raise RuntimeNotReady(
                "An explicit fresh Hindsight workspace key is required"
            )
        self.workspace_key = workspace_key.strip()
        self.workspace_id = str(
            uuid5(NAMESPACE_URL, f"ade://workspace/{self.workspace_key}")
        )
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
                    row = (
                        (
                            await connection.execute(
                                select(workspaces).where(
                                    workspaces.c.workspace_key == self.workspace_key
                                )
                            )
                        )
                        .mappings()
                        .one_or_none()
                    )
                    if row is not None and (
                        str(row["id"]) != self.workspace_id
                        or row["memory_backend"] != "hindsight"
                    ):
                        raise RuntimeNotReady(
                            "Configured workspace is not a fresh Hindsight authority"
                        )
            except RuntimeNotReady:
                raise
            except Exception as exc:
                raise RuntimeNotReady(
                    "ADE-native runtime database is not at the reviewed migration head"
                ) from exc
            self._ready = True

    @asynccontextmanager
    async def translated_errors(self) -> AsyncIterator[None]:
        try:
            yield
        except AgentRuntimeError:
            raise
        except NotFoundError as exc:
            raise RuntimeNotFound(str(exc)) from exc
        except IdempotencyConflictError as exc:
            raise IdempotencyConflict(str(exc)) from exc
        except OptimisticLockError as exc:
            raise RuntimeConflict(str(exc)) from exc
        except PersistenceError as exc:
            raise RuntimeConflict(str(exc)) from exc
        except IntegrityError as exc:
            raise RuntimeConflict("The requested v3 resource already exists") from exc

    async def ensure_workspace(self, connection: AsyncConnection) -> dict[str, Any]:
        row = await WorkspaceRepository(connection).ensure(
            {
                "id": self.workspace_id,
                "workspace_key": self.workspace_key,
                "name": "ADE Hindsight Workspace",
                "memory_backend": "hindsight",
            }
        )
        if str(row["id"]) != self.workspace_id or row["memory_backend"] != "hindsight":
            raise RuntimeNotReady(
                "Existing workspace is not the configured fresh Hindsight authority"
            )
        return row

    def require_workspace(self, row: dict[str, Any]) -> None:
        if str(row.get("workspace_id", "")) != self.workspace_id:
            raise RuntimeNotFound("resource does not exist in the active workspace")


def require_default_workspace(row: dict[str, Any]) -> None:
    if str(row.get("workspace_id", "")) != DEFAULT_WORKSPACE_ID:
        raise RuntimeNotFound("resource does not exist in the active workspace")
