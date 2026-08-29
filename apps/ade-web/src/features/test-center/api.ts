import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

export type TestRunType =
  | "ade_api_e2e_check"
  | "ade_mvp_smoke_e2e_check"
  | "chat_memory_eval"
  | "agent_runtime_v3_acceptance";

export type TestArtifact = {
  artifact_id: string;
  type: string;
  path: string;
  exists: boolean;
  size_bytes: number;
};

export type TestRunRecord = {
  run_id: string;
  run_type: string;
  status: string;
  command: string[];
  created_at: string;
  started_at: string;
  finished_at: string;
  exit_code: number | null;
  log_file: string;
  cancel_requested: boolean;
  output_tail: string[];
  error: string;
  artifacts?: TestArtifact[];
};

export type ChatMemoryEvaluationConfig = {
  model: string;
  prompt_key: string;
  persona_key: string;
  embedding: string;
  fixture_key: string;
  rounds: number;
  timeout_seconds: number;
  retry_count: number;
  judge_enabled: boolean;
};

export type ChatMemoryEvaluationMetrics = {
  rounds_total: number;
  rounds_passed: number;
  rounds_failed: number;
  errors: number;
  pass_rate: number;
  average_elapsed_seconds: number;
  forbidden_hit_count: number;
  memory_changed_rounds: number;
  expected_facts_passed_rounds: number;
  memory_tool_call_count: number;
  total_tool_call_count: number;
  cleanup_passed_rounds: number;
};

export type EvaluationListItem = {
  run_id: string;
  run_status: string;
  created_at: string;
  finished_at: string;
  ready: boolean;
  config: ChatMemoryEvaluationConfig;
  metrics: ChatMemoryEvaluationMetrics | null;
};

export type EvaluationToolCall = Record<string, unknown>;

export type EvaluationMemoryBlock = {
  label: string;
  value: string;
  description?: string;
  limit?: number;
};

export type EvaluationTurn = {
  turn_index: number;
  user_input: string;
  assistant_replies: string[];
  elapsed_seconds: number;
  memory_changed_this_turn: boolean;
  human_memory_before_turn: string;
  human_memory_after_turn: string;
  tool_calls: EvaluationToolCall[];
  memory_tool_calls: EvaluationToolCall[];
};

export type EvaluationRound = {
  round: number;
  status: string;
  passed: boolean;
  elapsed_seconds: number;
  agent_id: string;
  archived: boolean;
  purged: boolean;
  error: string;
  initial_human_memory: string;
  final_human_memory: string;
  deterministic_score: Record<string, unknown>;
  judge: Record<string, unknown> | null;
  memory_blocks: EvaluationMemoryBlock[];
  turns: EvaluationTurn[];
};

export type EvaluationDetail = EvaluationListItem & {
  fixture: Record<string, unknown>;
  rounds: EvaluationRound[];
};

export type CreateTestRunPayload = {
  run_type: TestRunType;
  model?: string;
  prompt_key?: string;
  persona_key?: string;
  embedding?: string;
  rounds?: number;
  fixture_key?: string;
  timeout_seconds?: number;
  retry_count?: number;
  judge_enabled?: boolean;
  judge_model_key?: string;
  conversation_model_key?: string;
  reviewer_model_key?: string;
  embedding_model_key?: string;
  include_llama_compatibility?: boolean;
};

export function listTestRuns(options?: ApiRequestOptions) {
  return requestJson<{ items: TestRunRecord[] }>("/api/v2/test-center/runs", options);
}

export function createTestRun(payload: CreateTestRunPayload) {
  return requestJson<TestRunRecord>("/api/v2/test-center/runs", { method: "POST", body: payload });
}

export function getTestRun(runId: string, options?: ApiRequestOptions) {
  return requestJson<TestRunRecord>(`/api/v2/test-center/runs/${runId}`, options);
}

export function cancelTestRun(runId: string) {
  return requestJson<TestRunRecord>(`/api/v2/test-center/runs/${runId}/cancel`, { method: "POST" });
}

export function listRunArtifacts(runId: string, options?: ApiRequestOptions) {
  return requestJson<{ run_id: string; items: TestArtifact[] }>(`/api/v2/test-center/runs/${runId}/artifacts`, options);
}

export function readRunArtifact(runId: string, artifactId: string, maxLines = 400, options?: ApiRequestOptions) {
  return requestJson<{
    run_id: string;
    artifact: TestArtifact;
    content: string;
    truncated: boolean;
    line_count: number;
  }>(`/api/v2/test-center/runs/${runId}/artifacts/${artifactId}?max_lines=${maxLines}`, options);
}

export function listChatMemoryEvaluations(options?: ApiRequestOptions) {
  return requestJson<{ items: EvaluationListItem[] }>("/api/v2/test-center/chat-memory-evaluations", options);
}

export function getChatMemoryEvaluation(runId: string, options?: ApiRequestOptions) {
  return requestJson<EvaluationDetail>(`/api/v2/test-center/chat-memory-evaluations/${runId}`, options);
}
