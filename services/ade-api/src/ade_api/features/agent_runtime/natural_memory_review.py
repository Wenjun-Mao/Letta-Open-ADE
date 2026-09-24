"""Mixed, source-role-aware reviewer contract for new natural-memory bindings."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Annotated, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from .fact_registry import FactRegistryError, fact_type_spec, normalize_qualifier
from .errors import RuntimeValidationError
from .memory_review import FactTypeName, QualifierName


SourceRole: TypeAlias = Literal[
    "user_assertion", "user_endorsement", "assistant_referent"
]
RevisionReason: TypeAlias = Literal["enrich", "supersede", "correct", "unspecified"]
EndingReason: TypeAlias = Literal["ended", "invalidated"]
DispositionReason: TypeAlias = Literal[
    "supported",
    "unresolved_reference",
    "no_save",
    "reply_conflict",
]


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message_id: StrictStr = Field(min_length=1, max_length=100)
    quote: StrictStr = Field(min_length=1, max_length=10_000)
    role: SourceRole


class _NaturalProposalBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: StrictStr = Field(min_length=1, max_length=100)
    evidence_quote: StrictStr = Field(min_length=1, max_length=10_000)
    sources: list[SourceRef] = Field(min_length=1, max_length=12)


class NaturalAdd(_NaturalProposalBase):
    operation: Literal["add"]
    fact_type: FactTypeName
    qualifier: QualifierName | None = None
    value: StrictStr = Field(min_length=1, max_length=10_000)
    entity_ref: StrictStr | None = None
    new_entity_label: StrictStr = Field(default="", max_length=500)

    @model_validator(mode="after")
    def _fact_contract(self) -> NaturalAdd:
        try:
            spec = fact_type_spec(self.fact_type)
            self.qualifier = normalize_qualifier(spec, self.qualifier)
        except FactRegistryError as exc:
            raise ValueError(str(exc)) from exc
        if not self.value.strip():
            raise ValueError("add value must not be blank")
        return self


class _NaturalTarget(_NaturalProposalBase):
    fact_id: StrictStr = Field(min_length=1, max_length=100)
    expected_version: StrictInt = Field(ge=1)


class NaturalRevise(_NaturalTarget):
    operation: Literal["revise"]
    reason: RevisionReason
    value: StrictStr | None = Field(max_length=10_000)

    @model_validator(mode="after")
    def _revision_value_contract(self) -> NaturalRevise:
        if self.value is None and self.reason != "correct":
            raise ValueError("null revision requires a correction/invalidation")
        if self.value is not None and not self.value.strip():
            raise ValueError("revision value must not be blank")
        return self


class NaturalEnd(_NaturalTarget):
    operation: Literal["end"]
    reason: EndingReason
    value: None


class NaturalReassert(_NaturalTarget):
    operation: Literal["reassert"]
    value: StrictStr = Field(min_length=1, max_length=10_000)

    @field_validator("value")
    @classmethod
    def _nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reasserted value must not be blank")
        return value


class NaturalForget(_NaturalTarget):
    operation: Literal["forget"]
    value: None


NaturalProposal: TypeAlias = Annotated[
    NaturalAdd | NaturalRevise | NaturalEnd | NaturalReassert | NaturalForget,
    Field(discriminator="operation"),
]


class ClaimDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: StrictStr = Field(min_length=1, max_length=100)
    outcome: Literal["allow", "defer", "contradiction"]
    reason: DispositionReason
    candidate_reply_quote: StrictStr | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def _matching_reason(self) -> ClaimDisposition:
        allowed = {
            "allow": {"supported"},
            "defer": {"unresolved_reference", "no_save"},
            "contradiction": {"reply_conflict"},
        }
        if self.reason not in allowed[self.outcome]:
            raise ValueError("claim disposition reason does not match outcome")
        if (self.reason == "reply_conflict") != bool(self.candidate_reply_quote):
            raise ValueError("reply conflict requires a candidate reply quote only")
        return self


class NaturalReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    proposals: list[NaturalProposal] = Field(default_factory=list, max_length=20)
    claim_dispositions: list[ClaimDisposition] = Field(
        default_factory=list, max_length=20
    )

    @model_validator(mode="after")
    def _one_disposition_per_claim(self) -> NaturalReviewDecision:
        proposal_ids = [proposal.claim_id for proposal in self.proposals]
        disposition_ids = [item.claim_id for item in self.claim_dispositions]
        if len(proposal_ids) != len(set(proposal_ids)):
            raise ValueError("claim IDs must be unique")
        if len(disposition_ids) != len(set(disposition_ids)):
            raise ValueError("claim dispositions must be unique")
        if set(proposal_ids) != set(disposition_ids):
            raise ValueError("every proposal requires one claim disposition")
        return self


@dataclass(frozen=True)
class BoundNaturalSource:
    message_id: str
    start_char: int
    end_char: int
    quote: str
    message_sha256: str
    authority_role: SourceRole


def bind_natural_sources(
    proposal: NaturalProposal,
    *,
    current_user_message: dict,
    available_messages: list[dict],
) -> tuple[BoundNaturalSource, ...]:
    """Bind all cited spans to the shared, server-selected evidence bundle."""

    messages = {str(item["id"]): item for item in available_messages}
    current_id = str(current_user_message["id"])
    bound: list[BoundNaturalSource] = []
    for source in proposal.sources:
        message = messages.get(source.message_id)
        if message is None:
            raise RuntimeValidationError("Reviewer cited a message outside its bundle")
        role = str(message["role"])
        if source.role in {"user_assertion", "user_endorsement"}:
            if role != "user" or str(message["id"]) != current_id:
                raise RuntimeValidationError(
                    "Write authority must cite the current user"
                )
        elif role != "assistant" or str(message["id"]) == current_id:
            raise RuntimeValidationError(
                "Assistant referent must cite a prior assistant"
            )
        content = str(message["content"])
        start = content.find(source.quote)
        if start < 0 or content.find(source.quote, start + 1) >= 0:
            raise RuntimeValidationError(
                "Source quote must bind one exact message span"
            )
        bound.append(
            BoundNaturalSource(
                message_id=source.message_id,
                start_char=start,
                end_char=start + len(source.quote),
                quote=source.quote,
                message_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                authority_role=source.role,
            )
        )
    roles = {item.authority_role for item in bound}
    if not roles.intersection({"user_assertion", "user_endorsement"}):
        raise RuntimeValidationError("Assistant referents cannot authorize memory")
    if "user_endorsement" in roles and "assistant_referent" not in roles:
        raise RuntimeValidationError("User endorsement requires a bound referent")
    if not any(
        proposal.evidence_quote in item.quote
        for item in bound
        if item.authority_role != "assistant_referent"
    ):
        raise RuntimeValidationError("Proposal evidence must cite the current user")
    return tuple(bound)


def parse_natural_review_decision(payload: object) -> NaturalReviewDecision:
    try:
        return NaturalReviewDecision.model_validate(payload)
    except ValueError as exc:
        raise RuntimeValidationError(
            f"Invalid natural memory review output: {exc}"
        ) from exc


def natural_review_json_schema() -> dict:
    return NaturalReviewDecision.model_json_schema()
