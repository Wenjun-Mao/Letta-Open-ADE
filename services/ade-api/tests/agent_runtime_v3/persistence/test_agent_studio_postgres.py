from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from ade_api.features.agent_runtime_v3.agent_studio_reset import (
    AgentStudioResetService,
)
from ade_api.features.agent_runtime_v3.agent_studio_sessions import (
    AgentStudioSessionService,
)
from ade_api.features.agent_runtime_v3.contracts import (
    AgentStudioResetRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
)
from ade_api.features.agent_runtime_v3.database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
)
from ade_api.features.agent_runtime_v3.errors import RuntimeConflict
from ade_api.features.agent_runtime_v3.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime_v3.persistence.metadata import (
    agent_definitions,
    agent_studio_reset_receipts,
    conversations,
    memory_subjects,
    runs,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL is required for Agent Studio PostgreSQL tests",
)


class _PreparedDefinitions:
    async def prepare(self, request: CreateAgentDefinitionRequest):
        return {
            "definition_key": request.definition_key,
            "name": request.name,
            "model_key": request.model_key,
            "reviewer_model_key": request.reviewer_model_key,
            "embedding_model_key": request.embedding_model_key,
            "prompt_key": request.prompt_key,
            "prompt_sha256": "a" * 64,
            "prompt_content": "system prompt",
            "persona_key": request.persona_key,
            "persona_sha256": "b" * 64,
            "persona_content": "persona",
            "tool_names": list(request.tool_names),
            "memory_policy_version": "typed-user-facts-v1",
            "qualification_state": "qualified",
            "deployment_snapshot": [],
        }


def _session_request(token: str) -> CreateAgentStudioSessionRequest:
    return CreateAgentStudioSessionRequest(
        idempotency_key=f"session-{token}",
        title="Persistent conversation",
        new_definition=CreateAgentDefinitionRequest(
            definition_key=f"studio_{token}",
            name="Studio definition",
            model_key="dgx_vllm::qwen",
            reviewer_model_key="dgx_vllm::qwen",
            embedding_model_key="dgx_embedding::qwen",
        ),
        new_subject=CreateMemorySubjectRequest(
            external_key=f"studio-subject-{token}",
            display_name="Local user",
        ),
    )


def test_agent_studio_session_is_atomic_replayable_and_scoped_reset() -> None:
    asyncio.run(_exercise_atomic_session_and_reset())


async def _exercise_atomic_session_and_reset() -> None:
    engine = create_persistence_engine(DATABASE_URL)
    database = RuntimeDatabase(engine)
    sessions = AgentStudioSessionService(
        database=database,
        definitions=_PreparedDefinitions(),  # type: ignore[arg-type]
    )
    reset = AgentStudioResetService(database)
    token = uuid4().hex[:12]
    try:
        created = await sessions.create(_session_request(token))
        replayed = await sessions.create(_session_request(token))

        assert created["idempotent_replay"] is False
        assert replayed["idempotent_replay"] is True
        assert replayed["conversation"]["id"] == created["conversation"]["id"]
        assert created["conversation"]["purpose"] == "agent_studio"
        assert created["agent_definition"]["agent_definition_id"]

        receipt = await reset.reset(
            AgentStudioResetRequest(
                idempotency_key=f"reset-{token}",
                confirmation="RESET ADE AGENT STUDIO",
            )
        )
        receipt_replay = await reset.reset(
            AgentStudioResetRequest(
                idempotency_key=f"reset-{token}",
                confirmation="RESET ADE AGENT STUDIO",
            )
        )
        assert receipt["idempotent_replay"] is False
        assert receipt_replay["idempotent_replay"] is True
        assert receipt_replay["receipt_id"] == receipt["receipt_id"]
        assert receipt["deleted_counts"]["conversations"] >= 1

        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    select(conversations.c.id).where(
                        conversations.c.id == created["conversation"]["id"]
                    )
                )
                is None
            )
            assert (
                await connection.scalar(
                    select(memory_subjects.c.id).where(
                        memory_subjects.c.id == created["memory_subject"]["id"]
                    )
                )
                is None
            )
            assert (
                await connection.scalar(
                    select(agent_definitions.c.id).where(
                        agent_definitions.c.id
                        == created["agent_definition"]["agent_definition_id"]
                    )
                )
                is None
            )
            assert (
                await connection.scalar(
                    select(agent_studio_reset_receipts.c.id).where(
                        agent_studio_reset_receipts.c.id == receipt["receipt_id"]
                    )
                )
                == receipt["receipt_id"]
            )
    finally:
        await engine.dispose()


def test_agent_studio_reset_refuses_an_active_run() -> None:
    asyncio.run(_exercise_active_run_refusal())


async def _exercise_active_run_refusal() -> None:
    engine = create_persistence_engine(DATABASE_URL)
    database = RuntimeDatabase(engine)
    sessions = AgentStudioSessionService(
        database=database,
        definitions=_PreparedDefinitions(),  # type: ignore[arg-type]
    )
    reset = AgentStudioResetService(database)
    token = uuid4().hex[:12]
    created = None
    try:
        created = await sessions.create(_session_request(token))
        run_id = str(uuid4())
        async with engine.begin() as connection:
            await connection.execute(
                runs.insert().values(
                    id=run_id,
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    conversation_id=created["conversation"]["id"],
                    idempotency_key=f"active-{token}",
                    request_hash="c" * 64,
                    status="pending",
                    qualification_state="qualified",
                    timeout_seconds=180,
                    retry_count=0,
                    accepted_conversation_version=1,
                )
            )

        request = AgentStudioResetRequest(
            idempotency_key=f"blocked-reset-{token}",
            confirmation="RESET ADE AGENT STUDIO",
        )
        with pytest.raises(RuntimeConflict, match="pending or running"):
            await reset.reset(request)

        async with engine.begin() as connection:
            await connection.execute(
                update(runs)
                .where(runs.c.id == run_id)
                .values(status="cancelled", finished_at=func.now())
            )
        completed = await reset.reset(request)
        assert completed["deleted_counts"]["runs"] >= 1
    finally:
        if created is not None:
            try:
                await reset.reset(
                    AgentStudioResetRequest(
                        idempotency_key=f"cleanup-{token}",
                        confirmation="RESET ADE AGENT STUDIO",
                    )
                )
            except Exception:
                pass
        await engine.dispose()
