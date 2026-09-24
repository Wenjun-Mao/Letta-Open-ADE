"""Bind compact natural decisions once to ADE-owned mutation records."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .errors import RuntimeValidationError
from .fact_registry import EntityKind, fact_key, fact_type_spec, normalize_qualifier
from .memory_policy import NewEntity, _normalize, _value_supported
from .natural_memory_authority import (
    has_no_save_restriction,
    restricted_scope,
    validate_write_authority,
)
from .natural_memory_binding import NaturalBindingMap, build_natural_binding_map
from .natural_memory_review import (
    BoundNaturalSource,
    NaturalConflict,
    NaturalDefer,
    NaturalEnd,
    NaturalForget,
    NaturalReassert,
    NaturalRelatedAdd,
    NaturalReviewDecision,
    NaturalRevise,
    NaturalSubjectAdd,
    NaturalWrite,
    DirectEvidence,
    ResolveUserEvidence,
    bind_exact_quote,
)


@dataclass(frozen=True)
class PreparedNaturalOperation:
    proposal: NaturalWrite
    fact_type: str
    qualifier: str | None
    value: str | None
    normalized_key: str
    entity_id: str
    sources: tuple[BoundNaturalSource, ...]
    current_anchor: BoundNaturalSource
    existing_fact: Mapping[str, Any] | None
    next_status: str
    revision_reason: str | None


@dataclass(frozen=True)
class PreparedNaturalReview:
    new_entities: tuple[NewEntity, ...]
    operations: tuple[PreparedNaturalOperation, ...]
    deferred_claims: tuple[dict[str, str], ...]


def prepare_natural_memory_review(
    *,
    decision: NaturalReviewDecision,
    subject_id: str,
    current_user_message: dict[str, Any],
    available_messages: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    candidate_reply: str,
    binding_map: NaturalBindingMap | None = None,
) -> PreparedNaturalReview:
    binding = binding_map or build_natural_binding_map(
        current_user_message=current_user_message,
        source_messages=available_messages,
        facts=facts,
        entities=entities,
    )
    if not any(
        str(entity["id"]) == subject_id and entity["kind"] == "subject"
        for entity in entities
    ):
        raise RuntimeValidationError("Memory subject entity is missing")
    staged_entities = _stage_related_identities(decision)
    operations: list[PreparedNaturalOperation] = []
    touched: set[str] = set()
    add_keys: set[str] = set()
    deferrals: list[dict[str, str]] = []
    no_save_scopes: list[str] = []
    current_text = str(binding.current["content"])
    for item in decision.decisions:
        if isinstance(item, NaturalDefer):
            source = bind_exact_quote(
                binding.current, item.current_quote, "user_assertion"
            )
            if item.reason == "no_save":
                if not has_no_save_restriction(current_text):
                    raise RuntimeValidationError(
                        "No-save deferral lacks current restriction"
                    )
                no_save_scopes.append(restricted_scope(current_text, source))
            deferrals.append({"quote": item.current_quote, "reason": item.reason})
            continue
        if isinstance(item, NaturalConflict):
            bind_exact_quote(binding.current, item.current_quote, "user_assertion")
            if candidate_reply.count(item.candidate_reply_quote) != 1:
                raise RuntimeValidationError(
                    "Conflict must bind one exact candidate span",
                    detail_code="natural_review_binding",
                )
            if len(item.references) != len(set(item.references)):
                raise RuntimeValidationError(
                    "Duplicate conflict reference", detail_code="natural_review_binding"
                )
            grounding = [
                binding.targets.get(ref) or binding.identities.get(ref)
                for ref in item.references
            ]
            if any(value is None for value in grounding):
                raise RuntimeValidationError(
                    "Conflict reference is outside held snapshot",
                    detail_code="natural_review_binding",
                )
            if any(
                _candidate_agrees_with_reference(
                    item.candidate_reply_quote,
                    str(value.get("value") or value.get("label") or ""),
                )
                for value in grounding
                if value is not None
            ):
                raise RuntimeValidationError(
                    "Candidate span agrees with cited snapshot",
                    detail_code="natural_review_semantic",
                )
            raise RuntimeValidationError(
                "Candidate reply conflicts with held memory",
                detail_code="natural_memory_reply_conflict",
            )
        sources, anchor = _bind_evidence(item, binding)
        existing = None
        if isinstance(item, (NaturalSubjectAdd, NaturalRelatedAdd)):
            spec = fact_type_spec(item.fact_type)
            qualifier = normalize_qualifier(spec, item.qualifier)
            if isinstance(item, NaturalSubjectAdd):
                if spec.entity_kind is not EntityKind.SUBJECT:
                    raise RuntimeValidationError("Related fact requires related add")
                entity_id = subject_id
            else:
                if spec.entity_kind is EntityKind.SUBJECT:
                    raise RuntimeValidationError("Subject fact requires subject add")
                entity_id = _related_entity_id(
                    item, binding, staged_entities, subject_id
                )
            fact_type = item.fact_type
            value: str | None = item.value
            status = "active"
            reason = None
        else:
            existing = binding.targets.get(item.target)
            if existing is None or str(existing["subject_id"]) != subject_id:
                raise RuntimeValidationError(
                    "Target handle is outside held subject",
                    detail_code="natural_review_binding",
                )
            fact_id = str(existing["id"])
            if fact_id in touched:
                raise RuntimeValidationError("A record can change only once per review")
            touched.add(fact_id)
            _validate_target(item, str(existing["status"]))
            fact_type = str(existing["fact_type"])
            qualifier = existing.get("qualifier")
            entity_id = str(existing["entity_id"])
            value = (
                None
                if isinstance(item, NaturalForget)
                else str(existing.get("value") or "")
                if isinstance(item, NaturalEnd)
                else item.value
            )
            status = (
                "forgotten"
                if isinstance(item, NaturalForget)
                else "inactive"
                if isinstance(item, NaturalEnd)
                or isinstance(item, NaturalRevise)
                and item.value is None
                else "active"
            )
            reason = (
                "forgotten"
                if isinstance(item, NaturalForget)
                else "reasserted"
                if isinstance(item, NaturalReassert)
                else "invalidated"
                if isinstance(item, NaturalRevise) and item.value is None
                else item.reason
            )
        validate_write_authority(item, binding, sources, anchor, value=value)
        key = (
            str(existing["normalized_key"])
            if existing is not None
            else f"{fact_key(fact_type, entity_id, qualifier)}|assertion:{uuid4()}"
            if fact_type == "person.preference"
            else fact_key(fact_type, entity_id, qualifier)
        )
        if existing is None:
            if key in add_keys or (
                fact_type != "person.preference"
                and any(
                    str(fact["normalized_key"]) == key
                    for fact in binding.targets.values()
                )
            ):
                raise RuntimeValidationError(
                    "Add collides with an existing memory slot"
                )
            add_keys.add(key)
        operations.append(
            PreparedNaturalOperation(
                proposal=item,
                fact_type=fact_type,
                qualifier=qualifier,
                value=value,
                normalized_key=key,
                entity_id=entity_id,
                sources=sources,
                current_anchor=anchor,
                existing_fact=existing,
                next_status=status,
                revision_reason=reason,
            )
        )
    for operation in operations:
        if operation.next_status == "forgotten":
            continue
        if any(
            _value_supported(str(operation.value or ""), scope)
            for scope in no_save_scopes
        ):
            raise RuntimeValidationError("No-save deferral conflicts with a write")
    used = {operation.entity_id for operation in operations}
    identity_ids = {
        operation.entity_id
        for operation in operations
        if isinstance(operation.proposal, NaturalRelatedAdd)
        and fact_type_spec(operation.fact_type).defines_entity_identity
    }
    if (used & {entity.id for entity in staged_entities.values()}) - identity_ids:
        raise RuntimeValidationError(
            "Related write needs a surviving identity assertion"
        )
    return PreparedNaturalReview(
        new_entities=tuple(
            entity for entity in staged_entities.values() if entity.id in used
        ),
        operations=tuple(operations),
        deferred_claims=tuple(deferrals),
    )


def _bind_evidence(
    item: NaturalWrite, binding: NaturalBindingMap
) -> tuple[tuple[BoundNaturalSource, ...], BoundNaturalSource]:
    evidence = item.evidence
    role = (
        "user_assertion"
        if isinstance(evidence, DirectEvidence)
        else "user_resolution"
        if isinstance(evidence, ResolveUserEvidence)
        else "user_endorsement"
    )
    anchor = bind_exact_quote(binding.current, evidence.current_quote, role)
    if isinstance(evidence, DirectEvidence):
        return (anchor,), anchor
    support = binding.messages.get(evidence.support_handle)
    if support is None:
        raise RuntimeValidationError(
            "Support handle is outside admitted exchange",
            detail_code="natural_review_binding",
        )
    expected_role = "user" if isinstance(evidence, ResolveUserEvidence) else "assistant"
    if support["role"] != expected_role:
        raise RuntimeValidationError(
            "Support handle has wrong role", detail_code="natural_review_binding"
        )
    support_role = (
        "user_antecedent" if expected_role == "user" else "assistant_referent"
    )
    source = bind_exact_quote(support, evidence.support_quote, support_role)
    return (anchor, source), anchor


def _candidate_agrees_with_reference(candidate: str, value: str) -> bool:
    """Reject a claimed conflict when its answer states the cited value plainly."""

    normalized_value = _normalize(value)
    if not normalized_value:
        return False
    answer = _normalize(candidate)
    pattern = r"(?<!\w)" + re.escape(normalized_value) + r"(?!\w)"
    for match in re.finditer(pattern, answer):
        if not re.search(
            r"(?:\b(?:not|never|isn't|wasn't)\s+|不是)$", answer[: match.start()]
        ):
            return True
    return False


def _related_entity_id(
    item: NaturalRelatedAdd,
    binding: NaturalBindingMap,
    staged: dict[str, NewEntity],
    subject_id: str,
) -> str:
    spec = fact_type_spec(item.fact_type)
    if item.entity_ref.startswith("E"):
        entity = binding.identities.get(item.entity_ref)
        if (
            entity is None
            or str(entity["subject_id"]) != subject_id
            or entity["kind"] != spec.entity_kind.value
        ):
            raise RuntimeValidationError(
                "Related identity handle is invalid",
                detail_code="natural_review_binding",
            )
        return str(entity["id"])
    if not re.fullmatch(r"new:[a-z][a-z0-9_-]{0,63}", item.entity_ref):
        raise RuntimeValidationError(
            "New entity reference is invalid", detail_code="natural_review_binding"
        )
    entity = staged.get(item.entity_ref)
    if entity is None or entity.kind != spec.entity_kind.value:
        raise RuntimeValidationError(
            "New related fact requires identity assertion",
            detail_code="natural_review_binding",
        )
    return entity.id


def _stage_related_identities(decision: NaturalReviewDecision) -> dict[str, NewEntity]:
    """Resolve local joins without making decision order part of the wire contract."""

    staged: dict[str, NewEntity] = {}
    for item in decision.decisions:
        if not isinstance(item, NaturalRelatedAdd) or not item.entity_ref.startswith(
            "new:"
        ):
            continue
        spec = fact_type_spec(item.fact_type)
        if not spec.defines_entity_identity:
            continue
        identity = staged.get(item.entity_ref)
        if identity is not None:
            raise RuntimeValidationError("New related identity reference is duplicated")
        staged[item.entity_ref] = NewEntity(
            str(uuid4()), spec.entity_kind.value, item.value.strip()
        )
    return staged


def _validate_target(item: NaturalWrite, status: str) -> None:
    if isinstance(item, (NaturalRevise, NaturalEnd)) and status != "active":
        raise RuntimeValidationError("Revision/end requires an active target")
    if isinstance(item, NaturalReassert) and status != "inactive":
        raise RuntimeValidationError("Reassert requires an inactive target")
    if isinstance(item, NaturalForget) and status not in {"active", "inactive"}:
        raise RuntimeValidationError("Forget requires active/inactive target")
