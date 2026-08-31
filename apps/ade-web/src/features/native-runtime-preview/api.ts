import { requestJson } from "@/shared/api/client";

export const NATIVE_PREVIEW_ENABLED = process.env.NEXT_PUBLIC_ADE_NATIVE_PREVIEW_ENABLED === "true";
export const DEFAULT_CONVERSATION_MODEL = "dgx_vllm::qwen3.6-35b-a3b-fp8";
export const DEFAULT_EMBEDDING_MODEL = "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B";

export type QualificationState = "qualified" | "unqualified";
export type RunStatus = "pending" | "running" | "succeeded" | "failed" | "cancelled";

export type NativeWorkerHealth = {
  status: "ready" | "not_ready";
  database_ready: boolean;
  worker_ready: boolean;
  checked_at: string;
  freshness_seconds: number;
  compatible_worker_count: number;
  matching_build_worker_count: number;
  compatibility_fingerprint: string;
  source_revision: string;
  source_dirty: boolean;
  source_fingerprint: string;
  latest_heartbeat_at: string | null;
  failure_code: string | null;
};

export type NativeDeployment = {
  deployment_id: string;
  route_alias: string;
  fingerprint: string;
  role: "conversation" | "reviewer" | "retriever";
  lifecycle: string;
  qualification_state: QualificationState;
  fingerprint_payload: Record<string, unknown>;
};

export type NativePreviewSession = {
  session_id: string;
  idempotent_replay: boolean;
  agent_definition: {
    id: string;
    definition_key: string;
    version: number;
    name: string;
    prompt_key: string;
    prompt_sha256: string;
    persona_key: string;
    persona_sha256: string;
    tool_names: string[];
    memory_policy_version: string;
    qualification_state: QualificationState;
    deployments: NativeDeployment[];
    created_at: string;
  };
  memory_subject: {
    id: string;
    external_key: string;
    display_name: string;
    created_at: string;
  };
  conversation: {
    id: string;
    agent_definition_id: string;
    memory_subject_id: string;
    version: number;
    created_at: string;
  };
};

export type NativeRun = {
  id: string;
  conversation_id: string;
  status: RunStatus;
  qualification_state: QualificationState;
  attempt_count: number;
  timeout_seconds: number;
  retry_count: number;
  cancellation_requested_at: string | null;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type NativeRunEvent = {
  id: string;
  schema_version: number;
  run_id: string;
  sequence: number;
  attempt: number | null;
  type: string;
  occurred_at: string;
  correlation_id: string;
  causation_id: string | null;
  visibility: "operator";
  payload: Record<string, unknown>;
};

export type NativeConversationState = NativePreviewSession["conversation"] & {
  messages: Array<{
    id: string;
    sequence: number;
    role: "user" | "assistant";
    content: string;
    run_id: string | null;
    created_at: string;
  }>;
  summary: null | {
    id: string;
    version: number;
    previous_summary_id: string | null;
    content: string;
    source_boundary: { through_sequence: number; message_ids: string[] };
    provenance: {
      run_id: string;
      model_key: string;
      model_fingerprint: string;
      provider_request_id: string | null;
      content_sha256: string;
      prompt_sha256: string;
      input_sha256: string;
      policy_sha256: string;
    };
    created_at: string;
  };
};

export type NativeSubjectMemories = {
  subject_id: string;
  facts: Array<{
    id: string;
    key: string;
    fact_type: string;
    entity_id: string;
    entity_kind: string;
    entity_label: string;
    qualifier: string | null;
    value: string | null;
    status: "active" | "superseded" | "forgotten";
    version: number;
    updated_at: string;
    revisions: Array<{
      id: string;
      operation: "add" | "correct" | "forget";
      fact_version: number;
      value: string | null;
      run_id: string;
      predecessor_revision_ids: string[];
      evidence: Array<{
        message_id: string;
        start_char: number;
        end_char: number;
        quote: string;
        message_sha256: string;
      }>;
      created_at: string;
    }>;
  }>;
};

export type CreateNativePreviewSession = {
  idempotency_key: string;
  name: string;
  subject_display_name: string;
  model_key: string;
  reviewer_model_key: string;
  embedding_model_key: string;
  prompt_key: string;
  persona_key: string;
};

export function parseNativeWorkerHealth(payload: unknown): NativeWorkerHealth {
  if (!payload || typeof payload !== "object") {
    throw new Error("Native runtime health response is invalid.");
  }
  const value = payload as Record<string, unknown>;
  const nullableString = (item: unknown) => item === null || typeof item === "string";
  const finiteNumber = (item: unknown) => typeof item === "number" && Number.isFinite(item);
  if (
    !["ready", "not_ready"].includes(String(value.status))
    || typeof value.database_ready !== "boolean"
    || typeof value.worker_ready !== "boolean"
    || typeof value.checked_at !== "string"
    || !finiteNumber(value.freshness_seconds)
    || !finiteNumber(value.compatible_worker_count)
    || !finiteNumber(value.matching_build_worker_count)
    || typeof value.compatibility_fingerprint !== "string"
    || typeof value.source_revision !== "string"
    || typeof value.source_dirty !== "boolean"
    || typeof value.source_fingerprint !== "string"
    || !nullableString(value.latest_heartbeat_at)
    || !nullableString(value.failure_code)
  ) {
    throw new Error("Native runtime health response is invalid.");
  }
  return value as NativeWorkerHealth;
}

export async function getNativeWorkerHealth(): Promise<NativeWorkerHealth> {
  const response = await fetch("/api/v3/worker-health", { cache: "no-store" });
  const payload: unknown = await response.json();
  if (response.ok || response.status === 503) {
    return parseNativeWorkerHealth(payload);
  }
  throw new Error(`Native runtime health failed (${response.status}): ${JSON.stringify(payload)}`);
}

export function createNativePreviewSession(
  payload: CreateNativePreviewSession,
): Promise<NativePreviewSession> {
  return requestJson<NativePreviewSession>("/api/v3/preview-sessions", {
    method: "POST",
    body: payload,
  });
}

export function acceptNativeTurn(
  conversationId: string,
  payload: { content: string; idempotency_key: string; timeout_seconds: number; retry_count: number },
): Promise<{ run_id: string; status: RunStatus; events_url: string; idempotent_replay: boolean }> {
  return requestJson(`/api/v3/conversations/${conversationId}/turns`, {
    method: "POST",
    body: payload,
  });
}

export function getNativeRun(runId: string): Promise<NativeRun> {
  return requestJson(`/api/v3/runs/${runId}`);
}

export function cancelNativeRun(runId: string): Promise<NativeRun> {
  return requestJson(`/api/v3/runs/${runId}/cancel`, { method: "POST" });
}

export function getNativeConversationState(
  conversationId: string,
): Promise<NativeConversationState> {
  return requestJson(`/api/v3/conversations/${conversationId}/state`);
}

export function getNativeSubjectMemories(subjectId: string): Promise<NativeSubjectMemories> {
  return requestJson(`/api/v3/memory-subjects/${subjectId}/memories`);
}

export function nativeRunEventsUrl(runId: string): string {
  return `/api/v3/runs/${encodeURIComponent(runId)}/events`;
}
