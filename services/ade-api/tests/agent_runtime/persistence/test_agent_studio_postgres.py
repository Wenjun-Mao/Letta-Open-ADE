from __future__ import annotations

import asyncio
import hashlib
import os
from uuid import uuid4

import pytest
from sqlalchemy import func, insert, select, update

from ade_api.features.agent_runtime.agent_studio_reset import (
    AgentStudioResetService,
)
from ade_api.features.agent_runtime.agent_studio_sessions import (
    AgentStudioSessionService,
)
from ade_api.features.agent_runtime.contracts import (
    AgentStudioResetRequest,
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
    MemoryRemovalRequest,
)
from ade_api.features.agent_runtime.database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
)
from ade_api.features.agent_runtime.errors import (
    MemoryActionIdempotencyConflict,
    MemoryGenerationConflict,
    MemoryTargetConflict,
    RuntimeConflict,
)
from ade_api.features.agent_runtime.memory_removals import MemoryRemovalService
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.memory import MemoryRepository
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definitions,
    agent_studio_reset_receipts,
    conversations,
    memory_actions,
    memory_facts,
    memory_revisions,
    memory_subjects,
    runs,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL", "")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL is required for Agent Studio PostgreSQL tests",
)


class _PreparedDefinitions:
    async def prepare(
        self, request: CreateAgentDefinitionRequest, *, purpose: str = "development"
    ):
        assert purpose == "agent_studio"
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


def test_operator_removal_is_atomic_scoped_and_replay_is_historical() -> None:
    asyncio.run(_exercise_operator_removal())


