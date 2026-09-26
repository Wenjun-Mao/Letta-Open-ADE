"""Immutable request-local handles for one natural-memory reviewer snapshot."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .errors import RuntimeValidationError
from .fact_registry import fact_type_spec


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


@dataclass(frozen=True)
class NaturalBindingMap:
    current: Mapping[str, Any]
    messages: Mapping[str, Mapping[str, Any]]
    targets: Mapping[str, Mapping[str, Any]]
    identities: Mapping[str, Mapping[str, Any]]
    ordered_messages: tuple[tuple[str, Mapping[str, Any]], ...]
    history_messages: Mapping[str, Mapping[str, Any]]
    history_packet: tuple[dict[str, Any], ...]

    def packet(
        self, candidate_reply: str, *, history_capable: bool = False
    ) -> dict[str, Any]:
        packet = {
            "current_user": {
                "handle": "CURRENT",
                "role": "user",
                "content": self.current["content"],
            },
            "context": [
                {"handle": handle, "role": item["role"], "content": item["content"]}
                for handle, item in self.ordered_messages
            ],
            "eligible_support": [
                {"handle": handle, "role": item["role"]}
                for handle, item in self.ordered_messages
            ],
            "targets": [
                {
                    "handle": handle,
                    "fact_type": item["fact_type"],
                    "qualifier": item.get("qualifier"),
                    "value": item.get("value"),
                    "status": item["status"],
                    "reason": item.get("reason"),
                }
                for handle, item in self.targets.items()
            ],
            "related_identities": [
                {"handle": handle, "kind": item["kind"], "label": item["label"]}
                for handle, item in self.identities.items()
            ],
            "candidate_visible_reply": candidate_reply,
        }
        if history_capable:
            packet["history"] = list(self.history_packet)
        return packet


def build_natural_binding_map(
    *,
    current_user_message: dict[str, Any],
    source_messages: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    history_exchanges: list[dict[str, Any]] | None = None,
) -> NaturalBindingMap:
    current_id = str(current_user_message["id"])
    if current_user_message.get("role") != "user":
        raise RuntimeValidationError("Current natural authority must be a user message")
    prior = [
        MappingProxyType(dict(item))
        for item in source_messages
        if str(item["id"]) != current_id
    ]
    if len({str(item["id"]) for item in source_messages}) != len(source_messages):
        raise RuntimeValidationError("Duplicate source message in reviewer bundle")
    current_sequence = current_user_message.get("sequence")
    for item in prior:
        if item.get("role") not in {"user", "assistant"}:
            raise RuntimeValidationError("Unsupported prior message role")
        if current_sequence is not None and item.get("sequence") is not None:
            if int(item["sequence"]) >= int(current_sequence):
                raise RuntimeValidationError("Support must precede current message")
    if all(item.get("sequence") is not None for item in prior):
        prior.sort(key=lambda item: int(item["sequence"]))
    ordered = []
    counts = {"user": 0, "assistant": 0}
    for item in prior:
        role = str(item["role"])
        counts[role] += 1
        ordered.append((f"{'U' if role == 'user' else 'A'}{counts[role]}", item))
    entity_by_id = {str(entity["id"]): entity for entity in entities}
    targets = {
        f"F{index}": MappingProxyType(dict(fact))
        for index, fact in enumerate(
            (item for item in facts if item["status"] in {"active", "inactive"}),
            start=1,
        )
    }
    identities = {}
    seen_entities: set[str] = set()
    for fact in targets.values():
        spec = fact_type_spec(str(fact["fact_type"]))
        entity_id = str(fact["entity_id"])
        if (
            not spec.defines_entity_identity
            or fact["status"] != "active"
            or entity_id in seen_entities
        ):
            continue
        entity = entity_by_id.get(entity_id)
        if entity is None or entity.get("kind") == "subject":
            continue
        seen_entities.add(entity_id)
        identities[f"E{len(identities) + 1}"] = MappingProxyType(
            {
                **entity,
                "label": str(fact.get("value") or ""),
            }
        )
    history_messages: dict[str, Mapping[str, Any]] = {}
    history_packet: list[dict[str, Any]] = []
    seen_history_source_ids: set[str] = set()
    for exchange in history_exchanges or []:
        wire_messages = []
        source_handles: dict[str, str] = {}
        for message in exchange["messages"]:
            source_id = str(message["id"])
            role = str(message["role"])
            content = str(message["content"])
            digest = hashlib.sha256(content.encode()).hexdigest()
            if (
                source_id in seen_history_source_ids
                or role not in {"user", "assistant"}
                or digest != message["content_sha256"]
            ):
                raise RuntimeValidationError(
                    "Historical source failed identity, role or hash validation",
                    detail_code="natural_history_integrity",
                )
            seen_history_source_ids.add(source_id)
            handle = f"H{len(history_messages) + 1}"
            history_messages[handle] = MappingProxyType(dict(message))
            source_handles[source_id] = handle
            wire_messages.append(
                {
                    "handle": handle,
                    "role": role,
                    "content": content,
                    "content_sha256": digest,
                    "created_at": message["created_at"].isoformat()
                    if hasattr(message["created_at"], "isoformat")
                    else str(message["created_at"]),
                }
            )
        if len(wire_messages) != 2 or [item["role"] for item in wire_messages] != [
            "user",
            "assistant",
        ]:
            raise RuntimeValidationError(
                "Historical evidence requires one complete exchange",
                detail_code="natural_history_integrity",
            )
        annotations = _json_ready(exchange["annotations"])
        links = annotations.get("links") if isinstance(annotations, dict) else None
        if not isinstance(links, list) or any(
            not isinstance(link, dict) for link in links
        ):
            raise RuntimeValidationError(
                "Historical source annotations are malformed",
                detail_code="natural_history_integrity",
            )
        for link in links:
            source_handle = source_handles.get(str(link.get("message_id")))
            if source_handle is None:
                raise RuntimeValidationError(
                    "Historical annotation source is outside its exchange",
                    detail_code="natural_history_integrity",
                )
            link["message_handle"] = source_handle
            del link["message_id"]
        history_packet.append(
            {
                "run_id": str(exchange["run_id"]),
                "conversation_id": str(exchange["conversation_id"]),
                "definition_version_id": str(exchange["definition_version_id"]),
                "archived": bool(exchange["archived"]),
                "messages": wire_messages,
                "annotations": annotations,
            }
        )
    return NaturalBindingMap(
        current=MappingProxyType(dict(current_user_message)),
        messages=MappingProxyType(dict(ordered)),
        targets=MappingProxyType(targets),
        identities=MappingProxyType(identities),
        ordered_messages=tuple(ordered),
        history_messages=MappingProxyType(history_messages),
        history_packet=tuple(history_packet),
    )
