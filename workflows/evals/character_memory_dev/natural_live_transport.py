"""Route-checked provider transport with best-effort diagnostic captures."""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from ade_api.features.agent_runtime.request_counts import dispatch_counts

_MAX_CAPTURE_BYTES = 2_000_000


def _sensitive_key(key: str) -> bool:
    return any(
        part in key.casefold()
        for part in ("reasoning", "thinking", "authorization", "api_key", "secret")
    )


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[redacted]" if _sensitive_key(key) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


@dataclass
class RequestScope:
    name: str
    generation_used: int = 0
    embedding_used: int = 0

    def observe(self, kind: str) -> int:
        field = f"{kind}_used"
        count = int(getattr(self, field)) + 1
        setattr(self, field, count)
        return count


class NaturalLiveTransport:
    """All setup and run calls pass one route-checked dispatch point."""

    def __init__(
        self,
        inner: Any,
        *,
        capture_dir: Path,
        generation_model: str,
        embedding_model: str,
    ) -> None:
        if capture_dir.is_symlink():
            raise ValueError("capture directory must not be a symlink")
        capture_dir.mkdir(parents=True, exist_ok=False)
        capture_dir.chmod(0o700)
        self.inner = inner
        self.capture_dir = capture_dir
        self.generation_model = generation_model
        self.embedding_model = embedding_model
        self._scope: RequestScope | None = None
        self._events: list[dict[str, Any]] = []

    @contextmanager
    def scope(self, scope: RequestScope) -> Iterator[RequestScope]:
        if self._scope is not None:
            raise RuntimeError("provider scopes cannot nest")
        if not scope.name or "/" in scope.name or ".." in scope.name:
            raise ValueError("invalid provider scope name")
        self._scope = scope
        try:
            yield scope
        finally:
            self._scope = None

    def counts(self) -> dict[str, Any]:
        return dispatch_counts(self._events)

    async def catalog(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        return await self.inner.catalog(timeout_seconds=timeout_seconds)

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._send("generation", payload, timeout_seconds)

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._send("embedding", payload, timeout_seconds)

    async def _send(
        self, kind: str, payload: dict[str, Any], timeout_seconds: float
    ) -> dict[str, Any]:
        scope = self._scope
        if scope is None:
            raise RuntimeError("unscoped provider request")
        expected_model = (
            self.generation_model if kind == "generation" else self.embedding_model
        )
        if payload.get("model") != expected_model:
            raise RuntimeError("provider route differs from approved campaign route")
        number = scope.observe(kind)
        request_id = str(uuid4())
        operation = "chat_completion" if kind == "generation" else "embeddings"
        common = {
            "request_id": request_id,
            "operation": operation,
            "stage": scope.name,
            "model_key": expected_model,
        }
        self._events.append({"event_type": "model.request.started", "payload": common})
        record = {
            "scope": scope.name,
            "kind": kind,
            "number": number,
            "request_id": request_id,
            "model": expected_model,
        }
        try:
            request_bytes = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
            record["request_sha256"] = hashlib.sha256(request_bytes).hexdigest()
            record["request"] = _redact(payload)
        except Exception:
            pass
        try:
            if kind == "generation":
                response = await self.inner.chat_completion(
                    payload, timeout_seconds=min(timeout_seconds, 180.0)
                )
            else:
                response = await self.inner.embeddings(
                    payload, timeout_seconds=min(timeout_seconds, 180.0)
                )
        except BaseException as exc:
            record["outcome"] = "failed"
            record["error_type"] = type(exc).__name__
            self._events.append(
                {
                    "event_type": "model.request.failed",
                    "payload": common,
                }
            )
            raise
        else:
            record["outcome"] = "completed"
            self._events.append(
                {
                    "event_type": "model.response.completed",
                    "payload": common,
                }
            )
            try:
                record["response"] = _redact(response)
            except Exception:
                pass
            return response
        finally:
            # The capture is optional. A full disk or oversized artifact cannot
            # replace the provider result or the provider's original exception.
            try:
                captured = json.dumps(
                    record, ensure_ascii=False, sort_keys=True
                ).encode()
                if len(captured) <= _MAX_CAPTURE_BYTES:
                    path = self.capture_dir / f"{scope.name}-{kind}-{number:03d}.json"
                    with path.open("xb") as stream:
                        stream.write(captured + b"\n")
                    path.chmod(0o600)
            except Exception:
                pass
