from __future__ import annotations

from typing import Any
from uuid import uuid4

from .contracts import CreateConversationRequest, CreateMemorySubjectRequest
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .presenters import (
    conversation_response,
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

    async def get_subject_memories(self, subject_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                repository = MemoryRepository(connection)
                subject = await repository.get_subject(subject_id)
                require_default_workspace(subject)
                facts = [
                    await _memory_fact_response(repository, fact)
                    for fact in await repository.list_facts(subject_id)
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
                row = await ConversationRepository(connection).create(
                    {
                        "id": str(uuid4()),
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "agent_definition_version_id": definition["id"],
                        "memory_subject_id": subject["id"],
                    }
                )
        return conversation_response(row)

    async def get_conversation_state(self, conversation_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                repository = ConversationRepository(connection)
                row = await repository.get(conversation_id)
                require_default_workspace(row)
                messages = await repository.list_messages(conversation_id)
        return {
            **conversation_response(row),
            "messages": [message_response(message) for message in messages],
        }


async def _memory_fact_response(
    repository: MemoryRepository, fact: dict[str, Any]
) -> dict[str, Any]:
    revisions = []
    for revision in await repository.list_revisions(str(fact["id"])):
        sources = await repository.list_revision_sources(str(revision["id"]))
        revisions.append(
            {
                "id": str(revision["id"]),
                "operation": revision["operation"],
                "fact_version": revision["fact_version"],
                "value": revision["value"],
                "run_id": str(revision["run_id"]),
                "evidence": [
                    {
                        "message_id": str(source["message_id"]),
                        "start_char": source["start_char"],
                        "end_char": source["end_char"],
                        "quote": source["quote"],
                        "message_sha256": source["message_sha256"],
                    }
                    for source in sources
                ],
                "created_at": revision["created_at"],
            }
        )
    return {
        "id": str(fact["id"]),
        "key": fact["normalized_key"],
        "fact_type": fact["fact_type"],
        "entity_id": str(fact["entity_id"]),
        "qualifier": fact["qualifier"],
        "value": fact["value"],
        "status": fact["status"],
        "version": fact["version"],
        "revisions": revisions,
        "updated_at": fact["updated_at"],
    }
