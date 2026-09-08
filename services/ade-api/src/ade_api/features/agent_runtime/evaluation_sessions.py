"""Focused lifecycle for isolated ADE evaluation sessions."""

from __future__ import annotations

from typing import Any

from sqlalchemy import delete, func, or_, select, update

from .agent_studio_sessions import (
    EVALUATION_PURPOSE,
    PurposeSessionService,
    session_identity,
)
from .contracts import (
    CreateAgentStudioSessionRequest,
    CreateEvaluationSessionRequest,
)
from .database_boundary import RuntimeDatabase
from .definition_service import DefinitionService
from .errors import RuntimeConflict, RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import (
    AgentDefinitionRepository,
    DefinitionVersionRepository,
)
from .persistence.base import NotFoundError
from .persistence.memory import MemoryRepository
from .persistence.metadata import (
    agent_definition_versions,
    agent_definitions,
    conversation_leases,
    conversation_summaries,
    conversations,
    memory_embeddings,
    memory_entities,
    memory_facts,
    memory_revision_predecessors,
    memory_revision_sources,
    memory_revisions,
    memory_subjects,
    messages,
    outbox,
    run_attempts,
    run_events,
    runs,
    summary_sources,
)
from .persistence.runs import RunRepository
from .resource_service import ResourceService


class EvaluationSessionService:
    """Expose the narrow evaluation boundary over purpose-owned resources."""

    def __init__(
        self,
        *,
        database: RuntimeDatabase,
        definitions: DefinitionService,
        resources: ResourceService,
    ) -> None:
        self.database = database
        self.resources = resources
        self.sessions = PurposeSessionService(
            database=database,
            definitions=definitions,
            purpose=EVALUATION_PURPOSE,
            session_namespace="evaluation",
            allowed_tool_names=frozenset({"search_memory", "get_weather"}),
        )

    async def create(self, request: CreateEvaluationSessionRequest) -> dict[str, Any]:
        identity = session_identity(request.idempotency_key, namespace="evaluation")
        session_request = CreateAgentStudioSessionRequest(
            idempotency_key=request.idempotency_key,
            title=request.title,
            agent_definition_id=request.agent_definition_id,
            new_definition=(
                None
                if request.agent_definition_id is not None
                else request.definition_request(
                    definition_key=f"evaluation_{identity.session_id.replace('-', '')}"
                )
            ),
            memory_subject_id=request.memory_subject_id,
            new_subject=(
                None
                if request.memory_subject_id is not None
                else request.subject_request(
                    external_key=f"evaluation:{identity.session_id}"
                )
            ),
        )
        return await self.sessions.create(session_request)

    async def get_state(
        self,
        conversation_id: str,
        *,
        message_limit: int,
        before_sequence: int | None,
    ) -> dict[str, Any]:
        conversation = await self.resources.get_conversation_state(
            conversation_id,
            required_purpose=EVALUATION_PURPOSE,
            message_limit=message_limit,
            before_sequence=before_sequence,
        )
        subject_id = str(conversation["memory_subject_id"])
        memories = await self.resources.get_subject_memories(
            subject_id, required_purpose=EVALUATION_PURPOSE
        )
        session = await self.sessions.get(conversation_id)
        return {
            "conversation": conversation,
            "memory_subject": session["memory_subject"],
            "memories": memories,
            "latest_run": session["latest_run"],
        }

    async def purge(self, conversation_id: str) -> dict[str, Any]:
        """Delete a completed evaluation graph, preserving shared fixtures."""

        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = ConversationRepository(connection)
                existing = await repository.find(conversation_id)
                if existing is None:
                    return {
                        "conversation_id": conversation_id,
                        "already_purged": True,
                        "deleted_counts": {},
                    }
                try:
                    conversation = await repository.get_for_update(conversation_id)
                except NotFoundError:
                    return {
                        "conversation_id": conversation_id,
                        "already_purged": True,
                        "deleted_counts": {},
                    }
                _require_evaluation(conversation, "conversation")
                if await RunRepository(connection).active_for_conversation(
                    conversation_id
                ):
                    raise RuntimeConflict(
                        "an evaluation session with an active run cannot be purged"
                    )

                definition = await DefinitionVersionRepository(connection).get(
                    str(conversation["agent_definition_version_id"])
                )
                root = await AgentDefinitionRepository(connection).get_for_update(
                    str(definition["agent_definition_id"])
                )
                subject = await MemoryRepository(connection).lock_subject(
                    str(conversation["memory_subject_id"])
                )
                _require_evaluation(definition, "agent definition version")
                _require_evaluation(root, "agent definition")
                _require_evaluation(subject, "memory subject")

                counts = await _delete_conversation_graph(connection, conversation_id)
                await _delete_subject_if_orphan(connection, str(subject["id"]), counts)
                await _delete_definition_if_orphan(
                    connection, str(definition["agent_definition_id"]), counts
                )
        return {
            "conversation_id": conversation_id,
            "already_purged": False,
            "deleted_counts": counts,
        }


