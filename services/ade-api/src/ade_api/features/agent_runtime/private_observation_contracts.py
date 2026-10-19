"""Versioned operator-only export, separate from ordinary activity contracts."""

from typing import Literal

from pydantic import BaseModel, Field

from .contracts import RunStatus


class ObservationIdentity(BaseModel):
    run_id: str
    attempt_id: str
    workspace_id: str
    conversation_id: str


class PrivateObservationRecord(BaseModel):
    schema_version: Literal[1]
    identity: ObservationIdentity
    sequence: int = Field(ge=1)
    recorded_at: float
    type: Literal[
        "attempt_execution.started",
        "attempt_execution.finished",
        "context.sources",
        "context.composed",
        "compaction.sources",
        "compaction.completed",
        "memory_lookup.started",
        "memory_lookup.completed",
        "memory_lookup.failed",
        "model_request.started",
        "model_request.finished",
    ]
    input_complete: bool
    value: dict


class PrivateAttemptObservation(BaseModel):
    attempt_id: str
    records: list[PrivateObservationRecord]


class SavedAttemptObservation(BaseModel):
    id: str
    attempt_number: int = Field(ge=1)
    status: str


class PrivateObservationResponse(BaseModel):
    schema_version: Literal[1]
    run_id: str
    workspace_id: str
    run_status: RunStatus
    saved_attempts: list[SavedAttemptObservation]
    committed_assistant_message_ids: list[str]
    observations: list[PrivateAttemptObservation]
