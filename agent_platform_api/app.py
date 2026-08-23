from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent_platform_api.auth import require_admin, require_operator, require_reader
from agent_platform_api.capability_validation import validate_platform_capabilities_startup
from agent_platform_api.dependencies import APP_VERSION, initialize_dependencies, shutdown_dependencies
from agent_platform_api.openapi_metadata import OPENAPI_TAGS
from agent_platform_api.routers import (
    agent_lifecycle,
    agent_state,
    agents,
    commenting,
    core,
    labeling,
    platform_meta,
    platform_runtime,
    prompt_center,
    schema_center,
    tool_center,
)
from agent_platform_api.settings import get_settings


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    initialize_dependencies()
    validate_platform_capabilities_startup()
    try:
        yield
    finally:
        shutdown_dependencies()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Agent Platform API",
        version=APP_VERSION,
        summary="Runtime and control APIs for ADE and local Agent Platform workflows",
        lifespan=app_lifespan,
        openapi_tags=OPENAPI_TAGS,
        description=(
            "Provides versioned API routes for Agent Platform runtime/control/test orchestration. "
            "Designed for backend-first API consumption and ADE frontend integration."
        ),
    )
    settings = get_settings()
    cors_origins = settings.parsed_cors_origins()
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/api/v1/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": APP_VERSION}

    app.include_router(core.router, dependencies=[Depends(require_reader)])
    app.include_router(agents.router, dependencies=[Depends(require_admin)])
    app.include_router(agent_lifecycle.router, dependencies=[Depends(require_admin)])
    app.include_router(agent_state.router, dependencies=[Depends(require_admin)])
    app.include_router(platform_meta.router, dependencies=[Depends(require_reader)])
    app.include_router(prompt_center.router, dependencies=[Depends(require_admin)])
    app.include_router(schema_center.router, dependencies=[Depends(require_admin)])
    app.include_router(tool_center.router, dependencies=[Depends(require_admin)])
    app.include_router(platform_runtime.router, dependencies=[Depends(require_operator)])
    app.include_router(commenting.router, dependencies=[Depends(require_operator)])
    app.include_router(labeling.router, dependencies=[Depends(require_operator)])
    return app


app = create_app()
