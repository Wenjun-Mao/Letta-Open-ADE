"""Stage a mixed natural-memory review before any embeddings or database writes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .errors import RuntimeValidationError
from .fact_registry import EntityKind, fact_key, fact_type_spec
from .memory_intent import is_explicit_forgetting_request
from .memory_policy import NewEntity, _claim_is_uncertain, _normalize, _value_supported
from .memory_review import BoundEvidence
from .natural_memory_review import (
    BoundNaturalSource,
    NaturalAdd,
    NaturalEnd,
    NaturalForget,
    NaturalProposal,
    NaturalReassert,
    NaturalReviewDecision,
    NaturalRevise,
    bind_natural_sources,
)


_NO_SAVE = re.compile(
    r"\b(?:do not|don't|never)\s+(?:save|remember|store)\b|不要(?:记住|保存|存储)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PreparedNaturalOperation:
    proposal: NaturalProposal
    fact_type: str
    qualifier: str | None
    value: str | None
    normalized_key: str
    entity_id: str
    sources: tuple[BoundNaturalSource, ...]
    existing_fact: dict[str, Any] | None
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
) -> PreparedNaturalReview:
    facts_by_id = {str(fact["id"]): fact for fact in facts}
    entities_by_id = {str(entity["id"]): entity for entity in entities}
    if subject_id not in entities_by_id:
        raise RuntimeValidationError("Memory subject entity is missing")
    staged_entities = _stage_identity_entities(decision.proposals)
    dispositions = {item.claim_id: item for item in decision.claim_dispositions}
    staged: list[PreparedNaturalOperation] = []
    touched_fact_ids: set[str] = set()
    add_keys: set[str] = set()
    forgotten_keys: set[str] = set()
    added_preferences: set[tuple[str, str | None, str]] = set()
    forgotten_preferences: set[tuple[str, str | None, str]] = set()
    current_keys = {
        str(fact["normalized_key"])
        for fact in facts
        if fact["status"] in {"active", "inactive"}
    }

    for index, proposal in enumerate(decision.proposals):
        sources = bind_natural_sources(
            proposal,
            current_user_message=current_user_message,
            available_messages=available_messages,
        )
        _validate_claim(proposal, sources, current_user_message, facts_by_id)
        disposition = dispositions[proposal.claim_id]
        if disposition.outcome == "allow" and not isinstance(proposal, NaturalForget):
            if _claim_sentence_has_no_save(
                str(current_user_message["content"]), sources, proposal
            ):
                raise RuntimeValidationError("No-save clause cannot authorize a write")
        if disposition.reason == "reply_conflict":
            quote = disposition.candidate_reply_quote
            if not quote or candidate_reply.count(quote) != 1:
                raise RuntimeValidationError(
                    "Reply-conflict disposition must cite one visible candidate span"
                )
        existing: dict[str, Any] | None = None
        if isinstance(proposal, NaturalAdd):
            spec = fact_type_spec(proposal.fact_type)
            fact_type = proposal.fact_type
            qualifier = proposal.qualifier
            entity_id = _resolve_add_entity(
                proposal,
                subject_id=subject_id,
                expected_kind=spec.entity_kind,
                entities_by_id=entities_by_id,
                staged_entities=staged_entities,
                index=index,
            )
            value: str | None = proposal.value
            next_status = "active"
            reason = None
        else:
            existing = facts_by_id.get(proposal.fact_id)
            if existing is None or str(existing["subject_id"]) != subject_id:
                raise RuntimeValidationError(
                    "Memory target is outside the bound subject"
                )
            if int(existing["version"]) != proposal.expected_version:
                raise RuntimeValidationError("Memory target version changed")
            if proposal.fact_id in touched_fact_ids:
                raise RuntimeValidationError("A record can change only once per review")
            touched_fact_ids.add(proposal.fact_id)
            _validate_target_status(proposal, str(existing["status"]))
            fact_type = str(existing["fact_type"])
            qualifier = existing.get("qualifier")
            entity_id = str(existing["entity_id"])
            value = (
                None
                if isinstance(proposal, NaturalForget)
                else str(existing["value"])
                if isinstance(proposal, NaturalEnd)
                else proposal.value
            )
            next_status = (
                "forgotten"
                if isinstance(proposal, NaturalForget)
                else "inactive"
                if isinstance(proposal, NaturalEnd)
                or isinstance(proposal, NaturalRevise)
                and proposal.value is None
                else "active"
            )
            reason = (
                "forgotten"
                if isinstance(proposal, NaturalForget)
                else "reasserted"
                if isinstance(proposal, NaturalReassert)
                else "invalidated"
                if isinstance(proposal, NaturalRevise) and proposal.value is None
                else proposal.reason
            )
        base_key = fact_key(fact_type, entity_id, qualifier)
        key = (
            f"{base_key}|assertion:{uuid4()}"
            if isinstance(proposal, NaturalAdd) and fact_type == "person.preference"
            else str(existing["normalized_key"])
            if existing is not None
            else base_key
        )
        if isinstance(proposal, NaturalAdd):
            if fact_type == "person.preference":
                identity = (entity_id, qualifier, _normalize(proposal.value))
                if identity in added_preferences or any(
                    str(fact["entity_id"]) == entity_id
                    and fact["fact_type"] == fact_type
                    and fact.get("qualifier") == qualifier
                    and fact["status"] in {"active", "inactive"}
                    and _normalize(str(fact["value"])) == identity[2]
                    for fact in facts
                ):
                    raise RuntimeValidationError(
                        "Equivalent preference requires an existing assertion target"
                    )
                added_preferences.add(identity)
            else:
                if key in current_keys or key in add_keys:
                    raise RuntimeValidationError(
                        "Add collides with a current memory slot"
                    )
                add_keys.add(key)
        if isinstance(proposal, NaturalForget):
            if fact_type == "person.preference":
                forgotten_preferences.add(
                    (entity_id, qualifier, _normalize(str(existing["value"])))
                )
            else:
                forgotten_keys.add(key)
        staged.append(
            PreparedNaturalOperation(
                proposal=proposal,
                fact_type=fact_type,
                qualifier=qualifier,
                value=value,
                normalized_key=key,
                entity_id=entity_id,
                sources=sources,
                existing_fact=existing,
                next_status=next_status,
                revision_reason=reason,
            )
        )

    # Check across the complete proposal set, including deferred claims. Proposal
    # order must never make a contradictory add/forget pair look valid.
    if add_keys.intersection(forgotten_keys) or added_preferences.intersection(
        forgotten_preferences
    ):
        raise RuntimeValidationError("A review cannot forget and recreate one slot")
    if any(item.outcome == "contradiction" for item in dispositions.values()):
        raise RuntimeValidationError(
            "Candidate reply contradicts a reviewed memory claim",
            detail_code="natural_memory_reply_conflict",
        )
    allowed = tuple(
        operation
        for operation in staged
        if dispositions[operation.proposal.claim_id].outcome == "allow"
    )
    used_entities = {operation.entity_id for operation in allowed}
    identity_entities = {
        operation.entity_id
        for operation in allowed
        if isinstance(operation.proposal, NaturalAdd)
        and fact_type_spec(operation.proposal.fact_type).defines_entity_identity
    }
    staged_entity_ids = {entity.id for entity in staged_entities.values()}
    if (used_entities & staged_entity_ids) - identity_entities:
        raise RuntimeValidationError(
            "A surviving related fact requires a surviving entity identity claim"
        )
    deferred = tuple(
        {"claim_id": item.claim_id, "reason": item.reason}
        for item in decision.claim_dispositions
        if item.outcome == "defer"
    )
    return PreparedNaturalReview(
        new_entities=tuple(
            entity for entity in staged_entities.values() if entity.id in used_entities
        ),
        operations=allowed,
        deferred_claims=deferred,
    )


def _validate_claim(
    proposal: NaturalProposal,
    sources: tuple[BoundNaturalSource, ...],
    current_user_message: dict[str, Any],
    facts_by_id: dict[str, dict[str, Any]],
) -> None:
    current_source = next(
        item for item in sources if item.authority_role != "assistant_referent"
    )
    evidence = BoundEvidence(
        message_id=current_source.message_id,
        start_char=current_source.start_char,
        end_char=current_source.end_char,
        quote=current_source.quote,
        message_sha256=current_source.message_sha256,
    )
    if not isinstance(proposal, NaturalForget) and _claim_is_uncertain(
        str(current_user_message["content"]), evidence
    ):
        raise RuntimeValidationError("Uncertain claims cannot become durable memory")
    if isinstance(proposal, NaturalForget):
        if not is_explicit_forgetting_request(current_source.quote):
            raise RuntimeValidationError("Forget requires explicit user removal intent")
        return
    if isinstance(proposal, (NaturalAdd, NaturalRevise, NaturalReassert)) and (
        proposal.value is not None
    ):
        support = " ".join(item.quote for item in sources)
        prior = facts_by_id.get(getattr(proposal, "fact_id", ""))
        if prior is not None:
            support += f" {prior.get('value') or ''}"
        if not _value_supported(proposal.value, support):
            raise RuntimeValidationError("Memory value is unsupported by bound spans")


def _claim_sentence_has_no_save(
    content: str,
    sources: tuple[BoundNaturalSource, ...],
    proposal: NaturalProposal,
) -> bool:
    current = next(
        item for item in sources if item.authority_role != "assistant_referent"
    )
    start = max(
        (
            match.end()
            for match in re.finditer(r"[.!?。！？；\n]", content)
            if match.end() <= current.start_char
        ),
        default=0,
    )
    next_boundary = re.search(r"[.!?。！？；\n]", content[current.end_char :])
    end = (
        current.end_char + next_boundary.start()
        if next_boundary is not None
        else len(content)
    )
    sentence = content[start:end]
    if _NO_SAVE.search(proposal.evidence_quote):
        return True
    value = getattr(proposal, "value", None)
    for match in _NO_SAVE.finditer(sentence):
        after = re.split(
            r"[,，]\s*(?:but|however|yet|不过|但|可是)\b",
            sentence[match.start() :],
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        if value is not None and _normalize(str(value)) in _normalize(after):
            return True
        absolute_match_start = start + match.start()
        if absolute_match_start >= current.end_char and re.search(
            r"\b(?:that|it|this)\b|这(?:个|件|条)?|它", after, re.IGNORECASE
        ):
            return True
    return False


def _validate_target_status(proposal: NaturalProposal, status: str) -> None:
    if isinstance(proposal, (NaturalRevise, NaturalEnd)) and status != "active":
        raise RuntimeValidationError("Revision/end requires an active record")
    if isinstance(proposal, NaturalReassert) and status != "inactive":
        raise RuntimeValidationError("Reassert requires an inactive record")
    if isinstance(proposal, NaturalForget) and status not in {"active", "inactive"}:
        raise RuntimeValidationError("Forget requires an active or inactive record")


def _stage_identity_entities(
    proposals: list[NaturalProposal],
) -> dict[str, NewEntity]:
    staged: dict[str, NewEntity] = {}
    for index, proposal in enumerate(proposals):
        if not isinstance(proposal, NaturalAdd):
            continue
        spec = fact_type_spec(proposal.fact_type)
        if not spec.defines_entity_identity or spec.entity_kind is EntityKind.SUBJECT:
            continue
        reference = str(proposal.entity_ref or "").strip() or f"new:auto-{index}"
        if reference.startswith("existing:"):
            continue
        if not reference.startswith("new:") or not reference.removeprefix("new:"):
            raise RuntimeValidationError("Identity requires a new or existing entity")
        prior = staged.get(reference)
        if prior is not None and prior.kind != spec.entity_kind.value:
            raise RuntimeValidationError("Entity reference crosses entity kinds")
        staged.setdefault(
            reference,
            NewEntity(
                id=str(uuid4()),
                kind=spec.entity_kind.value,
                label=proposal.new_entity_label.strip() or proposal.value.strip(),
            ),
        )
    return staged


def _resolve_add_entity(
    proposal: NaturalAdd,
    *,
    subject_id: str,
    expected_kind: EntityKind,
    entities_by_id: dict[str, dict[str, Any]],
    staged_entities: dict[str, NewEntity],
    index: int,
) -> str:
    if expected_kind is EntityKind.SUBJECT:
        if proposal.entity_ref:
            raise RuntimeValidationError("Subject facts cannot select an entity")
        return subject_id
    reference = str(proposal.entity_ref or "").strip() or f"new:auto-{index}"
    if reference.startswith("existing:"):
        entity = entities_by_id.get(reference.removeprefix("existing:"))
        if (
            entity is None
            or str(entity["subject_id"]) != subject_id
            or entity["kind"] != expected_kind.value
        ):
            raise RuntimeValidationError("Entity is outside the bound subject/kind")
        return str(entity["id"])
    entity = staged_entities.get(reference)
    if entity is None or entity.kind != expected_kind.value:
        raise RuntimeValidationError("New entity requires a staged identity claim")
    return entity.id
