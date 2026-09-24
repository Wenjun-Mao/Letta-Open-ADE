"""Immutable request-local handles for one natural-memory reviewer snapshot."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from .errors import RuntimeValidationError
from .fact_registry import fact_type_spec


@dataclass(frozen=True)
class NaturalBindingMap:
    current: Mapping[str, Any]
    messages: Mapping[str, Mapping[str, Any]]
    targets: Mapping[str, Mapping[str, Any]]
    identities: Mapping[str, Mapping[str, Any]]
    ordered_messages: tuple[tuple[str, Mapping[str, Any]], ...]

    def packet(self, candidate_reply: str) -> dict[str, Any]:
        return {
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


def build_natural_binding_map(
    *,
    current_user_message: dict[str, Any],
    source_messages: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
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
    return NaturalBindingMap(
        current=MappingProxyType(dict(current_user_message)),
        messages=MappingProxyType(dict(ordered)),
        targets=MappingProxyType(targets),
        identities=MappingProxyType(identities),
        ordered_messages=tuple(ordered),
    )
