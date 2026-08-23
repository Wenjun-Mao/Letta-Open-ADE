import { requestJson } from "./client";
import type { PlatformTool, PlatformToolTestInvokeResult, ToolCenterItem } from "./types";
import type { ApiRequestOptions } from "./platform";

export function listTools(search = "", limit = 200, agentId = "", options?: ApiRequestOptions) {
  const params = new URLSearchParams({ limit: `${limit}` });
  if (search.trim()) {
    params.set("search", search.trim());
  }
  if (agentId.trim()) {
    params.set("agent_id", agentId.trim());
  }
  return requestJson<{ total: number; items: PlatformTool[] }>(`/api/v1/platform/tools?${params.toString()}`, options);
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
  return requestJson<PlatformToolTestInvokeResult>("/api/v1/platform/tools/test-invoke", { method: "POST", body, signal });
}

export function attachTool(agentId: string, toolId: string) {
  return requestJson(`/api/v1/platform/agents/${agentId}/tools/attach/${toolId}`, { method: "PATCH" });
}

export function detachTool(agentId: string, toolId: string) {
  return requestJson(`/api/v1/platform/agents/${agentId}/tools/detach/${toolId}`, { method: "PATCH" });
}

export function listToolCenterTools(options?: {
  includeArchived?: boolean;
  includeBuiltin?: boolean;
  includeSource?: boolean;
  search?: string;
  signal?: AbortSignal;
}) {
  const params = new URLSearchParams({
    include_archived: options?.includeArchived ? "true" : "false",
    include_builtin: options?.includeBuiltin === false ? "false" : "true",
    include_source: options?.includeSource ? "true" : "false",
  });
  if (options?.search?.trim()) {
    params.set("search", options.search.trim());
  }
  return requestJson<{ total: number; include_archived: boolean; include_builtin: boolean; items: ToolCenterItem[] }>(
    `/api/v1/platform/tool-center/tools?${params.toString()}`,
    { signal: options?.signal },
  );
}

export function getToolCenterTool(slug: string, includeSource = true, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_source: includeSource ? "true" : "false" });
  return requestJson<ToolCenterItem>(`/api/v1/platform/tool-center/tools/${slug}?${params.toString()}`, options);
}

export type ToolCenterMutation = {
  source_code?: string;
  description?: string;
  tags?: string[];
  source_type?: string;
  enable_parallel_execution?: boolean;
  default_requires_approval?: boolean;
  return_char_limit?: number;
  pip_requirements?: Array<Record<string, unknown>>;
  npm_requirements?: Array<Record<string, unknown>>;
};

export function createToolCenterTool(payload: ToolCenterMutation & { slug: string; source_code: string }) {
  return requestJson<ToolCenterItem>("/api/v1/platform/tool-center/tools", { method: "POST", body: payload });
}

export function updateToolCenterTool(slug: string, payload: ToolCenterMutation) {
  return requestJson<ToolCenterItem>(`/api/v1/platform/tool-center/tools/${slug}`, { method: "PATCH", body: payload });
}

export function archiveToolCenterTool(slug: string) {
  return requestJson<ToolCenterItem>(`/api/v1/platform/tool-center/tools/${slug}/archive`, { method: "POST" });
}

export function restoreToolCenterTool(slug: string) {
  return requestJson<ToolCenterItem>(`/api/v1/platform/tool-center/tools/${slug}/restore`, { method: "POST" });
}

export function purgeToolCenterTool(slug: string) {
  return requestJson<{ ok: boolean; slug: string; kind: string }>(`/api/v1/platform/tool-center/tools/${slug}/purge`, { method: "DELETE" });
}
