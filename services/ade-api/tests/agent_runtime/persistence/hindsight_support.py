"""Controlled SQL fixtures, never a product-establishment or provider test."""

from dataclasses import dataclass
import hashlib
import os
from uuid import uuid4

from sqlalchemy import insert
from sqlalchemy.engine import make_url

from ade_api.integrations.hindsight_sources import (
    MemoryRelationship,
    MemorySourceMessage,
)
from ade_api.features.agent_runtime.persistence.conversations import (
    ConversationRepository,
)
from ade_api.features.agent_runtime.persistence.database import (
    create_persistence_engine,
)
from ade_api.features.agent_runtime.persistence.definitions import (
    DefinitionVersionRepository,
)
from ade_api.features.agent_runtime.persistence.metadata import (
    memory_subjects,
    workspaces,
)
from ade_api.features.agent_runtime.persistence.runs import RunRepository


DATABASE_URL = os.getenv("ADE_TEST_DATABASE_URL", "")


def engine():
    url = make_url(DATABASE_URL)
    if (
        url.host not in {"127.0.0.1", "localhost"}
        or url.username != "ade_hindsight_app"
        or not (url.database or "").startswith("ade_hindsight_test")
    ):
        raise ValueError(
            "Hindsight SQL tests require their disposable loopback application-role database"
        )
    return create_persistence_engine(DATABASE_URL)


@dataclass(frozen=True)
class Scope:
    relationship: MemoryRelationship
    definition: dict
    conversation: dict


async def scope(
    connection, *, workspace_id=None, subject_id=None, root=None, deployments=None
):
    if workspace_id is None:
        workspace_id = str(uuid4())
        await connection.execute(
            insert(workspaces).values(
                id=workspace_id,
                workspace_key="hindsight-sql-" + uuid4().hex,
                name="Controlled SQL fixture",
                memory_backend="hindsight",
            )
        )
    if subject_id is None:
        subject_id = str(uuid4())
        await connection.execute(
            insert(memory_subjects).values(
                id=subject_id,
                workspace_id=workspace_id,
                external_key=uuid4().hex,
            )
        )
    versions = DefinitionVersionRepository(connection)
    definition = await versions.create_next(
        workspace_id,
        {
            "id": str(uuid4()),
            "definition_key": root["definition_key"] if root else "sql_" + uuid4().hex,
            "name": "Controlled character",
            "model_key": "fake::character",
            "compaction_model_key": next(
                (
                    item["route_alias"]
                    for item in deployments or []
                    if item["role"] == "compaction"
                ),
                "fake::compaction",
            ),
            "prompt_key": "fixture",
            "prompt_content": "original instructions",
            "prompt_sha256": "a" * 64,
            "persona_key": "fixture",
            "persona_content": "original persona",
            "persona_sha256": "b" * 64,
            "tool_names": ["search_memory"],
            "memory_policy_version": "hindsight-message-v1",
            "qualification_state": "unqualified",
            "deployment_snapshot": deployments or [],
            **({"agent_definition_id": root["agent_definition_id"]} if root else {}),
        },
    )
    conversation = await ConversationRepository(connection).create(
        {
            "id": str(uuid4()),
            "workspace_id": workspace_id,
            "agent_definition_version_id": definition["id"],
            "memory_subject_id": subject_id,
        }
    )
    return Scope(
        MemoryRelationship(
            workspace_id, subject_id, str(definition["agent_definition_id"])
        ),
        definition,
        conversation,
    )


async def message(
    connection, owner, *, content="Original source", role="user", run_id=None
):
    if run_id is None:
        run_id = str(uuid4())
        await RunRepository(connection).accept(
            {
                "id": run_id,
                "workspace_id": owner.relationship.workspace_id,
                "conversation_id": owner.conversation["id"],
                "idempotency_key": uuid4().hex,
                "request_hash": hashlib.sha256(content.encode()).hexdigest(),
                "status": "pending",
                "qualification_state": "unqualified",
                "accepted_runtime_mode": "development",
                "timeout_seconds": 180,
                "retry_count": 0,
                "accepted_conversation_version": 1,
                "accepted_memory_generation": None,
            }
        )
    row = await ConversationRepository(connection).append_message(
        {
            "id": str(uuid4()),
            "workspace_id": owner.relationship.workspace_id,
            "conversation_id": owner.conversation["id"],
            "role": role,
            "content": content,
            "content_sha256": hashlib.sha256(content.encode()).hexdigest(),
            "run_id": run_id,
        }
    )
    return MemorySourceMessage(
        message_id=str(row["id"]),
        conversation_id=str(owner.conversation["id"]),
        definition_version_id=str(owner.definition["id"]),
        relationship=owner.relationship,
        sequence=int(row["sequence"]),
        role=role,
        content=content,
        occurred_at=row["created_at"],
        status="accepted" if role == "user" else "committed",
    ), run_id
