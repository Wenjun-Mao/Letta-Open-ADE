from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .errors import RuntimeValidationError
from .fact_registry import EntityKind, fact_key, fact_type_spec
from .memory_review import (
    AddProposal,
    BoundEvidence,
    CorrectProposal,
    ForgetProposal,
    MergeProposal,
    ReviewDecision,
    ReviewProposal,
    bind_evidence,
)


_UNCERTAIN_MARKERS = (
    "maybe",
    "perhaps",
    "might",
    "possibly",
    "guess",
    "也许",
    "可能",
    "大概",
    "猜",
)
_FORGET_MARKERS = ("forget", "remove", "delete", "忘", "删除", "不要记")
_VALUE_STOPWORDS = {"a", "an", "and", "as", "is", "my", "the", "to"}


@dataclass(frozen=True)
class NewEntity:
    id: str
    kind: str
    label: str


@dataclass(frozen=True)
class PreparedMemoryOperation:
    proposal: ReviewProposal
    normalized_key: str
    entity_id: str
    evidence: BoundEvidence
    existing_fact: dict[str, Any] | None = None
    merge_facts: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class PreparedMemoryReview:
    new_entities: tuple[NewEntity, ...]
    operations: tuple[PreparedMemoryOperation, ...]


def prepare_memory_review(
    *,
    decision: ReviewDecision,
    subject_id: str,
    current_user_message: dict[str, Any],
    active_facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
) -> PreparedMemoryReview:
    content = str(current_user_message.get("content", ""))
    facts_by_id = {str(fact["id"]): fact for fact in active_facts}
    entities_by_id = {str(entity["id"]): entity for entity in entities}
    if subject_id not in entities_by_id:
        raise RuntimeValidationError("Memory subject entity is missing")
    new_by_ref = _stage_identity_entities(decision.proposals)
    operations: list[PreparedMemoryOperation] = []
    projected_keys = {
        str(fact["normalized_key"]): str(fact["id"]) for fact in active_facts
    }
    mutated_fact_ids: set[str] = set()

    for index, proposal in enumerate(decision.proposals):
        evidence = bind_evidence(proposal, user_messages=[current_user_message])
        _validate_claim_semantics(proposal, content, facts_by_id)
        spec = fact_type_spec(proposal.fact_type)
        existing_fact: dict[str, Any] | None = None
        merge_facts: tuple[dict[str, Any], ...] = ()

        if isinstance(proposal, (CorrectProposal, ForgetProposal)):
            existing_fact = facts_by_id.get(proposal.fact_id)
            if existing_fact is None:
                raise RuntimeValidationError(
                    f"{proposal.operation.value} requires an active subject fact"
                )
            _validate_existing_fact(proposal, existing_fact, subject_id)
            entity_id = str(existing_fact["entity_id"])
            target_ids = {str(existing_fact["id"])}
        elif isinstance(proposal, MergeProposal):
            merge_facts = tuple(
                facts_by_id.get(fact_id) for fact_id in proposal.target_fact_ids
            )
            if len(merge_facts) < 2 or any(fact is None for fact in merge_facts):
                raise RuntimeValidationError(
                    "merge requires at least two active subject facts"
                )
            typed_merge_facts = tuple(fact for fact in merge_facts if fact is not None)
            _validate_merge(proposal, typed_merge_facts, subject_id)
            merge_facts = typed_merge_facts
            entity_id = str(merge_facts[0]["entity_id"])
            target_ids = {str(fact["id"]) for fact in merge_facts}
        elif isinstance(proposal, AddProposal):
            entity_id = _resolve_add_entity(
                proposal=proposal,
                subject_id=subject_id,
                expected_kind=spec.entity_kind,
                entities_by_id=entities_by_id,
                new_by_ref=new_by_ref,
                index=index,
            )
            target_ids = set()
        else:  # pragma: no cover - ReviewProposal is a closed union.
            raise AssertionError("unsupported memory proposal")

        repeated = mutated_fact_ids.intersection(target_ids)
        if repeated:
            raise RuntimeValidationError(
                f"A fact can change only once per review: {sorted(repeated)}"
            )
        mutated_fact_ids.update(target_ids)
        for fact_id in target_ids:
            projected_keys.pop(str(facts_by_id[fact_id]["normalized_key"]), None)

        key = fact_key(proposal.fact_type, entity_id, proposal.qualifier)
        if not isinstance(proposal, ForgetProposal):
            collision = projected_keys.get(key)
            if collision is not None:
                raise RuntimeValidationError(
                    f"An active or staged fact already uses key '{key}'"
                )
            projected_keys[key] = (
                proposal.fact_id
                if isinstance(proposal, CorrectProposal)
                else f"staged:{index}"
            )

        operations.append(
            PreparedMemoryOperation(
                proposal=proposal,
                normalized_key=key,
                entity_id=entity_id,
                evidence=evidence,
                existing_fact=existing_fact,
                merge_facts=merge_facts,
            )
        )

    return PreparedMemoryReview(
        new_entities=tuple(new_by_ref.values()),
        operations=tuple(operations),
    )


