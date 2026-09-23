"""One capped synthetic HTTP API -> worker -> persistence Agent Studio turn."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import text as sql_text

from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.router_transport import RouterTransport
from ade_api.features.agent_runtime.worker import AgentRuntimeWorker
from ade_api.features.prompt_center import build_prompt_template_reader
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.app import app
from ade_api.platform.settings import AdeApiSettings


class CappedNativeTransport:
    """Reserve each outbound request before it reaches either provider."""

    def __init__(self, inner: RouterTransport) -> None:
        self.inner = inner
        self.generation_count = 0
        self.embedding_count = 0

    async def catalog(self, *, timeout_seconds: float = 10.0) -> dict[str, Any]:
        return await self.inner.catalog(timeout_seconds=timeout_seconds)

    async def chat_completion(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        if self.generation_count >= 2:
            raise RuntimeError("DeepSeek generation reservation exhausted")
        self.generation_count += 1
        return await self.inner.chat_completion(
            payload, timeout_seconds=min(timeout_seconds, 180.0)
        )

    async def embeddings(
        self, payload: dict[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        if self.embedding_count >= 3:
            raise RuntimeError("Spark embedding reservation exhausted")
        self.embedding_count += 1
        return await self.inner.embeddings(
            payload, timeout_seconds=min(timeout_seconds, 180.0)
        )


class _ReadyWorker:
    async def get_health(self) -> dict[str, Any]:
        return {"worker_ready": True}


async def run_native_turn(
    transport: RouterTransport,
    *,
    database_url: str,
    database_name: str,
    root: Path,
) -> None:
    engine = create_persistence_engine(database_url)
    capped = CappedNativeTransport(transport)
    run_id: str | None = None
    conversation_id: str | None = None
    subject_id: str | None = None
    source_environment = {
        key: os.environ.get(key)
        for key in ("ADE_SOURCE_REVISION", "ADE_SOURCE_DIRTY", "ADE_SOURCE_FINGERPRINT")
    }
    try:
        async with engine.connect() as connection:
            identity = (
                await connection.execute(
                    sql_text("SELECT current_database(), current_user")
                )
            ).one()
            if tuple(identity) != (database_name, "ade_owner"):
                raise ValueError("Disposable database identity guard failed")
            pending = await connection.scalar(
                sql_text(
                    "SELECT count(*) FROM ade.runs WHERE status IN ('pending', 'running')"
                )
            )
            if pending:
                raise ValueError("Disposable database has unrelated pending runs")

        settings = AdeApiSettings(
            agent_runtime_enabled=True,
            agent_runtime_mode="development",
            model_discovery_timeout_seconds=30,
            database_url=database_url,
        )
        os.environ["ADE_SOURCE_REVISION"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        os.environ["ADE_SOURCE_DIRTY"] = "true"
        os.environ["ADE_SOURCE_FINGERPRINT"] = subprocess.check_output(
            [
                sys.executable,
                str(root / "scripts/source_fingerprint.py"),
                "--root",
                str(root),
            ],
            text=True,
        ).strip()
        with tempfile.TemporaryDirectory(prefix="ade-deepseek-native-") as temp_dir:
            application = AgentRuntimeApplication(
                engine=engine,
                settings=settings,
                prompt_registry=build_prompt_template_reader(
                    root, persona_db_path=Path(temp_dir) / "personas.sqlite3"
                ),
                router_transport=capped,
            )
            # A single local worker is constructed below; the readiness shim
            # avoids source-build identity checks on this deliberately dirty tree.
            application.runs.worker_health = _ReadyWorker()
            worker = AgentRuntimeWorker(
                engine=engine, settings=settings, transport=capped
            )
            app.dependency_overrides[get_agent_runtime_service] = lambda: application
            app.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
                role=AdeRole.ADMIN, key_name="synthetic-probe"
            )
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://ade-synthetic.local",
                    timeout=30,
                ) as client:
                    token = uuid4().hex[:12]
                    request = application.definitions.default_agent_studio_request()
                    response = await client.post(
                        "/api/v3/agent-studio/sessions",
                        json={
                            "idempotency_key": f"deepseek-native-{token}",
                            "title": "Synthetic DeepSeek native turn",
                            "new_definition": request.model_copy(
                                update={
                                    "definition_key": f"deepseek_native_{token}",
                                    "tool_names": [],
                                }
                            ).model_dump(),
                            "new_subject": {
                                "external_key": f"deepseek-native-{token}",
                                "display_name": "Synthetic test user",
                            },
                        },
                    )
                    response.raise_for_status()
                    session = response.json()
                    conversation_id = session["conversation"]["id"]
                    subject_id = session["memory_subject"]["id"]
                    response = await client.post(
                        f"/api/v3/conversations/{conversation_id}/turns",
                        json={
                            "idempotency_key": f"deepseek-native-turn-{token}",
                            "content": "I currently live in Toronto.",
                            "timeout_seconds": 180,
                            "retry_count": 0,
                        },
                    )
                    response.raise_for_status()
                    run_id = response.json()["run_id"]
                    await worker.process_once()
            finally:
                app.dependency_overrides.pop(get_agent_runtime_service, None)
                app.dependency_overrides.pop(authenticate_ade_request, None)

        # Independent connection reads back the committed state; no model call.
        if run_id and subject_id:
            async with engine.connect() as connection:
                status = await connection.scalar(
                    sql_text(
                        "SELECT status FROM ade.runs WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": run_id},
                )
                facts = (
                    (
                        await connection.execute(
                            sql_text(
                                "SELECT fact_type, value, status, version "
                                "FROM ade.memory_facts WHERE subject_id = CAST(:subject AS uuid)"
                            ),
                            {"subject": subject_id},
                        )
                    )
                    .mappings()
                    .all()
                )
                revision_count = await connection.scalar(
                    sql_text(
                        "SELECT count(*) FROM ade.memory_revisions WHERE run_id = CAST(:id AS uuid)"
                    ),
                    {"id": run_id},
                )
                event_types = (
                    (
                        await connection.execute(
                            sql_text(
                                "SELECT event_type FROM ade.run_events WHERE run_id = CAST(:id AS uuid) "
                                "ORDER BY sequence"
                            ),
                            {"id": run_id},
                        )
                    )
                    .scalars()
                    .all()
                )
            print(
                json.dumps(
                    {
                        "database": database_name,
                        "conversation_id": conversation_id,
                        "subject_id": subject_id,
                        "run_id": run_id,
                        "run_status": status,
                        "facts": [dict(row) for row in facts],
                        "memory_revision_count": revision_count,
                        "events": event_types,
                        "deepseek_generation_requests": capped.generation_count,
                        "spark_embedding_requests": capped.embedding_count,
                    },
                    default=str,
                )
            )
    except Exception as exc:
        print(
            json.dumps(
                {
                    "conversation_id": conversation_id,
                    "subject_id": subject_id,
                    "run_id": run_id,
                    "deepseek_generation_requests": capped.generation_count,
                    "spark_embedding_requests": capped.embedding_count,
                    "failure_type": type(exc).__name__,
                }
            )
        )
        raise
    finally:
        for key, value in source_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        await engine.dispose()
