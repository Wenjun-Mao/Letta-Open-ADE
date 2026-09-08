"""Transactional fresh-start boundary for ADE-owned Agent Studio state."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import and_, delete, func, insert, or_, select, update

from .agent_studio_sessions import AGENT_STUDIO_PURPOSE
from .contracts import AgentStudioResetRequest
from .database_boundary import DEFAULT_WORKSPACE_ID, RuntimeDatabase
from .errors import IdempotencyConflict, RuntimeConflict
from .persistence.metadata import (
    agent_definition_versions,
    agent_definitions,
    agent_studio_reset_receipts,
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
    workspaces,
)


class AgentStudioResetService:
    def __init__(self, database: RuntimeDatabase) -> None:
        self.database = database

    async def reset(self, request: AgentStudioResetRequest) -> dict[str, Any]:
        await self.database.ensure_ready()
        request_sha256 = _request_sha256(request)
        receipt_id = str(
            uuid5(
                NAMESPACE_URL,
                f"ade://agent-studio/reset/{DEFAULT_WORKSPACE_ID}/{request.idempotency_key}",
            )
        )
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                workspace = (
                    (
                        await connection.execute(
                            select(workspaces)
                            .where(workspaces.c.id == DEFAULT_WORKSPACE_ID)
                            .with_for_update()
                        )
                    )
                    .mappings()
                    .one()
                )
                existing = (
                    (
                        await connection.execute(
                            select(agent_studio_reset_receipts).where(
                                and_(
                                    agent_studio_reset_receipts.c.workspace_id
                                    == DEFAULT_WORKSPACE_ID,
                                    agent_studio_reset_receipts.c.idempotency_key
                                    == request.idempotency_key,
                                )
                            )
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is not None:
                    if existing["request_sha256"] != request_sha256:
                        raise IdempotencyConflict(
                            "reset idempotency key is bound to another request"
                        )
                    return _receipt_response(dict(existing), replayed=True)

                await _require_safe_reset(connection)
                deleted_counts = await _delete_agent_studio_state(connection)
                reset_generation = int(workspace["state_generation"]) + 1
                await connection.execute(
                    update(workspaces)
                    .where(workspaces.c.id == DEFAULT_WORKSPACE_ID)
                    .values(state_generation=reset_generation, updated_at=func.now())
                )
                receipt = (
                    (
                        await connection.execute(
                            insert(agent_studio_reset_receipts)
                            .values(
                                id=receipt_id,
                                workspace_id=DEFAULT_WORKSPACE_ID,
                                idempotency_key=request.idempotency_key,
                                request_sha256=request_sha256,
                                reset_generation=reset_generation,
                                deleted_counts=deleted_counts,
                            )
                            .returning(*agent_studio_reset_receipts.c)
                        )
                    )
                    .mappings()
                    .one()
                )
        return _receipt_response(dict(receipt), replayed=False)


async def _require_safe_reset(connection: Any) -> None:
    product_conversations = select(conversations.c.id).where(
        conversations.c.purpose == AGENT_STUDIO_PURPOSE
    )
    active_runs = int(
        await connection.scalar(
            select(func.count())
            .select_from(runs)
            .where(
                and_(
                    runs.c.conversation_id.in_(product_conversations),
                    runs.c.status.in_(("pending", "running")),
                )
            )
        )
        or 0
    )
    if active_runs:
        raise RuntimeConflict(
            "Agent Studio cannot be reset while a turn is pending or running"
        )

    mismatch_count = int(
        await connection.scalar(
            select(func.count())
            .select_from(
                conversations.join(
                    agent_definition_versions,
                    conversations.c.agent_definition_version_id
                    == agent_definition_versions.c.id,
                ).join(
                    memory_subjects,
                    conversations.c.memory_subject_id == memory_subjects.c.id,
                )
            )
            .where(
                and_(
                    or_(
                        conversations.c.purpose == AGENT_STUDIO_PURPOSE,
                        agent_definition_versions.c.purpose == AGENT_STUDIO_PURPOSE,
                        memory_subjects.c.purpose == AGENT_STUDIO_PURPOSE,
                    ),
                    or_(
                        conversations.c.purpose != agent_definition_versions.c.purpose,
                        conversations.c.purpose != memory_subjects.c.purpose,
                    ),
                )
            )
        )
        or 0
    )
    if mismatch_count:
        raise RuntimeConflict(
            "Agent Studio reset found cross-purpose references and refused deletion"
        )


async def _delete_agent_studio_state(connection: Any) -> dict[str, int]:
    conversation_ids = select(conversations.c.id).where(
        conversations.c.purpose == AGENT_STUDIO_PURPOSE
    )
    run_ids = select(runs.c.id).where(runs.c.conversation_id.in_(conversation_ids))
    subject_ids = select(memory_subjects.c.id).where(
        memory_subjects.c.purpose == AGENT_STUDIO_PURPOSE
    )
    fact_ids = select(memory_facts.c.id).where(
        memory_facts.c.subject_id.in_(subject_ids)
    )
    revision_ids = select(memory_revisions.c.id).where(
        memory_revisions.c.subject_id.in_(subject_ids)
    )
    summary_ids = select(conversation_summaries.c.id).where(
        conversation_summaries.c.conversation_id.in_(conversation_ids)
    )
    definition_root_ids = select(agent_definitions.c.id).where(
        agent_definitions.c.purpose == AGENT_STUDIO_PURPOSE
    )

    counts: dict[str, int] = {}

    async def remove(name: str, statement: Any) -> None:
        result = await connection.execute(statement)
        counts[name] = max(0, int(result.rowcount or 0))

    await remove("outbox", delete(outbox).where(outbox.c.run_id.in_(run_ids)))
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
    await remove(
        "summary_sources",
        delete(summary_sources).where(summary_sources.c.summary_id.in_(summary_ids)),
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
    await remove(
        "memory_entities",
        delete(memory_entities).where(memory_entities.c.subject_id.in_(subject_ids)),
    )
    await remove(
        "memory_subjects",
        delete(memory_subjects).where(memory_subjects.c.id.in_(subject_ids)),
    )
    await connection.execute(
        update(agent_definitions)
        .where(agent_definitions.c.id.in_(definition_root_ids))
        .values(current_version_id=None)
    )
    await remove(
        "agent_definition_versions",
        delete(agent_definition_versions).where(
            agent_definition_versions.c.agent_definition_id.in_(definition_root_ids)
        ),
    )
    await remove(
        "agent_definitions",
        delete(agent_definitions).where(
            agent_definitions.c.id.in_(definition_root_ids)
        ),
    )
    return counts


def _request_sha256(request: AgentStudioResetRequest) -> str:
    payload = {"confirmation": request.confirmation}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _receipt_response(row: dict[str, Any], *, replayed: bool) -> dict[str, Any]:
    return {
        "receipt_id": str(row["id"]),
        "idempotent_replay": replayed,
        "reset_generation": int(row["reset_generation"]),
        "deleted_counts": dict(row["deleted_counts"]),
        "reset_at": row["reset_at"],
    }
