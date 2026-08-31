from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ade_api.features.test_center.run_descriptors import (
    canonicalize_agent_runtime_v3_case_keys,
    validate_test_run_options,
)


class TestRunRequest(BaseModel):
    __test__: ClassVar[bool] = False

    model_config = ConfigDict(extra="forbid")

    run_type: Literal[
        "ade_api_e2e_check",
        "ade_mvp_smoke_e2e_check",
        "chat_memory_eval",
        "agent_runtime_v3_acceptance",
    ]
    model: str | None = None
    prompt_key: str | None = None
    persona_key: str | None = None
    embedding: str | None = None
    rounds: int | None = Field(default=None, ge=1, le=100)
    fixture_key: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    retry_count: int | None = Field(default=None, ge=0, le=5)
    judge_enabled: bool | None = None
    judge_model_key: str | None = None
    conversation_model_key: str | None = None
    reviewer_model_key: str | None = None
    embedding_model_key: str | None = None
    include_llama_compatibility: bool | None = None
    case_keys: list[str] | None = Field(default=None, min_length=1)

    @field_validator("case_keys")
    @classmethod
    def _canonicalize_agent_runtime_v3_case_keys(
        cls, case_keys: list[str] | None
    ) -> list[str] | None:
        if case_keys is None:
            return None
        return list(canonicalize_agent_runtime_v3_case_keys(case_keys))

    @model_validator(mode="after")
    def _validate_run_descriptor_options(self) -> TestRunRequest:
        validate_test_run_options(
            self.run_type,
            {
                field_name: getattr(self, field_name)
                for field_name in self.model_fields_set
                if field_name != "run_type"
            },
        )
        return self


class TestRunArtifactResponse(BaseModel):
    artifact_id: str
    type: str
    path: str
    exists: bool
    size_bytes: int


class TestRunRecordResponse(BaseModel):
    run_id: str
    run_type: str
    status: str
    command: list[str]
    created_at: str
    started_at: str
    finished_at: str
    exit_code: int | None = None
    log_file: str
    cancel_requested: bool
    output_tail: list[str] = Field(default_factory=list)
    error: str
    artifacts: list[TestRunArtifactResponse] = Field(default_factory=list)


class TestRunListResponse(BaseModel):
    items: list[TestRunRecordResponse]


class TestRunArtifactListResponse(BaseModel):
    run_id: str
    items: list[TestRunArtifactResponse]


class TestRunArtifactReadResponse(BaseModel):
    run_id: str
    artifact: TestRunArtifactResponse
    content: str
    truncated: bool
    line_count: int


class _ChatMemoryEvaluationResponseModel(BaseModel):
    """Strict public contract for Test Center chat-memory evaluation reads."""

    model_config = ConfigDict(extra="forbid", strict=True)


class ChatMemoryEvaluationConfigResponse(_ChatMemoryEvaluationResponseModel):
    model: str
    prompt_key: str
    persona_key: str
    embedding: str
    fixture_key: str
    rounds: int
    timeout_seconds: float
    retry_count: int
    judge_enabled: bool


class ChatMemoryEvaluationTemplateSnapshotResponse(_ChatMemoryEvaluationResponseModel):
    kind: Literal["prompt", "persona"]
    scenario: Literal["chat"]
    key: str
    label: str
    description: str
    content: str
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    updated_at: str


class ChatMemoryEvaluationOptionSnapshotResponse(_ChatMemoryEvaluationResponseModel):
    key: str
    label: str
    source_id: str
    source_label: str
    provider_model_id: str
    upstream_provider_model_id: str | None
    sampling_defaults: dict[str, Any]
    scenario_sampling_defaults: dict[str, Any]
    supports_top_k: bool | None
    supports_thinking: bool | None
    thinking_default_enabled: bool | None
    profile_applied: bool | None
    profile_source: str
    agent_studio_candidate: bool | None
    agent_studio_compatible: bool | None
    deployment: dict[str, Any] | None
    identity_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ChatMemoryEvaluationProvenanceResponse(_ChatMemoryEvaluationResponseModel):
    schema_version: Literal[1, 2]
    run_id: str | None = None
    captured_at: str
    configuration_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    controls: dict[str, Any]
    prompt: ChatMemoryEvaluationTemplateSnapshotResponse
    persona: ChatMemoryEvaluationTemplateSnapshotResponse
    model: ChatMemoryEvaluationOptionSnapshotResponse
    embedding: ChatMemoryEvaluationOptionSnapshotResponse | None = None

    @model_validator(mode="after")
    def _require_run_binding_in_schema_v2(
        self,
    ) -> ChatMemoryEvaluationProvenanceResponse:
        if self.schema_version == 2 and not str(self.run_id or "").strip():
            raise ValueError("schema v2 evaluation provenance requires run_id")
        if self.schema_version == 1 and self.run_id is not None:
            raise ValueError("schema v1 evaluation provenance cannot include run_id")
        return self


class ChatMemoryEvaluationProvenanceSummaryResponse(_ChatMemoryEvaluationResponseModel):
    run_id: str
    captured_at: str
    configuration_sha256: str
    provenance_sha256: str
    fixture_sha256: str
    prompt_content_sha256: str
    persona_content_sha256: str
    model_identity_sha256: str
    embedding_identity_sha256: str | None = None


class ChatMemoryEvaluationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    outcome: Literal["keep", "promote", "reject"]
    expected_provenance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_evidence_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_run_id: str | None = Field(default=None, min_length=1)
    expected_baseline_provenance_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    expected_baseline_evidence_sha256: str | None = Field(
        default=None, pattern=r"^[0-9a-f]{64}$"
    )
    note: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def _bind_baseline_to_reviewed_evidence(
        self,
    ) -> ChatMemoryEvaluationDecisionRequest:
        baseline_fields = (
            self.baseline_run_id,
            self.expected_baseline_provenance_sha256,
            self.expected_baseline_evidence_sha256,
        )
        if any(item is None for item in baseline_fields) and not all(
            item is None for item in baseline_fields
        ):
            raise ValueError(
                "baseline_run_id and expected baseline provenance/evidence hashes must be provided together"
            )
        return self


class ChatMemoryEvaluationDecisionResponse(_ChatMemoryEvaluationResponseModel):
    decision_id: str
    outcome: Literal["keep", "promote", "reject"]
    candidate_run_id: str
    baseline_run_id: str | None = None
    baseline_provenance_sha256: str | None = None
    baseline_evidence_sha256: str | None = None
    candidate_provenance_sha256: str
    candidate_evidence_sha256: str
    candidate_configuration_sha256: str
    note: str
    recorded_at: str


class ChatMemoryEvaluationMetricsResponse(_ChatMemoryEvaluationResponseModel):
    rounds_total: int
    rounds_passed: int
    rounds_failed: int
    errors: int
    pass_rate: float
    average_elapsed_seconds: float
    forbidden_hit_count: int
    memory_changed_rounds: int
    expected_facts_passed_rounds: int
    memory_tool_call_count: int
    total_tool_call_count: int
    cleanup_passed_rounds: int


class ChatMemoryEvaluationExpectedFactResponse(_ChatMemoryEvaluationResponseModel):
    key: str
    label: str
    aliases: list[str]


class ChatMemoryEvaluationFixtureResponse(_ChatMemoryEvaluationResponseModel):
    key: str
    description: str
    turns: list[str]
    expected_facts: list[ChatMemoryEvaluationExpectedFactResponse]
    forbidden_reply_substrings: list[str]


class ChatMemoryEvaluationMemoryBlockResponse(_ChatMemoryEvaluationResponseModel):
    label: str
    value: str
    description: str | None = None
    limit: int | None = None


class ChatMemoryEvaluationTurnResponse(_ChatMemoryEvaluationResponseModel):
    turn_index: int
    user_input: str
    assistant_replies: list[str]
    elapsed_seconds: float
    memory_changed_this_turn: bool
    human_memory_before_turn: str
    human_memory_after_turn: str
    tool_calls: list[dict[str, Any]]
    memory_tool_calls: list[dict[str, Any]]


class ChatMemoryEvaluationRoundResponse(_ChatMemoryEvaluationResponseModel):
    round: int
    status: str
    passed: bool
    elapsed_seconds: float
    agent_id: str
    archived: bool
    purged: bool
    error: str
    initial_human_memory: str
    final_human_memory: str
    deterministic_score: dict[str, Any]
    judge: dict[str, Any]
    turns: list[ChatMemoryEvaluationTurnResponse]
    memory_blocks: list[ChatMemoryEvaluationMemoryBlockResponse] = Field(
        default_factory=list
    )


class ChatMemoryEvaluationListItemResponse(_ChatMemoryEvaluationResponseModel):
    run_id: str
    run_status: str
    created_at: str
    finished_at: str
    ready: bool
    evidence_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    config: ChatMemoryEvaluationConfigResponse
    metrics: ChatMemoryEvaluationMetricsResponse | None = None
    provenance: ChatMemoryEvaluationProvenanceSummaryResponse | None = None
    decision: ChatMemoryEvaluationDecisionResponse | None = None
    preferred_baseline: bool = False


class ChatMemoryEvaluationListResponse(_ChatMemoryEvaluationResponseModel):
    items: list[ChatMemoryEvaluationListItemResponse]


class ChatMemoryEvaluationDetailResponse(ChatMemoryEvaluationListItemResponse):
    fixture: ChatMemoryEvaluationFixtureResponse
    rounds: list[ChatMemoryEvaluationRoundResponse]
    provenance_detail: ChatMemoryEvaluationProvenanceResponse | None = None


class ChatMemoryEvaluationComparisonValueResponse(_ChatMemoryEvaluationResponseModel):
    baseline: Any
    candidate: Any
    changed: bool


class ChatMemoryEvaluationComparisonResponse(_ChatMemoryEvaluationResponseModel):
    baseline: ChatMemoryEvaluationListItemResponse
    candidate: ChatMemoryEvaluationListItemResponse
    same_configuration: bool
    configuration_changes: dict[str, ChatMemoryEvaluationComparisonValueResponse]
    metric_deltas: dict[str, float]
