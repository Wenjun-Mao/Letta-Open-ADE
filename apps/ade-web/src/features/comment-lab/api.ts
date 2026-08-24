import { requestJson } from "@/shared/api/client";

import type { Scenario } from "@/features/model-catalog/api";

export type CommentingTaskShape = "classic" | "all_in_system" | "structured_output";

export type CommentingGenerateResponse = {
  scenario: Scenario;
  model_key: string;
  source_id: string;
  source_label: string;
  provider_model_id: string;
  prompt_key: string;
  persona_key: string;
  model: string;
  content: string;
  provider: string;
  max_tokens: number;
  timeout_seconds: number;
  task_shape: CommentingTaskShape;
  cache_prompt: boolean;
  enable_thinking: boolean;
  temperature: number;
  top_p: number;
  top_k?: number | null;
  content_source?: string | null;
  selected_attempt: string;
  finish_reason?: string | null;
  usage: Record<string, unknown>;
  received_at?: string | null;
  raw_request: Record<string, unknown>;
  raw_reply: Record<string, unknown>;
};

export type CommentingGenerateRequest = {
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
};

export function generateComment(payload: CommentingGenerateRequest) {
  return requestJson<CommentingGenerateResponse>("/api/v2/comment-lab/generations", {
    method: "POST",
    body: { scenario: "comment", ...payload, model_key: payload.model_key?.trim() || undefined, model: payload.model?.trim() || undefined },
  });
}
