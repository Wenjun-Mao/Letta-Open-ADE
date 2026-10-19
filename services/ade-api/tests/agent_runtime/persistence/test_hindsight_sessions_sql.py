"""Fresh Hindsight session provisioning through the actual public API contracts."""

import asyncio
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import FastAPI
import httpx
import pytest
from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from ade_api.features.agent_runtime.api import router
from ade_api.features.agent_runtime.application import AgentRuntimeApplication
from ade_api.features.agent_runtime.contracts import CreateAgentDefinitionRequest
from ade_api.features.agent_runtime.database_boundary import RuntimeDatabase
from ade_api.features.agent_runtime.dependencies import get_agent_runtime_service
from ade_api.features.agent_runtime.errors import RuntimeNotReady
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_relationships,
    workspaces,
)
from ade_api.features.agent_runtime.session_resources import session_identity
from ade_api.platform.auth import AdePrincipal, AdeRole, authenticate_ade_request
from ade_api.platform.settings import AdeApiSettings

from .hindsight_runtime_support import CharacterTransport, ReadyWorker
from .hindsight_support import DATABASE_URL, engine


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="Disposable Hindsight PostgreSQL fixture not configured"
)


class PromptRegistry:
    def get_template(self, kind, key, **kwargs):
        return {"content": f"Controlled original {kind}"}


def test_api_session_replay_continuity_and_fresh_workspace_isolation():
    asyncio.run(_session_continuity())


async def _session_continuity():
    db = engine()
    try:
        settings = AdeApiSettings(
            _env_file=None,
            agent_runtime_mode="development",
            agent_runtime_workspace_key="sessions-sql-" + uuid4().hex,
        )
        application = AgentRuntimeApplication(
            engine=db,
            settings=settings,
            prompt_registry=PromptRegistry(),
            router_transport=CharacterTransport(db),
        )
        application.runs.worker_health = ReadyWorker()
        api = FastAPI()
        api.include_router(router)
        api.dependency_overrides[get_agent_runtime_service] = lambda: application
        api.dependency_overrides[authenticate_ade_request] = lambda: AdePrincipal(
            role=AdeRole.ADMIN, key_name="controlled-api-test"
        )
        key = uuid4().hex
        payload = {
            "idempotency_key": key,
            "model_key": "fake::character",
            "compaction_model_key": "fake::character",
        }
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api), base_url="http://controlled"
        ) as client:
            first = await client.post("/api/v3/evaluation-sessions", json=payload)
            assert first.status_code == 201, first.text
            saved = first.json()
            replay = await client.post("/api/v3/evaluation-sessions", json=payload)
            assert replay.headers["Idempotent-Replay"] == "true"
            assert replay.json()["conversation"]["id"] == saved["conversation"]["id"]
            assert [
                item["role"] for item in saved["agent_definition"]["deployments"]
            ] == ["conversation", "compaction"]
            original = saved["agent_definition"]
            version = await application.definitions.create(
                CreateAgentDefinitionRequest(
                    definition_key=original["definition_key"],
                    name="Same character new immutable version",
                    model_key="fake::character",
                    compaction_model_key="fake::character",
                    expected_current_version=1,
                ),
                purpose="evaluation",
            )
            assert (
                version["agent_definition_id"] == original["agent_definition_id"]
                and version["id"] != original["id"]
            )
            next_chat = await client.post(
                "/api/v3/evaluation-sessions",
                json={
                    "idempotency_key": uuid4().hex,
                    "agent_definition_id": version["id"],
                    "memory_subject_id": saved["memory_subject"]["id"],
                },
            )
            assert next_chat.status_code == 201, next_chat.text
            await application.evaluations.sessions.set_archived(
                saved["conversation"]["id"], archived=True
            )
            state = await client.get(
                f"/api/v3/evaluation-sessions/{saved['conversation']['id']}/state"
            )
            assert state.status_code == 200
            assert state.json()["conversation"]["agent_definition_id"] == original["id"]
            assert "memories" not in state.json()
            assert (
                await client.delete(
                    f"/api/v3/evaluation-sessions/{saved['conversation']['id']}"
                )
            ).status_code == 404
            assert (
                await client.post("/api/v3/agent-studio/reset", json={})
            ).status_code == 404
            assert (
                await client.post(
                    f"/api/v3/agent-studio/subjects/{saved['memory_subject']['id']}/memory-removals",
                    json={},
                )
            ).status_code == 404
        async with db.connect() as connection:
            relationships = (
                (
                    await connection.execute(
                        select(memory_relationships).where(
                            memory_relationships.c.workspace_id
                            == application.database.workspace_id
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert len(relationships) == 1
            assert (
                str(relationships[0]["character_root_id"])
                == original["agent_definition_id"]
            )
        foreign = session_identity(
            key, workspace_id=str(uuid4()), namespace="evaluation"
        )
        assert foreign.conversation_id != saved["conversation"]["id"]
    finally:
        await db.dispose()


def test_existing_native_workspace_cannot_be_adopted_or_silently_reinitialized():
    asyncio.run(_existing_authority())


async def _existing_authority():
    db = engine()
    key = "incumbent-sql-" + uuid4().hex
    identity = str(uuid5(NAMESPACE_URL, f"ade://workspace/{key}"))
    try:
        async with db.begin() as connection:
            await connection.execute(
                insert(workspaces).values(
                    id=identity,
                    workspace_key=key,
                    name="Preserved synthetic native authority",
                    memory_backend="incumbent",
                )
            )
        database = RuntimeDatabase(db, workspace_key=key)
        with pytest.raises(RuntimeNotReady):
            await database.ensure_ready()
        async with db.connect() as connection:
            assert (
                await connection.scalar(
                    select(workspaces.c.memory_backend).where(
                        workspaces.c.id == identity
                    )
                )
                == "incumbent"
            )
        async with db.begin() as connection:
            with pytest.raises(IntegrityError, match="authority are immutable"):
                async with connection.begin_nested():
                    await connection.execute(
                        update(workspaces)
                        .where(workspaces.c.id == identity)
                        .values(memory_backend="hindsight")
                    )
            with pytest.raises(IntegrityError, match="authority are immutable"):
                async with connection.begin_nested():
                    await connection.execute(
                        update(workspaces)
                        .where(workspaces.c.id == identity)
                        .values(workspace_key=key + "-renamed")
                    )
        with pytest.raises(RuntimeNotReady):
            RuntimeDatabase(db, workspace_key="default")
        with pytest.raises(RuntimeNotReady):
            RuntimeDatabase(db, workspace_key="")
    finally:
        await db.dispose()
