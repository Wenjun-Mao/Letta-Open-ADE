import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

import type { Scenario } from "@/features/model-catalog/api";

export type AgentListItem = {
  id: string;
  name: string;
  model: string;
  created_at: string;
  last_updated_at: string;
  last_interaction_at: string;
  archived: boolean;
};

export type AgentLifecycleRecord = {
  id: string;
  name: string;
  model: string;
  archived: boolean;
  archived_at?: string | null;
  updated_at: string;
};

export type AgentDetails = {
  id: string;
  name: string;
  agent_type?: string;
  model: string;
  embedding?: string | null;
  created_at?: string;
  last_updated_at?: string;
  last_interaction_at?: string;
  llm_config?: unknown;
  embedding_config?: unknown;
  tool_rules?: unknown;
  context_window_limit?: number | null;
  system: string;
  tools: Record<string, string>;
  memory: Record<string, string>;
};

export type PersistentState = {
  source?: string;
  agent?: {
    id: string;
    name: string;
    agent_type: string;
    model: string;
    embedding?: string | null;
    created_at?: string;
    last_updated_at?: string;
    context_window_limit?: number | null;
    tool_rules?: string;
  };
  memory_blocks: Array<{
    label: string;
    value: string;
    description: string;
    limit: number | null;
  }>;
  tools?: Array<{
    id: string;
    name: string;
    description: string;
  }>;
  conversation_history: {
    total_persisted: number;
    displayed: number;
    limit?: number;
    counts_by_type?: Record<string, number>;
    items: Array<{
      id: string;
      created_at: string;
      role: string;
      message_type: string;
      content: string;
      name?: string | null;
      tool_arguments?: string | null;
    }>;
  };
};

export type ChatStep = {
  type: string;
  content?: string;
  name?: string;
  status?: string;
  arguments?: string;
  tool_arguments?: string;
  message_type?: string;
};

export type ChatResult = {
  total_steps: number;
  sequence: ChatStep[];
  memory_diff: {
    old: Record<string, string>;
    new: Record<string, string>;
  };
};

export type RuntimeTool = {
  id: string;
  name: string;
  description: string;
  tool_type: string;
  source_type: string;
  created_at: string;
  last_updated_at: string;
  tags: string[];
  attached_to_agent?: boolean;
  managed?: boolean;
  read_only?: boolean;
  archived?: boolean;
  slug?: string | null;
};

export type ToolProbeResult = {
  agent_id: string;
  input: string;
  expected_tool_name?: string | null;
  expected_tool_matched?: boolean | null;
  tool_call_count: number;
  tool_return_count: number;
  result: ChatResult;
};

export function listAgents(
  limit = 200,
  includeLastInteraction = false,
  includeArchived = false,
  options?: ApiRequestOptions,
) {
  const params = new URLSearchParams({ limit: `${limit}` });
  if (includeLastInteraction) params.set("include_last_interaction", "true");
  if (includeArchived) params.set("include_archived", "true");
  return requestJson<{ total: number; items: AgentListItem[] }>(`/api/v2/agent-studio/agents?${params.toString()}`, options);
}

export function createAgent(payload: {
  scenario: Scenario;
  name: string;
  model: string;
  prompt_key: string;
  persona_key?: string;
  embedding?: string | null;
  temperature?: number;
  top_p?: number;
  top_k?: number;
}) {
  return requestJson<{
    id: string;
    name: string;
    scenario: Scenario;
    model: string;
    embedding?: string | null;
    prompt_key: string;
    persona_key?: string;
  }>("/api/v2/agent-studio/agents", { method: "POST", body: payload });
}

export function archiveAgent(agentId: string) {
  return requestJson<AgentLifecycleRecord>(`/api/v2/agent-studio/agents/${agentId}/archive`, { method: "POST" });
}

export function restoreAgent(agentId: string) {
  return requestJson<AgentLifecycleRecord>(`/api/v2/agent-studio/agents/${agentId}/restore`, { method: "POST" });
}

export function purgeAgent(agentId: string) {
  return requestJson<{ ok: boolean; id: string; kind: string }>(`/api/v2/agent-studio/agents/${agentId}/purge`, { method: "DELETE" });
}

export function getAgentDetails(agentId: string, options?: ApiRequestOptions) {
  return requestJson<AgentDetails>(`/api/v2/agent-studio/agents/${agentId}`, options);
}

export function getPersistentState(agentId: string, limit = 120, options?: ApiRequestOptions) {
  return requestJson<PersistentState>(`/api/v2/agent-studio/agents/${agentId}/persistent-state?limit=${limit}`, options);
}

export function getRawPrompt(agentId: string, options?: ApiRequestOptions) {
  return requestJson<{ messages: Array<{ role: string; content: string }> }>(`/api/v2/agent-studio/agents/${agentId}/raw-prompt`, options);
}

export function sendChat(
  agentId: string,
  message: string,
  options?: { timeout_seconds?: number; retry_count?: number; signal?: AbortSignal },
) {
  return requestJson<ChatResult>(`/api/v2/agent-studio/agents/${agentId}/messages`, {
    method: "POST",
    signal: options?.signal,
    body: { message, timeout_seconds: options?.timeout_seconds, retry_count: options?.retry_count },
  });
}

export function updateSystemPrompt(agentId: string, system: string) {
  return requestJson<{ system_after: string; system_before: string }>(`/api/v2/agent-studio/agents/${agentId}/system-prompt`, {
    method: "PATCH",
    body: { system },
  });
}

export function updateAgentModel(agentId: string, model: string) {
  return requestJson<{ model_after: string; model_before: string }>(`/api/v2/agent-studio/agents/${agentId}/model`, {
    method: "PATCH",
    body: { model },
  });
}

export function updateCoreMemoryBlock(agentId: string, blockLabel: string, value: string) {
  return requestJson<{ value_before: string; value_after: string }>(
    `/api/v2/agent-studio/agents/${agentId}/memory/${blockLabel}`,
    { method: "PATCH", body: { value } },
  );
}

export function listRuntimeTools(search = "", limit = 200, agentId = "", options?: ApiRequestOptions) {
  const params = new URLSearchParams({ limit: `${limit}` });
  if (search.trim()) params.set("search", search.trim());
  if (agentId.trim()) params.set("agent_id", agentId.trim());
  return requestJson<{ total: number; items: RuntimeTool[] }>(`/api/v2/tool-center/runtime-tools?${params.toString()}`, options);
}

export function testInvokeTool(payload: {
  agent_id: string;
  input: string;
  expected_tool_name?: string;
  override_model?: string;
  override_system?: string;
  timeout_seconds?: number;
  retry_count?: number;
  signal?: AbortSignal;
}) {
  const { signal, ...body } = payload;
  return requestJson<ToolProbeResult>("/api/v2/tool-center/invocations", { method: "POST", body, signal });
}

export function attachTool(agentId: string, toolId: string) {
  return requestJson(`/api/v2/agent-studio/agents/${agentId}/tools/${toolId}/attach`, { method: "PATCH" });
}

export function detachTool(agentId: string, toolId: string) {
  return requestJson(`/api/v2/agent-studio/agents/${agentId}/tools/${toolId}/detach`, { method: "PATCH" });
}
