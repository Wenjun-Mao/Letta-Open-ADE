import { requestJson } from "./client";
import type { PromptTemplateRecord, Scenario } from "./types";
import type { ApiRequestOptions } from "./platform";

function scenarioQuery(scenario?: Scenario): string {
  if (!scenario) {
    return "";
  }
  return `?${new URLSearchParams({ scenario }).toString()}`;
}

export function listPromptTemplates(includeArchived = false, scenario?: Scenario, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_archived: includeArchived ? "true" : "false" });
  if (scenario) {
    params.set("scenario", scenario);
  }
  return requestJson<{ total: number; scenario?: Scenario | null; include_archived: boolean; items: PromptTemplateRecord[] }>(
    `/api/v1/platform/prompt-center/prompts?${params.toString()}`,
    options,
  );
}

export function createPromptTemplate(payload: {
  scenario?: Scenario;
  key: string;
  label?: string;
  description?: string;
  content: string;
}) {
  return requestJson<PromptTemplateRecord>("/api/v1/platform/prompt-center/prompts", { method: "POST", body: payload });
}

export function updatePromptTemplate(
  key: string,
  payload: { label?: string; description?: string; content?: string },
  scenario?: Scenario,
) {
  return requestJson<PromptTemplateRecord>(`/api/v1/platform/prompt-center/prompts/${key}${scenarioQuery(scenario)}`, {
    method: "PATCH",
    body: payload,
  });
}

export function archivePromptTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v1/platform/prompt-center/prompts/${key}/archive${scenarioQuery(scenario)}`, { method: "POST" });
}

export function restorePromptTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v1/platform/prompt-center/prompts/${key}/restore${scenarioQuery(scenario)}`, { method: "POST" });
}

export function purgePromptTemplate(key: string, scenario?: Scenario) {
  return requestJson<{ ok: boolean; key: string; kind: string }>(`/api/v1/platform/prompt-center/prompts/${key}/purge${scenarioQuery(scenario)}`, { method: "DELETE" });
}

export function listPersonaTemplates(includeArchived = false, scenario?: Scenario, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_archived: includeArchived ? "true" : "false" });
  if (scenario) {
    params.set("scenario", scenario);
  }
  return requestJson<{ total: number; scenario?: Scenario | null; include_archived: boolean; items: PromptTemplateRecord[] }>(
    `/api/v1/platform/prompt-center/personas?${params.toString()}`,
    options,
  );
}

export function createPersonaTemplate(payload: {
  scenario?: Scenario;
  key: string;
  label?: string;
  description?: string;
  content: string;
}) {
  return requestJson<PromptTemplateRecord>("/api/v1/platform/prompt-center/personas", { method: "POST", body: payload });
}

export function updatePersonaTemplate(
  key: string,
  payload: { label?: string; description?: string; content?: string },
  scenario?: Scenario,
) {
  return requestJson<PromptTemplateRecord>(`/api/v1/platform/prompt-center/personas/${key}${scenarioQuery(scenario)}`, {
    method: "PATCH",
    body: payload,
  });
}

export function archivePersonaTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v1/platform/prompt-center/personas/${key}/archive${scenarioQuery(scenario)}`, { method: "POST" });
}

export function restorePersonaTemplate(key: string, scenario?: Scenario) {
  return requestJson<PromptTemplateRecord>(`/api/v1/platform/prompt-center/personas/${key}/restore${scenarioQuery(scenario)}`, { method: "POST" });
}

export function purgePersonaTemplate(key: string, scenario?: Scenario) {
  return requestJson<{ ok: boolean; key: string; kind: string }>(`/api/v1/platform/prompt-center/personas/${key}/purge${scenarioQuery(scenario)}`, { method: "DELETE" });
}
