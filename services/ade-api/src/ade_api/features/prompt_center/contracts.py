from __future__ import annotations

from pydantic import BaseModel

from ade_api.platform.contracts import ScenarioType


class ApiPromptPersonaDefaultResponse(BaseModel):
    scenario: ScenarioType
    prompt_key: str
    persona_key: str


class ApiPromptMetadataResponse(BaseModel):
    scenario: ScenarioType
    key: str
    label: str
    description: str
    preview: str
    length: int


class ApiPersonaMetadataResponse(BaseModel):
    scenario: ScenarioType
    key: str
    preview: str
    length: int


class ApiPromptPersonaMetadataResponse(BaseModel):
    defaults: ApiPromptPersonaDefaultResponse
    prompts: list[ApiPromptMetadataResponse]
    personas: list[ApiPersonaMetadataResponse]


class PromptTemplateWriteRequest(BaseModel):
    scenario: ScenarioType | None = None
    key: str
    label: str = ""
    description: str = ""
    content: str


class PromptTemplatePatchRequest(BaseModel):
    label: str | None = None
    description: str | None = None
    content: str | None = None


class PersonaTemplateWriteRequest(BaseModel):
    scenario: ScenarioType | None = None
    key: str
    label: str = ""
    description: str = ""
    content: str


class PersonaTemplatePatchRequest(BaseModel):
    label: str | None = None
    description: str | None = None
    content: str | None = None


class ApiTemplateRecordResponse(BaseModel):
    kind: str
    scenario: ScenarioType
    key: str
    label: str
    description: str
    content: str
    content_sha256: str
    preview: str
    length: int
    archived: bool
    source_path: str
    updated_at: str
    output_schema: str | None = None


class ApiTemplateListResponse(BaseModel):
    total: int
    scenario: ScenarioType | None = None
    include_archived: bool
    items: list[ApiTemplateRecordResponse]


class ApiPromptPersonaRevisionResponse(BaseModel):
    revision_id: str
    recorded_at: str
    agent_id: str
    field: str
    source: str
    before: str
    after: str
    before_preview: str
    after_preview: str
    before_length: int
    after_length: int
    delta_length: int


class ApiPromptPersonaRevisionsResponse(BaseModel):
    total: int
    limit: int
    agent_id: str | None = None
    field: str | None = None
    items: list[ApiPromptPersonaRevisionResponse]
