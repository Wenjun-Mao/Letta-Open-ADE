from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    created_at: datetime


class CreateMemorySubjectRequest(StrictRequest):
    external_key: str = Field(min_length=1, max_length=200)
    display_name: str = Field(default="", max_length=200)


class MemorySubjectResponse(BaseModel):
    id: str
    external_key: str
    display_name: str
    created_at: datetime


class CreateConversationRequest(StrictRequest):
    agent_definition_id: str = Field(min_length=1, max_length=100)
    memory_subject_id: str = Field(min_length=1, max_length=100)


class ConversationResponse(BaseModel):
    id: str
    agent_definition_id: str
    memory_subject_id: str
    version: int
    created_at: datetime


class CreatePreviewSessionRequest(StrictRequest):
    """Create the bounded resources needed by the separate native pilot."""

    idempotency_key: str = Field(min_length=1, max_length=200)
    name: str = Field(default="Native Runtime Preview", min_length=1, max_length=120)
    subject_display_name: str = Field(default="Preview User", max_length=200)
    model_key: str = Field(min_length=1, max_length=300)
    reviewer_model_key: str = Field(min_length=1, max_length=300)
    embedding_model_key: str = Field(min_length=1, max_length=300)
    prompt_key: str = Field(default="chat_v20260516", min_length=1, max_length=128)
    persona_key: str = Field(default="chat_linxiaotang", min_length=1, max_length=128)

    @field_validator("idempotency_key", "name")
    @classmethod
    def _reject_blank_preview_identity(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()


class PreviewSessionResponse(BaseModel):
    session_id: str
    idempotent_replay: bool = False
    agent_definition: AgentDefinitionResponse
    memory_subject: MemorySubjectResponse
    conversation: ConversationResponse


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
