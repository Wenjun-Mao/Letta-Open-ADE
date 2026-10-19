"""Atomic fresh-workspace sessions with immutable character-version bindings."""

from uuid import uuid4

from .errors import RuntimeConflict, RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import (
    AgentDefinitionRepository,
    DefinitionVersionRepository,
)
from .persistence.memory import MemoryRepository
from .persistence.memory_relationships import MemoryRelationshipRepository
from .persistence.runs import RunRepository
from .session_resources import (
    AGENT_STUDIO_PURPOSE,
    load_existing,
    load_session_resources,
    lock_session_identity,
    require_purpose,
    require_tools,
    session_identity,
    session_response,
    validate_existing,
)
from .studio_catalog import StudioCatalog
from .turn_sources import relationship_for, require_hindsight_definition


class PurposeSessionService:
    def __init__(
        self,
        *,
        database,
        definitions,
        purpose=AGENT_STUDIO_PURPOSE,
        session_namespace="agent-studio",
        allowed_tool_names=frozenset({"search_memory"}),
    ):
        self.database, self.definitions = database, definitions
        self.purpose, self.session_namespace = purpose, session_namespace
        self.allowed_tool_names = allowed_tool_names
        self.catalog = StudioCatalog(
            database=database,
            definitions=definitions,
            purpose=purpose,
            allowed_tool_names=allowed_tool_names,
        )

    async def options(self):
        bundle = self.definitions.configured_agent_studio_bundle()
        return {
            "runtime": "ade_native",
            "default_bundle_key": bundle["key"],
            "bundles": [bundle]
            if self.definitions.settings.agent_runtime_mode == "development"
            or bundle["qualification_state"] == "qualified"
            else [],
            "default_timeout_seconds": 180.0,
            "default_retry_count": 0,
            "max_retry_count": 5,
        }

    async def create(self, request):
        await self.database.ensure_ready()
        identity = session_identity(
            request.idempotency_key,
            workspace_id=self.database.workspace_id,
            namespace=self.session_namespace,
        )
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                existing = await load_existing(
                    connection, identity, database=self.database, purpose=self.purpose
                )
                if existing:
                    validate_existing(existing, request, purpose=self.purpose)
                    return await session_response(
                        connection, identity.session_id, existing, replayed=True
                    )
        if request.new_definition:
            require_tools(
                request.new_definition.tool_names, self.allowed_tool_names, self.purpose
            )
        prepared = (
            await self.definitions.prepare(request.new_definition, purpose=self.purpose)
            if request.new_definition
            else None
        )
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                await lock_session_identity(connection, identity.session_id)
                existing = await load_existing(
                    connection, identity, database=self.database, purpose=self.purpose
                )
                if existing:
                    validate_existing(existing, request, purpose=self.purpose)
                    return await session_response(
                        connection, identity.session_id, existing, replayed=True
                    )
                definition = await self._resolve_definition(
                    connection, request, identity, prepared
                )
                subject = await self._resolve_subject(connection, request, identity)
                conversation = await ConversationRepository(connection).create(
                    {
                        "id": identity.conversation_id,
                        "workspace_id": self.database.workspace_id,
                        "agent_definition_version_id": definition["id"],
                        "memory_subject_id": subject["id"],
                        "title": request.title,
                        "purpose": self.purpose,
                    }
                )
                await MemoryRelationshipRepository(connection).ensure(
                    relationship_for(conversation, definition)
                )
                return await session_response(
                    connection,
                    identity.session_id,
                    (definition, subject, conversation),
                    replayed=False,
                )

    async def get(self, conversation_id):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                conversation = await ConversationRepository(connection).get(
                    conversation_id
                )
                resources = await load_session_resources(
                    connection,
                    conversation,
                    database=self.database,
                    purpose=self.purpose,
                )
                return await session_response(
                    connection, str(conversation["id"]), resources, replayed=False
                )

    async def list(self, *, include_archived, limit, offset):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                total, rows = await ConversationRepository(
                    connection
                ).list_for_workspace(
                    self.database.workspace_id,
                    purpose=self.purpose,
                    include_archived=include_archived,
                    limit=limit,
                    offset=offset,
                )
                items = [
                    await session_response(
                        connection,
                        str(row["id"]),
                        await load_session_resources(
                            connection,
                            row,
                            database=self.database,
                            purpose=self.purpose,
                        ),
                        replayed=False,
                    )
                    for row in rows
                ]
        return {"total": total, "items": items}

    async def set_archived(self, conversation_id, *, archived):
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = ConversationRepository(connection)
                conversation = await repository.get_for_update(conversation_id)
                require_purpose(
                    self.database, conversation, self.purpose, "conversation"
                )
                if archived and await RunRepository(connection).active_for_conversation(
                    conversation_id
                ):
                    raise RuntimeConflict(
                        "Resolve the pending, running or paused reply before archiving"
                    )
                conversation = await repository.set_archived(
                    conversation_id, archived=archived
                )
                resources = await load_session_resources(
                    connection,
                    conversation,
                    database=self.database,
                    purpose=self.purpose,
                )
                return await session_response(
                    connection, str(conversation["id"]), resources, replayed=False
                )

    async def _resolve_definition(self, connection, request, identity, prepared):
        repository = DefinitionVersionRepository(connection)
        if request.agent_definition_id:
            definition = await repository.get(request.agent_definition_id)
            require_purpose(self.database, definition, self.purpose, "definition")
            require_hindsight_definition(definition)
            require_tools(
                definition["tool_names"], self.allowed_tool_names, self.purpose
            )
            root = await AgentDefinitionRepository(connection).get_for_update(
                str(definition["agent_definition_id"])
            )
            if root["archived_at"]:
                raise RuntimeValidationError(
                    "Archived characters cannot start new conversations"
                )
            return definition
        return await repository.create_next(
            self.database.workspace_id,
            {
                "id": identity.definition_version_id,
                "agent_definition_id": identity.definition_root_id,
                **prepared,
            },
            purpose=self.purpose,
            expected_current_version=0,
        )

    async def _resolve_subject(self, connection, request, identity):
        repository = MemoryRepository(connection)
        if request.memory_subject_id:
            subject = await repository.lock_subject(request.memory_subject_id)
            require_purpose(self.database, subject, self.purpose, "subject")
            if subject["archived_at"]:
                raise RuntimeValidationError(
                    "Archived subjects cannot start new conversations"
                )
            return subject
        return await repository.create_subject(
            {
                "id": identity.subject_id or str(uuid4()),
                "workspace_id": self.database.workspace_id,
                "external_key": request.new_subject.external_key,
                "display_name": request.new_subject.display_name,
                "purpose": self.purpose,
            }
        )
