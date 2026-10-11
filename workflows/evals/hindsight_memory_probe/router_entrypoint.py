"""Workflow-only lifespan/client injection around the unchanged shared router."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import model_router.app as shared
from model_router.forwarding import upstream_http_limits
from model_router.settings import get_settings
from starlette.responses import JSONResponse

from .receipts import CaptureFailure, ReceiptStore
from .wire_capture import CapturingTransport, request_context

PHASES = {"startup", "retain", "consolidation", "recall", "character"}
SENSITIVE_FIELDS = {
    "authorization",
    "api_key",
    "password",
    "reasoning_content",
    "reasoning",
}


def has_sensitive_fields(value):
    if isinstance(value, dict):
        return bool(SENSITIVE_FIELDS.intersection(k.lower() for k in value)) or any(
            has_sensitive_fields(v) for v in value.values()
        )
    return isinstance(value, list) and any(has_sensitive_fields(v) for v in value)


def read_phase(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        if value["phase"] not in PHASES or not re.fullmatch(
            r"[a-zA-Z0-9_-]{1,96}", value["operation_id"]
        ):
            raise ValueError()
        return {"phase": value["phase"], "operation_id": value["operation_id"]}
    except (OSError, ValueError, KeyError, TypeError):
        raise CaptureFailure() from None


class ObservedRouter:
    def __init__(self, inner, store: ReceiptStore, phase_file: Path):
        self.inner, self.store, self.phase_file = inner, store, phase_file

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.inner(scope, receive, send)
        if scope["path"] == "/probe/qualification":
            return await JSONResponse(
                {"qualified_capture": not self.store.failed},
                status_code=503 if self.store.failed else 200,
            )(scope, receive, send)
        if scope["method"] != "POST":
            return await self.inner(scope, receive, send)
        # Auth remains enforced by shared routes too. Never persist rejected auth bodies.
        headers = dict(scope["headers"])
        expected = get_settings().resolve_api_key()
        if not expected or not secrets.compare_digest(
            headers.get(b"authorization", b""), ("Bearer " + expected).encode()
        ):
            return await JSONResponse({"error": "unauthorized"}, status_code=401)(
                scope, receive, send
            )
        request_id = uuid.uuid4().hex
        try:
            if self.store.failed:
                raise CaptureFailure()
            chunks = bytearray()
            while True:
                message = await receive()
                if message["type"] != "http.request":
                    raise CaptureFailure()
                chunks.extend(message.get("body", b""))
                if len(chunks) > 2 * 1024 * 1024:
                    raise CaptureFailure()
                if not message.get("more_body"):
                    break
            raw = bytes(chunks)
            payload = json.loads(raw)
            if (
                not isinstance(payload, dict)
                or payload.get("stream")
                or has_sensitive_fields(payload)
            ):
                raise CaptureFailure()
            context = {
                **read_phase(self.phase_file),
                "request_id": request_id,
                "incoming_time_ns": time.time_ns(),
                "incoming_path": scope["path"],
            }
            self.store.write(
                request_id + ".incoming.json", {**context, "payload": payload}
            )
        except (CaptureFailure, ValueError, TypeError):
            self.store.failure(request_id, "incoming_capture_or_contract_failed")
            return await JSONResponse(
                {"error": "probe_qualification_failed"}, status_code=503
            )(scope, receive, send)
        consumed = False

        async def replay_receive():
            nonlocal consumed
            if not consumed:
                consumed = True
                return {"type": "http.request", "body": raw, "more_body": False}
            return await receive()

        async def observed_send(message):
            if (
                message["type"] == "http.response.start"
                and message["status"] >= 400
                and not self.store.failed
            ):
                self.store.failure(request_id, "router_rejected_or_upstream_failed")
            await send(message)

        token = request_context.set(context)
        try:
            return await self.inner(scope, replay_receive, observed_send)
        finally:
            request_context.reset(token)


def build_app(store: ReceiptStore, phase_file: Path, inner_transport=None):
    @asynccontextmanager
    async def lifespan(application):
        transport = CapturingTransport(
            store,
            inner_transport
            or httpx.AsyncHTTPTransport(retries=0, limits=upstream_http_limits()),
        )
        async with httpx.AsyncClient(
            transport=transport, timeout=get_settings().request_timeout_seconds
        ) as client:
            application.state.upstream_client = client
            try:
                await asyncio.to_thread(shared.catalog_service.snapshot)
                yield
            finally:
                del application.state.upstream_client

    # This runs only in the workflow process. Same endpoints/adapters/catalog, observed client.
    shared.app.router.lifespan_context = lifespan
    return ObservedRouter(shared.app, store, phase_file)


def create_app():
    # Providers/transport can include secret-bearing exception strings in diagnostics.
    logging.disable(logging.CRITICAL)
    return build_app(
        ReceiptStore(Path(os.environ["PROBE_RECEIPTS"])),
        Path(os.environ["PROBE_PHASE_FILE"]),
    )


# uvicorn factory defers private filesystem access until actual service start.
