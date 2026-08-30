from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from .contracts import MemoryOperation
from .errors import RuntimeValidationError
from .fact_registry import FactRegistryError, fact_type_spec, normalize_qualifier


FactTypeName: TypeAlias = Literal[
    "person.name",
    "person.current_location",
    "person.preference",
    "person.shoe_size",
    "pet.name",
    "pet.breed",
    "relationship.person",
]
QualifierName: TypeAlias = Literal[
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
    "child",
    "colleague",
    "friend",
    "parent",
    "partner",
    "sibling",
]


class _EvidenceProposalBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_quote: StrictStr = Field(min_length=1, max_length=10_000)


class _TypedProposalBase(_EvidenceProposalBase):
    fact_type: FactTypeName
    qualifier: QualifierName | None = None

    @model_validator(mode="after")
    def _normalize_fact_contract(self) -> "_TypedProposalBase":
        try:
            spec = fact_type_spec(self.fact_type)
            self.fact_type = spec.name
            self.qualifier = normalize_qualifier(spec, self.qualifier)
        except FactRegistryError as exc:
            raise ValueError(str(exc)) from exc
        return self


class AddProposal(_TypedProposalBase):
    operation: Literal[MemoryOperation.ADD]
    value: StrictStr = Field(min_length=1, max_length=10_000)
    entity_ref: StrictStr | None = None
    new_entity_label: StrictStr = Field(default="", max_length=500)

    @field_validator("value")
    @classmethod
    def _nonblank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("add requires a nonblank value")
        return value


class CorrectProposal(_EvidenceProposalBase):
    operation: Literal[MemoryOperation.CORRECT]
    value: StrictStr = Field(min_length=1, max_length=10_000)
    fact_id: StrictStr = Field(min_length=1, max_length=100)
    expected_version: StrictInt = Field(ge=1)

    @field_validator("value")
    @classmethod
    def _nonblank_value(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("correct requires a nonblank value")
        return value


class ForgetProposal(_EvidenceProposalBase):
    operation: Literal[MemoryOperation.FORGET]
    value: None
    fact_id: StrictStr = Field(min_length=1, max_length=100)
    expected_version: StrictInt = Field(ge=1)


ReviewProposal: TypeAlias = Annotated[
    AddProposal | CorrectProposal | ForgetProposal,
    Field(discriminator="operation"),
]


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposals: list[ReviewProposal] = Field(default_factory=list, max_length=20)


@dataclass(frozen=True)
class BoundEvidence:
    message_id: str
    start_char: int
    end_char: int
    quote: str
    message_sha256: str


def bind_evidence(
    proposal: ReviewProposal,
    *,
    user_messages: list[dict[str, Any]],
) -> BoundEvidence:
    quote = proposal.evidence_quote
    matches: list[tuple[dict[str, Any], int]] = []
    for message in user_messages:
        content = str(message.get("content", ""))
        offset = content.find(quote)
        while offset >= 0:
            matches.append((message, offset))
            offset = content.find(quote, offset + 1)
    if len(matches) != 1:
        raise RuntimeValidationError(
            "Memory evidence_quote must identify exactly one user-authored span"
        )
    message, start = matches[0]
    content = str(message["content"])
    return BoundEvidence(
        message_id=str(message["id"]),
        start_char=start,
        end_char=start + len(quote),
        quote=quote,
        message_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
    )


def review_json_schema() -> dict[str, Any]:
    return ReviewDecision.model_json_schema()


def parse_review_decision(payload: object) -> ReviewDecision:
    try:
        return ReviewDecision.model_validate(payload)
    except ValueError as exc:
        raise RuntimeValidationError(f"Invalid memory review output: {exc}") from exc
