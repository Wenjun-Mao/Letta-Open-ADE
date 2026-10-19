from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from model_router.catalog import (
    RoutedModel,
    RouterCatalogService,
    normalize_router_model_id,
    parse_router_model_id,
)
from model_router.forwarding import (
    forward_chat_completion,
    forward_embeddings,
    router_error,
    upstream_client_lifespan,
)
from model_router.payloads import (
    _apply_sampling_defaults,
    _normalize_adapter_payload,
    _normalize_openai_payload,
)
from model_router.settings import get_settings
from model_router.observation_api import install_observation_api
from model_router.request_observations import bind_router_model


catalog_service = RouterCatalogService()


@asynccontextmanager
async def app_lifespan(application: FastAPI) -> AsyncIterator[None]:
    async with upstream_client_lifespan(application):
        await asyncio.to_thread(catalog_service.snapshot)
        yield


app = FastAPI(
    title="ADE Model Router",
    version="0.1.0",
    description="First-party OpenAI-compatible router for ADE model sources.",
    lifespan=app_lifespan,
)


def _require_router_auth(authorization: str | None) -> None:
    expected_key = get_settings().resolve_api_key()
    if not expected_key:
        return
    scheme, _, token = str(authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(
        token.strip(), expected_key
    ):
        raise HTTPException(status_code=401, detail="Invalid model-router API key")


def _source_dict(source) -> dict[str, Any]:
    return {
        "id": source.id,
        "label": source.label,
        "kind": source.kind,
        "adapter": source.adapter,
        "base_url": source.base_url,
        "module_visibility": list(source.module_visibility),
        "status": source.status,
        "detail": source.detail,
        "allowlist_applied": source.allowlist_applied,
        "allowlist_checked_at": source.allowlist_checked_at,
        "raw_model_count": source.raw_model_count,
        "filtered_model_count": source.filtered_model_count,
        "models": [
            {
                "provider_model_id": model.provider_model_id,
                "model_type": model.model_type,
            }
            for model in source.models
        ],
    }


install_observation_api(app, _require_router_auth)


def _catalog_payload(*, force_refresh: bool = False) -> dict[str, Any]:
    snapshot = catalog_service.snapshot(force_refresh=force_refresh)
    return {
        "generated_at": snapshot.generated_at,
        "sources": [_source_dict(source) for source in snapshot.sources],
        "items": [model.as_dict() for model in catalog_service.flatten(snapshot)],
    }


def _openai_model_item(model: RoutedModel) -> dict[str, Any]:
    return {
        "id": model.router_model_id,
        "object": "model",
        "created": 0,
        "owned_by": "model_router",
        "source_id": model.source_id,
        "source_label": model.source_label,
    }


@app.get("/v1/health")
@app.get("/v1/health/")
def health() -> dict[str, Any]:
    settings = get_settings()
    return {
        "status": "ok",
        "configured_sources": len(settings.sources),
        "enabled_sources": len(
            [source for source in settings.sources if source.enabled]
        ),
    }


@app.get("/v1/models")
@app.get("/v1/models/")
def list_models(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_router_auth(authorization)
    snapshot = catalog_service.snapshot()
    models = [
        _openai_model_item(model)
        for model in catalog_service.flatten(snapshot)
        if model.agent_studio_available or model.model_type == "embedding"
    ]
    return {"object": "list", "data": models}


@app.get("/v1/router/model-catalog")
@app.get("/v1/router/model-catalog/")
def router_model_catalog(
    refresh: bool = False,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_router_auth(authorization)
    return _catalog_payload(force_refresh=refresh)


@app.get("/v1/router/sources")
@app.get("/v1/router/sources/")
def router_sources(
    refresh: bool = False,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    _require_router_auth(authorization)
    snapshot = catalog_service.snapshot(force_refresh=refresh)
    return {
        "generated_at": snapshot.generated_at,
        "sources": [_source_dict(source) for source in snapshot.sources],
    }


@app.post("/v1/chat/completions")
@app.post("/v1/chat/completions/")
async def chat_completions(
    request: Request,
    authorization: str | None = Header(default=None),
):
    _require_router_auth(authorization)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Request body must be valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Request body must be a JSON object"
        )

    requested_model = str(payload.get("model", "") or "").strip()
    if not requested_model:
        raise HTTPException(status_code=400, detail="model is required")

    routed_model = catalog_service.find_routed_model(requested_model)
    if routed_model is None:
        return _unknown_model_error(requested_model)
    source = catalog_service.source_config(routed_model.source_id)
    if source is None or not source.enabled:
        return router_error(
            404,
            "source_disabled",
            f"Model source '{routed_model.source_id}' is disabled or missing.",
            model=normalize_router_model_id(requested_model),
            source_id=routed_model.source_id,
        )

    upstream_payload = dict(payload)
    upstream_payload["model"] = routed_model.provider_model_id
    upstream_payload = _normalize_openai_payload(upstream_payload)
    try:
        upstream_payload = _normalize_adapter_payload(source, upstream_payload)
    except ValueError as exc:
        return router_error(
            400,
            "invalid_tool_choice"
            if source.adapter == "llama_cpp_server"
            else "unsupported_provider_payload",
            str(exc),
            model=routed_model.router_model_id,
            source_id=source.id,
        )
    upstream_payload = _apply_sampling_defaults(routed_model, source, upstream_payload)
    bind_router_model(routed_model.router_model_id)
    return await forward_chat_completion(request.app, source, upstream_payload)


@app.post("/v1/embeddings")
@app.post("/v1/embeddings/")
async def embeddings(
    request: Request,
    authorization: str | None = Header(default=None),
):
    _require_router_auth(authorization)
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="Request body must be valid JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400, detail="Request body must be a JSON object"
        )

    requested_model = str(payload.get("model", "") or "").strip()
    if not requested_model:
        raise HTTPException(status_code=400, detail="model is required")

    routed_model = catalog_service.find_routed_model(requested_model)
    if routed_model is None:
        return _unknown_model_error(requested_model)
    if routed_model.model_type != "embedding":
        return router_error(
            400,
            "unsupported_model_type",
            f"Model '{routed_model.router_model_id}' is not an embedding model.",
            model=routed_model.router_model_id,
            model_type=routed_model.model_type,
        )
    source = catalog_service.source_config(routed_model.source_id)
    if source is None or not source.enabled:
        return router_error(
            404,
            "source_disabled",
            f"Model source '{routed_model.source_id}' is disabled or missing.",
            model=normalize_router_model_id(requested_model),
            source_id=routed_model.source_id,
        )

    upstream_payload = dict(payload)
    upstream_payload["model"] = routed_model.provider_model_id
    bind_router_model(routed_model.router_model_id)
    return await forward_embeddings(request.app, source, upstream_payload)


def _unknown_model_error(requested_model: str) -> JSONResponse:
    normalized = normalize_router_model_id(requested_model)
    source_id = ""
    source_status = None
    try:
        source_id, _ = parse_router_model_id(normalized)
        source_status = catalog_service.source_status(source_id)
    except ValueError:
        pass
    extra: dict[str, Any] = {"model": normalized}
    if source_id:
        extra["source_id"] = source_id
    if source_status is not None:
        extra["source_status"] = source_status.status
        extra["source_detail"] = source_status.detail
    return router_error(
        404,
        "unknown_or_unavailable_model",
        f"Model '{normalized}' is not currently available through the router.",
        **extra,
    )