async def _exercise_operator_removal() -> None:
    engine = create_persistence_engine(DATABASE_URL)
    database = RuntimeDatabase(engine)
    sessions = AgentStudioSessionService(
        database=database,
        definitions=_PreparedDefinitions(),  # type: ignore[arg-type]
    )
    removals = MemoryRemovalService(database)
    token = uuid4().hex[:12]
    try:
        created = await sessions.create(_session_request(token))
        subject_id = created["memory_subject"]["id"]
        conversation_id = created["conversation"]["id"]
        other_subject_id = str(uuid4())
        fact_ids = [str(uuid4()), str(uuid4())]
        run_id = str(uuid4())
        content = "I like coffee and blue."
        digest = hashlib.sha256(content.encode()).hexdigest()
        async with engine.begin() as connection:
            await connection.execute(
                insert(runs).values(
                    id=run_id,
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    conversation_id=conversation_id,
                    idempotency_key=f"setup-{token}",
                    request_hash=digest,
                    status="succeeded",
                    qualification_state="qualified",
                    timeout_seconds=180,
                    retry_count=0,
                    accepted_conversation_version=1,
                    accepted_memory_generation=1,
                    attempt_count=1,
                )
            )
            message = await ConversationRepository(connection).append_message(
                {
                    "id": str(uuid4()),
                    "workspace_id": DEFAULT_WORKSPACE_ID,
                    "conversation_id": conversation_id,
                    "role": "user",
                    "content": content,
                    "content_sha256": digest,
                    "run_id": run_id,
                }
            )
            memory = MemoryRepository(connection)
            await memory.create_subject(
                {
                    "id": other_subject_id,
                    "workspace_id": DEFAULT_WORKSPACE_ID,
                    "external_key": f"other-removal-{token}",
                    "display_name": "Other subject",
                    "purpose": "agent_studio",
                }
            )
            for fact_id, qualifier, value in zip(
                fact_ids, ("drink", "color"), ("coffee", "blue"), strict=True
            ):
                start = content.index(value)
                await memory.create_initial_revision(
                    {
                        "id": fact_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "subject_id": subject_id,
                        "entity_id": subject_id,
                        "normalized_key": f"person.preference|{subject_id}|{qualifier}|{fact_id}",
                        "fact_type": "person.preference",
                        "qualifier": qualifier,
                        "value": value,
                        "status": "active",
                        "assertion_schema_version": 2,
                        "version": 1,
                        "current_revision_id": None,
                    },
                    {
                        "id": str(uuid4()),
                        "fact_id": fact_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "subject_id": subject_id,
                        "operation": "add",
                        "fact_version": 1,
                        "value": value,
                        "run_id": run_id,
                    },
                    evidence=[
                        {
                            "id": str(uuid4()),
                            "message_id": message["id"],
                            "start_char": start,
                            "end_char": start + len(value),
                            "quote": value,
                            "message_sha256": digest,
                            "authority_role": "user_assertion",
                        }
                    ],
                )
            assert (
                await memory.advance_memory_generation(
                    subject_id, expected_generation=1
                )
                == 2
            )
            await ConversationRepository(connection).set_archived(
                conversation_id, archived=True
            )

        target_pair = [
            {"fact_id": fact_id, "expected_version": 1} for fact_id in fact_ids
        ]
        wrong = MemoryRemovalRequest(
            idempotency_key=f"wrong-{token}",
            expected_memory_generation=2,
            targets=[target_pair[0], {**target_pair[1], "expected_version": 2}],
        )
        with pytest.raises(MemoryTargetConflict):
            await removals.remove(subject_id, wrong, actor_label="operator")
        with pytest.raises(MemoryTargetConflict):
            await removals.remove(
                other_subject_id,
                MemoryRemovalRequest(
                    idempotency_key=f"cross-subject-{token}",
                    expected_memory_generation=1,
                    targets=[target_pair[0]],
                ),
                actor_label="operator",
            )
        async with engine.connect() as connection:
            assert (await MemoryRepository(connection).get_subject(subject_id))[
                "memory_generation"
            ] == 2
            assert all(
                fact["status"] == "active"
                for fact in await MemoryRepository(connection).list_facts(subject_id)
            )

        request = MemoryRemovalRequest(
            idempotency_key=f"remove-{token}",
            expected_memory_generation=2,
            targets=target_pair,
        )
        receipt = await removals.remove(subject_id, request, actor_label="operator")
        assert receipt["outcome"] == "committed"
        assert receipt["resulting_memory_generation"] == 3
        assert len(receipt["revision_ids"]) == 2
        assert not receipt["idempotent_replay"]
        with pytest.raises(MemoryActionIdempotencyConflict):
            await removals.remove(
                subject_id,
                request.model_copy(update={"targets": request.targets[:1]}),
                actor_label="operator",
            )
        with pytest.raises(MemoryGenerationConflict):
            await removals.remove(
                subject_id,
                MemoryRemovalRequest(
                    idempotency_key=f"stale-{token}",
                    expected_memory_generation=2,
                    targets=target_pair,
                ),
                actor_label="operator",
            )

        replay = await removals.remove(subject_id, request, actor_label="operator")
        assert replay["action_id"] == receipt["action_id"]
        assert replay["revision_ids"] == receipt["revision_ids"]
        assert replay["idempotent_replay"]
        async with engine.connect() as connection:
            assert (await MemoryRepository(connection).get_subject(subject_id))[
                "memory_generation"
            ] == 3
            assert all(
                fact["status"] == "forgotten"
                for fact in await MemoryRepository(connection).list_facts(subject_id)
            )
            actions = (
                (await connection.execute(select(memory_actions))).mappings().all()
            )
            assert any(row["id"] == receipt["action_id"] for row in actions)
            revisions = (
                (
                    await connection.execute(
                        select(memory_revisions).where(
                            memory_revisions.c.id.in_(receipt["revision_ids"])
                        )
                    )
                )
                .mappings()
                .all()
            )
            assert len(revisions) == 2
            assert all(row["run_id"] is None for row in revisions)
            assert all(row["action_id"] == receipt["action_id"] for row in revisions)

        reset = AgentStudioResetService(database)
        await reset.reset(
            AgentStudioResetRequest(
                idempotency_key=f"cleanup-removal-{token}",
                confirmation="RESET ADE AGENT STUDIO",
            )
        )
        async with engine.connect() as connection:
            assert (
                await connection.scalar(
                    select(memory_facts.c.id).where(memory_facts.c.id.in_(fact_ids))
                )
                is None
            )
    finally:
        await engine.dispose()


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
