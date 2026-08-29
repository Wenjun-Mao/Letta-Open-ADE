from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class EntityKind(StrEnum):
    SUBJECT = "subject"
    PET = "pet"
    RELATED_PERSON = "related_person"


class FactRegistryError(ValueError):
    pass


@dataclass(frozen=True)
class FactTypeSpec:
    name: str
    entity_kind: EntityKind
    qualifier_required: bool = False
    allowed_qualifiers: tuple[str, ...] = ()
    defines_entity_identity: bool = False
    cardinality: str = "one_per_entity"


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
    "person.name": FactTypeSpec("person.name", EntityKind.SUBJECT),
    "person.current_location": FactTypeSpec(
        "person.current_location", EntityKind.SUBJECT
    ),
    "person.preference": FactTypeSpec(
        "person.preference",
        EntityKind.SUBJECT,
        qualifier_required=True,
        allowed_qualifiers=PREFERENCE_QUALIFIERS,
    ),
    "person.shoe_size": FactTypeSpec("person.shoe_size", EntityKind.SUBJECT),
    "pet.name": FactTypeSpec("pet.name", EntityKind.PET, defines_entity_identity=True),
    "pet.breed": FactTypeSpec("pet.breed", EntityKind.PET),
    "relationship.person": FactTypeSpec(
        "relationship.person",
        EntityKind.RELATED_PERSON,
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
        allowed = ", ".join(spec.allowed_qualifiers)
        raise FactRegistryError(
            f"Invalid qualifier '{normalized}' for {spec.name}; allowed: {allowed}"
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