def _validate_claim_semantics(
    proposal: ReviewProposal,
    current_content: str,
    facts_by_id: dict[str, dict[str, Any]],
) -> None:
    normalized_content = _normalize(current_content)
    if not isinstance(proposal, ForgetProposal) and any(
        marker in normalized_content for marker in _UNCERTAIN_MARKERS
    ):
        raise RuntimeValidationError(
            "Uncertain or hypothetical claims cannot become durable memory"
        )
    evidence = _normalize(proposal.evidence_quote)
    if isinstance(proposal, ForgetProposal) and not any(
        marker in evidence for marker in _FORGET_MARKERS
    ):
        raise RuntimeValidationError("forget requires explicit user removal intent")
    if isinstance(proposal, ForgetProposal):
        return
    support = [proposal.evidence_quote]
    if isinstance(proposal, CorrectProposal) and proposal.fact_id in facts_by_id:
        support.append(str(facts_by_id[proposal.fact_id].get("value") or ""))
    if isinstance(proposal, MergeProposal):
        for fact_id in proposal.target_fact_ids:
            fact = facts_by_id.get(fact_id)
            if fact is not None:
                support.append(str(fact.get("value") or ""))
    if not _value_supported(proposal.value, " ".join(support)):
        raise RuntimeValidationError(
            "Memory value is not supported by current evidence and referenced facts"
        )


def _validate_existing_fact(
    proposal: CorrectProposal | ForgetProposal,
    fact: dict[str, Any],
    subject_id: str,
) -> None:
    if str(fact["subject_id"]) != subject_id or fact["status"] != "active":
        raise RuntimeValidationError("Memory fact is not active for the bound subject")
    if int(fact["version"]) != proposal.expected_version:
        raise RuntimeValidationError("Memory fact version changed before review")
    if (
        fact["fact_type"] != proposal.fact_type
        or fact.get("qualifier") != proposal.qualifier
    ):
        raise RuntimeValidationError(
            "Reviewed fact metadata does not match the selected fact"
        )


def _validate_merge(
    proposal: MergeProposal,
    facts: tuple[dict[str, Any], ...],
    subject_id: str,
) -> None:
    entity_ids = {str(fact["entity_id"]) for fact in facts}
    if len(entity_ids) != 1:
        raise RuntimeValidationError("merge targets must belong to one entity")
    for fact in facts:
        fact_id = str(fact["id"])
        if str(fact["subject_id"]) != subject_id or fact["status"] != "active":
            raise RuntimeValidationError("merge target is outside the bound subject")
        if proposal.expected_versions.get(fact_id) != int(fact["version"]):
            raise RuntimeValidationError("merge target version changed before review")
        if fact["fact_type"] != proposal.fact_type:
            raise RuntimeValidationError(
                "merge targets must use the reviewed fact type"
            )


def _resolve_add_entity(
    *,
    proposal: AddProposal,
    subject_id: str,
    expected_kind: EntityKind,
    entities_by_id: dict[str, dict[str, Any]],
    new_by_ref: dict[str, NewEntity],
    index: int,
) -> str:
    if expected_kind is EntityKind.SUBJECT:
        if proposal.entity_ref:
            raise RuntimeValidationError("Subject facts cannot select an entity")
        return subject_id
    reference = str(proposal.entity_ref or "").strip()
    if reference.startswith("existing:"):
        entity_id = reference.removeprefix("existing:").strip()
        entity = entities_by_id.get(entity_id)
        if (
            entity is None
            or str(entity["subject_id"]) != subject_id
            or entity["kind"] != expected_kind.value
        ):
            raise RuntimeValidationError(
                "Reviewed entity does not belong to the bound subject"
            )
        return entity_id
    spec = fact_type_spec(proposal.fact_type)
    if not reference and spec.defines_entity_identity:
        reference = f"new:auto-{index}"
    if not reference.startswith("new:") or not reference.removeprefix("new:").strip():
        raise RuntimeValidationError(
            f"{proposal.fact_type} requires existing:<id> or new:<local-ref>"
        )
    prior = new_by_ref.get(reference)
    if prior is not None:
        if prior.kind != expected_kind.value:
            raise RuntimeValidationError("entity_ref was reused with another kind")
        return prior.id
    if any(entity.kind == expected_kind.value for entity in new_by_ref.values()):
        raise RuntimeValidationError(
            f"{proposal.fact_type} must reuse the new entity_ref from its identity fact"
        )
    label = proposal.new_entity_label.strip()
    entity = NewEntity(id=str(uuid4()), kind=expected_kind.value, label=label)
    new_by_ref[reference] = entity
    return entity.id


def _stage_identity_entities(
    proposals: list[ReviewProposal],
) -> dict[str, NewEntity]:
    staged: dict[str, NewEntity] = {}
    for index, proposal in enumerate(proposals):
        if not isinstance(proposal, AddProposal):
            continue
        spec = fact_type_spec(proposal.fact_type)
        if not spec.defines_entity_identity or spec.entity_kind is EntityKind.SUBJECT:
            continue
        reference = str(proposal.entity_ref or "").strip() or f"new:auto-{index}"
        if reference.startswith("existing:"):
            continue
        if (
            not reference.startswith("new:")
            or not reference.removeprefix("new:").strip()
        ):
            raise RuntimeValidationError(
                f"{proposal.fact_type} requires existing:<id> or new:<local-ref>"
            )
        prior = staged.get(reference)
        if prior is not None:
            if prior.kind != spec.entity_kind.value:
                raise RuntimeValidationError("entity_ref was reused with another kind")
            continue
        staged[reference] = NewEntity(
            id=str(uuid4()),
            kind=spec.entity_kind.value,
            label=proposal.new_entity_label.strip() or proposal.value.strip(),
        )
    return staged


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


def _terms(value: str) -> set[str]:
    normalized = _normalize(value).replace("_", " ")
    latin = set(re.findall(r"[a-z0-9_]+", normalized)) - _VALUE_STOPWORDS
    cjk = set(re.findall(r"[\u4e00-\u9fff]", normalized))
    return latin | cjk


def _value_supported(value: str, support: str) -> bool:
    normalized_value = _normalize(value)
    normalized_support = _normalize(support)
    if not normalized_value:
        return False
    if normalized_value in normalized_support:
        return True
    terms = _terms(normalized_value)
    return bool(terms) and terms.issubset(_terms(normalized_support))
