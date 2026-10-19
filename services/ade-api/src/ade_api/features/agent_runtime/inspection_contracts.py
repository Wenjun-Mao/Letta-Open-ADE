"""Read-only relationship Memory and independent ADE delivery inspection."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .contracts import StrictRequest


class DeliveryRetryRequest(StrictRequest):
    expected_check_count: int = Field(ge=0)


class RelationshipResponse(BaseModel):
    subject_id: str
    character_root_id: str
    state: str
    last_error_code: str | None


class DeliveryResponse(BaseModel):
    operation_id: str
    document_id: str
    message_id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    message_sequence: int
    relationship_sequence: int
    status: Literal[
        "queued", "submitting", "processing", "retained", "failed", "uncertain"
    ]
    attempt_count: int
    check_count: int
    retry_requested: bool
    last_error_code: str | None
    native_status: str | None
    native_progress: dict
    accepted_at: datetime | None
    retained_at: datetime | None
    last_checked_at: datetime | None
    created_at: datetime
    updated_at: datetime
    queue_age_seconds: float
    blocked_by_operation_id: str | None


class DeliveryListResponse(BaseModel):
    relationship: RelationshipResponse
    total: int
    limit: int
    offset: int
    counts: dict[str, int]
    blocked_operation_id: str | None
    items: list[DeliveryResponse]


class LearnedMemoryResponse(BaseModel):
    id: str
    text: str
    context: str = ""
    fact_type: str | None = None
    document_id: str | None = None
    date: str = ""
    mentioned_at: str | None = None
    occurred_start: str | None = None
    occurred_end: str | None = None
    entities: str = ""
    state: str = "valid"
    consolidated_at: str | None = None
    consolidation_failed_at: str | None = None
    source_memory_ids: list[str] = Field(default_factory=list)


class RelationshipMemoriesResponse(BaseModel):
    relationship: RelationshipResponse
    total: int
    limit: int
    offset: int
    items: list[LearnedMemoryResponse]


class SourceResponse(BaseModel):
    relationship: RelationshipResponse
    delivery: DeliveryResponse
    content: str
    occurred_at: datetime
    definition_version_id: str
    native_original_text: str | None
    native_context: str | None


class NativeOperationResponse(BaseModel):
    operation_id: str
    operation_type: str | None = None
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    native_progress: dict


class NativeOperationsResponse(BaseModel):
    relationship: RelationshipResponse
    total: int
    limit: int
    offset: int
    items: list[NativeOperationResponse]
