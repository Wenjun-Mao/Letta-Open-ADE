"""Bind compact natural decisions once to ADE-owned mutation records."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from .errors import RuntimeValidationError
from .fact_registry import EntityKind, fact_key, fact_type_spec, normalize_qualifier
from .memory_intent import is_explicit_forgetting_request
from .memory_policy import (
    NewEntity,
    _claim_clause,
    _claim_is_uncertain,
    _normalize,
    _value_supported,
)
from .memory_review import BoundEvidence
from .natural_memory_binding import NaturalBindingMap, build_natural_binding_map
from .natural_memory_review import (
    BoundNaturalSource,
    DirectEvidence,
    EndorseAssistantEvidence,
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
    ResolveUserEvidence,
    bind_exact_quote,
)

_NO_SAVE = re.compile(
    r"\b(?:do not|don't|never)\s+(?:save|remember|store)\b|(?:不要|别)(?:记住|保存|存储)",
    re.I,
)
_WITHDRAWN = re.compile(
    r"\b(?:withdraw|take that back|ignore that claim)\b|撤回|收回", re.I
)
_AFFIRMATIVE = re.compile(
    r"^(?:yes|yeah|yep|correct|exactly|sure|是|对|没错)(?:[\s,，.!。]|$)", re.I
)
_NEGATED = re.compile(
    r"\b(?:no|not|don't|never|maybe|might|if)\b|不是|不对|可能|如果", re.I
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
                if not _NO_SAVE.search(current_text):
                    raise RuntimeValidationError(
                        "No-save deferral lacks current restriction"
                    )
                no_save_scopes.append(_restricted_scope(current_text, source))
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
                _normalize(str(value.get("value") or value.get("label") or ""))
                == _normalize(item.candidate_reply_quote)
                for value in grounding
                if value is not None
            ):
                raise RuntimeValidationError(
                    "Candidate span agrees with cited snapshot"
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
        _validate_semantics(item, binding, sources, anchor)
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


def _validate_semantics(
    item: NaturalWrite,
    binding: NaturalBindingMap,
    sources: tuple[BoundNaturalSource, ...],
    anchor: BoundNaturalSource,
) -> None:
    evidence = item.evidence
    current = str(binding.current["content"])
    current_bound = BoundEvidence(
        anchor.message_id,
        anchor.start_char,
        anchor.end_char,
        anchor.quote,
        anchor.message_sha256,
    )
    if not isinstance(item, NaturalForget) and _claim_is_uncertain(
        current, current_bound
    ):
        raise RuntimeValidationError("Uncertain current claim cannot become durable")
    if not isinstance(item, NaturalForget) and _no_save_restricts(current, anchor):
        raise RuntimeValidationError("No-save restriction blocks this write")
    if isinstance(evidence, ResolveUserEvidence):
        earlier = binding.messages[evidence.support_handle]
        earlier_text = str(earlier["content"])
        antecedent = sources[1]
        earlier_bound = BoundEvidence(
            antecedent.message_id,
            antecedent.start_char,
            antecedent.end_char,
            antecedent.quote,
            antecedent.message_sha256,
        )
        if (
            _claim_is_uncertain(earlier_text, earlier_bound)
            or _NO_SAVE.search(earlier_text)
            or _WITHDRAWN.search(earlier_text)
        ):
            raise RuntimeValidationError(
                "Restricted antecedent cannot become definite memory"
            )
        ordered = [value for _, value in binding.ordered_messages]
        start = ordered.index(earlier)
        if any(
            _NO_SAVE.search(str(value["content"]))
            or _WITHDRAWN.search(str(value["content"]))
            for value in ordered[start + 1 :]
            if value["role"] == "user"
        ):
            raise RuntimeValidationError("Intervening restriction withdraws antecedent")
    if isinstance(evidence, EndorseAssistantEvidence):
        if not _AFFIRMATIVE.match(evidence.current_quote.strip()) or _NEGATED.search(
            evidence.current_quote
        ):
            raise RuntimeValidationError("Current text is not explicit assent")
        proposition = evidence.support_quote
        if proposition.count("?") + proposition.count("？") != 1 or re.search(
            r"\bor\b|还是|或者", proposition, re.I
        ):
            raise RuntimeValidationError("Assistant assent has ambiguous proposition")
    if isinstance(item, NaturalForget):
        if isinstance(evidence, DirectEvidence):
            permitted = is_explicit_forgetting_request(current)
        elif isinstance(evidence, ResolveUserEvidence):
            permitted = is_explicit_forgetting_request(
                str(binding.messages[evidence.support_handle]["content"])
            )
        else:
            permitted = is_explicit_forgetting_request(
                evidence.support_quote.replace("Shall I ", "Please ")
            ) or bool(
                re.search(
                    r"\b(?:remove|delete|forget|erase)\b|删除|忘掉",
                    evidence.support_quote,
                    re.I,
                )
            )
        if not permitted:
            raise RuntimeValidationError(
                "Forget requires operation-specific removal assent"
            )
        return
    value = getattr(item, "value", None)
    if value is not None:
        factual = anchor.quote
        if isinstance(evidence, ResolveUserEvidence):
            factual += " " + sources[1].quote
        elif isinstance(evidence, EndorseAssistantEvidence):
            factual += " " + sources[1].quote
        if not _value_supported(value, factual):
            raise RuntimeValidationError(
                "Value is unsupported by permitted factual sources"
            )


def _no_save_restricts(content: str, anchor: BoundNaturalSource) -> bool:
    if _NO_SAVE.search(_claim_clause(content, anchor.start_char, anchor.end_char)):
        return True
    # A following anaphoric restriction attaches to the preceding claim only.
    after = content[anchor.end_char :]
    next_sentence = re.match(r"\s*[.!?。！？;；]?\s*([^.!?。！？;；]*)", after)
    return bool(
        next_sentence
        and _NO_SAVE.search(next_sentence.group(1))
        and re.search(
            r"\b(?:that|this|it)\b|这个|这件|这条|它", next_sentence.group(1), re.I
        )
    )


def _restricted_scope(content: str, source: BoundNaturalSource) -> str:
    before = content[: source.start_char]
    prior = re.split(r"[.!?。！？;；]", before)[-1]
    return (
        f"{prior} {source.quote}"
        if _NO_SAVE.search(source.quote)
        else _claim_clause(content, source.start_char, source.end_char)
    )


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