def _require_evaluation(row: dict[str, Any], label: str) -> None:
    if str(row.get("purpose", "development")) != EVALUATION_PURPOSE:
        raise RuntimeValidationError(f"{label} is not owned by evaluation")


async def _delete_conversation_graph(
    connection: Any, conversation_id: str
) -> dict[str, int]:
    conversation_ids = select(conversations.c.id).where(
        conversations.c.id == conversation_id
    )
    run_ids = select(runs.c.id).where(runs.c.conversation_id.in_(conversation_ids))
    summary_ids = select(conversation_summaries.c.id).where(
        conversation_summaries.c.conversation_id.in_(conversation_ids)
    )
    counts: dict[str, int] = {}

    async def remove(name: str, statement: Any) -> None:
        result = await connection.execute(statement)
        counts[name] = max(0, int(result.rowcount or 0))

    await remove("outbox", delete(outbox).where(outbox.c.run_id.in_(run_ids)))
    await remove(
        "summary_sources",
        delete(summary_sources).where(summary_sources.c.summary_id.in_(summary_ids)),
    )
    await remove(
        "conversation_summaries",
        delete(conversation_summaries).where(
            conversation_summaries.c.id.in_(summary_ids)
        ),
    )
    await remove(
        "conversation_leases",
        delete(conversation_leases).where(
            conversation_leases.c.conversation_id.in_(conversation_ids)
        ),
    )
    await remove(
        "messages",
        delete(messages).where(messages.c.conversation_id.in_(conversation_ids)),
    )
    await remove(
        "run_events", delete(run_events).where(run_events.c.run_id.in_(run_ids))
    )
    await remove(
        "run_attempts", delete(run_attempts).where(run_attempts.c.run_id.in_(run_ids))
    )
    await remove("runs", delete(runs).where(runs.c.id.in_(run_ids)))
    await remove(
        "conversations",
        delete(conversations).where(conversations.c.id.in_(conversation_ids)),
    )
    return counts


async def _delete_subject_if_orphan(
    connection: Any, subject_id: str, counts: dict[str, int]
) -> None:
    references = int(
        await connection.scalar(
            select(func.count())
            .select_from(conversations)
            .where(conversations.c.memory_subject_id == subject_id)
        )
        or 0
    )
    if references:
        return
    subject_ids = select(memory_subjects.c.id).where(memory_subjects.c.id == subject_id)
    fact_ids = select(memory_facts.c.id).where(
        memory_facts.c.subject_id.in_(subject_ids)
    )
    revision_ids = select(memory_revisions.c.id).where(
        memory_revisions.c.subject_id.in_(subject_ids)
    )

    async def remove(name: str, statement: Any) -> None:
        result = await connection.execute(statement)
        counts[name] = counts.get(name, 0) + max(0, int(result.rowcount or 0))

    await remove(
        "memory_revision_sources",
        delete(memory_revision_sources).where(
            memory_revision_sources.c.revision_id.in_(revision_ids)
        ),
    )
    await remove(
        "memory_revision_predecessors",
        delete(memory_revision_predecessors).where(
            or_(
                memory_revision_predecessors.c.revision_id.in_(revision_ids),
                memory_revision_predecessors.c.predecessor_revision_id.in_(
                    revision_ids
                ),
            )
        ),
    )
    await remove(
        "memory_embeddings",
        delete(memory_embeddings).where(
            memory_embeddings.c.subject_id.in_(subject_ids)
        ),
    )
    await connection.execute(
        update(memory_facts)
        .where(memory_facts.c.id.in_(fact_ids))
        .values(current_revision_id=None)
    )
    await remove(
        "memory_revisions",
        delete(memory_revisions).where(memory_revisions.c.id.in_(revision_ids)),
    )
    await remove(
        "memory_facts", delete(memory_facts).where(memory_facts.c.id.in_(fact_ids))
    )
    await remove(
        "memory_entities",
        delete(memory_entities).where(memory_entities.c.subject_id.in_(subject_ids)),
    )
    await remove(
        "memory_subjects",
        delete(memory_subjects).where(memory_subjects.c.id.in_(subject_ids)),
    )


async def _delete_definition_if_orphan(
    connection: Any, definition_id: str, counts: dict[str, int]
) -> None:
    version_ids = select(agent_definition_versions.c.id).where(
        agent_definition_versions.c.agent_definition_id == definition_id
    )
    references = int(
        await connection.scalar(
            select(func.count())
            .select_from(conversations)
            .where(conversations.c.agent_definition_version_id.in_(version_ids))
        )
        or 0
    )
    if references:
        return

    async def remove(name: str, statement: Any) -> None:
        result = await connection.execute(statement)
        counts[name] = counts.get(name, 0) + max(0, int(result.rowcount or 0))

    await connection.execute(
        update(agent_definitions)
        .where(agent_definitions.c.id == definition_id)
        .values(current_version_id=None)
    )
    await remove(
        "agent_definition_versions",
        delete(agent_definition_versions).where(
            agent_definition_versions.c.agent_definition_id == definition_id
        ),
    )
    await remove(
        "agent_definitions",
        delete(agent_definitions).where(agent_definitions.c.id == definition_id),
    )
