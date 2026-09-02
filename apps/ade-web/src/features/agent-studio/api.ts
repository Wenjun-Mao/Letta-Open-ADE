import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

import type {
  AgentDefinition,
  AgentStudioOptions,
  AgentStudioSession,
  ConversationState,
  CreateDefinition,
  CreateSession,
  MemorySubject,
  Run,
  RunEvent,
  SubjectMemories,
} from "./types";

type ListResponse<T> = { total: number; items: T[] };

function listPath(path: string, includeArchived: boolean): string {
  const query = new URLSearchParams({ limit: "200", offset: "0" });
  if (includeArchived) query.set("include_archived", "true");
  return `${path}?${query.toString()}`;
}

export function getAgentStudioOptions(): Promise<AgentStudioOptions> {
  return requestJson("/api/v3/agent-studio/options");
}

export function listAgentStudioSessions(includeArchived = false): Promise<ListResponse<AgentStudioSession>> {
  return requestJson(listPath("/api/v3/agent-studio/sessions", includeArchived));
}

export function getAgentStudioSession(conversationId: string): Promise<AgentStudioSession> {
  return requestJson(`/api/v3/agent-studio/sessions/${encodeURIComponent(conversationId)}`);
}

export function createAgentStudioSession(payload: CreateSession): Promise<AgentStudioSession> {
  return requestJson("/api/v3/agent-studio/sessions", { method: "POST", body: payload });
}

export function archiveAgentStudioSession(conversationId: string): Promise<AgentStudioSession> {
  return requestJson(`/api/v3/agent-studio/sessions/${encodeURIComponent(conversationId)}`, { method: "DELETE" });
}

export function restoreAgentStudioSession(conversationId: string): Promise<AgentStudioSession> {
  return requestJson(`/api/v3/agent-studio/sessions/${encodeURIComponent(conversationId)}/restore`, { method: "POST" });
}

export function getConversationState(conversationId: string, beforeSequence?: number): Promise<ConversationState> {
  const query = new URLSearchParams({ message_limit: "120" });
  if (beforeSequence) query.set("before_sequence", String(beforeSequence));
  return requestJson(`/api/v3/agent-studio/sessions/${encodeURIComponent(conversationId)}/state?${query.toString()}`);
}

export function listAgentStudioDefinitions(includeArchived = false): Promise<ListResponse<AgentDefinition>> {
  return requestJson(listPath("/api/v3/agent-studio/definitions", includeArchived));
}

export function createAgentStudioDefinition(payload: CreateDefinition): Promise<AgentDefinition> {
  return requestJson("/api/v3/agent-studio/definitions", { method: "POST", body: payload });
}

export function archiveAgentStudioDefinition(rootId: string): Promise<AgentDefinition> {
  return requestJson(`/api/v3/agent-studio/definitions/${encodeURIComponent(rootId)}`, { method: "DELETE" });
}

export function restoreAgentStudioDefinition(rootId: string): Promise<AgentDefinition> {
  return requestJson(`/api/v3/agent-studio/definitions/${encodeURIComponent(rootId)}/restore`, { method: "POST" });
}

export function listAgentStudioSubjects(includeArchived = false): Promise<ListResponse<MemorySubject>> {
  return requestJson(listPath("/api/v3/agent-studio/subjects", includeArchived));
}

export function createAgentStudioSubject(payload: { external_key: string; display_name: string }): Promise<MemorySubject> {
  return requestJson("/api/v3/agent-studio/subjects", { method: "POST", body: payload });
}

export function updateAgentStudioSubject(
  subjectId: string,
  payload: { display_name: string; expected_version: number },
): Promise<MemorySubject> {
  return requestJson(`/api/v3/agent-studio/subjects/${encodeURIComponent(subjectId)}`, { method: "PATCH", body: payload });
}

export function archiveAgentStudioSubject(subjectId: string): Promise<MemorySubject> {
  return requestJson(`/api/v3/agent-studio/subjects/${encodeURIComponent(subjectId)}`, { method: "DELETE" });
}

export function restoreAgentStudioSubject(subjectId: string): Promise<MemorySubject> {
  return requestJson(`/api/v3/agent-studio/subjects/${encodeURIComponent(subjectId)}/restore`, { method: "POST" });
}

export function getSubjectMemories(subjectId: string): Promise<SubjectMemories> {
  return requestJson(`/api/v3/agent-studio/subjects/${encodeURIComponent(subjectId)}/memories`);
}

export function acceptTurn(
  conversationId: string,
  payload: { content: string; idempotency_key: string; timeout_seconds: number; retry_count: number },
): Promise<{ run_id: string; status: Run["status"]; events_url: string; idempotent_replay: boolean }> {
  return requestJson(`/api/v3/conversations/${encodeURIComponent(conversationId)}/turns`, { method: "POST", body: payload });
}

export function getRun(runId: string): Promise<Run> {
  return requestJson(`/api/v3/runs/${encodeURIComponent(runId)}`);
}

export function listConversationRuns(conversationId: string): Promise<ListResponse<Run>> {
  return requestJson(`/api/v3/conversations/${encodeURIComponent(conversationId)}/runs`);
}

export function cancelRun(runId: string): Promise<Run> {
  return requestJson(`/api/v3/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
}

export function getRunEventLog(runId: string): Promise<ListResponse<RunEvent>> {
  return requestJson(`/api/v3/runs/${encodeURIComponent(runId)}/event-log`);
}

export function runEventsUrl(runId: string): string {
  return `/api/v3/runs/${encodeURIComponent(runId)}/events`;
}

// Dashboard still consumes this small, read-only count adapter. It now counts
// ADE-native definition roots instead of legacy Letta agents.
export type AgentListItem = {
  id: string;
  name: string;
  model: string;
  created_at: string;
  last_updated_at: string;
  last_interaction_at: string;
  archived: boolean;
};

export async function listAgents(
  _limit = 200,
  _includeLastInteraction = false,
  includeArchived = false,
  options?: ApiRequestOptions,
): Promise<ListResponse<AgentListItem>> {
  const response = await requestJson<ListResponse<AgentDefinition>>(
    listPath("/api/v3/agent-studio/definitions", includeArchived),
    options,
  );
  return {
    total: response.total,
    items: response.items.map((definition) => ({
      id: definition.agent_definition_id || definition.id,
      name: definition.name,
      model: definition.deployments.find((deployment) => deployment.role === "conversation")?.route_alias || "native",
      created_at: definition.created_at,
      last_updated_at: definition.created_at,
      last_interaction_at: definition.created_at,
      archived: Boolean(definition.archived_at),
    })),
  };
}
