"""Coherent subject-memory reads for one accepted runtime turn."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from .embeddings import NATURAL_RETRIEVAL_POLICY_VERSION, RETRIEVAL_POLICY_VERSION
from .errors import RuntimeValidationError
from .persistence.base import OptimisticLockError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .persistence.history import read_history_corpus
from .persistence.evaluation_observations import observation_binding, observe_snapshot
from .natural_attempt_evidence import capture_allowed
from .natural_context import NATURAL_POLICY_BINDINGS


async def load_turn_state(
    engine: AsyncEngine,
    run: dict[str, Any],
    *,
    include_history: bool = False,
    capture_database_url: str | None = None,
    runtime_mode: str = "",
) -> dict[str, Any]:
    async with engine.connect() as connection:
        await connection.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        conversations = ConversationRepository(connection)
        memory = MemoryRepository(connection)
        conversation = await conversations.get(str(run["conversation_id"]))
        definition = await DefinitionVersionRepository(connection).get(
            str(conversation["agent_definition_version_id"])
        )
        subject_id = str(conversation["memory_subject_id"])
        subject = await memory.get_subject(subject_id)
        if int(subject["memory_generation"]) != int(run["accepted_memory_generation"]):
            raise OptimisticLockError("subject memory changed after turn acceptance")
        state = {
            "conversation": conversation,
            "definition": definition,
            "subject": subject,
            "messages": await conversations.list_messages(str(conversation["id"])),
            "summary": await conversations.latest_summary(str(conversation["id"])),
            "active_facts": await memory.list_active_facts(subject_id),
            "facts": await memory.list_facts(subject_id),
            "entities": await memory.list_entities(subject_id),
        }
        observe = (
            capture_database_url is not None
            and definition["memory_policy_version"] in NATURAL_POLICY_BINDINGS
            and capture_allowed(
                database_url=capture_database_url,
                runtime_mode=runtime_mode,
                purpose=str(conversation["purpose"]),
            )
        )
        if observe:
            binding = observation_binding(run, conversation, definition)
            state["observation_binding"] = binding
            state["persistence_before"] = await observe_snapshot(
                connection, binding=binding
            )
        if include_history:
            try:
                async with connection.begin_nested():
                    state["history"] = await read_history_corpus(
                        connection,
                        workspace_id=str(conversation["workspace_id"]),
                        subject_id=subject_id,
                        purpose=str(conversation["purpose"]),
                        definition_root_id=str(definition["agent_definition_id"]),
                        current_run_id=str(run["id"]),
                        include_observations=observe,
                    )
            except SQLAlchemyError:
                # The mandatory RR snapshot remains intact on optional reader
                # failure. Integrity errors from the reader are never softened.
                state["history"] = {"exchanges": [], "unavailable": True}
        return state


def current_user_message(messages: list[dict[str, Any]], run_id: str) -> dict[str, Any]:
    matches = [
        message
        for message in messages
        if message["role"] == "user" and str(message.get("run_id")) == run_id
    ]
    if len(matches) != 1:
        raise RuntimeValidationError(
            "Accepted run must reference exactly one immutable user message"
        )
    return matches[0]


async def search_turn_memory(
    engine: AsyncEngine,
    *,
    subject_id: str,
    query_vector: list[float],
    fingerprint: str,
    limit: int,
    maximum_distance: float | None,
    accepted_memory_generation: int,
    natural: bool = False,
) -> list[dict[str, Any]]:
    async with engine.connect() as connection:
        await connection.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        )
        memory = MemoryRepository(connection)
        subject = await memory.get_subject(subject_id)
        if int(subject["memory_generation"]) != accepted_memory_generation:
            raise OptimisticLockError("subject memory changed before retrieval")
        if natural:
            return await memory.search_current_lifecycle_facts(
                subject_id=subject_id,
                query_embedding=query_vector,
                model_fingerprint=fingerprint,
                legacy_policy_version=RETRIEVAL_POLICY_VERSION,
                lifecycle_policy_version=NATURAL_RETRIEVAL_POLICY_VERSION,
                limit=limit,
                maximum_distance=maximum_distance,
            )
        return await memory.search_active_facts(
            subject_id=subject_id,
            query_embedding=query_vector,
            model_fingerprint=fingerprint,
            retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
            limit=limit,
            maximum_distance=maximum_distance,
        )
