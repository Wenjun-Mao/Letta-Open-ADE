import { requestJson } from "./client";
import type { AgentDetails, AgentLifecycleRecord, AgentListItem, ChatResult, PersistentState, Scenario } from "./types";
import type { ApiRequestOptions } from "./platform";

export function listAgents(
  limit = 200,
  includeLastInteraction = false,
  includeArchived = false,
  options?: ApiRequestOptions,
) {
  const params = new URLSearchParams({ limit: `${limit}` });
  if (includeLastInteraction) {
    params.set("include_last_interaction", "true");
  }
  if (includeArchived) {
    params.set("include_archived", "true");
  }
  return requestJson<{ total: number; items: AgentListItem[] }>(`/api/v1/agents?${params.toString()}`, options);
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
  }>("/api/v1/agents", { method: "POST", body: payload });
}

export function archiveAgent(agentId: string) {
  return requestJson<AgentLifecycleRecord>(`/api/v1/platform/agents/${agentId}/archive`, { method: "POST" });
}

export function restoreAgent(agentId: string) {
  return requestJson<AgentLifecycleRecord>(`/api/v1/platform/agents/${agentId}/restore`, { method: "POST" });
}

export function purgeAgent(agentId: string) {
  return requestJson<{ ok: boolean; id: string; kind: string }>(`/api/v1/platform/agents/${agentId}/purge`, { method: "DELETE" });
}

export function getAgentDetails(agentId: string, options?: ApiRequestOptions) {
  return requestJson<AgentDetails>(`/api/v1/agents/${agentId}/details`, options);
}

export function getPersistentState(agentId: string, limit = 120, options?: ApiRequestOptions) {
  return requestJson<PersistentState>(`/api/v1/agents/${agentId}/persistent_state?limit=${limit}`, options);
}

export function getRawPrompt(agentId: string, options?: ApiRequestOptions) {
  return requestJson<{ messages: Array<{ role: string; content: string }> }>(`/api/v1/agents/${agentId}/raw_prompt`, options);
}

export function sendChat(
  agentId: string,
  message: string,
  options?: { timeout_seconds?: number; retry_count?: number; signal?: AbortSignal },
) {
  return requestJson<ChatResult>("/api/v1/chat", {
    method: "POST",
    signal: options?.signal,
    body: {
      agent_id: agentId,
      message,
      timeout_seconds: options?.timeout_seconds,
      retry_count: options?.retry_count,
    },
  });
}

export function updateSystemPrompt(agentId: string, system: string) {
  return requestJson<{ system_after: string; system_before: string }>(`/api/v1/platform/agents/${agentId}/system`, {
    method: "PATCH",
    body: { system },
  });
}

export function updateAgentModel(agentId: string, model: string) {
  return requestJson<{ model_after: string; model_before: string }>(`/api/v1/platform/agents/${agentId}/model`, {
    method: "PATCH",
    body: { model },
  });
}

export function updateCoreMemoryBlock(agentId: string, blockLabel: string, value: string) {
  return requestJson<{ value_before: string; value_after: string }>(
    `/api/v1/platform/agents/${agentId}/core-memory/blocks/${blockLabel}`,
    { method: "PATCH", body: { value } },
  );
}
