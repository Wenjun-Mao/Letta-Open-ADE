from __future__ import annotations

from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ade_api.features.test_center.run_descriptors import validate_test_run_options


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
    config: ChatMemoryEvaluationConfigResponse
    metrics: ChatMemoryEvaluationMetricsResponse | None = None


class ChatMemoryEvaluationListResponse(_ChatMemoryEvaluationResponseModel):
    items: list[ChatMemoryEvaluationListItemResponse]


class ChatMemoryEvaluationDetailResponse(ChatMemoryEvaluationListItemResponse):
    fixture: ChatMemoryEvaluationFixtureResponse
    rounds: list[ChatMemoryEvaluationRoundResponse]
