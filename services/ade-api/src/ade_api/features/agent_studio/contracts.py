from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ade_api.platform.contracts import ScenarioType


class ChatRequest(BaseModel):
    message: str
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    retry_count: int | None = Field(default=None, ge=0, le=5)


class AgentCreateRequest(BaseModel):
    scenario: ScenarioType = "chat"
    name: str = "dev-agent"
    model: str = ""
    prompt_key: str = "chat_v20260516"
    persona_key: str = "chat_linxiaotang"
    embedding: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    top_k: int | None = Field(default=None, gt=0)


class ApiAgentListItemResponse(BaseModel):
    id: str
    name: str
    model: str
    created_at: str
    last_updated_at: str
    last_interaction_at: str
    archived: bool = False


class ApiAgentListResponse(BaseModel):
    total: int
    items: list[ApiAgentListItemResponse]


class ApiAgentCreateResponse(BaseModel):
    id: str
    name: str
    scenario: ScenarioType
    model: str
    embedding: str | None = None
    prompt_key: str
    persona_key: str


class ApiAgentLifecycleResponse(BaseModel):
    id: str
    name: str
    model: str
    archived: bool
    archived_at: str | None = None
    updated_at: str


class ApiAgentPurgeResponse(BaseModel):
    ok: bool
    id: str
    kind: str


class ApiAgentDetailsResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    model: str
    embedding: str | None = None
    llm_config: Any = None
    embedding_config: Any = None
    tool_rules: Any = None
    description: str | None = None
    created_at: str
    last_updated_at: str
    last_interaction_at: str
    context_window_limit: int | None = None
    tools: dict[str, str]
    system: str
    memory: dict[str, str]


class ApiPersistentAgentSummaryResponse(BaseModel):
    id: str
    name: str
    agent_type: str
    model: str
    embedding: str | None = None
    created_at: str
    last_updated_at: str
    context_window_limit: int | None = None
    tool_rules: str


class ApiPersistentMemoryBlockResponse(BaseModel):
    label: str
    description: str
    limit: int | None = None
    value: str


class ApiPersistentToolResponse(BaseModel):
    id: str
    name: str
    description: str


class ApiConversationHistoryItemResponse(BaseModel):
    id: str
    created_at: str
    message_type: str
    role: str
    status: str
    name: str | None = None
    tool_arguments: str | None = None
    content: str


class ApiConversationHistoryResponse(BaseModel):
    total_persisted: int
    displayed: int
    limit: int
    counts_by_type: dict[str, int]
    items: list[ApiConversationHistoryItemResponse]


class ApiPersistentStateResponse(BaseModel):
    source: str
    agent: ApiPersistentAgentSummaryResponse
    memory_blocks: list[ApiPersistentMemoryBlockResponse]
    tools: list[ApiPersistentToolResponse]
    conversation_history: ApiConversationHistoryResponse


class ApiRawPromptMessageResponse(BaseModel):
    role: str
    content: str


class ApiRawPromptResponse(BaseModel):
    messages: list[ApiRawPromptMessageResponse]


class ApiChatResponse(BaseModel):
    total_steps: int = 0
    sequence: list[dict[str, Any]] = Field(default_factory=list)
    memory_diff: dict[str, Any] = Field(default_factory=dict)


class RuntimeMessageRequest(BaseModel):
    input: str
    override_model: str | None = None
    override_system: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0, le=600)
    retry_count: int | None = Field(default=None, ge=0, le=5)


class SystemPromptUpdateRequest(BaseModel):
    system: str


class AgentModelUpdateRequest(BaseModel):
    model: str


class MemoryBlockUpdateRequest(BaseModel):
    value: str


class ApiRuntimeMessageResponse(BaseModel):
    agent_id: str
    override_model: str | None = None
    override_system: str | None = None
    result: dict[str, Any]


class ApiSystemUpdateResponse(BaseModel):
    agent_id: str
    model: str
    system_before: str
    system_after: str


class ApiModelUpdateResponse(BaseModel):
    agent_id: str
    model_before: str
    model_after: str
    system: str


class ApiMemoryBlockUpdateResponse(BaseModel):
    agent_id: str
    block_label: str
    value_before: str
    value_after: str
    description: str
    limit: int | None = None


class ApiToolAttachDetachResponse(BaseModel):
    agent_id: str
    tool_id: str
    tool_was_attached: bool
    tool_is_attached: bool
    tool_count_before: int
    tool_count_after: int
