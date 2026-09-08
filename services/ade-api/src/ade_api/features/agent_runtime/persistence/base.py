"""Shared primitives for Core repositories."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.engine import RowMapping
from sqlalchemy.ext.asyncio import AsyncConnection
from sqlalchemy.sql import Executable


class PersistenceError(RuntimeError):
    """Base error raised by the ADE persistence boundary."""


class NotFoundError(PersistenceError):
    pass


class IdempotencyConflictError(PersistenceError):
    pass


class OptimisticLockError(PersistenceError):
    pass


class LeaseUnavailableError(PersistenceError):
    pass


async def fetch_one(
    connection: AsyncConnection, statement: Executable, message: str
) -> dict[str, Any]:
    result = await connection.execute(statement)
    row: RowMapping | None = result.mappings().one_or_none()
    if row is None:
        raise NotFoundError(message)
    return dict(row)


def values(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Copy caller input so repository calls never mutate runtime-owned payloads."""

    return dict(payload)
