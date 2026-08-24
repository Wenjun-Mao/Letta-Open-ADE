import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

import type { Scenario } from "@/features/model-catalog/api";

export type PromptTemplateRecord = {
  kind: "prompt" | "persona";
  scenario: Scenario;
  key: string;
  label: string;
  description: string;
  content: string;
  preview: string;
  length: number;
  archived: boolean;
  source_path: string;
  updated_at: string;
  output_schema?: string | null;
};

export type PromptPersonaRevisionRecord = {
  revision_id: string;
  recorded_at: string;
  agent_id: string;
  field: "system" | "persona" | "human";
  source: string;
  before: string;
  after: string;
  before_preview: string;
  after_preview: string;
  before_length: number;
  after_length: number;
  delta_length: number;
};

function scenarioQuery(scenario?: Scenario): string {
  return scenario ? `?${new URLSearchParams({ scenario }).toString()}` : "";
}

export function listPromptTemplates(includeArchived = false, scenario?: Scenario, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_archived: includeArchived ? "true" : "false" });
  if (scenario) params.set("scenario", scenario);
  return requestJson<{ total: number; scenario?: Scenario | null; include_archived: boolean; items: PromptTemplateRecord[] }>(
    `/api/v2/prompt-center/prompts?${params.toString()}`,
    options,
  );
}

export function createPromptTemplate(payload: { scenario?: Scenario; key: string; label?: string; description?: string; content: string }) {
  return requestJson<PromptTemplateRecord>("/api/v2/prompt-center/prompts", { method: "POST", body: payload });
}

export function updatePromptTemplate(key: string, payload: { label?: string; description?: string; content?: string }, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v2/prompt-center/prompts/${key}${scenarioQuery(scenario)}`, {
    method: "PATCH",
    body: payload,
  });
}

export function archivePromptTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v2/prompt-center/prompts/${key}/archive${scenarioQuery(scenario)}`, { method: "POST" });
}

export function restorePromptTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v2/prompt-center/prompts/${key}/restore${scenarioQuery(scenario)}`, { method: "POST" });
}

export function purgePromptTemplate(key: string, scenario?: Scenario) {
  return requestJson<{ ok: boolean; key: string; kind: string }>(`/api/v2/prompt-center/prompts/${key}/purge${scenarioQuery(scenario)}`, { method: "DELETE" });
}

export function listPersonaTemplates(includeArchived = false, scenario?: Scenario, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_archived: includeArchived ? "true" : "false" });
  if (scenario) params.set("scenario", scenario);
  return requestJson<{ total: number; scenario?: Scenario | null; include_archived: boolean; items: PromptTemplateRecord[] }>(
    `/api/v2/prompt-center/personas?${params.toString()}`,
    options,
  );
}

export function createPersonaTemplate(payload: { scenario?: Scenario; key: string; label?: string; description?: string; content: string }) {
  return requestJson<PromptTemplateRecord>("/api/v2/prompt-center/personas", { method: "POST", body: payload });
}

export function updatePersonaTemplate(key: string, payload: { label?: string; description?: string; content?: string }, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v2/prompt-center/personas/${key}${scenarioQuery(scenario)}`, {
    method: "PATCH",
    body: payload,
  });
}

export function archivePersonaTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v2/prompt-center/personas/${key}/archive${scenarioQuery(scenario)}`, { method: "POST" });
}

export function restorePersonaTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v2/prompt-center/personas/${key}/restore${scenarioQuery(scenario)}`, { method: "POST" });
}

export function purgePersonaTemplate(key: string, scenario?: Scenario) {
  return requestJson<{ ok: boolean; key: string; kind: string }>(`/api/v2/prompt-center/personas/${key}/purge${scenarioQuery(scenario)}`, { method: "DELETE" });
}

export function fetchPromptPersonaMetadata(scenario: Scenario = "chat", options?: ApiRequestOptions) {
  const params = new URLSearchParams({ scenario });
  return requestJson<{
    defaults: { scenario: Scenario; prompt_key: string; persona_key: string };
    prompts: Array<{ scenario: Scenario; key: string; label: string; description: string; preview: string; length: number }>;
    personas: Array<{ scenario: Scenario; key: string; preview: string; length: number }>;
  }>(`/api/v2/prompt-center/catalog?${params.toString()}`, options);
}

export function fetchPromptPersonaRevisions(agentId: string, field = "", limit = 80, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ limit: `${Math.max(1, Math.min(500, limit))}` });
  if (agentId.trim()) params.set("agent_id", agentId.trim());
  if (field.trim()) params.set("field", field.trim());
  return requestJson<{
    total: number;
    limit: number;
    agent_id: string | null;
    field: string | null;
    items: PromptPersonaRevisionRecord[];
  }>(`/api/v2/prompt-center/revisions?${params.toString()}`, options);
}
