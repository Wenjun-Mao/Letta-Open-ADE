"""Public immutable source envelopes for the concrete Hindsight integration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid5


DELIVERY_VERSION = "ade-hindsight-message-v1"
DELIVERY_NAMESPACE = UUID("81d75e7f-bd94-4681-89a0-9c04699d71c4")
ANTECEDENT_CHARACTERS = 8_000


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


@dataclass(frozen=True)
class MemoryRelationship:
    workspace_id: str
    subject_id: str
    character_root_id: str

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not value.strip()
            for value in self.as_dict().values()
        ):
            raise ValueError("Memory relationship identities must be nonempty")

    def as_dict(self) -> dict[str, str]:
        return {
            "workspace_id": self.workspace_id,
            "subject_id": self.subject_id,
            "character_root_id": self.character_root_id,
        }

    @property
    def bank_id(self) -> str:
        identity = canonical_bytes(self.as_dict()).decode("utf-8")
        return f"ade-{uuid5(DELIVERY_NAMESPACE, identity).hex}"


@dataclass(frozen=True)
class MemorySourceMessage:
    message_id: str
    conversation_id: str
    definition_version_id: str
    relationship: MemoryRelationship
    sequence: int
    role: Literal["user", "assistant"]
    content: str
    occurred_at: datetime
    status: Literal["accepted", "committed"]

    def __post_init__(self) -> None:
        if not self.definition_version_id.strip():
            raise ValueError(
                "A memory source requires its immutable definition binding"
            )
        if not self.message_id.strip() or not self.conversation_id.strip():
            raise ValueError(
                "A memory source requires original message/conversation IDs"
            )
        if (
            type(self.sequence) is not int
            or self.sequence < 1
            or not isinstance(self.content, str)
            or not self.content.strip()
        ):
            raise ValueError("A memory source requires a positive sequence and content")
        if (
            not isinstance(self.occurred_at, datetime)
            or self.occurred_at.utcoffset() is None
        ):
            raise ValueError(
                "A memory source requires its original timezone-aware time"
            )
        expected = {"user": "accepted", "assistant": "committed"}.get(self.role)
        if expected is None or self.status != expected:
            raise ValueError(
                "Only accepted users and committed assistant replies are sources"
            )
        if "\x00" in self.content:
            raise ValueError(
                "Source text cannot be silently changed by native sanitization"
            )
        self.content.encode("utf-8")

    def as_dict(self) -> dict[str, object]:
        return {
            "message_id": self.message_id,
            "conversation_id": self.conversation_id,
            "definition_version_id": self.definition_version_id,
            "sequence": self.sequence,
            "speaker": self.role,
            "content": self.content,
            "occurred_at": self.occurred_at.astimezone(timezone.utc).isoformat(),
            "status": self.status,
        }


@dataclass(frozen=True)
class MemoryDelivery:
    bank_id: str
    message_id: str
    operation_id: str
    document_id: str
    payload: bytes
    payload_sha256: str

    def verify(self) -> dict:
        if hashlib.sha256(self.payload).hexdigest() != self.payload_sha256:
            raise ValueError("Immutable memory-delivery payload changed")
        body = json.loads(self.payload)
        if not isinstance(body, dict):
            raise ValueError("Memory-delivery payload must be an object")
        items = body.get("items")
        if (
            not isinstance(items, list)
            or len(items) != 1
            or not isinstance(items[0], dict)
        ):
            raise ValueError("Memory delivery must contain one source item")
        metadata = items[0].get("metadata")
        if not isinstance(metadata, dict) or not all(
            isinstance(metadata.get(key), str) and metadata[key].strip()
            for key in ("workspace_id", "subject_id", "character_root_id", "message_id")
        ):
            raise ValueError("Memory delivery requires attributed source metadata")
        if (
            body.get("operation_id") != self.operation_id
            or body.get("async") is not True
            or items[0].get("document_id") != self.document_id
            or metadata["message_id"] != self.message_id
        ):
            raise ValueError("Memory-delivery identities do not match the payload")
        relationship = MemoryRelationship(
            metadata["workspace_id"],
            metadata["subject_id"],
            metadata["character_root_id"],
        )
        expected_operation = str(
            uuid5(DELIVERY_NAMESPACE, f"{relationship.bank_id}:{self.message_id}")
        )
        if (
            relationship.bank_id != self.bank_id
            or self.document_id != f"ade-message-{self.message_id}"
            or self.operation_id != expected_operation
        ):
            raise ValueError("Memory-delivery ownership does not match its identities")
        return body


def prepare_memory_delivery(
    source: MemorySourceMessage,
    *,
    earlier_messages: tuple[MemorySourceMessage, ...] = (),
    antecedent_characters: int = ANTECEDENT_CHARACTERS,
) -> MemoryDelivery:
    """Freeze once at source commit; retries reuse these exact bytes."""
    if antecedent_characters < 0:
        raise ValueError("Antecedent context budget cannot be negative")
    previous_sequence = 0
    previous_time: datetime | None = None
    seen = {source.message_id}
    for previous in earlier_messages:
        if (
            previous.relationship != source.relationship
            or previous.conversation_id != source.conversation_id
            or not previous_sequence < previous.sequence < source.sequence
            or previous.message_id in seen
            or previous.occurred_at > source.occurred_at
            or (previous_time is not None and previous.occurred_at < previous_time)
        ):
            raise ValueError(
                "Antecedents must be ordered sources from this conversation"
            )
        seen.add(previous.message_id)
        previous_sequence, previous_time = previous.sequence, previous.occurred_at

    selected: list[dict[str, object]] = []
    used = 0
    for previous in reversed(earlier_messages):
        value = previous.as_dict()
        size = len(canonical_bytes(value).decode("utf-8"))
        if used + size > antecedent_characters:
            break
        selected.insert(0, value)
        used += size

    document_id = f"ade-message-{source.message_id}"
    operation_id = str(
        uuid5(DELIVERY_NAMESPACE, f"{source.relationship.bank_id}:{source.message_id}")
    )
    context = {
        "delivery_contract": DELIVERY_VERSION,
        "relationship": source.relationship.as_dict(),
        "earlier_context_only": selected,
        "context_purpose": (
            "Earlier attributed messages resolve references in the current source. "
            "They are not new statements and retain their original speakers and times."
        ),
    }
    payload = canonical_bytes(
        {
            "async": True,
            "operation_id": operation_id,
            "items": [
                {
                    "document_id": document_id,
                    "content": canonical_bytes(source.as_dict()).decode("utf-8"),
                    "context": canonical_bytes(context).decode("utf-8"),
                    "timestamp": source.as_dict()["occurred_at"],
                    "update_mode": "replace",
                    "metadata": {
                        **source.relationship.as_dict(),
                        "message_id": source.message_id,
                        "conversation_id": source.conversation_id,
                        "definition_version_id": source.definition_version_id,
                        "speaker": source.role,
                        "delivery_contract": DELIVERY_VERSION,
                    },
                }
            ],
        }
    )
    return MemoryDelivery(
        source.relationship.bank_id,
        source.message_id,
        operation_id,
        document_id,
        payload,
        hashlib.sha256(payload).hexdigest(),
    )
