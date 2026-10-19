"""ADE-owned subjects and original conversation state, independent of remote reads."""

from uuid import uuid4

from .errors import RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .persistence.memory_relationships import MemoryRelationshipRepository
from .presenters import (
    conversation_response,
    conversation_summary_response,
    message_response,
    subject_response,
)
from .turn_sources import relationship_for, require_hindsight_definition


class ResourceService:
    def __init__(self, database):
        self.database = database

    async def create_subject(self, request):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                row = await MemoryRepository(connection).create_subject(
                    {
                        "id": str(uuid4()),
                        "workspace_id": self.database.workspace_id,
                        "external_key": request.external_key,
                        "display_name": request.display_name,
                        "purpose": "development",
                    }
                )
        return subject_response(row)

    async def get_subject(self, subject_id):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                row = await MemoryRepository(connection).get_subject(subject_id)
                self.database.require_workspace(row)
        return subject_response(row)

    async def create_conversation(self, request):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                definition = await DefinitionVersionRepository(connection).get(
                    request.agent_definition_id
                )
                subject = await MemoryRepository(connection).lock_subject(
                    request.memory_subject_id
                )
                self.database.require_workspace(definition)
                self.database.require_workspace(subject)
                require_hindsight_definition(definition)
                if definition.get("purpose", "development") != subject.get(
                    "purpose", "development"
                ):
                    raise RuntimeValidationError(
                        "Definition and subject must share a purpose"
                    )
                if subject["archived_at"]:
                    raise RuntimeValidationError(
                        "Archived subjects cannot start new conversations"
                    )
                row = await ConversationRepository(connection).create(
                    {
                        "id": str(uuid4()),
                        "workspace_id": self.database.workspace_id,
                        "agent_definition_version_id": definition["id"],
                        "memory_subject_id": subject["id"],
                        "title": request.title,
                        "purpose": definition.get("purpose", "development"),
                    }
                )
                await MemoryRelationshipRepository(connection).ensure(
                    relationship_for(row, definition)
                )
        return conversation_response(row)

    async def get_conversation_state(
        self,
        conversation_id,
        *,
        required_purpose=None,
        message_limit=200,
        before_sequence=None,
    ):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                repository = ConversationRepository(connection)
                row = await repository.get(conversation_id)
                self.database.require_workspace(row)
                if (
                    required_purpose is not None
                    and row.get("purpose", "development") != required_purpose
                ):
                    raise RuntimeValidationError(
                        "Conversation is outside the requested purpose"
                    )
                total, messages = await repository.list_message_page(
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
                    if summary
                    else None
                )
        first = int(messages[0]["sequence"]) if messages else None
        return {
            **conversation_response(row),
            "messages": [message_response(message) for message in messages],
            "message_total": total,
            "messages_truncated": len(messages) < total,
            "next_before_sequence": first if first and first > 1 else None,
            "summary": summary_response,
        }
