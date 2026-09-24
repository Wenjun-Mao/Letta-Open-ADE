"""One scoped, durable request boundary for the approved natural-memory campaign.

The native API and worker share this instance. Every generation or embedding path
must enter an explicit schedule scope before the underlying ledger can send.
"""

from __future__ import annotations

import hashlib
import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from ade_api.features.agent_runtime.request_budget import BudgetedTransport


_MAX_CAPTURE_BYTES = 2_000_000


def _sensitive_key(key: str) -> bool:
    lowered = key.casefold()
    return any(
        part in lowered
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
    generation_limit: int
    embedding_limit: int
    generation_used: int = 0
    embedding_used: int = 0

    def reserve_local(self, kind: str) -> int:
        used_name = f"{kind}_used"
        used = int(getattr(self, used_name))
        if used >= int(getattr(self, f"{kind}_limit")):
            raise RuntimeError(f"{self.name} {kind} schedule exhausted")
        setattr(self, used_name, used + 1)
        return used + 1


class NaturalLiveTransport:
    """Require an explicit cell/setup scope around the shared budget transport."""

    def __init__(
        self,
        inner: BudgetedTransport,
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
        number = scope.reserve_local(kind)
        request_bytes = json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
        record = {
            "scope": scope.name,
            "kind": kind,
            "number": number,
            "model": expected_model,
            "request_sha256": hashlib.sha256(request_bytes).hexdigest(),
            "request": _redact(payload),
            "ledger_before": self.inner.ledger.counts(),
        }
        try:
            if kind == "generation":
                response = await self.inner.chat_completion(
                    payload, timeout_seconds=timeout_seconds
                )
            else:
                response = await self.inner.embeddings(
                    payload, timeout_seconds=timeout_seconds
                )
        except BaseException as exc:
            record["outcome"] = "failed"
            record["error_type"] = type(exc).__name__
            raise
        else:
            record["outcome"] = "completed"
            record["response"] = _redact(response)
            return response
        finally:
            record["ledger_after"] = self.inner.ledger.counts()
            captured = json.dumps(record, ensure_ascii=False, sort_keys=True).encode()
            if len(captured) > _MAX_CAPTURE_BYTES:
                raise RuntimeError("provider capture exceeded size limit")
            path = self.capture_dir / f"{scope.name}-{kind}-{number:03d}.json"
            with path.open("xb") as stream:
                stream.write(captured + b"\n")
            path.chmod(0o600)
