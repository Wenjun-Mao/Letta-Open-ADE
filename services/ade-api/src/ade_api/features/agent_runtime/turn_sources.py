"""Bind committed product messages to their character-local delivery intent."""

from ade_api.integrations.hindsight_sources import (
    MemoryRelationship,
    MemorySourceMessage,
)

from .errors import RuntimeValidationError
from .persistence.conversations import ConversationRepository
from .persistence.memory_deliveries import MemoryDeliveryRepository


HINDSIGHT_MEMORY_POLICY = "hindsight-message-v1"


def require_hindsight_definition(definition: dict) -> None:
    if definition.get("memory_policy_version") != HINDSIGHT_MEMORY_POLICY:
        raise RuntimeValidationError(
            "This runtime requires a fresh Hindsight definition; retained native definitions cannot execute",
            detail_code="hindsight_definition_required",
        )


def relationship_for(conversation: dict, definition: dict) -> MemoryRelationship:
    if str(conversation["agent_definition_version_id"]) != str(definition["id"]):
        raise ValueError("Conversation definition binding changed")
    return MemoryRelationship(
        str(conversation["workspace_id"]),
        str(conversation["memory_subject_id"]),
        str(definition["agent_definition_id"]),
    )


def source_message(
    row: dict, conversation: dict, definition: dict
) -> MemorySourceMessage:
    if str(row["workspace_id"]) != str(conversation["workspace_id"]) or str(
        row["conversation_id"]
    ) != str(conversation["id"]):
        raise ValueError("Message is outside its conversation")
    return MemorySourceMessage(
        message_id=str(row["id"]),
        conversation_id=str(row["conversation_id"]),
        definition_version_id=str(definition["id"]),
        relationship=relationship_for(conversation, definition),
        sequence=int(row["sequence"]),
        role=row["role"],
        content=row["content"],
        occurred_at=row["created_at"],
        status="accepted" if row["role"] == "user" else "committed",
    )


async def enqueue_message(
    connection, *, message: dict, conversation: dict, definition: dict
) -> dict:
    """Must run in the same transaction as the source insert, never after commit."""
    require_hindsight_definition(definition)
    earlier = await ConversationRepository(connection).list_messages(
        str(conversation["id"])
    )
    return await MemoryDeliveryRepository(connection).enqueue(
        source_message(message, conversation, definition),
        earlier_messages=tuple(
            source_message(row, conversation, definition)
            for row in earlier
            if int(row["sequence"]) < int(message["sequence"])
        ),
    )
