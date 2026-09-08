from __future__ import annotations

from typing import Annotated, ClassVar, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ade_api.features.test_center.run_descriptors import (
    canonicalize_agent_runtime_case_keys,
    validate_test_run_options,
)


class _TestRunRequest(BaseModel):
    """Base contract shared by the explicit Test Center launch requests."""

    __test__: ClassVar[bool] = False

    model_config = ConfigDict(extra="forbid")

    run_type: str

    @model_validator(mode="after")
    def _validate_descriptor_options(self) -> _TestRunRequest:
        validate_test_run_options(
            self.run_type,
            self.model_dump(exclude={"run_type"}, exclude_none=True),
        )
        return self


class CurrentStackSmokeRunRequest(_TestRunRequest):
    run_type: Literal["ade_api_e2e_check"]


class ChatMemoryEvaluationRunRequest(_TestRunRequest):
    run_type: Literal["chat_memory_eval"]
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


class AgentRuntimeAcceptanceRunRequest(_TestRunRequest):
    run_type: Literal["agent_runtime_acceptance"]
    conversation_model_key: str | None = None
    reviewer_model_key: str | None = None
    embedding_model_key: str | None = None
    prompt_key: str | None = None
    persona_key: str | None = None
    rounds: int | None = Field(default=None, ge=1, le=3)
    timeout_seconds: float | None = Field(default=None, ge=5, le=600)
    retry_count: int | None = Field(default=None, ge=0, le=5)
    include_llama_compatibility: bool | None = None
    case_keys: list[str] | None = Field(default=None, min_length=1)

    @field_validator("case_keys")
    @classmethod
    def _canonicalize_case_keys(cls, case_keys: list[str] | None) -> list[str] | None:
        if case_keys is None:
            return None
        return list(canonicalize_agent_runtime_case_keys(case_keys))


TestRunRequest: TypeAlias = Annotated[
    CurrentStackSmokeRunRequest
    | ChatMemoryEvaluationRunRequest
    | AgentRuntimeAcceptanceRunRequest,
    Field(discriminator="run_type"),
]


class TestRunOptionResponse(BaseModel):
    key: str
    label: str
    available: bool = True


class TestCenterCatalogOptionsResponse(BaseModel):
    models: list[TestRunOptionResponse]
    embeddings: list[TestRunOptionResponse]
    prompts: list[TestRunOptionResponse]
    personas: list[TestRunOptionResponse]


class ChatMemoryEvaluationDefaultsResponse(BaseModel):
    model: str
    prompt_key: str
    persona_key: str
    embedding: str
    fixture_key: str
    rounds: int
    timeout_seconds: float
    retry_count: int
    judge_enabled: bool


class ChatMemoryEvaluationOptionsResponse(BaseModel):
    defaults: ChatMemoryEvaluationDefaultsResponse
    fixtures: list[TestRunOptionResponse]


class AgentRuntimeAcceptanceDefaultsResponse(BaseModel):
    conversation_model_key: str
    reviewer_model_key: str
    embedding_model_key: str
    prompt_key: str
    persona_key: str
    rounds: int
    timeout_seconds: float
    retry_count: int
    include_llama_compatibility: bool


class AgentRuntimeAcceptanceOptionsResponse(BaseModel):
    defaults: AgentRuntimeAcceptanceDefaultsResponse
    cases: list[TestRunOptionResponse]


class CurrentStackSmokeOptionsResponse(BaseModel):
    run_type: Literal["ade_api_e2e_check"]


class TestCenterOptionsResponse(BaseModel):
    run_types: list[TestRunOptionResponse]
    catalog: TestCenterCatalogOptionsResponse
    chat_memory_eval: ChatMemoryEvaluationOptionsResponse
    agent_runtime_acceptance: AgentRuntimeAcceptanceOptionsResponse
    current_stack_smoke: CurrentStackSmokeOptionsResponse


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
