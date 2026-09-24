from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, delete, inspect, insert, select, text, update

from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.validation import (
    alembic_config,
    validate_database_at_head,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    agent_definitions,
    conversations,
    memory_embeddings,
    memory_entities,
    memory_facts,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    messages,
    runs,
    worker_instances,
    workspaces,
)
from ade_api.features.agent_runtime.persistence.workers import (
    WorkerInstanceRepository,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
MIGRATION_URL = os.getenv("ADE_DATABASE_MIGRATION_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL is required for PostgreSQL pgvector migration tests",
)


def _sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+psycopg://"):
        return database_url
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql+psycopg://", 1)
    raise ValueError("ADE_TEST_DATABASE_URL must be a PostgreSQL URL")


def test_alembic_upgrade_creates_named_ade_pgvector_schema() -> None:
    assert DATABASE_URL is not None
    engine = create_engine(_sync_database_url(DATABASE_URL))
    try:
        with engine.connect() as connection:
            validate_database_at_head(connection)
            inspector = inspect(connection)
            assert "agent_definitions" in inspector.get_table_names(schema="ade")
            assert "agent_studio_reset_receipts" in inspector.get_table_names(
                schema="ade"
            )
            assert "memory_embeddings" in inspector.get_table_names(schema="ade")
            assert "worker_instances" in inspector.get_table_names(schema="ade")
            worker_columns = {
                column["name"]
                for column in inspector.get_columns("worker_instances", schema="ade")
            }
            assert "source_fingerprint" in worker_columns
            definition_version_columns = {
                column["name"]
                for column in inspector.get_columns(
                    "agent_definition_versions", schema="ade"
                )
            }
            assert "agent_definition_id" in definition_version_columns
            subject_columns = {
                column["name"]
                for column in inspector.get_columns("memory_subjects", schema="ade")
            }
            assert {"purpose", "version", "archived_at", "updated_at"} <= (
                subject_columns
            )
            conversation_columns = {
                column["name"]
                for column in inspector.get_columns("conversations", schema="ade")
            }
            assert {"title", "purpose"} <= conversation_columns
            summary_columns = {
                column["name"]
                for column in inspector.get_columns(
                    "conversation_summaries", schema="ade"
                )
            }
            assert {
                "previous_summary_id",
                "model_key",
                "model_fingerprint",
                "provider_request_id",
                "content_sha256",
                "prompt_sha256",
                "input_sha256",
                "policy_sha256",
            } <= summary_columns
            assert "uq_runs_active_conversation" in {
                index["name"] for index in inspector.get_indexes("runs", schema="ade")
            }
            run_columns = {
                column["name"] for column in inspector.get_columns("runs", schema="ade")
            }
            assert "accepted_runtime_mode" in run_columns
            assert connection.scalar(
                text(
                    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
                )
            )
    finally:
        engine.dispose()


def test_worker_health_snapshot_executes_as_the_application_role() -> None:
    assert DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_persistence_engine(DATABASE_URL)
        instance_id = str(uuid4())
        try:
            async with engine.begin() as connection:
                workers = WorkerInstanceRepository(connection)
                await workers.register(
                    {
                        "instance_id": instance_id,
                        "worker_id": "postgres-permission-test",
                        "state": "ready",
                        "contract_version": "agent-runtime-worker-v1",
                        "compatibility_fingerprint": "f" * 64,
                        "runtime_version": "test",
                        "source_revision": "a" * 40,
                        "source_dirty": False,
                        "source_fingerprint": "b" * 64,
                    }
                )
                assert await workers.heartbeat(instance_id) is True
                snapshot = await workers.health_snapshot(
                    compatibility_fingerprint="f" * 64,
                    source_revision="a" * 40,
                    source_dirty=False,
                    source_fingerprint="b" * 64,
                    freshness_seconds=15.0,
                )
                assert snapshot["compatible_worker_count"] == 1
                assert snapshot["matching_build_worker_count"] == 1
                assert await workers.mark_draining(instance_id) is True
                assert await workers.mark_stopped(instance_id) is True
        finally:
            async with engine.begin() as connection:
                result = await connection.execute(
                    delete(worker_instances).where(
                        worker_instances.c.instance_id == instance_id
                    )
                )
                assert result.rowcount in {0, 1}
            await engine.dispose()

    asyncio.run(scenario())


@pytest.mark.skipif(
    not MIGRATION_URL,
    reason="ADE_DATABASE_MIGRATION_URL is required for migration transition tests",
)
def test_0001_to_0002_preserves_legacy_summary_with_explicit_provenance() -> None:
    assert MIGRATION_URL is not None
    config = alembic_config(MIGRATION_URL)
    command.downgrade(config, "20260829_0001")
    ids = {
        name: str(uuid4())
        for name in (
            "workspace",
            "definition",
            "subject",
            "conversation",
            "run",
            "message",
            "summary",
        )
    }
    engine = create_engine(_sync_database_url(MIGRATION_URL))
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO ade.workspaces (id, workspace_key, name) "
                    "VALUES (:id, :key, 'Migration test')"
                ),
                {"id": ids["workspace"], "key": f"migration-{ids['workspace']}"},
            )
            connection.execute(
                text(
                    "INSERT INTO ade.agent_definition_versions ("
                    "id, workspace_id, definition_key, version, name, model_key, "
                    "reviewer_model_key, embedding_model_key, prompt_key, "
                    "prompt_sha256, prompt_content, persona_key, persona_sha256, "
                    "persona_content, tool_names, memory_policy_version, "
                    "qualification_state, deployment_snapshot) VALUES ("
                    ":id, :workspace_id, 'migration-test', 1, 'Migration test', "
                    "'chat', 'reviewer', 'embedding', 'prompt', :digest, '', "
                    "'persona', :digest, '', CAST('[]' AS jsonb), 'v1', "
                    "'unqualified', CAST('[]' AS jsonb))"
                ),
                {
                    "id": ids["definition"],
                    "workspace_id": ids["workspace"],
                    "digest": "0" * 64,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO ade.memory_subjects "
                    "(id, workspace_id, external_key) VALUES "
                    "(:id, :workspace_id, :external_key)"
                ),
                {
                    "id": ids["subject"],
                    "workspace_id": ids["workspace"],
                    "external_key": f"subject-{ids['subject']}",
                },
            )
            connection.execute(
                text(
                    "INSERT INTO ade.conversations "
                    "(id, workspace_id, agent_definition_version_id, "
                    "memory_subject_id) VALUES "
                    "(:id, :workspace_id, :definition_id, :subject_id)"
                ),
                {
                    "id": ids["conversation"],
                    "workspace_id": ids["workspace"],
                    "definition_id": ids["definition"],
                    "subject_id": ids["subject"],
                },
            )
            connection.execute(
                text(
                    "INSERT INTO ade.runs (id, workspace_id, conversation_id, "
                    "idempotency_key, request_hash, status, qualification_state, "
                    "timeout_seconds, retry_count, accepted_conversation_version, "
                    "attempt_count) VALUES (:id, :workspace_id, :conversation_id, "
                    ":key, :digest, 'succeeded', 'unqualified', 180, 0, 1, 1)"
                ),
                {
                    "id": ids["run"],
                    "workspace_id": ids["workspace"],
                    "conversation_id": ids["conversation"],
                    "key": f"turn-{ids['run']}",
                    "digest": "1" * 64,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO ade.messages (id, workspace_id, conversation_id, "
                    "sequence, role, content, content_sha256, run_id) VALUES "
                    "(:id, :workspace_id, :conversation_id, 1, 'user', 'legacy', "
                    ":digest, :run_id)"
                ),
                {
                    "id": ids["message"],
                    "workspace_id": ids["workspace"],
                    "conversation_id": ids["conversation"],
                    "digest": "2" * 64,
                    "run_id": ids["run"],
                },
            )
            connection.execute(
                text(
                    "INSERT INTO ade.conversation_summaries "
                    "(id, conversation_id, version, through_sequence, content, run_id) "
                    "VALUES (:id, :conversation_id, 1, 1, 'legacy summary', :run_id)"
                ),
                {
                    "id": ids["summary"],
                    "conversation_id": ids["conversation"],
                    "run_id": ids["run"],
                },
            )
            connection.execute(
                text(
                    "INSERT INTO ade.summary_sources (summary_id, message_id) "
                    "VALUES (:summary_id, :message_id)"
                ),
                {"summary_id": ids["summary"], "message_id": ids["message"]},
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            summary = (
                connection.execute(
                    text(
                        "SELECT model_key, model_fingerprint, content_sha256, "
                        "prompt_sha256, input_sha256, policy_sha256 "
                        "FROM ade.conversation_summaries WHERE id = :id"
                    ),
                    {"id": ids["summary"]},
                )
                .mappings()
                .one()
            )
            assert summary["model_key"] == "legacy-unattributed"
            assert set(summary.values()) == {"legacy-unattributed", "0" * 64}
            assert (
                connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM ade.summary_sources "
                        "WHERE summary_id = :summary_id AND message_id = :message_id"
                    ),
                    {"summary_id": ids["summary"], "message_id": ids["message"]},
                )
                == 1
            )
    finally:
        command.upgrade(config, "head")
        engine.dispose()


