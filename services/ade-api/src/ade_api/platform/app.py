from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ade_api.platform.dependencies import (
    APP_VERSION,
    initialize_dependencies,
    shutdown_dependencies,
)
from ade_api.features.agent_runtime import (
    router as agent_runtime_router,
    shutdown_agent_runtime,
)
from ade_api.features.comment_lab import api as comment_lab
from ade_api.features.label_lab import api as label_lab
from ade_api.features.model_catalog import api as model_catalog
from ade_api.features.prompt_center import api as prompt_center
from ade_api.features.schema_center import api as schema_center
from ade_api.features.test_center import api as test_center
from ade_api.platform.openapi_metadata import OPENAPI_TAGS
from ade_api.platform.settings import get_settings


@asynccontextmanager
async def app_lifespan(_: FastAPI):
    initialize_dependencies()
    try:
        yield
    finally:
        await shutdown_agent_runtime()
        shutdown_dependencies()


def create_app() -> FastAPI:
    app = FastAPI(
        title="ADE API",
        version=APP_VERSION,
        summary="ADE-owned runtime, evaluation, and authoring APIs",
        lifespan=app_lifespan,
        openapi_tags=OPENAPI_TAGS,
        description=(
            "Provides Agent Studio, lab, content-center, model-catalog, and test APIs "
            "used by ADE Web and first-class developer clients."
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

    @app.get("/api/v2/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": APP_VERSION}

    app.include_router(agent_runtime_router)
    app.include_router(comment_lab.router)
    app.include_router(label_lab.router)
    app.include_router(model_catalog.router)
    app.include_router(prompt_center.router)
    app.include_router(schema_center.router)
    app.include_router(test_center.router)
    return app


app = create_app()
