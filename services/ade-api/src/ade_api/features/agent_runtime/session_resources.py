"""Workspace-scoped session identities, replay validation and readback."""

from dataclasses import dataclass
import hashlib
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import func, select

from .definition_service import normalize_route_alias
from .errors import IdempotencyConflict, RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .persistence.runs import RunRepository
from .presenters import (
    conversation_response,
    definition_response,
    run_response,
    subject_response,
)
from .turn_sources import require_hindsight_definition


AGENT_STUDIO_PURPOSE = "agent_studio"
EVALUATION_PURPOSE = "evaluation"


@dataclass(frozen=True)
class SessionIdentity:
    session_id: str
    definition_root_id: str
    definition_version_id: str
    subject_id: str
    conversation_id: str


def session_identity(
    idempotency_key: str, *, workspace_id: str, namespace: str
) -> SessionIdentity:
    root = uuid5(NAMESPACE_URL, f"ade://{workspace_id}/{namespace}/{idempotency_key}")

    def child(name):
        return str(uuid5(UUID(str(root)), name))

    return SessionIdentity(
        str(root),
        child("definition-root"),
        child("definition-version"),
        child("subject"),
        str(root),
    )


def require_purpose(database, row: dict, purpose: str, label: str) -> None:
    database.require_workspace(row)
    if str(row.get("purpose", "development")) != purpose:
        raise RuntimeValidationError(f"{label} is not owned by {purpose}")


def require_tools(tool_names, allowed, purpose):
    if disallowed := sorted(set(tool_names) - set(allowed)):
        raise RuntimeValidationError(
            f"Tools are not available for {purpose}: {disallowed}"
        )


async def lock_session_identity(connection, session_id):
    key = int.from_bytes(
        hashlib.sha256(session_id.encode()).digest()[:8], byteorder="big", signed=True
    )
    await connection.execute(select(func.pg_advisory_xact_lock(key)))


async def load_session_resources(connection, conversation, *, database, purpose):
    definition = await DefinitionVersionRepository(connection).get(
        str(conversation["agent_definition_version_id"])
    )
    subject = await MemoryRepository(connection).get_subject(
        str(conversation["memory_subject_id"])
    )
    for row in (definition, subject, conversation):
        require_purpose(database, row, purpose, "session resource")
    require_hindsight_definition(definition)
    return definition, subject, conversation


async def load_existing(connection, identity, *, database, purpose):
    conversation = await ConversationRepository(connection).find(
        identity.conversation_id
    )
    if conversation is None:
        return None
    return await load_session_resources(
        connection, conversation, database=database, purpose=purpose
    )


def validate_existing(existing, request, *, purpose):
    definition, subject, conversation = existing
    if request.new_definition is not None:
        new = request.new_definition
        expected = {
            "definition_key": new.definition_key,
            "name": new.name,
            "model_key": normalize_route_alias(new.model_key),
            "compaction_model_key": normalize_route_alias(new.compaction_model_key),
            "prompt_key": new.prompt_key,
            "persona_key": new.persona_key,
            "tool_names": list(new.tool_names),
        }
        if any(definition.get(key) != value for key, value in expected.items()):
            raise IdempotencyConflict("Session key already owns a different definition")
    elif str(definition["id"]) != request.agent_definition_id:
        raise IdempotencyConflict("Session key already owns another definition")
    if request.new_subject is not None:
        if (
            subject["external_key"] != request.new_subject.external_key
            or subject["display_name"] != request.new_subject.display_name
        ):
            raise IdempotencyConflict("Session key already owns a different subject")
    elif str(subject["id"]) != request.memory_subject_id:
        raise IdempotencyConflict("Session key already owns another subject")
    if conversation["title"] != request.title or conversation["purpose"] != purpose:
        raise IdempotencyConflict("Session key already owns a different conversation")


async def session_response(connection, session_id, resources, *, replayed):
    definition, subject, conversation = resources
    _, latest = await RunRepository(connection).list_for_conversation(
        str(conversation["id"]), limit=1, offset=0
    )
    return {
        "session_id": session_id,
        "idempotent_replay": replayed,
        "agent_definition": definition_response(definition),
        "memory_subject": subject_response(subject),
        "conversation": conversation_response(conversation),
        "latest_run": run_response(latest[0]) if latest else None,
    }
