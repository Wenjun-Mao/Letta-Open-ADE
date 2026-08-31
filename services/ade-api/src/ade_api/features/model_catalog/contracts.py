from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ade_api.platform.contracts import (
    CommentingTaskShape,
    LabelingOutputMode,
    ScenarioType,
)


class ApiOptionEntryResponse(BaseModel):
    key: str
    label: str
    description: str
    scenario: ScenarioType | None = None
    available: bool | None = None
    is_default: bool | None = None
    source_id: str | None = None
    source_label: str | None = None
    provider_model_id: str | None = None
    upstream_provider_model_id: str | None = None
    label_lab_available: bool | None = None
    structured_output_mode: LabelingOutputMode | None = None
    sampling_defaults: dict[str, Any] = Field(default_factory=dict)
    scenario_sampling_defaults: dict[str, dict[str, Any]] = Field(default_factory=dict)
    supports_top_k: bool | None = None
    supports_thinking: bool | None = None
    thinking_default_enabled: bool | None = None
    profile_applied: bool | None = None
    profile_source: str | None = None
    agent_studio_candidate: bool | None = None
    agent_studio_compatible: bool | None = None
    deployment: dict[str, Any] | None = None
    identity_sha256: str | None = None


class ApiOptionsDefaultsResponse(BaseModel):
    scenario: ScenarioType
    model: str
    prompt_key: str
    persona_key: str
    embedding: str
    schema_key: str = ""


class ApiAgentStudioRuntimeDefaultsResponse(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None


class ApiCommentingRuntimeDefaultsResponse(BaseModel):
    max_tokens: int
    timeout_seconds: float
    task_shape: CommentingTaskShape
    cache_prompt: bool
    temperature: float
    top_p: float
    top_k: int | None = None


class ApiLabelingRuntimeDefaultsResponse(BaseModel):
    max_tokens: int
    timeout_seconds: float
    repair_retry_count: int
    temperature: float
    top_p: float
    top_k: int | None = None


class ApiOptionsResponse(BaseModel):
    scenario: ScenarioType
    models: list[ApiOptionEntryResponse]
    embeddings: list[ApiOptionEntryResponse]
    prompts: list[ApiOptionEntryResponse]
    personas: list[ApiOptionEntryResponse]
    schemas: list[ApiOptionEntryResponse] = Field(default_factory=list)
    defaults: ApiOptionsDefaultsResponse
    agent_studio: ApiAgentStudioRuntimeDefaultsResponse | None = None
    commenting: ApiCommentingRuntimeDefaultsResponse | None = None
    labeling: ApiLabelingRuntimeDefaultsResponse | None = None


class RuntimeCapabilitiesResponse(BaseModel):
    per_request_model_override: bool
    per_request_model_override_via_extra_body: bool
    per_request_system_override: bool
    per_request_system_override_via_extra_body: bool


class ControlCapabilitiesResponse(BaseModel):
    update_system_prompt: bool
    update_agent_model: bool
    update_core_memory_block: bool
    attach_tool: bool
    detach_tool: bool


class SdkCapabilitiesResponse(BaseModel):
    messages_create_params: list[str]
    agents_update_params: list[str]
    blocks_update_params: list[str]


class CapabilitiesResponse(BaseModel):
    enabled: bool
    strict_mode: bool
    missing_required: list[str]
    runtime: RuntimeCapabilitiesResponse
    control: ControlCapabilitiesResponse
    sdk: SdkCapabilitiesResponse


class ModelCatalogSourceModelResponse(BaseModel):
    provider_model_id: str
    model_type: str


class ModelCatalogSourceResponse(BaseModel):
    id: str
    label: str
    kind: str
    adapter: str = "generic_openai"
    base_url: str
    enabled_for: list[str]
    letta_handle_prefix: str
    status: str
    detail: str
    allowlist_applied: bool | None = None
    allowlist_checked_at: str | None = None
    raw_model_count: int = 0
    filtered_model_count: int = 0
    models: list[ModelCatalogSourceModelResponse] = Field(default_factory=list)


class ModelCatalogEntryResponse(BaseModel):
    model_key: str
    source_id: str
    source_label: str
    source_kind: str
    source_adapter: str = "generic_openai"
    provider_model_id: str
    model_type: str
    letta_handle: str | None = None
    letta_catalog_visible: bool = False
    agent_studio_available: bool
    comment_lab_available: bool
    label_lab_available: bool
    structured_output_mode: LabelingOutputMode | None = None
    sampling_defaults: dict[str, Any] = Field(default_factory=dict)
    scenario_sampling_defaults: dict[str, dict[str, Any]] = Field(default_factory=dict)
    supports_top_k: bool = False
    supports_thinking: bool = False
    thinking_default_enabled: bool = False
    profile_applied: bool = False
    profile_source: str = ""
    agent_studio_candidate: bool = False
    agent_studio_compatible: bool = True
    deployment: dict[str, Any] | None = None


class ModelCatalogResponse(BaseModel):
    generated_at: float
    sources: list[ModelCatalogSourceResponse] = Field(default_factory=list)
    items: list[ModelCatalogEntryResponse] = Field(default_factory=list)
