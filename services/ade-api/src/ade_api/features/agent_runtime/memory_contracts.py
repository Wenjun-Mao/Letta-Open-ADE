"""Public memory lifecycle, provenance, and operator-action API shapes."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryOperation(StrEnum):
    ADD = "add"
    CORRECT = "correct"
    FORGET = "forget"
    REVISE = "revise"
    END = "end"
    REASSERT = "reassert"


class _StrictMemoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MemoryRemovalTarget(_StrictMemoryRequest):
    fact_id: UUID
    expected_version: int = Field(ge=1)


class MemoryRemovalRequest(_StrictMemoryRequest):
    idempotency_key: str = Field(min_length=1, max_length=200)
    expected_memory_generation: int = Field(ge=1)
    targets: list[MemoryRemovalTarget] = Field(min_length=1, max_length=20)

    @field_validator("idempotency_key")
    @classmethod
    def _nonblank_key(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("idempotency_key must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def _unique_targets(self) -> MemoryRemovalRequest:
        ids = [target.fact_id for target in self.targets]
        if len(ids) != len(set(ids)):
            raise ValueError("memory removal targets must be unique")
        return self


class MemoryRemovalResponse(BaseModel):
    action_id: str
    outcome: Literal["committed"]
    revision_ids: list[str]
    resulting_memory_generation: int = Field(ge=2)
    idempotent_replay: bool = False
    committed_at: datetime


class MemoryEvidenceResponse(BaseModel):
    message_id: str
    conversation_id: str
    message_sequence: int
    start_char: int
    end_char: int
    quote: str
    message_sha256: str
    authority_role: Literal[
        "user_assertion", "user_endorsement", "assistant_referent"
    ] = "user_assertion"


class MemoryRevisionResponse(BaseModel):
    id: str
    operation: MemoryOperation
    fact_version: int
    value: str | None
    run_id: str | None = None
    action_id: str | None = None
    reason: str | None = None
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
    status: Literal["active", "inactive", "superseded", "forgotten"]
    assertion_schema_version: int = Field(default=1, ge=1)
    version: int
    revisions: list[MemoryRevisionResponse]
    updated_at: datetime


class SubjectMemoriesResponse(BaseModel):
    subject_id: str
    memory_generation: int = Field(default=1, ge=1)
    facts: list[MemoryFactResponse]
