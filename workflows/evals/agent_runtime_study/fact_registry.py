from __future__ import annotations

from dataclasses import dataclass

from .contracts import MemoryEntityKind


class FactRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class FactTypeSpec:
    name: str
    entity_kind: MemoryEntityKind
    qualifier_required: bool = False
    allowed_qualifiers: tuple[str, ...] = ()
    defines_entity_identity: bool = False


PREFERENCE_QUALIFIERS = (
    "activity",
    "color",
    "drink",
    "food",
    "language",
    "media",
    "music",
    "place",
    "season",
    "style",
    "other",
)
RELATIONSHIP_QUALIFIERS = (
    "child",
    "colleague",
    "friend",
    "other",
    "parent",
    "partner",
    "sibling",
)


FACT_TYPE_REGISTRY: dict[str, FactTypeSpec] = {
    "person.name": FactTypeSpec("person.name", MemoryEntityKind.SUBJECT),
    "person.current_location": FactTypeSpec(
        "person.current_location", MemoryEntityKind.SUBJECT
    ),
    "person.preference": FactTypeSpec(
        "person.preference",
        MemoryEntityKind.SUBJECT,
        qualifier_required=True,
        allowed_qualifiers=PREFERENCE_QUALIFIERS,
    ),
    "person.shoe_size": FactTypeSpec("person.shoe_size", MemoryEntityKind.SUBJECT),
    "pet.name": FactTypeSpec(
        "pet.name",
        MemoryEntityKind.PET,
        defines_entity_identity=True,
    ),
    "pet.breed": FactTypeSpec("pet.breed", MemoryEntityKind.PET),
    "relationship.person": FactTypeSpec(
        "relationship.person",
        MemoryEntityKind.RELATED_PERSON,
        qualifier_required=True,
        allowed_qualifiers=RELATIONSHIP_QUALIFIERS,
        defines_entity_identity=True,
    ),
}


def fact_type_spec(fact_type: str) -> FactTypeSpec:
    normalized = str(fact_type or "").strip()
    try:
        return FACT_TYPE_REGISTRY[normalized]
    except KeyError as exc:
        raise FactRegistryError(
            f"Unknown fact type: {normalized or '<empty>'}"
        ) from exc


def normalize_qualifier(spec: FactTypeSpec, qualifier: str | None) -> str | None:
    normalized = str(qualifier or "").strip().casefold() or None
    if spec.qualifier_required and normalized is None:
        raise FactRegistryError(f"{spec.name} requires a qualifier")
    if not spec.qualifier_required and normalized is not None:
        raise FactRegistryError(f"{spec.name} does not accept a qualifier")
    if normalized is not None and normalized not in spec.allowed_qualifiers:
        raise FactRegistryError(
            f"Invalid qualifier '{normalized}' for {spec.name}; allowed values are "
            f"{', '.join(spec.allowed_qualifiers)}"
        )
    return normalized


def fact_key(fact_type: str, entity_id: str, qualifier: str | None) -> str:
    spec = fact_type_spec(fact_type)
    normalized_entity_id = str(entity_id or "").strip()
    if not normalized_entity_id:
        raise FactRegistryError("entity_id is required")
    normalized_qualifier = normalize_qualifier(spec, qualifier)
    parts = [spec.name, normalized_entity_id]
    if normalized_qualifier:
        parts.append(normalized_qualifier)
    return "|".join(parts)
