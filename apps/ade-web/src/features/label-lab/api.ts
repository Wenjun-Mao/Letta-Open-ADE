import { requestJson } from "@/shared/api/client";

import type { LabelingOutputMode, Scenario } from "@/features/model-catalog/api";

export type LabelExtractionResult = Record<string, string[]>;

export type LabelingGenerateResponse = {
  scenario: Scenario;
  model_key: string;
  source_id: string;
  source_label: string;
  provider_model_id: string;
  prompt_key: string;
  schema_key: string;
  output_mode: LabelingOutputMode;
  selected_attempt: "primary" | "repair";
  result: LabelExtractionResult;
  finish_reason?: string | null;
  usage: Record<string, unknown>;
  received_at?: string | null;
  raw_request: Record<string, unknown>;
  raw_reply: Record<string, unknown>;
  validation_errors: string[];
  temperature: number;
  top_p: number;
  top_k?: number | null;
};

export type LabelingGenerateRequest = {
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
};

export function generateLabels(payload: LabelingGenerateRequest) {
  return requestJson<LabelingGenerateResponse>("/api/v2/label-lab/generations", {
    method: "POST",
    body: { scenario: "label", ...payload, model_key: payload.model_key.trim() },
  });
}
