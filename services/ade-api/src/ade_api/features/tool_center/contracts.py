from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCenterCreateRequest(BaseModel):
    slug: str
    source_code: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    source_type: str = "python"
    enable_parallel_execution: bool | None = None
    default_requires_approval: bool | None = None
    return_char_limit: int | None = None
    pip_requirements: list[dict[str, Any]] | None = None
    npm_requirements: list[dict[str, Any]] | None = None


class ToolCenterUpdateRequest(BaseModel):
    source_code: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    source_type: str | None = None
    enable_parallel_execution: bool | None = None
    default_requires_approval: bool | None = None
    return_char_limit: int | None = None
    pip_requirements: list[dict[str, Any]] | None = None
    npm_requirements: list[dict[str, Any]] | None = None


class ApiToolCenterItemResponse(BaseModel):
    slug: str | None = None
    tool_id: str
    name: str
    description: str
    tool_type: str
    source_type: str
    tags: list[str] = Field(default_factory=list)
    managed: bool
    read_only: bool
    archived: bool
    source_path: str | None = None
    source_code: str | None = None
    created_at: str = ""
    last_updated_at: str = ""
    updated_at: str | None = None
    archived_at: str | None = None


class ApiToolCenterListResponse(BaseModel):
    total: int
    include_archived: bool
    include_builtin: bool
    items: list[ApiToolCenterItemResponse]


class ToolTestInvokeRequest(BaseModel):
    agent_id: str
    input: str
    expected_tool_name: str | None = None
    override_model: str | None = None
    override_system: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    retry_count: int | None = Field(default=None, ge=0, le=5)


class ApiRuntimeToolResponse(BaseModel):
    id: str
    name: str
    description: str
    tool_type: str
    source_type: str
    created_at: str
    last_updated_at: str
    tags: list[str]
    attached_to_agent: bool | None = None
    managed: bool | None = None
    read_only: bool | None = None
    archived: bool | None = None
    slug: str | None = None


class ApiRuntimeToolListResponse(BaseModel):
    total: int
    search: str
    limit: int
    agent_id: str | None = None
    items: list[ApiRuntimeToolResponse]


class ApiToolTestInvokeResponse(BaseModel):
    agent_id: str
    input: str
    expected_tool_name: str | None = None
    expected_tool_matched: bool | None = None
    tool_call_count: int
    tool_return_count: int
    result: dict[str, Any]
