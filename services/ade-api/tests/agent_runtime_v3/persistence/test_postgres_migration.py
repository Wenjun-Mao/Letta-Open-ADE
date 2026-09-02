from __future__ import annotations

import asyncio
import os
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, delete, inspect, text

from ade_api.features.agent_runtime_v3.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime_v3.persistence.validation import (
    alembic_config,
    validate_database_at_head,
)
from ade_api.features.agent_runtime_v3.persistence.metadata import worker_instances
from ade_api.features.agent_runtime_v3.persistence.workers import (
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
                        "contract_version": "agent-runtime-v3-worker-v1",
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
