from __future__ import annotations

from typing import Any
from uuid import uuid4

from .contracts import CreateConversationRequest, CreateMemorySubjectRequest
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .errors import RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .presenters import (
    conversation_summary_response,
    conversation_response,
    memory_fact_response,
    memory_revision_response,
    message_response,
    subject_response,
)


class ResourceService:
    def __init__(self, database: RuntimeDatabase) -> None:
        self.database = database

    async def create_subject(
        self, request: CreateMemorySubjectRequest
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        subject_id = str(uuid4())
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                repository = MemoryRepository(connection)
                row = await repository.create_subject(
                    {
                        "id": subject_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "external_key": request.external_key,
                        "display_name": request.display_name,
                        "purpose": "development",
                    }
                )
                await repository.create_entity(
                    {
                        "id": subject_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "subject_id": subject_id,
                        "kind": "subject",
                        "label": request.display_name,
                    }
                )
        return subject_response(row)

    async def get_subject(self, subject_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                row = await MemoryRepository(connection).get_subject(subject_id)
                require_default_workspace(row)
        return subject_response(row)

    async def get_subject_memories(
        self, subject_id: str, *, required_purpose: str | None = None
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                repository = MemoryRepository(connection)
                subject = await repository.get_subject(subject_id)
                require_default_workspace(subject)
                _require_purpose(subject, required_purpose, "memory subject")
                facts = [
                    await _memory_fact_response(repository, fact)
                    for fact in await repository.list_facts_with_entities(subject_id)
                ]
        return {"subject_id": subject_id, "facts": facts}

    async def create_conversation(
        self, request: CreateConversationRequest
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                definition = await DefinitionVersionRepository(connection).get(
                    request.agent_definition_id
                )
                subject = await MemoryRepository(connection).get_subject(
                    request.memory_subject_id
                )
                require_default_workspace(definition)
                require_default_workspace(subject)
                if definition.get("purpose", "development") != subject.get(
                    "purpose", "development"
                ):
                    raise RuntimeValidationError(
                        "definition and memory subject must share one runtime purpose"
                    )
                row = await ConversationRepository(connection).create(
                    {
                        "id": str(uuid4()),
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "agent_definition_version_id": definition["id"],
                        "memory_subject_id": subject["id"],
                        "title": request.title,
                        "purpose": definition.get("purpose", "development"),
                    }
                )
        return conversation_response(row)

    async def get_conversation_state(
        self,
        conversation_id: str,
        *,
        required_purpose: str | None = None,
        message_limit: int = 200,
        before_sequence: int | None = None,
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                repository = ConversationRepository(connection)
                row = await repository.get(conversation_id)
                require_default_workspace(row)
                _require_purpose(row, required_purpose, "conversation")
                message_total, messages = await repository.list_message_page(
                    conversation_id,
                    limit=message_limit,
                    before_sequence=before_sequence,
                )
                summary = await repository.latest_summary(conversation_id)
                summary_response = (
                    conversation_summary_response(
                        summary,
                        source_message_ids=await repository.list_summary_source_message_ids(
                            str(summary["id"])
                        ),
                    )
                    if summary is not None
                    else None
                )
        first_sequence = int(messages[0]["sequence"]) if messages else None
        return {
            **conversation_response(row),
            "messages": [message_response(message) for message in messages],
            "message_total": message_total,
            "messages_truncated": len(messages) < message_total,
            "next_before_sequence": (
                first_sequence
                if first_sequence is not None and first_sequence > 1
                else None
            ),
            "summary": summary_response,
        }


def _require_purpose(
    row: dict[str, Any], required_purpose: str | None, label: str
) -> None:
    if required_purpose is None:
        return
    if str(row.get("purpose", "development")) != required_purpose:
        raise RuntimeValidationError(f"{label} is not owned by {required_purpose}")


async def _memory_fact_response(
    repository: MemoryRepository, fact: dict[str, Any]
) -> dict[str, Any]:
    revisions = []
    for revision in await repository.list_revisions(str(fact["id"])):
        sources = await repository.list_revision_sources(str(revision["id"]))
        revisions.append(
            memory_revision_response(
                revision,
                predecessor_revision_ids=await repository.list_revision_predecessor_ids(
                    str(revision["id"])
                ),
                evidence=[
                    {
                        "message_id": str(source["message_id"]),
                        "start_char": source["start_char"],
                        "end_char": source["end_char"],
                        "quote": source["quote"],
                        "message_sha256": source["message_sha256"],
                    }
                    for source in sources
                ],
            )
        )
    return memory_fact_response(fact, revisions=revisions)
