from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException

from .errors import AgentRuntimeV3Error
from .flags import ensure_agent_runtime_v3_enabled
from .service_protocol import AgentRuntimeV3Service
from .worker_health import (
    RuntimeWorkerHealthServiceProtocol,
    build_runtime_worker_health_service,
)


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


@lru_cache(maxsize=1)
def _build_health_service() -> RuntimeWorkerHealthServiceProtocol:
    return build_runtime_worker_health_service()


def get_agent_runtime_v3_health_service() -> RuntimeWorkerHealthServiceProtocol:
    return _build_health_service()


def clear_agent_runtime_v3_service() -> None:
    _build_service.cache_clear()
    _build_health_service.cache_clear()


async def shutdown_agent_runtime_v3_service() -> None:
    for builder in (_build_service, _build_health_service):
        if not builder.cache_info().currsize:
            continue
        service = builder()
        close = getattr(service, "aclose", None)
        if callable(close):
            await close()
    _build_service.cache_clear()
    _build_health_service.cache_clear()


AgentRuntimeV3ServiceDependency = Annotated[
    AgentRuntimeV3Service,
    Depends(get_agent_runtime_v3_service),
]

AgentRuntimeV3HealthServiceDependency = Annotated[
    RuntimeWorkerHealthServiceProtocol,
    Depends(get_agent_runtime_v3_health_service),
]
