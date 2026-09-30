"""Independent terminal readback after worker finalization, in one RR snapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from .persistence.evaluation_observations import observation_binding, observe_snapshot
from .persistence.metadata import (
    agent_definition_versions,
    conversations,
    memory_revisions,
    memory_subjects,
    messages,
    run_attempts,
    runs,
)

if TYPE_CHECKING:
    from .natural_attempt_evidence import NaturalAttemptEvidence


async def terminal_readback(
    engine: AsyncEngine, evidence: NaturalAttemptEvidence
) -> tuple[Any, Any, list[str], list[str], int | None, dict[str, Any]]:
    async with engine.connect() as connection:
        await connection.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )

        async def one(statement):
            return (await connection.execute(statement)).mappings().one_or_none()

        async def ids(statement):
            return [
                str(value) for value in (await connection.execute(statement)).scalars()
            ]

        run = await one(select(runs).where(runs.c.id == evidence.run_id))
        attempt = await one(
            select(run_attempts).where(
                run_attempts.c.run_id == evidence.run_id,
                run_attempts.c.attempt_number == evidence.attempt,
            )
        )
        assistant_ids = await ids(
            select(messages.c.id).where(
                messages.c.run_id == evidence.run_id, messages.c.role == "assistant"
            )
        )
        revision_ids = await ids(
            select(memory_revisions.c.id).where(
                memory_revisions.c.run_id == evidence.run_id
            )
        )
        generation = None
        after = {"status": "unavailable"}
        if run is not None:
            conversation = await one(
                select(conversations).where(
                    conversations.c.id == run["conversation_id"]
                )
            )
            if conversation is not None:
                generation = await connection.scalar(
                    select(memory_subjects.c.memory_generation).where(
                        memory_subjects.c.id == conversation["memory_subject_id"]
                    )
                )
                if evidence.observation_binding:
                    # Optional observation failure cannot invalidate legacy receipts.
                    try:
                        async with connection.begin_nested():
                            definition = await one(
                                select(agent_definition_versions).where(
                                    agent_definition_versions.c.id
                                    == conversation["agent_definition_version_id"]
                                )
                            )
                            binding = observation_binding(run, conversation, definition)
                            if binding == evidence.observation_binding:
                                after = await observe_snapshot(
                                    connection, binding=binding
                                )
                            else:
                                after = {"status": "binding_mismatch"}
                    except Exception:
                        after = {"status": "unavailable"}
    return run, attempt, assistant_ids, revision_ids, generation, after
