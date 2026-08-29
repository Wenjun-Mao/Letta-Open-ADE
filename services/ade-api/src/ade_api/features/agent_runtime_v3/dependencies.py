from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException

from .errors import AgentRuntimeV3Error
from .flags import ensure_agent_runtime_v3_enabled
from .service_protocol import AgentRuntimeV3Service


@lru_cache(maxsize=1)
def _build_service() -> AgentRuntimeV3Service:
    from .application import build_agent_runtime_v3_service

    return build_agent_runtime_v3_service()


def get_agent_runtime_v3_service() -> AgentRuntimeV3Service:
    try:
        ensure_agent_runtime_v3_enabled()
        return _build_service()
    except AgentRuntimeV3Error as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


def clear_agent_runtime_v3_service() -> None:
    _build_service.cache_clear()


async def shutdown_agent_runtime_v3_service() -> None:
    if not _build_service.cache_info().currsize:
        return
    service = _build_service()
    close = getattr(service, "aclose", None)
    if callable(close):
        await close()
    _build_service.cache_clear()


AgentRuntimeV3ServiceDependency = Annotated[
    AgentRuntimeV3Service,
    Depends(get_agent_runtime_v3_service),
]
