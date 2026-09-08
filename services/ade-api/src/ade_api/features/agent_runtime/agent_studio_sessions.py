from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from .contracts import (
    CreateAgentDefinitionRequest,
    CreateAgentStudioSessionRequest,
    CreateMemorySubjectRequest,
    RuntimeResourcePurpose,
    UpdateMemorySubjectRequest,
)
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .definition_service import DefinitionService, normalize_route_alias
from .errors import IdempotencyConflict, RuntimeConflict, RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import (
    AgentDefinitionRepository,
    DefinitionVersionRepository,
)
from .persistence.memory import MemoryRepository
from .persistence.runs import RunRepository
from .presenters import (
    conversation_response,
    definition_response,
    run_response,
    subject_response,
)

AGENT_STUDIO_PURPOSE = RuntimeResourcePurpose.AGENT_STUDIO.value
EVALUATION_PURPOSE = RuntimeResourcePurpose.EVALUATION.value


@dataclass(frozen=True)
class _SessionIdentity:
    session_id: str
    definition_root_id: str
    definition_version_id: str
    subject_id: str
    conversation_id: str


class PurposeSessionService:
    """Atomically provision and read a session within one runtime purpose."""

    def __init__(
        self,
        *,
        database: RuntimeDatabase,
        definitions: DefinitionService,
        purpose: str = AGENT_STUDIO_PURPOSE,
        session_namespace: str = "agent-studio",
        allowed_tool_names: frozenset[str] = frozenset({"search_memory"}),
    ) -> None:
        self.database = database
        self.definitions = definitions
        self.purpose = purpose
        self.session_namespace = session_namespace
        self.allowed_tool_names = allowed_tool_names

    async def options(self) -> dict[str, Any]:
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

    async def create(self, request: CreateAgentStudioSessionRequest) -> dict[str, Any]:
        await self.database.ensure_ready()
        identity = session_identity(
            request.idempotency_key, namespace=self.session_namespace
        )
        existing = await self._read_existing(identity, request)
        if existing is not None:
            return await self._response(identity.session_id, existing, replayed=True)

        prepared = (
            await self.definitions.prepare(request.new_definition, purpose=self.purpose)
            if request.new_definition is not None
            else None
        )
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                await _lock_session_identity(connection, identity.session_id)
                existing = await _load_existing(
                    connection, identity, purpose=self.purpose
                )
                if existing is not None:
                    _validate_existing(existing, request, purpose=self.purpose)
                    return await _session_response_from_connection(
                        connection,
                        identity.session_id,
                        existing,
                        purpose=self.purpose,
                        replayed=True,
                    )

                definition = await self._resolve_definition(
                    connection, request, identity, prepared
                )
                subject = await self._resolve_subject(connection, request, identity)
                conversation = await ConversationRepository(connection).create(
                    {
                        "id": identity.conversation_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "agent_definition_version_id": definition["id"],
                        "memory_subject_id": subject["id"],
                        "title": request.title,
                        "purpose": self.purpose,
                    }
                )
                resources = (definition, subject, conversation)
                return await _session_response_from_connection(
                    connection,
                    identity.session_id,
                    resources,
                    purpose=self.purpose,
                    replayed=False,
                )

    async def get(self, conversation_id: str) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                conversation = await ConversationRepository(connection).get(
                    conversation_id
                )
                _require_purpose(conversation, self.purpose, "conversation")
                resources = await _load_session_resources(connection, conversation)
                return await _session_response_from_connection(
                    connection,
                    str(conversation["id"]),
                    resources,
                    purpose=self.purpose,
                    replayed=False,
                )

    async def list(
        self,
        *,
        include_archived: bool,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                total, conversations = await ConversationRepository(
                    connection
                ).list_for_workspace(
                    DEFAULT_WORKSPACE_ID,
                    purpose=self.purpose,
                    include_archived=include_archived,
                    limit=limit,
                    offset=offset,
                )
                items = [
                    await _session_response_from_connection(
                        connection,
                        str(conversation["id"]),
                        await _load_session_resources(connection, conversation),
                        purpose=self.purpose,
                        replayed=False,
                    )
                    for conversation in conversations
                ]
        return {"total": total, "items": items}

    async def set_archived(
        self, conversation_id: str, *, archived: bool
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                conversations = ConversationRepository(connection)
                conversation = await conversations.get_for_update(conversation_id)
                _require_purpose(conversation, self.purpose, "conversation")
                if archived and await RunRepository(connection).active_for_conversation(
                    conversation_id
                ):
                    raise RuntimeConflict(
                        "a session with an active run cannot be archived"
                    )
                conversation = await conversations.set_archived(
                    conversation_id, archived=archived
                )
                resources = await _load_session_resources(connection, conversation)
                return await _session_response_from_connection(
                    connection,
                    str(conversation["id"]),
                    resources,
                    purpose=self.purpose,
                    replayed=False,
                )

    async def list_definitions(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                total, rows = await AgentDefinitionRepository(connection).list_current(
                    DEFAULT_WORKSPACE_ID,
                    purpose=self.purpose,
                    include_archived=include_archived,
                    limit=limit,
                    offset=offset,
                )
        return {"total": total, "items": [definition_response(row) for row in rows]}

    async def create_definition(
        self, request: CreateAgentDefinitionRequest
    ) -> dict[str, Any]:
        self._require_allowed_tool_names(request.tool_names)
        return await self.definitions.create(request, purpose=self.purpose)

    async def set_definition_archived(
        self, definition_id: str, *, archived: bool
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                roots = AgentDefinitionRepository(connection)
                root = await roots.get_for_update(definition_id)
                _require_purpose(root, self.purpose, "agent definition")
                root = await roots.set_archived(definition_id, archived=archived)
                version = await DefinitionVersionRepository(connection).get(
                    str(root["current_version_id"])
                )
                version["definition_archived_at"] = root["archived_at"]
        return definition_response(version)

    async def list_subjects(
        self, *, include_archived: bool, limit: int, offset: int
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                total, rows = await MemoryRepository(connection).list_subjects(
                    DEFAULT_WORKSPACE_ID,
                    purpose=self.purpose,
                    include_archived=include_archived,
                    limit=limit,
                    offset=offset,
                )
        return {"total": total, "items": [subject_response(row) for row in rows]}

    async def create_subject(
        self, request: CreateMemorySubjectRequest
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                repository = MemoryRepository(connection)
                subject = await repository.create_subject(
                    {
                        "id": str(
                            uuid5(
                                NAMESPACE_URL, f"ade://subject/{request.external_key}"
                            )
                        ),
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "external_key": request.external_key,
                        "display_name": request.display_name,
                        "purpose": self.purpose,
                    }
                )
                await repository.create_entity(
                    {
                        "id": subject["id"],
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "subject_id": subject["id"],
                        "kind": "subject",
                        "label": request.display_name,
                    }
                )
        return subject_response(subject)

    async def update_subject(
        self, subject_id: str, request: UpdateMemorySubjectRequest
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = MemoryRepository(connection)
                subject = await repository.lock_subject(subject_id)
                _require_purpose(subject, self.purpose, "memory subject")
                subject = await repository.update_subject_name(
                    subject_id,
                    display_name=request.display_name,
                    expected_version=request.expected_version,
                )
        return subject_response(subject)

    async def set_subject_archived(
        self, subject_id: str, *, archived: bool
    ) -> dict[str, Any]:
        await self.database.ensure_ready()
        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                repository = MemoryRepository(connection)
                subject = await repository.lock_subject(subject_id)
                _require_purpose(subject, self.purpose, "memory subject")
                if archived and await ConversationRepository(
                    connection
                ).has_unarchived_for_subject(subject_id):
                    raise RuntimeConflict(
                        "archive the subject's conversations before archiving the subject"
                    )
                subject = await repository.set_subject_archived(
                    subject_id, archived=archived
                )
        return subject_response(subject)

    def _require_allowed_tool_names(self, tool_names: list[str]) -> None:
        disallowed = sorted(set(tool_names) - self.allowed_tool_names)
        if disallowed:
            raise RuntimeValidationError(
                f"tools are not available for {self.purpose}: {disallowed}"
            )

    async def _resolve_definition(
        self,
        connection: AsyncConnection,
        request: CreateAgentStudioSessionRequest,
        identity: _SessionIdentity,
        prepared: dict[str, Any] | None,
    ) -> dict[str, Any]:
        repository = DefinitionVersionRepository(connection)
        if request.agent_definition_id is not None:
            definition = await repository.get(request.agent_definition_id)
            _require_purpose(definition, self.purpose, "agent definition version")
            self._require_allowed_tool_names(list(definition["tool_names"]))
            root = await AgentDefinitionRepository(connection).get_for_update(
                str(definition["agent_definition_id"])
            )
            if root.get("archived_at") is not None:
                raise RuntimeValidationError(
                    "archived agent definitions cannot start new conversations"
                )
            return definition
        assert request.new_definition is not None and prepared is not None
        return await repository.create_next(
            DEFAULT_WORKSPACE_ID,
            {
                "id": identity.definition_version_id,
                "agent_definition_id": identity.definition_root_id,
                **prepared,
            },
            purpose=self.purpose,
            expected_current_version=0,
        )

    async def _resolve_subject(
        self,
        connection: AsyncConnection,
        request: CreateAgentStudioSessionRequest,
        identity: _SessionIdentity,
    ) -> dict[str, Any]:
        repository = MemoryRepository(connection)
        if request.memory_subject_id is not None:
            subject = await repository.lock_subject(request.memory_subject_id)
            _require_purpose(subject, self.purpose, "memory subject")
            if subject.get("archived_at") is not None:
                raise RuntimeValidationError(
                    "archived memory subjects cannot start new conversations"
                )
            return subject
        assert request.new_subject is not None
        subject = await repository.create_subject(
            {
                "id": identity.subject_id,
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "external_key": request.new_subject.external_key,
                "display_name": request.new_subject.display_name,
                "purpose": self.purpose,
            }
        )
        await repository.create_entity(
            {
                "id": identity.subject_id,
                "workspace_id": DEFAULT_WORKSPACE_ID,
                "subject_id": identity.subject_id,
                "kind": "subject",
                "label": request.new_subject.display_name,
            }
        )
        return subject

    async def _read_existing(
        self,
        identity: _SessionIdentity,
        request: CreateAgentStudioSessionRequest,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                existing = await _load_existing(
                    connection, identity, purpose=self.purpose
                )
                if existing is not None:
                    _validate_existing(existing, request, purpose=self.purpose)
                return existing

    async def _response(
        self,
        session_id: str,
        resources: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
        *,
        replayed: bool,
    ) -> dict[str, Any]:
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                return await _session_response_from_connection(
                    connection,
                    session_id,
                    resources,
                    purpose=self.purpose,
                    replayed=replayed,
                )


async def _load_existing(
    connection: AsyncConnection,
    identity: _SessionIdentity,
    *,
    purpose: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    conversation = await ConversationRepository(connection).find(
        identity.conversation_id
    )
    if conversation is None:
        return None
    _require_purpose(conversation, purpose, "conversation")
    return await _load_session_resources(connection, conversation)


async def _load_session_resources(
    connection: AsyncConnection, conversation: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    definition = await DefinitionVersionRepository(connection).get(
        str(conversation["agent_definition_version_id"])
    )
    subject = await MemoryRepository(connection).get_subject(
        str(conversation["memory_subject_id"])
    )
    for row in (definition, subject, conversation):
        require_default_workspace(row)
    return definition, subject, conversation


def _validate_existing(
    existing: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    request: CreateAgentStudioSessionRequest,
    *,
    purpose: str,
) -> None:
    definition, subject, conversation = existing
    expected_definition_id = request.agent_definition_id
    expected_subject_id = request.memory_subject_id
    if request.new_definition is not None:
        new_definition = request.new_definition
        expected_definition = {
            "definition_key": new_definition.definition_key,
            "name": new_definition.name,
            "model_key": normalize_route_alias(new_definition.model_key),
            "reviewer_model_key": normalize_route_alias(
                new_definition.reviewer_model_key
            ),
            "embedding_model_key": normalize_route_alias(
                new_definition.embedding_model_key
            ),
            "prompt_key": new_definition.prompt_key,
            "persona_key": new_definition.persona_key,
            "tool_names": list(new_definition.tool_names),
        }
        if any(
            definition.get(key) != value for key, value in expected_definition.items()
        ):
            raise IdempotencyConflict(
                "session key was already used for a different definition"
            )
    elif str(definition["id"]) != expected_definition_id:
        raise IdempotencyConflict("session key was already used for another definition")

    if request.new_subject is not None:
        if (
            subject.get("external_key") != request.new_subject.external_key
            or subject.get("display_name") != request.new_subject.display_name
        ):
            raise IdempotencyConflict(
                "session key was already used for a different subject"
            )
    elif str(subject["id"]) != expected_subject_id:
        raise IdempotencyConflict("session key was already used for another subject")

    if (
        conversation.get("title") != request.title
        or conversation.get("purpose") != purpose
    ):
        raise IdempotencyConflict(
            "session key was already used for another conversation"
        )


async def _session_response_from_connection(
    connection: AsyncConnection,
    session_id: str,
    resources: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    *,
    purpose: str,
    replayed: bool,
) -> dict[str, Any]:
    definition, subject, conversation = resources
    _require_purpose(definition, purpose, "agent definition version")
    _require_purpose(subject, purpose, "memory subject")
    _require_purpose(conversation, purpose, "conversation")
    _total, latest_runs = await RunRepository(connection).list_for_conversation(
        str(conversation["id"]), limit=1, offset=0
    )
    return {
        "session_id": session_id,
        "idempotent_replay": replayed,
        "agent_definition": definition_response(definition),
        "memory_subject": subject_response(subject),
        "conversation": conversation_response(conversation),
        "latest_run": run_response(latest_runs[0]) if latest_runs else None,
    }


def _require_purpose(row: dict[str, Any], purpose: str, label: str) -> None:
    require_default_workspace(row)
    if str(row.get("purpose", "development")) != purpose:
        raise RuntimeValidationError(f"{label} is not owned by {purpose}")


async def _lock_session_identity(connection: AsyncConnection, session_id: str) -> None:
    digest = hashlib.sha256(session_id.encode("utf-8")).digest()
    lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    await connection.execute(select(func.pg_advisory_xact_lock(lock_key)))


def session_identity(idempotency_key: str, *, namespace: str) -> _SessionIdentity:
    session_uuid = uuid5(NAMESPACE_URL, f"ade://{namespace}/{idempotency_key}")

    def child(name: str) -> str:
        return str(uuid5(UUID(str(session_uuid)), name))

    session_id = str(session_uuid)
    return _SessionIdentity(
        session_id=session_id,
        definition_root_id=child("definition-root"),
        definition_version_id=child("definition-version"),
        subject_id=child("subject"),
        conversation_id=session_id,
    )


# The product API imports this established name. Its default configuration remains
# Agent Studio-only while evaluation configures the same lifecycle explicitly.
AgentStudioSessionService = PurposeSessionService
