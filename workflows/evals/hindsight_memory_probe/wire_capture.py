"""Observe serialized httpx requests, retaining no upstream response content."""

from __future__ import annotations

import asyncio
import contextvars
import hashlib
import json
import time

import httpx

from .receipts import CaptureFailure, ReceiptStore

request_context = contextvars.ContextVar("probe_request_context", default=None)


def safe_response(response: httpx.Response, payload: dict, elapsed: float) -> dict:
    projection = {"status": response.status_code, "latency_seconds": elapsed}
    try:
        body = response.json()
    except (ValueError, UnicodeDecodeError):
        return projection
    if not isinstance(body, dict):
        return projection
    usage = body.get("usage")
    if isinstance(usage, dict):
        projection["usage"] = {
            key: value
            for key, value in usage.items()
            if key
            in {
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "prompt_cache_hit_tokens",
                "prompt_cache_miss_tokens",
            }
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        }
    if response.request.url.path.endswith("/embeddings"):
        data = body.get("data")
        if isinstance(data, list):
            projection["embedding_dimensions"] = [
                len(item["embedding"])
                for item in data
                if isinstance(item, dict) and isinstance(item.get("embedding"), list)
            ]
        inputs = payload.get("input")
        projection["input_count"] = len(inputs) if isinstance(inputs, list) else 1
    return projection


class CapturingTransport(httpx.AsyncBaseTransport):
    def __init__(self, store: ReceiptStore, inner: httpx.AsyncBaseTransport):
        self.store = store
        self.inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        context = request_context.get()
        if context is None or self.store.failed:
            raise CaptureFailure()
        request_id = context["request_id"]
        started = time.monotonic()
        try:
            raw = await request.aread()
            payload = json.loads(raw)
            # This is AFTER real adapter defaults and httpx serialization, BEFORE socket dispatch.
            self.store.write_bytes(request_id + ".outbound.body.json", raw)
            self.store.write(
                request_id + ".outbound.json",
                {
                    **context,
                    "method": request.method,
                    "path": request.url.path,
                    "host": request.url.host,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "payload": payload,
                    "dispatch_time_ns": time.time_ns(),
                },
            )
        except (CaptureFailure, ValueError, TypeError):
            self.store.failure(request_id, "outbound_capture_failed")
            raise CaptureFailure() from None
        try:
            response = await self.inner.handle_async_request(request)
            await response.aread()
            response.request = request
        except asyncio.CancelledError:
            self.store.failure(request_id, "upstream_dispatch_cancelled")
            raise
        except Exception:
            self.store.failure(request_id, "upstream_transport_failed")
            # Shared router formats exception text; never let original text reach it.
            raise RuntimeError("probe_upstream_transport_failed") from None
        try:
            self.store.write(
                request_id + ".response.json",
                {
                    **context,
                    **safe_response(response, payload, time.monotonic() - started),
                },
            )
        except CaptureFailure:
            self.store.failure(request_id, "response_capture_failed")
            raise CaptureFailure() from None
        return response

    async def aclose(self) -> None:
        await self.inner.aclose()
