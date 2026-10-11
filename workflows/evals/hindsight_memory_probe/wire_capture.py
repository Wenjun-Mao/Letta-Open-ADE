"""Observe serialized httpx requests, retaining no upstream response content."""

from __future__ import annotations

import asyncio
import base64
import contextvars
import hashlib
import json
import math
import struct
import time

import httpx

from .receipts import CaptureFailure, ReceiptStore

request_context = contextvars.ContextVar("probe_request_context", default=None)


def _finite_number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _embedding_input_count(value: object) -> int:
    """Count embedding inputs without confusing token IDs with separate inputs."""
    if isinstance(value, str) and value:
        return 1
    if not isinstance(value, list) or not value:
        raise CaptureFailure()
    if all(isinstance(item, str) and item for item in value):
        return len(value)
    if all(type(item) is int and item >= 0 for item in value):
        return 1
    if all(
        isinstance(item, list)
        and item
        and all(type(token) is int and token >= 0 for token in item)
        for item in value
    ):
        return len(value)
    raise CaptureFailure()


def _embedding_dimension(value: object) -> int:
    if isinstance(value, list):
        if not value or any(not _finite_number(item) for item in value):
            raise CaptureFailure()
        return len(value)
    if isinstance(value, str):
        try:
            decoded = base64.b64decode(value, validate=True)
        except (ValueError, UnicodeEncodeError):
            raise CaptureFailure() from None
        if not decoded or len(decoded) % 4:
            raise CaptureFailure()
        try:
            numbers = struct.iter_unpack("<f", decoded)
            dimension = 0
            for (number,) in numbers:
                if not math.isfinite(number):
                    raise CaptureFailure()
                dimension += 1
        except (struct.error, TypeError):
            raise CaptureFailure() from None
        return dimension
    raise CaptureFailure()


def _embedding_projection(body: dict, payload: dict) -> dict:
    data = body.get("data")
    count = _embedding_input_count(payload.get("input"))
    if not isinstance(data, list) or len(data) != count:
        raise CaptureFailure()
    indexed_dimensions = []
    kinds = set()
    for item in data:
        if not isinstance(item, dict):
            raise CaptureFailure()
        index = item.get("index")
        if type(index) is not int or index < 0 or index >= count:
            raise CaptureFailure()
        vector = item.get("embedding")
        kinds.add(
            "array"
            if isinstance(vector, list)
            else "base64"
            if isinstance(vector, str)
            else "invalid"
        )
        indexed_dimensions.append((index, _embedding_dimension(vector)))
    if (
        len({index for index, _ in indexed_dimensions}) != count
        or len(kinds) != 1
        or "invalid" in kinds
    ):
        raise CaptureFailure()
    ordered = [dimension for _, dimension in sorted(indexed_dimensions)]
    if len(set(ordered)) != 1:
        raise CaptureFailure()
    requested = payload.get("dimensions")
    if requested is not None and (
        type(requested) is not int or requested != ordered[0]
    ):
        raise CaptureFailure()
    return {"embedding_dimensions": ordered, "input_count": count}


def _safe_usage(value: object) -> bool:
    return _finite_number(value) and value >= 0


def safe_response(response: httpx.Response, payload: dict, elapsed: float) -> dict:
    projection = {"status": response.status_code, "latency_seconds": elapsed}
    if response.status_code >= 400:
        return projection
    try:
        body = response.json()
    except (ValueError, UnicodeDecodeError):
        if response.request.url.path.endswith("/embeddings"):
            raise CaptureFailure() from None
        return projection
    if not isinstance(body, dict):
        if response.request.url.path.endswith("/embeddings"):
            raise CaptureFailure()
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
            and _safe_usage(value)
        }
    if response.request.url.path.endswith("/embeddings"):
        projection.update(_embedding_projection(body, payload))
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
