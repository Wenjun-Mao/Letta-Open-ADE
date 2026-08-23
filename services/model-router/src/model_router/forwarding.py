from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response, StreamingResponse

from model_router.settings import RouterSourceConfig, get_settings


def create_upstream_client() -> httpx.AsyncClient:
    """Create the single upstream transport owned for the app lifespan."""
    return httpx.AsyncClient(timeout=get_settings().request_timeout_seconds)


@asynccontextmanager
async def upstream_client_lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Attach one shared upstream client for the router application lifetime."""
    upstream_client = create_upstream_client()
    application.state.upstream_client = upstream_client
    try:
        yield
    finally:
        await upstream_client.aclose()
        del application.state.upstream_client


def router_error(
    status_code: int, code: str, message: str, **extra: Any
) -> JSONResponse:
    """Return the router's stable OpenAI-compatible error envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": "model_router_error",
                "code": code,
                "message": message,
                **extra,
            }
        },
    )


def _upstream_headers(source: RouterSourceConfig) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    api_key = source.resolve_api_key()
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _upstream_client(application: FastAPI) -> httpx.AsyncClient:
    client = getattr(application.state, "upstream_client", None)
    if not isinstance(client, httpx.AsyncClient) or client.is_closed:
        raise RuntimeError("Model-router upstream transport is not available")
    return client


async def forward_chat_completion(
    application: FastAPI,
    source: RouterSourceConfig,
    payload: dict[str, Any],
) -> Response:
    """Forward exactly one OpenAI-compatible chat completion request upstream."""
    client = _upstream_client(application)
    if bool(payload.get("stream", False)):
        return await _stream_chat_completion(client, source, payload)
    return await _post_chat_completion(client, source, payload)


async def _post_chat_completion(
    client: httpx.AsyncClient,
    source: RouterSourceConfig,
    payload: dict[str, Any],
) -> Response:
    try:
        # httpx has no implicit retry; one call here is the complete retry policy.
        response = await client.post(
            source.chat_completions_url(),
            json=payload,
            headers=_upstream_headers(source),
        )
    except Exception as exc:
        return router_error(
            502,
            "upstream_unreachable",
            f"Source '{source.id}' could not be reached: {exc}",
            source_id=source.id,
        )
    return _response_from_upstream(response, source_id=source.id)


async def _stream_chat_completion(
    client: httpx.AsyncClient,
    source: RouterSourceConfig,
    payload: dict[str, Any],
) -> StreamingResponse | JSONResponse:
    upstream_request = client.build_request(
        "POST",
        source.chat_completions_url(),
        json=payload,
        headers=_upstream_headers(source),
    )
    try:
        # Streaming also issues one request; downstream cancellation closes it below.
        response = await client.send(upstream_request, stream=True)
    except Exception as exc:
        return router_error(
            502,
            "upstream_unreachable",
            f"Source '{source.id}' could not be reached: {exc}",
        )

    async def iter_bytes() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()

    media_type = response.headers.get("content-type") or "text/event-stream"
    return StreamingResponse(
        iter_bytes(), status_code=response.status_code, media_type=media_type
    )


def _response_from_upstream(response: httpx.Response, *, source_id: str) -> Response:
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type.lower():
        try:
            return JSONResponse(
                status_code=response.status_code, content=response.json()
            )
        except json.JSONDecodeError:
            pass
    return Response(
        status_code=response.status_code,
        content=response.content,
        media_type=content_type or None,
        headers={"X-Model-Router-Source": source_id},
    )
