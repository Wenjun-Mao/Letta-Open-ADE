"""Workflow evidence contracts, not product schemas or semantic scoring rules."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

Text = Annotated[str, StringConstraints(min_length=1, pattern=r"\S")]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z][a-z0-9-]{0,79}$")]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]
Positive = Annotated[int, Field(ge=1)]
Family = Literal["Q01", "Q02", "Q03", "Q04", "Q05"]
Mode = Literal["offline_scripted", "live_capture"]
Result = Literal["meets", "partly_meets", "fails", "cannot_assess"]
LENSES = ("grounding", "conversational_judgment", "character_fidelity")
RESULTS = ("meets", "partly_meets", "fails", "cannot_assess")


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Scope(Record):
    workspace: Text
    subject: Text
    character_root: Text


class SeedMessage(Record):
    fixture_id: Identifier
    role: Literal["user", "assistant"]
    content: Text


class Rubric(Record):
    success: Annotated[list[Text], Field(min_length=1)]
    failures: Annotated[list[Text], Field(min_length=1)]
    alternatives: Annotated[list[Text], Field(min_length=1)]
    unknowns: Annotated[list[Text], Field(min_length=1)]
    limits: Annotated[list[Text], Field(min_length=1)]


class Case(Record):
    case_id: Identifier
    family: Family
    revision: Positive
    title: Text
    language: Literal["zh-CN"]
    history_kind: Literal["user_dialogue", "controlled_history", "creation"]
    source_scope: Scope
    target_scope: Scope
    history: list[SeedMessage]
    prompt: Text
    rubric: Rubric

    @model_validator(mode="after")
    def consistent_case(self) -> Case:
        ids = [message.fixture_id for message in self.history]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate fixture message ID")
        if not self.case_id.startswith(self.family.lower() + "-"):
            raise ValueError("Case ID must carry its family prefix")
        if (self.history_kind == "creation") != (not self.history):
            raise ValueError("Only a creation case has no source history")
        if self.history_kind == "user_dialogue" and any(
            message.role != "user" for message in self.history
        ):
            raise ValueError("Authored assistant history requires controlled_history")
        return self


class RuntimeBinding(Record):
    product_revision: Text
    persona_version: Text
    persona_text: Text
    prompt_version: Text
    system_prompt: Text
    character_route: Text
    character_identity_sha256: Digest
    character_settings: dict[str, Any]
    context_compaction_identity_sha256: Digest | None = None
    memory_implementation: Literal["scripted", "hindsight"]
    memory_config_sha256: Digest
    embedding_identity_sha256: Digest


class Run(Record):
    schema_version: Literal[1] = 1
    run_id: Identifier
    mode: Mode
    prepared_at: AwareDatetime
    suite_revision: Text
    suite_sha256: Digest
    evaluator_revision: Text
    evaluator_files_sha256: Digest
    repeats: Annotated[int, Field(ge=1, le=100)]
    runtime: RuntimeBinding
    cases: Annotated[list[Case], Field(min_length=1)]

    @model_validator(mode="after")
    def consistent_run(self) -> Run:
        ids = [case.case_id for case in self.cases]
        if len(set(ids)) != len(ids):
            raise ValueError("Duplicate case ID")
        expected = "scripted" if self.mode == "offline_scripted" else "hindsight"
        if self.runtime.memory_implementation != expected:
            raise ValueError("Runtime binding does not match the evidence mode")
        return self


class Attempt(Record):
    schema_version: Literal[1] = 1
    run_sha256: Digest
    case_sha256: Digest
    case_id: Identifier
    repeat: Positive
    started_at: AwareDatetime


class SourceMessage(Record):
    message_id: Text
    fixture_id: Identifier | None = None
    conversation_id: Text
    scope: Scope
    role: Literal["user", "assistant"]
    content: Text
    occurred_at: AwareDatetime
    status: Literal["accepted", "committed", "uncommitted"]


class RequestSnapshot(Record):
    request_id: Text
    sent_at: AwareDatetime
    served_identity_sha256: Digest
    body: dict[str, Any]


class ProductCaptureProvenance(Record):
    manifest_file: Text
    file_sha256: Digest


class Observation(Record):
    mode: Mode
    status: Literal["completed", "failed", "cancelled", "blocked"]
    stage: Literal[
        "setup",
        "retention",
        "consolidation",
        "recall",
        "generation",
        "capture",
        "finished",
    ]
    observed_runtime: RuntimeBinding | None = None
    history_provenance: (
        Literal["product_dialogue", "controlled_history", "no_history"] | None
    ) = None
    source_scope: Scope | None = None
    target_scope: Scope | None = None
    source_conversation_id: Text | None = None
    probe_conversation_id: Text | None = None
    fresh_state_receipt: dict[str, Any] | None = None
    source_complete: bool = False
    input_complete: bool = False
    source_messages: list[SourceMessage] = Field(default_factory=list)
    retention: Literal[
        "complete", "pending", "failed", "not_applicable", "not_observed"
    ] = "not_observed"
    consolidation: Literal[
        "complete", "pending", "failed", "not_applicable", "not_observed"
    ] = "not_observed"
    delivery_receipts: list[dict[str, Any]] = Field(default_factory=list)
    memory_snapshot: dict[str, Any] | None = None
    recall_payload: dict[str, Any] | None = None
    recalled_scopes: list[Scope] = Field(default_factory=list)
    requests: list[RequestSnapshot] = Field(default_factory=list)
    reply: Text | None = None
    reply_message_id: Text | None = None
    reply_committed: bool = False
    error: Text | None = None
    limitations: list[Text] = Field(default_factory=list)
    product_capture: ProductCaptureProvenance | None = None

    @model_validator(mode="after")
    def explain_missing_evidence(self) -> Observation:
        if self.status != "completed" and not self.error:
            raise ValueError("Unsuccessful execution requires an error explanation")
        if (
            not self.source_complete or not self.input_complete
        ) and not self.limitations:
            raise ValueError("Incomplete capture requires an explicit limitation")
        return self


class Capture(Record):
    schema_version: Literal[1] = 1
    attempt_sha256: Digest
    captured_at: AwareDatetime
    observation: Observation


class Judgment(Record):
    result: Result
    quote: str
    rationale: Text


class Review(Record):
    schema_version: Literal[1] = 1
    capture_sha256: Digest
    revision: Positive
    supersedes_sha256: Digest | None = None
    change_reason: Text | None = None
    reviewer: Text
    kind: Literal["human", "scripted_example"]
    judgments: dict[str, Judgment]

    @model_validator(mode="after")
    def review_contract(self) -> Review:
        if set(self.judgments) != set(LENSES):
            raise ValueError("Review requires exactly the three assessment lenses")
        if self.revision == 1:
            if self.supersedes_sha256 is not None or self.change_reason is not None:
                raise ValueError("Initial review cannot supersede a prior review")
        elif not self.supersedes_sha256 or not self.change_reason:
            raise ValueError("Revised review requires previous hash and change reason")
        return self
