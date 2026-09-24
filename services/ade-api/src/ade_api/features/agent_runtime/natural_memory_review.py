"""Compact, closed reviewer wire contract and exact source binding."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StrictStr, model_validator

from .errors import RuntimeValidationError
from .memory_review import FactTypeName, QualifierName


class _Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DirectEvidence(_Closed):
    mode: Literal["direct"]
    current_quote: StrictStr = Field(min_length=1, max_length=10_000)


class ResolveUserEvidence(_Closed):
    mode: Literal["resolve_user"]
    current_quote: StrictStr = Field(min_length=1, max_length=10_000)
    support_handle: StrictStr = Field(pattern=r"^U[1-9][0-9]*$")
    support_quote: StrictStr = Field(min_length=1, max_length=10_000)


class EndorseAssistantEvidence(_Closed):
    mode: Literal["endorse_assistant"]
    current_quote: StrictStr = Field(min_length=1, max_length=10_000)
    support_handle: StrictStr = Field(pattern=r"^A[1-9][0-9]*$")
    support_quote: StrictStr = Field(min_length=1, max_length=10_000)


Evidence: TypeAlias = Annotated[
    DirectEvidence | ResolveUserEvidence | EndorseAssistantEvidence,
    Field(discriminator="mode"),
]


class _Write(_Closed):
    evidence: Evidence

    @property
    def operation(self) -> str:
        return "add" if self.kind in {"subject_add", "related_add"} else self.kind


class NaturalSubjectAdd(_Write):
    kind: Literal["subject_add"]
    fact_type: FactTypeName
    qualifier: QualifierName | None = None
    value: StrictStr = Field(min_length=1, max_length=10_000)


class NaturalRelatedAdd(_Write):
    kind: Literal["related_add"]
    fact_type: FactTypeName
    qualifier: QualifierName | None = None
    value: StrictStr = Field(min_length=1, max_length=10_000)
    entity_ref: StrictStr = Field(min_length=2, max_length=100)


class _Target(_Write):
    target: StrictStr = Field(pattern=r"^F[1-9][0-9]*$")


class NaturalRevise(_Target):
    kind: Literal["revise"]
    reason: Literal["enrich", "supersede", "correct", "unspecified"]
    value: StrictStr | None = Field(max_length=10_000)

    @model_validator(mode="after")
    def _value_contract(self):
        if self.value is None and self.reason != "correct":
            raise ValueError("null revise requires correct reason")
        if self.value is not None and not self.value.strip():
            raise ValueError("revision value must not be blank")
        return self


class NaturalEnd(_Target):
    kind: Literal["end"]
    reason: Literal["ended", "invalidated"]


class NaturalReassert(_Target):
    kind: Literal["reassert"]
    value: StrictStr = Field(min_length=1, max_length=10_000)


class NaturalForget(_Target):
    kind: Literal["forget"]


class NaturalDefer(_Closed):
    kind: Literal["defer"]
    current_quote: StrictStr = Field(min_length=1, max_length=10_000)
    reason: Literal["unresolved", "uncertain", "nonasserted"]


SnapshotReference: TypeAlias = Annotated[StrictStr, Field(pattern=r"^[FE][1-9][0-9]*$")]


class NaturalConflict(_Closed):
    kind: Literal["conflict"]
    current_quote: StrictStr = Field(min_length=1, max_length=10_000)
    candidate_reply_quote: StrictStr = Field(min_length=1, max_length=10_000)
    references: list[SnapshotReference] = Field(min_length=1, max_length=6)


NaturalWrite: TypeAlias = (
    NaturalSubjectAdd
    | NaturalRelatedAdd
    | NaturalRevise
    | NaturalEnd
    | NaturalReassert
    | NaturalForget
)
NaturalDecision: TypeAlias = Annotated[
    NaturalSubjectAdd
    | NaturalRelatedAdd
    | NaturalRevise
    | NaturalEnd
    | NaturalReassert
    | NaturalForget
    | NaturalDefer
    | NaturalConflict,
    Field(discriminator="kind"),
]


class NaturalReviewDecision(_Closed):
    decisions: list[NaturalDecision] = Field(max_length=20)


@dataclass(frozen=True)
class BoundNaturalSource:
    message_id: str
    start_char: int
    end_char: int
    quote: str
    message_sha256: str
    authority_role: Literal[
        "user_assertion",
        "user_endorsement",
        "user_resolution",
        "user_antecedent",
        "assistant_referent",
    ]


def bind_exact_quote(
    message: Mapping[str, Any], quote: str, role: str
) -> BoundNaturalSource:
    content = str(message["content"])
    start = content.find(quote)
    if start < 0 or content.find(quote, start + 1) >= 0:
        raise RuntimeValidationError(
            "Source quote must bind one exact message span",
            detail_code="natural_review_binding",
        )
    return BoundNaturalSource(
        message_id=str(message["id"]),
        start_char=start,
        end_char=start + len(quote),
        quote=quote,
        message_sha256=hashlib.sha256(content.encode()).hexdigest(),
        authority_role=role,
    )


def parse_natural_review_decision(payload: object) -> NaturalReviewDecision:
    try:
        return NaturalReviewDecision.model_validate(payload)
    except ValueError as exc:
        raise RuntimeValidationError(
            f"Invalid natural memory review output: {exc}",
            detail_code="natural_review_schema",
        ) from exc


def natural_review_json_schema() -> dict:
    return NaturalReviewDecision.model_json_schema()
