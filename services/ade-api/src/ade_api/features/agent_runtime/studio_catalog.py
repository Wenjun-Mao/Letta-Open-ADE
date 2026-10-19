"""Purpose-scoped character versions and subject administration, not learned memory."""

from uuid import uuid4

from .errors import RuntimeConflict
from .persistence.conversations import ConversationRepository
from .persistence.definitions import (
    AgentDefinitionRepository,
    DefinitionVersionRepository,
)
from .persistence.memory import MemoryRepository
from .presenters import definition_response, subject_response
from .session_resources import require_purpose, require_tools


class StudioCatalog:
    def __init__(self, *, database, definitions, purpose, allowed_tool_names):
        self.database, self.definitions = database, definitions
        self.purpose, self.allowed_tool_names = purpose, allowed_tool_names

    async def list_definitions(self, *, include_archived, limit, offset):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                total, rows = await AgentDefinitionRepository(connection).list_current(
                    self.database.workspace_id,
                    purpose=self.purpose,
                    include_archived=include_archived,
                    limit=limit,
                    offset=offset,
                )
        return {"total": total, "items": [definition_response(row) for row in rows]}

    async def create_definition(self, request):
        require_tools(request.tool_names, self.allowed_tool_names, self.purpose)
        return await self.definitions.create(request, purpose=self.purpose)

    async def set_definition_archived(self, definition_id, *, archived):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = AgentDefinitionRepository(connection)
                root = await repository.get_for_update(definition_id)
                require_purpose(self.database, root, self.purpose, "character root")
                root = await repository.set_archived(definition_id, archived=archived)
                row = await DefinitionVersionRepository(connection).get(
                    str(root["current_version_id"])
                )
                row["definition_archived_at"] = root["archived_at"]
        return definition_response(row)

    async def list_subjects(self, *, include_archived, limit, offset):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                total, rows = await MemoryRepository(connection).list_subjects(
                    self.database.workspace_id,
                    purpose=self.purpose,
                    include_archived=include_archived,
                    limit=limit,
                    offset=offset,
                )
        return {"total": total, "items": [subject_response(row) for row in rows]}

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
                        "purpose": self.purpose,
                    }
                )
        return subject_response(row)

    async def update_subject(self, subject_id, request):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = MemoryRepository(connection)
                row = await repository.lock_subject(subject_id)
                require_purpose(self.database, row, self.purpose, "subject")
                row = await repository.update_subject_name(
                    subject_id,
                    display_name=request.display_name,
                    expected_version=request.expected_version,
                )
        return subject_response(row)

    async def set_subject_archived(self, subject_id, *, archived):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = MemoryRepository(connection)
                row = await repository.lock_subject(subject_id)
                require_purpose(self.database, row, self.purpose, "subject")
                if archived and await ConversationRepository(
                    connection
                ).has_unarchived_for_subject(subject_id):
                    raise RuntimeConflict(
                        "Archive the subject's conversations before archiving the subject"
                    )
                row = await repository.set_subject_archived(
                    subject_id, archived=archived
                )
        return subject_response(row)
