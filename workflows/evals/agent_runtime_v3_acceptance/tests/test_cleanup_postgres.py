from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest
from psycopg.types.json import Jsonb

from workflows.evals.agent_runtime_v3_acceptance.cleanup import (
    CleanupScope,
    ScopedPostgresCleanup,
    _psycopg_url,
)


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL,
    reason="ADE_TEST_DATABASE_URL is required for PostgreSQL cleanup tests",
)


def test_scoped_cleanup_honors_the_complete_provenance_fk_graph(
    tmp_path: Path,
) -> None:
    assert DATABASE_URL is not None
    run_id = f"agent-runtime-v3-cleanup-{uuid4().hex[:8]}"
    definition_key = f"{run_id}-definition"
    subject_external_key = f"{run_id}-subject"
    unrelated_definition_key = f"{run_id}-unrelated-definition"
    ids = {name: uuid4() for name in _ID_NAMES}

    with psycopg.connect(_psycopg_url(DATABASE_URL)) as connection:
        with connection.cursor() as cursor:
            workspace_id = cursor.execute(
                "SELECT id FROM ade.workspaces WHERE workspace_key = 'default'"
            ).fetchone()[0]
            _insert_cleanup_graph(
                cursor,
                workspace_id=workspace_id,
                definition_key=definition_key,
                subject_external_key=subject_external_key,
                unrelated_definition_key=unrelated_definition_key,
                ids=ids,
            )

    manifest = ScopedPostgresCleanup(
        database_url=DATABASE_URL,
        output_dir=tmp_path,
    ).cleanup(
        CleanupScope(
            run_id=run_id,
            definition_keys=(definition_key,),
            subject_external_keys=(subject_external_key,),
        )
    )

    assert manifest.payload["status"] == "completed"
    with psycopg.connect(_psycopg_url(DATABASE_URL)) as connection:
        with connection.cursor() as cursor:
            assert (
                cursor.execute(
                    "SELECT count(*) FROM ade.agent_definitions WHERE definition_key = %s",
                    (definition_key,),
                ).fetchone()[0]
                == 0
            )
            assert (
                cursor.execute(
                    "SELECT count(*) FROM ade.agent_definition_versions WHERE definition_key = %s",
                    (definition_key,),
                ).fetchone()[0]
                == 0
            )
            assert (
                cursor.execute(
                    "SELECT count(*) FROM ade.memory_subjects WHERE external_key = %s",
                    (subject_external_key,),
                ).fetchone()[0]
                == 0
            )
            assert (
                cursor.execute(
                    "SELECT count(*) FROM ade.agent_definitions WHERE definition_key = %s",
                    (unrelated_definition_key,),
                ).fetchone()[0]
                == 1
            )
            assert (
                cursor.execute(
                    "SELECT count(*) FROM ade.agent_definition_versions WHERE definition_key = %s",
                    (unrelated_definition_key,),
                ).fetchone()[0]
                == 1
            )


_ID_NAMES = (
    "definition_root",
    "definition_version",
    "unrelated_definition_root",
    "unrelated_definition_version",
    "subject",
    "entity",
    "conversation",
    "run",
    "message",
    "fact",
    "revision",
    "source",
)