@pytest.mark.skipif(
    not MIGRATION_URL,
    reason="ADE_DATABASE_MIGRATION_URL is required for populated transition tests",
)
def test_0006_to_0007_preserves_populated_fact_vector_and_source() -> None:
    assert MIGRATION_URL is not None
    config = alembic_config(MIGRATION_URL)
    command.downgrade(config, "20260902_0006")
    keys = (
        "workspace",
        "root",
        "definition",
        "subject",
        "conversation",
        "run",
        "message",
        "entity",
        "fact",
        "revision",
        "source",
        "embedding",
    )
    ids = {key: str(uuid4()) for key in keys}
    engine = create_engine(_sync_database_url(MIGRATION_URL))
    try:
        with engine.begin() as connection:
            connection.execute(
                insert(workspaces).values(
                    id=ids["workspace"],
                    workspace_key=f"natural-migration-{ids['workspace']}",
                    name="Natural migration preservation",
                )
            )
            connection.execute(
                insert(agent_definitions).values(
                    id=ids["root"],
                    workspace_id=ids["workspace"],
                    definition_key=f"migration-{ids['root'][:8]}",
                    name="Migration",
                )
            )
            connection.execute(
                insert(agent_definition_versions).values(
                    id=ids["definition"],
                    workspace_id=ids["workspace"],
                    agent_definition_id=ids["root"],
                    definition_key=f"migration-{ids['root'][:8]}",
                    version=1,
                    name="Migration",
                    model_key="chat",
                    reviewer_model_key="reviewer",
                    embedding_model_key="embedding",
                    prompt_key="prompt",
                    prompt_sha256="0" * 64,
                    prompt_content="",
                    persona_key="persona",
                    persona_sha256="1" * 64,
                    persona_content="",
                    tool_names=[],
                    memory_policy_version="typed-user-facts-v1",
                    qualification_state="unqualified",
                    deployment_snapshot=[],
                )
            )
            connection.execute(
                insert(memory_subjects).values(
                    id=ids["subject"],
                    workspace_id=ids["workspace"],
                    external_key=f"migration-{ids['subject']}",
                    display_name="Legacy user",
                )
            )
            connection.execute(
                insert(memory_entities).values(
                    id=ids["entity"],
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject"],
                    kind="subject",
                    label="Legacy user",
                )
            )
            connection.execute(
                insert(conversations).values(
                    id=ids["conversation"],
                    workspace_id=ids["workspace"],
                    agent_definition_version_id=ids["definition"],
                    memory_subject_id=ids["subject"],
                    title="Migration",
                )
            )
            connection.execute(
                insert(runs).values(
                    id=ids["run"],
                    workspace_id=ids["workspace"],
                    conversation_id=ids["conversation"],
                    idempotency_key=f"run-{ids['run']}",
                    request_hash="2" * 64,
                    status="succeeded",
                    qualification_state="unqualified",
                    accepted_runtime_mode="development",
                    timeout_seconds=180,
                    retry_count=0,
                    accepted_conversation_version=1,
                    attempt_count=1,
                )
            )
            connection.execute(
                insert(messages).values(
                    id=ids["message"],
                    workspace_id=ids["workspace"],
                    conversation_id=ids["conversation"],
                    sequence=1,
                    role="user",
                    content="I live in Toronto.",
                    content_sha256="3" * 64,
                    run_id=ids["run"],
                )
            )
            connection.execute(
                insert(memory_facts).values(
                    id=ids["fact"],
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject"],
                    entity_id=ids["entity"],
                    normalized_key=f"person.current_location|{ids['entity']}",
                    fact_type="person.current_location",
                    value="Toronto",
                    status="active",
                    version=1,
                )
            )
            connection.execute(
                insert(memory_revisions).values(
                    id=ids["revision"],
                    fact_id=ids["fact"],
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject"],
                    operation="add",
                    fact_version=1,
                    value="Toronto",
                    run_id=ids["run"],
                )
            )
            connection.execute(
                update(memory_facts)
                .where(memory_facts.c.id == ids["fact"])
                .values(current_revision_id=ids["revision"])
            )
            connection.execute(
                insert(memory_revision_sources).values(
                    id=ids["source"],
                    revision_id=ids["revision"],
                    message_id=ids["message"],
                    start_char=10,
                    end_char=17,
                    quote="Toronto",
                    message_sha256="3" * 64,
                )
            )
            connection.execute(
                insert(memory_embeddings).values(
                    id=ids["embedding"],
                    workspace_id=ids["workspace"],
                    subject_id=ids["subject"],
                    fact_id=ids["fact"],
                    revision_id=ids["revision"],
                    model_fingerprint="legacy-test-space",
                    dimensions=3,
                    normalized=True,
                    retrieval_policy_version="qwen3-semantic-facts-v1",
                    embedding=[1.0, 0.0, 0.0],
                )
            )
        command.upgrade(config, "head")
        with engine.connect() as connection:
            subject = (
                connection.execute(
                    select(memory_subjects).where(
                        memory_subjects.c.id == ids["subject"]
                    )
                )
                .mappings()
                .one()
            )
            fact = (
                connection.execute(
                    select(memory_facts).where(memory_facts.c.id == ids["fact"])
                )
                .mappings()
                .one()
            )
            revision = (
                connection.execute(
                    select(memory_revisions).where(
                        memory_revisions.c.id == ids["revision"]
                    )
                )
                .mappings()
                .one()
            )
            source = (
                connection.execute(
                    select(memory_revision_sources).where(
                        memory_revision_sources.c.id == ids["source"]
                    )
                )
                .mappings()
                .one()
            )
            vector = (
                connection.execute(
                    select(memory_embeddings).where(
                        memory_embeddings.c.id == ids["embedding"]
                    )
                )
                .mappings()
                .one()
            )
            assert subject["memory_generation"] == 1
            assert fact["assertion_schema_version"] == 1
            assert fact["current_revision_id"] == ids["revision"]
            assert revision["run_id"] == ids["run"] and revision["action_id"] is None
            assert source["authority_role"] == "user_assertion"
            assert list(vector["embedding"]) == [1.0, 0.0, 0.0]
    finally:
        command.upgrade(config, "head")
        engine.dispose()
