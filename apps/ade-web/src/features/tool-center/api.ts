import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

export type ToolCenterItem = {
  slug?: string | null;
  tool_id: string;
  name: string;
  description: string;
  tool_type: string;
  source_type: string;
  tags: string[];
  managed: boolean;
  read_only: boolean;
  archived: boolean;
  source_path?: string | null;
  source_code?: string | null;
  created_at?: string;
  last_updated_at?: string;
  updated_at?: string | null;
  archived_at?: string | null;
};

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
  if (options?.search?.trim()) params.set("search", options.search.trim());
  return requestJson<{ total: number; include_archived: boolean; include_builtin: boolean; items: ToolCenterItem[] }>(
    `/api/v2/tool-center/tools?${params.toString()}`,
    { signal: options?.signal },
  );
}

export function getToolCenterTool(slug: string, includeSource = true, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_source: includeSource ? "true" : "false" });
  return requestJson<ToolCenterItem>(`/api/v2/tool-center/tools/${slug}?${params.toString()}`, options);
}

export function createToolCenterTool(payload: ToolCenterMutation & { slug: string; source_code: string }) {
  return requestJson<ToolCenterItem>("/api/v2/tool-center/tools", { method: "POST", body: payload });
}

export function updateToolCenterTool(slug: string, payload: ToolCenterMutation) {
  return requestJson<ToolCenterItem>(`/api/v2/tool-center/tools/${slug}`, { method: "PATCH", body: payload });
}

export function archiveToolCenterTool(slug: string) {
  return requestJson<ToolCenterItem>(`/api/v2/tool-center/tools/${slug}/archive`, { method: "POST" });
}

export function restoreToolCenterTool(slug: string) {
  return requestJson<ToolCenterItem>(`/api/v2/tool-center/tools/${slug}/restore`, { method: "POST" });
}

export function purgeToolCenterTool(slug: string) {
  return requestJson<{ ok: boolean; slug: string; kind: string }>(`/api/v2/tool-center/tools/${slug}/purge`, { method: "DELETE" });
}
