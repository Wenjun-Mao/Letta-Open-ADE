"""Isolated M3 HTTP API, worker, and router."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

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


async def _serve(
    *,
    env_file: Path,
    database_url: str,
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
        transport = RouterTransport(base_url=f"http://127.0.0.1:{router_port}/v1")
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
    parser.add_argument("--api-port", type=int, default=8130)
    parser.add_argument("--router-port", type=int, default=8131)
    arguments = parser.parse_args()
    asyncio.run(
        _serve(
            env_file=arguments.env_file,
            database_url=arguments.database_url,
            api_port=arguments.api_port,
            router_port=arguments.router_port,
        )
    )
