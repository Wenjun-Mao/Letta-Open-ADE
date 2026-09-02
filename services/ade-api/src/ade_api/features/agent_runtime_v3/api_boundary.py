"""Stable HTTP translation for native-runtime application errors."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import TypeVar

from fastapi import HTTPException

from .errors import AgentRuntimeV3Error
from .router_transport import RouterRequestError


T = TypeVar("T")


async def call_runtime(operation: Awaitable[T]) -> T:
    try:
        return await operation
    except AgentRuntimeV3Error as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except RouterRequestError as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "model_router_unavailable",
                "message": "Model Router is not ready",
            },
        ) from exc
