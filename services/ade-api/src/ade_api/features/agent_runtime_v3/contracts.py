from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RuntimeMode(StrEnum):
    RELEASE = "release"
    DEVELOPMENT = "development"


class QualificationState(StrEnum):
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MemoryOperation(StrEnum):
    ADD = "add"
    CORRECT = "correct"
    FORGET = "forget"


class RuntimeResourcePurpose(StrEnum):
    DEVELOPMENT = "development"
    AGENT_STUDIO = "agent_studio"
    EVALUATION = "evaluation"
    PREVIEW = "preview"


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateAgentDefinitionRequest(StrictRequest):
    definition_key: str = Field(
        min_length=2, max_length=64, pattern=r"^[a-z][a-z0-9_-]+$"
    )
    name: str = Field(min_length=1, max_length=120)
    model_key: str = Field(min_length=1, max_length=300)
    reviewer_model_key: str = Field(min_length=1, max_length=300)
    embedding_model_key: str = Field(min_length=1, max_length=300)
    prompt_key: str = Field(default="chat_v20260516", min_length=1, max_length=128)
    persona_key: str = Field(default="chat_linxiaotang", min_length=1, max_length=128)
    tool_names: list[Literal["search_memory", "get_weather"]] = Field(
        default_factory=lambda: ["search_memory"], max_length=2
    )
    expected_current_version: int | None = Field(default=None, ge=0)

    @field_validator("tool_names")
    @classmethod
    def _dedupe_tools(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("tool_names must not contain duplicates")
        return value


class DeploymentSnapshotResponse(BaseModel):
    deployment_id: str
    route_alias: str
    fingerprint: str
    role: Literal["conversation", "reviewer", "retriever"]
    lifecycle: str
    qualification_state: QualificationState
    fingerprint_payload: dict[str, Any] = Field(default_factory=dict)


class AgentDefinitionResponse(BaseModel):
    id: str
    agent_definition_id: str | None = None
    definition_key: str
    version: int
    name: str
    prompt_key: str
    prompt_sha256: str
    persona_key: str
    persona_sha256: str
    tool_names: list[str]
    memory_policy_version: str
    qualification_state: QualificationState
    deployments: list[DeploymentSnapshotResponse]
    archived_at: datetime | None = None
    created_at: datetime


class AgentDefinitionListResponse(BaseModel):
    total: int
    items: list[AgentDefinitionResponse]


class AgentStudioBundleResponse(BaseModel):
    key: str
    name: str
    model_key: str
    reviewer_model_key: str
    embedding_model_key: str
    prompt_key: str
    persona_key: str
    tool_names: list[str]
    memory_policy_version: str
    qualification_state: QualificationState
    deployments: list[DeploymentSnapshotResponse]


class AgentStudioOptionsResponse(BaseModel):
    runtime: Literal["ade_native_v3"] = "ade_native_v3"
    default_bundle_key: str
    bundles: list[AgentStudioBundleResponse]
    default_timeout_seconds: float = 180.0
    default_retry_count: int = 0
    max_retry_count: int = 5


class CreateMemorySubjectRequest(StrictRequest):
    external_key: str = Field(min_length=1, max_length=200)
    display_name: str = Field(default="", max_length=200)


class MemorySubjectResponse(BaseModel):
    id: str
    external_key: str
    display_name: str
    version: int = 1
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class MemorySubjectListResponse(BaseModel):
    total: int
    items: list[MemorySubjectResponse]


class UpdateMemorySubjectRequest(StrictRequest):
    display_name: str = Field(min_length=1, max_length=200)
    expected_version: int = Field(ge=1)


class CreateConversationRequest(StrictRequest):
    agent_definition_id: str = Field(min_length=1, max_length=100)
    memory_subject_id: str = Field(min_length=1, max_length=100)
    title: str = Field(default="Conversation", min_length=1, max_length=120)


class ConversationResponse(BaseModel):
    id: str
    agent_definition_id: str
    memory_subject_id: str
    title: str = "Conversation"
    purpose: RuntimeResourcePurpose = RuntimeResourcePurpose.DEVELOPMENT
    version: int
    archived_at: datetime | None = None
    created_at: datetime


class ConversationListResponse(BaseModel):
    total: int
    items: list[ConversationResponse]


class CreateAgentStudioSessionRequest(StrictRequest):
    idempotency_key: str = Field(min_length=1, max_length=200)
    title: str = Field(default="New conversation", min_length=1, max_length=120)
    agent_definition_id: str | None = Field(default=None, min_length=1, max_length=100)
    new_definition: CreateAgentDefinitionRequest | None = None
    memory_subject_id: str | None = Field(default=None, min_length=1, max_length=100)
    new_subject: CreateMemorySubjectRequest | None = None

    @field_validator("idempotency_key", "title")
    @classmethod
    def _reject_blank_session_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def _require_one_resource_source(self) -> CreateAgentStudioSessionRequest:
        if (self.agent_definition_id is None) == (self.new_definition is None):
            raise ValueError("exactly one definition source is required")
        if (self.memory_subject_id is None) == (self.new_subject is None):
            raise ValueError("exactly one subject source is required")
        if (
            self.new_definition is not None
            and self.new_definition.expected_current_version not in {None, 0}
        ):
            raise ValueError(
                "a session-created definition must start at expected version 0"
            )
        return self


class AgentStudioResetRequest(StrictRequest):
    idempotency_key: str = Field(min_length=1, max_length=200)
    confirmation: Literal["RESET ADE AGENT STUDIO"]


class AgentStudioResetResponse(BaseModel):
    receipt_id: str
    idempotent_replay: bool = False
    reset_generation: int
    deleted_counts: dict[str, int]
    reset_at: datetime


class MessageResponse(BaseModel):
    id: str
    sequence: int
    role: Literal["user", "assistant"]
    content: str
    run_id: str | None = None
    created_at: datetime


class ConversationSummarySourceBoundaryResponse(BaseModel):
    """The immutable raw-message prefix represented by a summary version."""

    through_sequence: int
    message_ids: list[str]


class ConversationSummaryProvenanceResponse(BaseModel):
    run_id: str
    model_key: str
    model_fingerprint: str
    provider_request_id: str | None = None
    content_sha256: str
    prompt_sha256: str
    input_sha256: str
    policy_sha256: str


class ConversationSummaryResponse(BaseModel):
    id: str
    version: int
    previous_summary_id: str | None = None
    content: str
    source_boundary: ConversationSummarySourceBoundaryResponse
    provenance: ConversationSummaryProvenanceResponse
    created_at: datetime


class ConversationStateResponse(ConversationResponse):
    messages: list[MessageResponse]
    message_total: int = 0
    messages_truncated: bool = False
    next_before_sequence: int | None = None
    summary: ConversationSummaryResponse | None = None


class AcceptTurnRequest(StrictRequest):
    content: str = Field(min_length=1, max_length=100_000)
    idempotency_key: str = Field(min_length=1, max_length=200)
    timeout_seconds: float = Field(default=180.0, ge=5.0, le=600.0)
    retry_count: int = Field(default=0, ge=0, le=5)

    @field_validator("content", "idempotency_key")
    @classmethod
    def _reject_whitespace_only(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value


class TurnAcceptedResponse(BaseModel):
    run_id: str
    status: RunStatus
    events_url: str
    idempotent_replay: bool = False


class RunResponse(BaseModel):
    id: str
    conversation_id: str
    status: RunStatus
    qualification_state: QualificationState
    attempt_count: int
    timeout_seconds: float
    retry_count: int
    cancellation_requested_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunListResponse(BaseModel):
    total: int
    items: list[RunResponse]


class AgentStudioSessionResponse(BaseModel):
    session_id: str
    idempotent_replay: bool = False
    agent_definition: AgentDefinitionResponse
    memory_subject: MemorySubjectResponse
    conversation: ConversationResponse
    latest_run: RunResponse | None = None


class AgentStudioSessionListResponse(BaseModel):
    total: int
    items: list[AgentStudioSessionResponse]


class RuntimeWorkerHealthResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    database_ready: bool
    worker_ready: bool
    checked_at: datetime
    freshness_seconds: float
    compatible_worker_count: int
    matching_build_worker_count: int
    compatibility_fingerprint: str
    source_revision: str
    source_dirty: bool
    source_fingerprint: str
    latest_heartbeat_at: datetime | None = None
    failure_code: str | None = None


class RunEventResponse(BaseModel):
    id: str
    schema_version: int = 1
    run_id: str
    sequence: int
    attempt: int | None = None
    type: str
    occurred_at: datetime
    correlation_id: str
    causation_id: str | None = None
    visibility: Literal["operator"] = "operator"
    payload: dict[str, Any] = Field(default_factory=dict)


class RunEventListResponse(BaseModel):
    total: int
    items: list[RunEventResponse]


class MemoryEvidenceResponse(BaseModel):
    message_id: str
    start_char: int
    end_char: int
    quote: str
    message_sha256: str


class MemoryRevisionResponse(BaseModel):
    id: str
    operation: MemoryOperation
    fact_version: int
    value: str | None
    run_id: str
    predecessor_revision_ids: list[str] = Field(default_factory=list)
    evidence: list[MemoryEvidenceResponse]
    created_at: datetime


class MemoryFactResponse(BaseModel):
    id: str
    key: str
    fact_type: str
    entity_id: str
    entity_kind: str
    entity_label: str
    qualifier: str | None = None
    value: str | None
    status: Literal["active", "superseded", "forgotten"]
    version: int
    revisions: list[MemoryRevisionResponse]
    updated_at: datetime


class SubjectMemoriesResponse(BaseModel):
    subject_id: str
    facts: list[MemoryFactResponse]
