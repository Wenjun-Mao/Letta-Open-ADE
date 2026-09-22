from __future__ import annotations

import hashlib
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from ade_api.features.agent_runtime.memory_policy import prepare_memory_review
from ade_api.features.agent_runtime.memory_review import ReviewDecision
from ade_api.features.agent_runtime.persistence.metadata import (
    agent_definition_versions,
    agent_definitions,
    conversations,
    memory_entities,
    memory_subjects,
    messages,
    runs,
    workspaces,
)


@pytest.fixture
def m2_memory_lifecycle_support():
    return SimpleNamespace(
        prepare_review=prepare_review,
        record_turn=record_turn,
        seed_resources=seed_resources,
    )


async def seed_resources(connection: AsyncConnection) -> dict[str, str]:
    ids = {
        key: str(uuid4())
        for key in (
            "workspace",
            "definition",
            "definition_version",
            "subject_one",
            "subject_two",
            "conversation_one",
            "conversation_two",
            "other_conversation",
        )
    }
    await connection.execute(
        insert(workspaces).values(
            id=ids["workspace"],
            workspace_key=f"m2-storage-{ids['workspace']}",
            name="M2 storage integration test",
        )
    )
    await connection.execute(
        insert(agent_definitions).values(
            id=ids["definition"],
            workspace_id=ids["workspace"],
            definition_key="m2-storage-test",
            name="M2 storage test",
        )
    )
    await connection.execute(
        insert(agent_definition_versions).values(
            id=ids["definition_version"],
            workspace_id=ids["workspace"],
            agent_definition_id=ids["definition"],
            definition_key="m2-storage-test",
            version=1,
            name="M2 storage test",
            model_key="synthetic::chat",
            reviewer_model_key="synthetic::reviewer",
            embedding_model_key="synthetic::embedding",
            prompt_key="synthetic",
            prompt_sha256="0" * 64,
            prompt_content="",
            persona_key="synthetic",
            persona_sha256="1" * 64,
            persona_content="",
            tool_names=[],
            memory_policy_version="storage-test-v1",
            qualification_state="unqualified",
            deployment_snapshot=[],
        )
    )
    await connection.execute(
        insert(memory_subjects),
        [
            {
                "id": ids[key],
                "workspace_id": ids["workspace"],
                "external_key": key,
                "display_name": key,
            }
            for key in ("subject_one", "subject_two")
        ],
    )
    await connection.execute(
        insert(memory_entities),
        [
            {
                "id": ids[key],
                "workspace_id": ids["workspace"],
                "subject_id": ids[key],
                "kind": "subject",
            }
            for key in ("subject_one", "subject_two")
        ],
    )
    await connection.execute(
        insert(conversations),
        [
            {
                "id": ids[key],
                "workspace_id": ids["workspace"],
                "agent_definition_version_id": ids["definition_version"],
                "memory_subject_id": ids[subject_key],
                "title": key,
            }
            for key, subject_key in (
                ("conversation_one", "subject_one"),
                ("conversation_two", "subject_one"),
                ("other_conversation", "subject_two"),
            )
        ],
    )
    return ids


async def record_turn(
    connection: AsyncConnection,
    workspace_id: str,
    conversation_id: str,
    content: str,
    *,
    sequence: int = 1,
) -> dict[str, str]:
    run_id, message_id = str(uuid4()), str(uuid4())
    await connection.execute(
        insert(runs).values(
            id=run_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            idempotency_key=f"storage-{run_id}",
            request_hash=hashlib.sha256(run_id.encode()).hexdigest(),
            status="succeeded",
            qualification_state="unqualified",
            accepted_runtime_mode="development",
            timeout_seconds=180,
            retry_count=0,
            accepted_conversation_version=1,
            attempt_count=1,
        )
    )
    await connection.execute(
        insert(messages).values(
            id=message_id,
            workspace_id=workspace_id,
            conversation_id=conversation_id,
            sequence=sequence,
            role="user",
            content=content,
            content_sha256=hashlib.sha256(content.encode()).hexdigest(),
            run_id=run_id,
        )
    )
    return {"id": message_id, "run_id": run_id, "content": content}


def prepare_review(
    decision: ReviewDecision,
    *,
    subject_id: str,
    message: dict[str, str],
    entities: list[dict[str, str]],
    active_facts: list[dict[str, Any]] | None = None,
):
    return prepare_memory_review(
        decision=decision,
        subject_id=subject_id,
        current_user_message=message,
        active_facts=active_facts or [],
        entities=entities,
    )
