from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncConnection

from .contracts import CreateAgentDefinitionRequest, CreatePreviewSessionRequest
from .database_boundary import (
    DEFAULT_WORKSPACE_ID,
    RuntimeDatabase,
    require_default_workspace,
)
from .definition_service import DefinitionService, normalize_route_alias
from .errors import IdempotencyConflict, RuntimeConflict
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .presenters import conversation_response, definition_response, subject_response


@dataclass(frozen=True)
class _PreviewIdentity:
    session_id: str
    definition_id: str
    definition_key: str
    subject_id: str
    subject_external_key: str
    conversation_id: str


class PreviewSessionService:
    """Create the pilot's definition, subject, and conversation as one unit."""

    def __init__(
        self,
        *,
        database: RuntimeDatabase,
        definitions: DefinitionService,
    ) -> None:
        self.database = database
        self.definitions = definitions

    async def create(self, request: CreatePreviewSessionRequest) -> dict[str, Any]:
        await self.database.ensure_ready()
        identity = _preview_identity(request.idempotency_key)
        existing = await self._read_existing(identity, request)
        if existing is not None:
            return _preview_response(identity.session_id, existing, replayed=True)

        definition_request = CreateAgentDefinitionRequest(
            definition_key=identity.definition_key,
            name=request.name,
            model_key=request.model_key,
            reviewer_model_key=request.reviewer_model_key,
            embedding_model_key=request.embedding_model_key,
            prompt_key=request.prompt_key,
            persona_key=request.persona_key,
            tool_names=["search_memory"],
        )
        prepared = await self.definitions.prepare(definition_request)

        async with self.database.translated_errors():
            async with self.database.engine.begin() as connection:
                await self.database.ensure_workspace(connection)
                await _lock_preview_identity(connection, identity.session_id)
                existing = await _load_existing(connection, identity)
                if existing is not None:
                    _validate_existing(existing, identity, request)
                    return _preview_response(
                        identity.session_id, existing, replayed=True
                    )

                definition = await DefinitionVersionRepository(connection).create_next(
                    DEFAULT_WORKSPACE_ID,
                    {"id": identity.definition_id, **prepared},
                )
                memories = MemoryRepository(connection)
                subject = await memories.create_subject(
                    {
                        "id": identity.subject_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "external_key": identity.subject_external_key,
                        "display_name": request.subject_display_name,
                    }
                )
                await memories.create_entity(
                    {
                        "id": identity.subject_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "subject_id": identity.subject_id,
                        "kind": "subject",
                        "label": request.subject_display_name,
                    }
                )
                conversation = await ConversationRepository(connection).create(
                    {
                        "id": identity.conversation_id,
                        "workspace_id": DEFAULT_WORKSPACE_ID,
                        "agent_definition_version_id": identity.definition_id,
                        "memory_subject_id": identity.subject_id,
                    }
                )

        return _preview_response(
            identity.session_id,
            (definition, subject, conversation),
            replayed=False,
        )

    async def _read_existing(
        self,
        identity: _PreviewIdentity,
        request: CreatePreviewSessionRequest,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
        async with self.database.translated_errors():
            async with self.database.engine.connect() as connection:
                existing = await _load_existing(connection, identity)
                if existing is not None:
                    _validate_existing(existing, identity, request)
                return existing


async def _load_existing(
    connection: AsyncConnection,
    identity: _PreviewIdentity,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]] | None:
    definition = await DefinitionVersionRepository(connection).find(
        identity.definition_id
    )
    subject = await MemoryRepository(connection).find_subject(identity.subject_id)
    conversation = await ConversationRepository(connection).find(
        identity.conversation_id
    )
    resources = (definition, subject, conversation)
    if all(item is None for item in resources):
        return None
    if any(item is None for item in resources):
        raise RuntimeConflict(
            "Preview session resources are incomplete; create a new session identity"
        )
    return definition, subject, conversation  # type: ignore[return-value]


def _validate_existing(
    existing: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    identity: _PreviewIdentity,
    request: CreatePreviewSessionRequest,
) -> None:
    definition, subject, conversation = existing
    for row in existing:
        require_default_workspace(row)
    expected_definition = {
        "id": identity.definition_id,
        "definition_key": identity.definition_key,
        "name": request.name,
        "model_key": normalize_route_alias(request.model_key),
        "reviewer_model_key": normalize_route_alias(request.reviewer_model_key),
        "embedding_model_key": normalize_route_alias(request.embedding_model_key),
        "prompt_key": request.prompt_key,
        "persona_key": request.persona_key,
        "tool_names": ["search_memory"],
    }
    expected_subject = {
        "id": identity.subject_id,
        "external_key": identity.subject_external_key,
        "display_name": request.subject_display_name,
    }
    expected_conversation = {
        "id": identity.conversation_id,
        "agent_definition_version_id": identity.definition_id,
        "memory_subject_id": identity.subject_id,
    }
    for label, row, expected in (
        ("definition", definition, expected_definition),
        ("subject", subject, expected_subject),
        ("conversation", conversation, expected_conversation),
    ):
        if any(row.get(key) != value for key, value in expected.items()):
            raise IdempotencyConflict(
                f"Preview session idempotency key was already used for a different {label}"
            )


async def _lock_preview_identity(
    connection: AsyncConnection,
    session_id: str,
) -> None:
    digest = hashlib.sha256(session_id.encode("utf-8")).digest()
    lock_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    await connection.execute(select(func.pg_advisory_xact_lock(lock_key)))


def _preview_identity(idempotency_key: str) -> _PreviewIdentity:
    session_uuid = uuid5(NAMESPACE_URL, f"ade://native-preview/{idempotency_key}")

    def child(name: str) -> str:
        return str(uuid5(UUID(str(session_uuid)), name))

    session_id = str(session_uuid)
    return _PreviewIdentity(
        session_id=session_id,
        definition_id=child("definition"),
        definition_key=f"preview_{session_uuid.hex}",
        subject_id=child("subject"),
        subject_external_key=f"preview-session:{session_id}",
        conversation_id=child("conversation"),
    )


def _preview_response(
    session_id: str,
    resources: tuple[dict[str, Any], dict[str, Any], dict[str, Any]],
    *,
    replayed: bool,
) -> dict[str, Any]:
    definition, subject, conversation = resources
    return {
        "session_id": session_id,
        "idempotent_replay": replayed,
        "agent_definition": definition_response(definition),
        "memory_subject": subject_response(subject),
        "conversation": conversation_response(conversation),
    }
