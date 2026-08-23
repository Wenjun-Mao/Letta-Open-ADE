import { requestJson, type RequestOptions } from "./client";
import type { CommentingTaskShape, OptionEntry, PromptPersonaRevisionRecord, Scenario } from "./types";

export type ApiRequestOptions = Pick<RequestOptions, "signal">;

export type ScenarioOptions = {
  scenario: Scenario;
  models: OptionEntry[];
  embeddings: OptionEntry[];
  prompts: OptionEntry[];
  personas: OptionEntry[];
  schemas: OptionEntry[];
  defaults: {
    scenario: Scenario;
    model: string;
    prompt_key: string;
    persona_key: string;
    embedding: string;
    schema_key: string;
  };
  commenting?: {
    max_tokens: number;
    timeout_seconds: number;
    task_shape: CommentingTaskShape;
    cache_prompt: boolean;
    temperature: number;
    top_p: number;
    top_k?: number | null;
  };
  labeling?: {
    max_tokens: number;
    timeout_seconds: number;
    repair_retry_count: number;
    temperature: number;
    top_p: number;
    top_k?: number | null;
  };
  agent_studio?: {
    temperature?: number | null;
    top_p?: number | null;
    top_k?: number | null;
  };
};

export function fetchCapabilities(options?: ApiRequestOptions) {
  return requestJson<{
    enabled: boolean;
    strict_mode: boolean;
    missing_required: string[];
    runtime: Record<string, boolean>;
    control: Record<string, boolean>;
    sdk?: {
      messages_create_params: string[];
      agents_update_params: string[];
      blocks_update_params: string[];
    };
  }>("/api/v1/platform/capabilities", options);
}

export function fetchOptions(
  scenario: Scenario = "chat",
  options?: { refresh?: boolean; signal?: AbortSignal },
) {
  const params = new URLSearchParams({ scenario });
  if (options?.refresh) {
    params.set("refresh", "true");
  }
  return requestJson<ScenarioOptions>(`/api/v1/options?${params.toString()}`, { signal: options?.signal });
}

export function fetchPromptPersonaMetadata(scenario: Scenario = "chat", options?: ApiRequestOptions) {
  const params = new URLSearchParams({ scenario });
  return requestJson<{
    defaults: { scenario: Scenario; prompt_key: string; persona_key: string };
    prompts: Array<{
      scenario: Scenario;
      key: string;
      label: string;
      description: string;
      preview: string;
      length: number;
    }>;
    personas: Array<{ scenario: Scenario; key: string; preview: string; length: number }>;
  }>(`/api/v1/platform/metadata/prompts-personas?${params.toString()}`, options);
}

export function fetchPromptPersonaRevisions(agentId: string, field = "", limit = 80, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ limit: `${Math.max(1, Math.min(500, limit))}` });
  if (agentId.trim()) {
    params.set("agent_id", agentId.trim());
  }
  if (field.trim()) {
    params.set("field", field.trim());
  }
  return requestJson<{
    total: number;
    limit: number;
    agent_id: string | null;
    field: string | null;
    items: PromptPersonaRevisionRecord[];
  }>(`/api/v1/platform/metadata/prompts-personas/revisions?${params.toString()}`, options);
}
