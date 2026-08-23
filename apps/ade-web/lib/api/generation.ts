import { requestJson } from "./client";
import type {
  CommentingGenerateResponse,
  CommentingTaskShape,
  LabelSchemaRecord,
  LabelingGenerateResponse,
} from "./types";
import type { ApiRequestOptions } from "./platform";

export function generateComment(payload: {
  input: string;
  prompt_key: string;
  persona_key: string;
  model_key?: string;
  model?: string;
  max_tokens?: number;
  timeout_seconds?: number;
  retry_count?: number;
  task_shape?: CommentingTaskShape;
  cache_prompt?: boolean;
  enable_thinking?: boolean;
  temperature?: number;
  top_p?: number;
  top_k?: number;
}) {
  return requestJson<CommentingGenerateResponse>("/api/v2/comment-lab/generations", {
    method: "POST",
    body: { scenario: "comment", ...payload, model_key: payload.model_key?.trim() || undefined, model: payload.model?.trim() || undefined },
  });
}

export function generateLabels(payload: {
  input: string;
  prompt_key: string;
  schema_key: string;
  model_key: string;
  max_tokens?: number;
  timeout_seconds?: number;
  repair_retry_count?: number;
  temperature?: number;
  top_p?: number;
  top_k?: number;
}) {
  return requestJson<LabelingGenerateResponse>("/api/v2/label-lab/generations", {
    method: "POST",
    body: { scenario: "label", ...payload, model_key: payload.model_key.trim() },
  });
}

export function listLabelSchemas(includeArchived = false, options?: ApiRequestOptions) {
  const params = new URLSearchParams({ include_archived: includeArchived ? "true" : "false" });
  return requestJson<{ total: number; include_archived: boolean; items: LabelSchemaRecord[] }>(
    `/api/v2/schema-center/label-schemas?${params.toString()}`,
    options,
  );
}

export function createLabelSchema(payload: { key: string; label?: string; description?: string; schema: Record<string, unknown> }) {
  return requestJson<LabelSchemaRecord>("/api/v2/schema-center/label-schemas", { method: "POST", body: payload });
}

export function updateLabelSchema(
  key: string,
  payload: { label?: string; description?: string; schema?: Record<string, unknown> },
) {
  return requestJson<LabelSchemaRecord>(`/api/v2/schema-center/label-schemas/${key}`, { method: "PATCH", body: payload });
}

export function archiveLabelSchema(key: string) {
  return requestJson<LabelSchemaRecord>(`/api/v2/schema-center/label-schemas/${key}/archive`, { method: "POST" });
}

export function restoreLabelSchema(key: string) {
  return requestJson<LabelSchemaRecord>(`/api/v2/schema-center/label-schemas/${key}/restore`, { method: "POST" });
}

export function purgeLabelSchema(key: string) {
  return requestJson<{ ok: boolean; key: string; kind: string }>(`/api/v2/schema-center/label-schemas/${key}/purge`, { method: "DELETE" });
}
