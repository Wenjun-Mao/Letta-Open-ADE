"""Durable pre-request limits shared by the Agent Runtime API and worker."""

from __future__ import annotations

import os
import re
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ade_api.platform.project_paths import resolve_project_path
from ade_api.platform.settings import AdeApiSettings

from .errors import RuntimeNotReady
from .router_transport import RouterTransport


class RequestLedger:
    """Reserve in SQLite before send; interrupted reservations still count."""

    def __init__(
        self,
        path: Path,
        *,
        generation_limit: int,
        embedding_limit: int,
        binding: Mapping[str, str] | None = None,
    ) -> None:
        if generation_limit < 1 or embedding_limit < 1:
            raise ValueError("provider request limits must be positive")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.limits = {"generation": generation_limit, "embedding": embedding_limit}
        expected_binding = dict(binding or {})
        with sqlite3.connect(path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, "
                "model TEXT NOT NULL, reserved_at TEXT NOT NULL, outcome TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS limits (kind TEXT PRIMARY KEY, cap INTEGER NOT NULL)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS binding (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            for kind, cap in self.limits.items():
                connection.execute(
                    "INSERT OR IGNORE INTO limits(kind, cap) VALUES (?, ?)",
                    (kind, cap),
                )
            if dict(connection.execute("SELECT kind, cap FROM limits")) != self.limits:
                raise ValueError("provider request ledger limits differ")
            stored_binding = dict(connection.execute("SELECT key, value FROM binding"))
            spent = connection.execute("SELECT count(*) FROM calls").fetchone()[0]
            if stored_binding != expected_binding and (stored_binding or spent):
                raise ValueError("provider request ledger binding differs")
            for key, value in expected_binding.items():
                connection.execute(
                    "INSERT OR IGNORE INTO binding(key, value) VALUES (?, ?)",
                    (key, value),
                )

    def reserve(self, kind: str, model: str) -> int:
        if kind not in self.limits:
            raise ValueError("provider request kind is invalid")
        with sqlite3.connect(self.path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT count(*) FROM calls WHERE kind = ?", (kind,)
            ).fetchone()[0]
            if count >= self.limits[kind]:
                raise RuntimeError(f"{kind} provider budget exhausted")
            cursor = connection.execute(
                "INSERT INTO calls(kind, model, reserved_at) VALUES (?, ?, ?)",
                (kind, model, datetime.now(UTC).isoformat()),
            )
            return int(cursor.lastrowid)

    def finish(self, call_id: int, outcome: str) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                "UPDATE calls SET outcome = ? WHERE id = ?", (outcome, call_id)
            )

    def counts(self) -> dict[str, int]:
        with sqlite3.connect(self.path) as connection:
            return {
                kind: int(
                    connection.execute(
                        "SELECT count(*) FROM calls WHERE kind = ?", (kind,)
                    ).fetchone()[0]
                )
                for kind in self.limits
            }

    def exhausted(self) -> bool:
        counts = self.counts()
        return any(counts[kind] >= cap for kind, cap in self.limits.items())


class BudgetedTransport:
    def __init__(self, inner: RouterTransport, ledger: RequestLedger) -> None:
        self.inner = inner
        self.ledger = ledger

    async def catalog(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        return await self.inner.catalog(timeout_seconds=timeout_seconds)

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._send(
            "generation", payload, timeout_seconds, self.inner.chat_completion
        )

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        return await self._send(
            "embedding", payload, timeout_seconds, self.inner.embeddings
        )

    async def _send(self, kind: str, payload: dict[str, Any], timeout: float, send):
        call_id = self.ledger.reserve(kind, str(payload.get("model") or ""))
        try:
            result = await send(payload, timeout_seconds=min(timeout, 180.0))
        except BaseException as exc:
            self.ledger.finish(call_id, f"failed:{type(exc).__name__}")
            raise
        self.ledger.finish(call_id, "completed")
        return result


def budget_identity(settings: AdeApiSettings) -> dict[str, object] | None:
    if not settings.agent_runtime_budget_ledger_path:
        return None
    return {
        "path": str(
            resolve_project_path(settings.agent_runtime_budget_ledger_path).resolve()
        ),
        "stage": settings.agent_runtime_budget_stage,
        "generation_limit": settings.agent_runtime_budget_generation_limit,
        "embedding_limit": settings.agent_runtime_budget_embedding_limit,
    }


def budget_ledger(settings: AdeApiSettings) -> RequestLedger | None:
    identity = budget_identity(settings)
    if identity is None:
        return None
    path = Path(str(identity["path"]))
    runtime_dir = resolve_project_path(settings.runtime_data_dir).resolve()
    if path == runtime_dir or not path.is_relative_to(runtime_dir):
        raise RuntimeNotReady("provider request ledger must live in runtime data")
    revision = str(os.getenv("ADE_SOURCE_REVISION") or "").strip().casefold()
    fingerprint = str(os.getenv("ADE_SOURCE_FINGERPRINT") or "").strip().casefold()
    dirty = str(os.getenv("ADE_SOURCE_DIRTY") or "true").strip().casefold()
    if (
        not re.fullmatch(r"[0-9a-f]{40,64}", revision)
        or not re.fullmatch(r"[0-9a-f]{64}", fingerprint)
        or dirty not in {"0", "false", "no", "off"}
    ):
        raise RuntimeNotReady("budgeted runtime requires an exact clean build identity")
    return RequestLedger(
        path,
        generation_limit=settings.agent_runtime_budget_generation_limit,
        embedding_limit=settings.agent_runtime_budget_embedding_limit,
        binding={
            "stage": settings.agent_runtime_budget_stage,
            "source_revision": revision,
            "source_fingerprint": fingerprint,
            "runtime_mode": settings.agent_runtime_mode,
        },
    )


def build_runtime_router_transport(
    settings: AdeApiSettings,
) -> RouterTransport | BudgetedTransport:
    inner = RouterTransport(
        base_url=settings.model_router_v1_base_url(),
        api_key=settings.resolve_model_router_api_key(),
    )
    ledger = budget_ledger(settings)
    return BudgetedTransport(inner, ledger) if ledger is not None else inner
