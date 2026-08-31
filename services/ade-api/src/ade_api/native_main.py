from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ade_api.features.agent_runtime_v3 import (
    router as agent_runtime_v3_router,
    shutdown_agent_runtime_v3,
)
from ade_api.platform.openapi_metadata import TAG_AGENT_RUNTIME_V3
from ade_api.platform.settings import get_settings


APP_VERSION = os.getenv("ADE_API_VERSION", "0.3.0")


@asynccontextmanager
async def native_app_lifespan(_: FastAPI):
    """Release only native runtime resources; never initialize the v2 service graph."""
    try:
        yield
    finally:
        await shutdown_agent_runtime_v3()


def create_native_app() -> FastAPI:
    """Create the isolated API surface used by the opt-in native runtime lane."""
    app = FastAPI(
        title="ADE Native Runtime API",
        version=APP_VERSION,
        summary="Isolated ADE-owned agent runtime preview API",
        description=(
            "Serves only the disabled-by-default ADE-native runtime. It does not "
            "initialize Letta-backed v2 services or depend on Redis."
        ),
        lifespan=native_app_lifespan,
        openapi_tags=[
            {
                "name": TAG_AGENT_RUNTIME_V3,
                "description": "Disabled-by-default ADE-owned agent runtime preview APIs.",
            }
        ],
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
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

    @app.get("/health", include_in_schema=False)
    async def liveness() -> dict[str, str]:
        """Container liveness only; `/api/v3/worker-health` is the readiness gate."""
        return {"status": "ok", "runtime": "native"}

    app.include_router(agent_runtime_v3_router)
    return app


app = create_native_app()
