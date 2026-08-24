import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

export type LabelSchemaRecord = {
  key: string;
  label: string;
  description: string;
  schema: Record<string, unknown>;
  preview: string;
  archived: boolean;
  source_path: string;
  updated_at: string;
};

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

export function updateLabelSchema(key: string, payload: { label?: string; description?: string; schema?: Record<string, unknown> }) {
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
