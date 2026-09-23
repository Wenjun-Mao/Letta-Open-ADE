"""Isolated M3 HTTP API, worker, and router with one durable provider budget."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import uvicorn
from sqlalchemy import text as sql_text

import model_router.app as router_app
import model_router.forwarding as forwarding
from model_router.catalog import RouterCatalogService

from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.dependencies import (
    get_agent_runtime_health_service,
    get_agent_runtime_service,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.app import app as api_app
from ade_api.platform.settings import AdeApiSettings

from workflows.evals.deepseek_dev_smoke.isolation import (
    ROOT,
    isolated_database_url,
    router_settings,
)


class RequestLedger:
    """SQLite reservation is committed before any outbound provider request."""

    def __init__(self, path: Path, *, generation_limit: int, embedding_limit: int):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.limits = {"generation": generation_limit, "embedding": embedding_limit}
        with sqlite3.connect(path) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS calls (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, "
                "model TEXT NOT NULL, reserved_at TEXT NOT NULL, outcome TEXT)"
            )
            connection.execute(
                "CREATE TABLE IF NOT EXISTS limits (kind TEXT PRIMARY KEY, cap INTEGER NOT NULL)"
            )
            for kind, cap in self.limits.items():
                connection.execute(
                    "INSERT OR IGNORE INTO limits(kind, cap) VALUES (?, ?)",
                    (kind, cap),
                )
            stored = dict(connection.execute("SELECT kind, cap FROM limits"))
            if stored != self.limits:
                raise ValueError("M3 ledger limits differ from the authorized budget")

    def reserve(self, kind: str, model: str) -> int:
        with sqlite3.connect(self.path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            count = connection.execute(
                "SELECT count(*) FROM calls WHERE kind = ?", (kind,)
            ).fetchone()[0]
            if count >= self.limits[kind]:
                raise RuntimeError(f"M3 {kind} provider budget exhausted")
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


class BudgetedTransport:
    def __init__(self, inner: RouterTransport, ledger: RequestLedger):
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
        except Exception as exc:
            self.ledger.finish(call_id, f"failed:{type(exc).__name__}")
            raise
        self.ledger.finish(call_id, "completed")
        return result


async def _serve(
    *,
    env_file: Path,
    database_url: str,
    ledger_path: Path,
    api_port: int,
    router_port: int,
) -> None:
    checked_url, database_name = isolated_database_url(database_url)
    engine = create_persistence_engine(checked_url)
    try:
        async with engine.connect() as connection:
            identity = (
                await connection.execute(
                    sql_text("SELECT current_database(), current_user")
                )
            ).one()
            pending = await connection.scalar(
                sql_text(
                    "SELECT count(*) FROM ade.runs WHERE status IN ('pending', 'running')"
                )
            )
        if tuple(identity) != (database_name, "ade_owner") or pending:
            raise ValueError("Disposable database identity/pending-run guard failed")
        await RuntimeDatabase(engine).ensure_ready()

        os.environ["ADE_SOURCE_REVISION"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        os.environ["ADE_SOURCE_DIRTY"] = "true"
        os.environ["ADE_SOURCE_FINGERPRINT"] = subprocess.check_output(
            [
                sys.executable,
                str(ROOT / "scripts/source_fingerprint.py"),
                "--root",
                str(ROOT),
            ],
            text=True,
        ).strip()

        configured_router = router_settings(env_file, include_spark=True)
        router_app.get_settings = lambda: configured_router
        router_app.catalog_service = RouterCatalogService(
            settings_factory=lambda: configured_router
        )
        forwarding.get_settings = lambda: configured_router
        ledger = RequestLedger(ledger_path, generation_limit=24, embedding_limit=24)
        transport = BudgetedTransport(
            RouterTransport(base_url=f"http://127.0.0.1:{router_port}/v1"), ledger
        )
        settings = AdeApiSettings(
            agent_runtime_enabled=True,
            agent_runtime_mode="development",
            model_discovery_timeout_seconds=30,
            database_url=checked_url,
            agent_runtime_worker_poll_seconds=0.2,
        )
        with tempfile.TemporaryDirectory(prefix="ade-m3-native-") as temporary:
            application = AgentRuntimeApplication(
                engine=engine,
                settings=settings,
                prompt_registry=build_prompt_template_reader(
                    ROOT, persona_db_path=Path(temporary) / "personas.sqlite3"
                ),
                router_transport=transport,
            )
            worker = AgentRuntimeWorker(
                engine=engine, settings=settings, transport=transport
            )
            api_app.dependency_overrides[get_agent_runtime_service] = lambda: (
                application
            )
            api_app.dependency_overrides[get_agent_runtime_health_service] = lambda: (
                application.runs.worker_health
            )
            api_app.dependency_overrides[authenticate_ade_request] = lambda: (
                AdePrincipal(role=AdeRole.ADMIN, key_name="synthetic-loopback")
            )
            router_server = uvicorn.Server(
                uvicorn.Config(
                    router_app.app,
                    host="127.0.0.1",
                    port=router_port,
                    log_level="warning",
                    access_log=False,
                )
            )
            api_server = uvicorn.Server(
                uvicorn.Config(
                    api_app,
                    host="127.0.0.1",
                    port=api_port,
                    log_level="warning",
                    access_log=False,
                )
            )
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for signum in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(signum, stop.set)
            router_task = asyncio.create_task(router_server.serve())
            api_task = asyncio.create_task(api_server.serve())
            worker_task = asyncio.create_task(worker.run_forever(stop))
            try:
                for _ in range(200):
                    if router_server.started and api_server.started:
                        health = await application.runs.worker_health.get_health()
                        if health.get("worker_ready"):
                            break
                    if any(
                        task.done() for task in (router_task, api_task, worker_task)
                    ):
                        raise RuntimeError("Isolated M3 host exited during startup")
                    await asyncio.sleep(0.1)
                else:
                    raise RuntimeError("Isolated M3 host did not become ready")
                print(
                    json.dumps(
                        {
                            "status": "ready",
                            "database": database_name,
                            "api_url": f"http://127.0.0.1:{api_port}",
                            "router_url": f"http://127.0.0.1:{router_port}/v1",
                            "ledger": str(ledger_path),
                            "counts": ledger.counts(),
                        }
                    ),
                    flush=True,
                )
                await stop.wait()
            finally:
                stop.set()
                api_server.should_exit = True
                router_server.should_exit = True
                await asyncio.gather(
                    worker_task, api_task, router_task, return_exceptions=True
                )
                api_app.dependency_overrides.pop(get_agent_runtime_service, None)
                api_app.dependency_overrides.pop(get_agent_runtime_health_service, None)
                api_app.dependency_overrides.pop(authenticate_ade_request, None)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--api-port", type=int, default=8130)
    parser.add_argument("--router-port", type=int, default=8131)
    arguments = parser.parse_args()
    asyncio.run(
        _serve(
            env_file=arguments.env_file,
            database_url=arguments.database_url,
            ledger_path=arguments.ledger,
            api_port=arguments.api_port,
            router_port=arguments.router_port,
        )
    )
