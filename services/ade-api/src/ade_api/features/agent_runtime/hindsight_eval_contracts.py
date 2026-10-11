"""Synthetic evaluation inputs; not a product Memory interface."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

HINDSIGHT_SOURCE = "eb6df499d35300e5b2f3f029b2e6adda04ed90f8"
CONTRACT = "ade-hindsight-character-evaluation-v1"
ATTRIBUTION_METADATA_KEYS = {
    "speaker",
    "source_id",
    "source_timestamp",
    "subject_id",
    "character_root_id",
    "definition_version",
}
Identifier = Annotated[
    str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
]
Text = Annotated[str, Field(min_length=1)]


class EvaluationError(RuntimeError):
    """A safe failure code, without response bodies, credentials or reasoning."""


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class RecallScope(StrictInput):
    workspace_id: Identifier
    subject_id: Identifier
    character_root_id: Identifier

    @property
    def bank_id(self) -> str:
        identity = json.dumps(
            [self.workspace_id, self.subject_id], separators=(",", ":")
        ).encode()
        return "ade-probe-" + hashlib.sha256(identity).hexdigest()[:32]

    @property
    def tags(self) -> list[str]:
        return [f"character:{self.character_root_id}", "kind:profile"]

    def receipt(self) -> dict:
        return {
            **self.model_dump(),
            "bank_id": self.bank_id,
            "tags": self.tags,
            "tags_match": "any_strict",
        }


class DialogueMessage(StrictInput):
    role: Literal["user", "assistant"]
    content: Text

    @field_validator("content")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("content must not be blank")
        return value


class RecalledMemory(BaseModel):
    # A projection of pinned RecallResult, excluding scores, attachments and
    # arbitrary metadata. New upstream diagnostic fields cannot enter Character.
    model_config = ConfigDict(extra="ignore", strict=True, frozen=True)
    id: Text
    text: Text
    type: Literal["world", "experience", "observation"]
    tags: list[Text]
    entities: list[str] | None = None
    context: str | None = None
    occurred_start: str | None = None
    occurred_end: str | None = None
    mentioned_at: str | None = None
    document_id: str | None = None
    source_fact_ids: list[str] | None = None
    metadata: dict[str, str] | None = None

    @field_validator("metadata")
    @classmethod
    def attribution_only(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return {
            key: text
            for key, text in (value or {}).items()
            if key in ATTRIBUTION_METADATA_KEYS
        }

    @field_validator("id", "text")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("memory identity and text must not be blank")
        return value

    def check_scope(self, scope: RecallScope) -> None:
        character = scope.tags[0]
        if not set(self.tags).intersection(scope.tags):
            raise EvaluationError("recall_scope_violation")
        if self.type == "observation":
            characters = {tag for tag in self.tags if tag.startswith("character:")}
            if characters != {character}:
                raise EvaluationError("recall_observation_scope_violation")


class EvaluationInput(StrictInput):
    contract: Literal["ade-hindsight-character-evaluation-v1"]
    synthetic: Literal[True]
    case_id: Identifier
    scope: RecallScope
    model_key: Text
    persona: Text
    dialogue: Annotated[list[DialogueMessage], Field(min_length=1)]
    query: Text
    query_timestamp: Text
    arms: Annotated[
        list[Literal["hindsight", "empty", "adequate"]], Field(min_length=1)
    ]
    adequate_memories: list[RecalledMemory] = Field(default_factory=list)
    timeout_seconds: Annotated[float, Field(gt=0, le=180)] = 120.0
    recall_timeout_seconds: Annotated[float, Field(gt=0, le=180)] = 120.0
    max_output_tokens: Annotated[int, Field(gt=0, le=32768)] = 2048
    input_token_limit: Annotated[int, Field(gt=0, le=131072)] = 8192
    recall_max_tokens: Annotated[int, Field(gt=0, le=32768)] = 2048
    recall_budget: Literal["low", "mid", "high"] = "mid"
    recall_types: list[Literal["world", "experience", "observation"]] = Field(
        default_factory=lambda: ["world", "experience", "observation"]
    )

    @field_validator("persona", "model_key", "query")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be blank")
        return value

    @field_validator("query_timestamp")
    @classmethod
    def anchored_time(cls, value: str) -> str:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("query_timestamp requires a timezone")
        return value

    @field_validator("model_key")
    @classmethod
    def canonical_route(cls, value: str) -> str:
        if not re.fullmatch(r"[^\s:]+::[^\s]+", value):
            raise ValueError("model_key must be a canonical source::model route")
        return value

    @model_validator(mode="after")
    def complete_comparison(self) -> EvaluationInput:
        if self.dialogue[-1].role != "user":
            raise ValueError("dialogue must end with the current user question")
        if len(self.arms) != len(set(self.arms)):
            raise ValueError("comparison arms must be unique")
        if not self.recall_types or len(self.recall_types) != len(
            set(self.recall_types)
        ):
            raise ValueError("recall_types must be nonempty and unique")
        if ("adequate" in self.arms) != bool(self.adequate_memories):
            raise ValueError("adequate arm requires nonempty adequate_memories only")
        for memory in self.adequate_memories:
            memory.check_scope(self.scope)
        return self


def json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def fingerprint(value: object) -> str:
    return hashlib.sha256(json_bytes(value)).hexdigest()
