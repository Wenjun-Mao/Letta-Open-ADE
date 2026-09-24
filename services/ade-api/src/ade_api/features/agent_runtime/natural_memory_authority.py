"""Claim-scoped authority checks shared by compact reviewer evidence modes."""

from __future__ import annotations

import re

from .errors import RuntimeValidationError
from .memory_intent import is_explicit_forgetting_request
from .memory_policy import (
    _claim_clause,
    _claim_is_uncertain,
    _value_supported,
)
from .memory_review import BoundEvidence
from .natural_memory_binding import NaturalBindingMap
from .natural_memory_review import (
    BoundNaturalSource,
    DirectEvidence,
    EndorseAssistantEvidence,
    NaturalForget,
    NaturalWrite,
    ResolveUserEvidence,
)

_NO_SAVE = re.compile(
    r"\b(?:do not|don't|never)\s+(?:save|remember|store)\b|(?:不要|别)(?:记住|保存|存储)",
    re.I,
)
_WITHDRAWN = re.compile(
    r"\b(?:withdraw|take that back|ignore that claim)\b|撤回|收回", re.I
)
_ANAPHOR = re.compile(r"\b(?:that|this|it)\b|这个|这件|这条|它", re.I)
_SAVE_PERMISSION = re.compile(
    r"\b(?:you can|please|go ahead and|it's okay to)\s+(?:save|remember|store)\b"
    r"|(?:可以|请|现在能)(?:记住|保存|存储)",
    re.I,
)
_ASSERTION = re.compile(
    r"\b(?:am|is|are|have|has|like|likes|prefer|prefers|live|lives|own|owns)\b"
    r"|(?:是|喜欢|住在|拥有)",
    re.I,
)
_AFFIRMATIVE = re.compile(
    r"^(?:yes|yeah|yep|correct|exactly|sure|是|对|没错)(?:[\s,，.!。]|$)",
    re.I,
)
_NEGATED = re.compile(
    r"\b(?:no|not|don't|never|maybe|might|if)\b|不是|不对|可能|如果", re.I
)
_CLAUSE = re.compile(r"[^.!?。！？;；]+")


def has_no_save_restriction(content: str) -> bool:
    return bool(_NO_SAVE.search(content))


def restricted_scope(content: str, source: BoundNaturalSource) -> str:
    before = content[: source.start_char]
    prior = re.split(r"[.!?。！？;；]", before)[-1]
    return (
        f"{prior} {source.quote}"
        if _bare_anaphoric_restriction(source.quote)
        else _claim_clause(content, source.start_char, source.end_char)
    )


def validate_write_authority(
    item: NaturalWrite,
    binding: NaturalBindingMap,
    sources: tuple[BoundNaturalSource, ...],
    anchor: BoundNaturalSource,
    *,
    value: str | None,
) -> None:
    evidence = item.evidence
    current = str(binding.current["content"])
    current_bound = _bound_evidence(anchor)
    if not isinstance(item, NaturalForget) and _claim_is_uncertain(
        current, current_bound
    ):
        raise RuntimeValidationError("Uncertain current claim cannot become durable")
    if not isinstance(item, NaturalForget) and _no_save_restricts(current, anchor):
        raise RuntimeValidationError("No-save restriction blocks this write")
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
        _validate_removal(evidence, binding, current)
        return
    if value is not None:
        inherited = _inherited_restrictions(value, binding)
        if "no_save" in inherited and not _explicit_save_change(value, anchor):
            raise RuntimeValidationError("Inherited no-save blocks this write")
        if inherited & {"uncertain", "withdrawn"} and not _fresh_current_assertion(
            value, anchor
        ):
            raise RuntimeValidationError("Inherited restriction blocks this write")
    if value is not None:
        factual = anchor.quote
        if isinstance(evidence, (ResolveUserEvidence, EndorseAssistantEvidence)):
            factual += " " + sources[1].quote
        if not _value_supported(value, factual):
            raise RuntimeValidationError(
                "Value is unsupported by permitted factual sources"
            )


def _inherited_restrictions(value: str, binding: NaturalBindingMap) -> set[str]:
    """Retain restrictions on a claim through later mode changes in this exchange."""

    restrictions: set[str] = set()
    last_user_claim = ""
    for _, message in binding.ordered_messages:
        if message["role"] != "user":
            continue
        content = str(message["content"])
        for match in _CLAUSE.finditer(content):
            clause = match.group().strip()
            if not clause:
                continue
            no_save = bool(_NO_SAVE.search(clause))
            withdrawn = bool(_WITHDRAWN.search(clause))
            restricted = no_save or withdrawn
            uncertain = _claim_is_uncertain(
                content,
                BoundEvidence(
                    str(message["id"]), match.start(), match.end(), clause, ""
                ),
            )
            if restricted or uncertain:
                scope = clause
                if restricted and _bare_anaphoric_restriction(clause):
                    scope = last_user_claim
                if scope and _value_supported(value, scope):
                    if no_save:
                        restrictions.add("no_save")
                    if withdrawn:
                        restrictions.add("withdrawn")
                    if uncertain:
                        restrictions.add("uncertain")
            else:
                last_user_claim = clause
    return restrictions


def _fresh_current_assertion(value: str, anchor: BoundNaturalSource) -> bool:
    # A bare answer or assent cannot reset a prior claim's qualifications.
    quote = anchor.quote
    if not _value_supported(value, quote) or "?" in quote or "？" in quote:
        return False
    if not _ASSERTION.search(quote):
        return False
    return True


def _explicit_save_change(value: str, anchor: BoundNaturalSource) -> bool:
    # Permission must be in the cited current span and identify this claim.
    for match in _SAVE_PERMISSION.finditer(anchor.quote):
        scope = _claim_clause(anchor.quote, match.start(), match.end())
        if _ANAPHOR.search(scope) or _value_supported(value, scope):
            return True
    return False


def _no_save_restricts(content: str, anchor: BoundNaturalSource) -> bool:
    if _NO_SAVE.search(_claim_clause(content, anchor.start_char, anchor.end_char)):
        return True
    after = content[anchor.end_char :]
    next_sentence = re.match(r"\s*[.!?。！？;；]?\s*([^.!?。！？;；]*)", after)
    return bool(
        next_sentence
        and _NO_SAVE.search(next_sentence.group(1))
        and _bare_anaphoric_restriction(next_sentence.group(1))
    )


def _bare_anaphoric_restriction(clause: str) -> bool:
    remaining = _NO_SAVE.sub("", _WITHDRAWN.sub("", clause)).strip()
    remaining = re.sub(r"^I\s+", "", remaining, flags=re.I)
    return bool(
        re.fullmatch(
            r"(?:that|this|it)(?:\s+(?:claim|fact|one))?|这个|这件|这条|它",
            remaining,
            re.I,
        )
    )


def _bound_evidence(source: BoundNaturalSource) -> BoundEvidence:
    return BoundEvidence(
        source.message_id,
        source.start_char,
        source.end_char,
        source.quote,
        source.message_sha256,
    )


def _validate_removal(
    evidence: DirectEvidence | ResolveUserEvidence | EndorseAssistantEvidence,
    binding: NaturalBindingMap,
    current: str,
) -> None:
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
