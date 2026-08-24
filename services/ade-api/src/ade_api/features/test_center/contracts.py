from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ade_api.features.test_center.run_descriptors import validate_test_run_options


class TestRunRequest(BaseModel):
    __test__: ClassVar[bool] = False

    model_config = ConfigDict(extra="forbid")

    run_type: Literal[
        "ade_api_e2e_check",
        "ade_mvp_smoke_e2e_check",
        "chat_memory_eval",
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