def _insert_cleanup_graph(
    cursor: psycopg.Cursor,
    *,
    workspace_id: object,
    definition_key: str,
    subject_external_key: str,
    unrelated_definition_key: str,
    ids: dict[str, object],
) -> None:
    _insert_definition(
        cursor,
        workspace_id=workspace_id,
        definition_id=ids["definition_root"],
        version_id=ids["definition_version"],
        definition_key=definition_key,
        purpose="development",
    )
    _insert_definition(
        cursor,
        workspace_id=workspace_id,
        definition_id=ids["unrelated_definition_root"],
        version_id=ids["unrelated_definition_version"],
        definition_key=unrelated_definition_key,
        purpose="agent_studio",
    )
    cursor.execute(
        """
        INSERT INTO ade.memory_subjects (
            id, workspace_id, external_key, display_name, purpose
        ) VALUES (%s, %s, %s, 'cleanup test', 'development')
        """,
        (ids["subject"], workspace_id, subject_external_key),
    )
    cursor.execute(
        "INSERT INTO ade.memory_entities (id, workspace_id, subject_id, kind, label) VALUES (%s, %s, %s, 'person', 'user')",
        (ids["entity"], workspace_id, ids["subject"]),
    )
    cursor.execute(
        """
        INSERT INTO ade.conversations (
            id, workspace_id, agent_definition_version_id, memory_subject_id, title,
            purpose
        ) VALUES (%s, %s, %s, %s, 'cleanup test', 'development')
        """,
        (
            ids["conversation"],
            workspace_id,
            ids["definition_version"],
            ids["subject"],
        ),
    )
    cursor.execute(
        """
        INSERT INTO ade.runs (
            id, workspace_id, conversation_id, idempotency_key, request_hash,
            status, qualification_state, timeout_seconds, retry_count,
            accepted_conversation_version, attempt_count
        ) VALUES (%s, %s, %s, 'cleanup-test', %s, 'succeeded', 'unqualified', 180, 0, 1, 1)
        """,
        (ids["run"], workspace_id, ids["conversation"], "c" * 64),
    )
    cursor.execute(
        """
        INSERT INTO ade.messages (
            id, workspace_id, conversation_id, sequence, role, content,
            content_sha256, run_id
        ) VALUES (%s, %s, %s, 1, 'user', 'remember this', %s, %s)
        """,
        (
            ids["message"],
            workspace_id,
            ids["conversation"],
            "d" * 64,
            ids["run"],
        ),
    )
    cursor.execute(
        """
        INSERT INTO ade.memory_facts (
            id, workspace_id, subject_id, entity_id, normalized_key,
            fact_type, value, status, version
        ) VALUES (%s, %s, %s, %s, 'person.name', 'person.name', %s, 'active', 1)
        """,
        (
            ids["fact"],
            workspace_id,
            ids["subject"],
            ids["entity"],
            Jsonb("Alice"),
        ),
    )
    cursor.execute(
        """
        INSERT INTO ade.memory_revisions (
            id, fact_id, workspace_id, subject_id, operation, fact_version,
            value, run_id
        ) VALUES (%s, %s, %s, %s, 'add', 1, %s, %s)
        """,
        (
            ids["revision"],
            ids["fact"],
            workspace_id,
            ids["subject"],
            Jsonb("Alice"),
            ids["run"],
        ),
    )
    cursor.execute(
        "UPDATE ade.memory_facts SET current_revision_id = %s WHERE id = %s",
        (ids["revision"], ids["fact"]),
    )
    cursor.execute(
        """
        INSERT INTO ade.memory_revision_sources (
            id, revision_id, message_id, start_char, end_char, quote,
            message_sha256
        ) VALUES (%s, %s, %s, 0, 8, 'remember', %s)
        """,
        (ids["source"], ids["revision"], ids["message"], "d" * 64),
    )


def _insert_definition(
    cursor: psycopg.Cursor,
    *,
    workspace_id: object,
    definition_id: object,
    version_id: object,
    definition_key: str,
    purpose: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO ade.agent_definitions (
            id, workspace_id, definition_key, name, purpose
        ) VALUES (%s, %s, %s, 'cleanup test', %s)
        """,
        (definition_id, workspace_id, definition_key, purpose),
    )
    cursor.execute(
        """
        INSERT INTO ade.agent_definition_versions (
            id, workspace_id, agent_definition_id, definition_key, version, name,
            purpose, model_key,
            reviewer_model_key, embedding_model_key, prompt_key, prompt_sha256,
            prompt_content, persona_key, persona_sha256, persona_content,
            tool_names, memory_policy_version, qualification_state,
            deployment_snapshot
        ) VALUES (
            %s, %s, %s, %s, 1, 'cleanup test', %s, 'chat', 'reviewer',
            'embedding', 'prompt', %s, 'prompt', 'persona', %s, 'persona', %s,
            'v1', 'unqualified', %s
        )
        """,
        (
            version_id,
            workspace_id,
            definition_id,
            definition_key,
            purpose,
            "a" * 64,
            "b" * 64,
            Jsonb([]),
            Jsonb({}),
        ),
    )
    cursor.execute(
        "UPDATE ade.agent_definitions SET current_version_id = %s WHERE id = %s",
        (version_id, definition_id),
    )
