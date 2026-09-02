import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

export type TestRunType =
  | "ade_api_e2e_check"
  | "ade_mvp_smoke_e2e_check"
  | "chat_memory_eval"
  | "agent_runtime_v3_acceptance"
  | "agent_runtime_parity_eval";

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

export type EvaluationProvenanceSummary = {
  run_id: string;
  captured_at: string;
  configuration_sha256: string;
  provenance_sha256: string;
  fixture_sha256: string;
  prompt_content_sha256: string;
  persona_content_sha256: string;
  model_identity_sha256: string;
  embedding_identity_sha256: string | null;
};

export type EvaluationTemplateSnapshot = {
  kind: "prompt" | "persona";
  scenario: "chat";
  key: string;
  label: string;
  description: string;
  content: string;
  content_sha256: string;
  updated_at: string;
};

export type EvaluationOptionSnapshot = {
  key: string;
  label: string;
  source_id: string;
  source_label: string;
  provider_model_id: string;
  upstream_provider_model_id: string | null;
  sampling_defaults: Record<string, unknown>;
  scenario_sampling_defaults: Record<string, unknown>;
  supports_top_k: boolean | null;
  supports_thinking: boolean | null;
  thinking_default_enabled: boolean | null;
  tool_call_thinking_default_enabled: boolean | null;
  profile_applied: boolean | null;
  profile_source: string;
  agent_studio_candidate: boolean | null;
  agent_studio_compatible: boolean | null;
  deployment: Record<string, unknown> | null;
  identity_sha256: string;
};

export type EvaluationProvenance = {
  schema_version: 1 | 2 | 3;
  run_id: string | null;
  captured_at: string;
  configuration_sha256: string;
  provenance_sha256: string;
  fixture_sha256: string;
  controls: Record<string, unknown>;
  prompt: EvaluationTemplateSnapshot;
  persona: EvaluationTemplateSnapshot;
  model: EvaluationOptionSnapshot;
  embedding: EvaluationOptionSnapshot | null;
};

export type EvaluationDecisionOutcome = "keep" | "promote" | "reject";

export type EvaluationDecision = {
  decision_id: string;
  outcome: EvaluationDecisionOutcome;
  candidate_run_id: string;
  baseline_run_id: string | null;
  baseline_provenance_sha256: string | null;
  baseline_evidence_sha256: string | null;
  candidate_provenance_sha256: string;
  candidate_evidence_sha256: string;
  candidate_configuration_sha256: string;
  note: string;
  recorded_at: string;
};

export type EvaluationListItem = {
  run_id: string;
  run_status: string;
  created_at: string;
  finished_at: string;
  ready: boolean;
  evidence_sha256: string | null;
  config: ChatMemoryEvaluationConfig;
  metrics: ChatMemoryEvaluationMetrics | null;
  provenance: EvaluationProvenanceSummary | null;
  decision: EvaluationDecision | null;
  preferred_baseline: boolean;
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
  provenance_detail: EvaluationProvenance | null;
};

export type EvaluationComparisonValue = {
  baseline: unknown;
  candidate: unknown;
  changed: boolean;
};

export type EvaluationComparison = {
  baseline: EvaluationListItem;
  candidate: EvaluationListItem;
  same_configuration: boolean;
  configuration_changes: Record<string, EvaluationComparisonValue>;
  metric_deltas: Record<string, number>;
};

export type AgentRuntimeParityConfig = {
  prompt_key: string;
  persona_key: string;
  legacy_model: string;
  legacy_embedding: string;
  native_conversation_model: string;
  native_reviewer_model: string;
  native_embedding_model: string;
  rounds: number;
  timeout_seconds: number;
  retry_count: 0;
};

export type AgentRuntimeParityArtifactDigests = {
  parity_spec_sha256: string;
  provenance_sha256: string;
  normalized_turns_sha256: string;
  comparison_sha256: string;
  summary_sha256: string;
  evidence_sha256: string;
};

export type AgentRuntimeParityListItem = {
  run_id: string;
  run_status: string;
  created_at: string;
  finished_at: string;
  ready: boolean;
  config: AgentRuntimeParityConfig;
  passed: boolean | null;
  inputs_comparable: boolean | null;
  cleanup_complete: boolean | null;
  rounds_requested: number | null;
  rounds_completed: number | null;
  rounds_passed: number | null;
  artifact_digests: AgentRuntimeParityArtifactDigests | null;
};

export type AgentRuntimeParityRound = {
  round: number;
  passed: boolean;
  legacy_passed: boolean;
  native_passed: boolean;
  legacy_checks: Record<string, boolean>;
  native_checks: Record<string, boolean>;
};

export type AgentRuntimeParityTurn = {
  engine: "letta-v2" | "ade-native-v3";
  round: number;
  turn_index: number;
  terminal_status: string;
  user_content: string;
  assistant_replies: string[];
  attempt_count: number | null;
  elapsed_seconds: number;
  tool_names: string[];
  event_types: string[];
  memory_changed: boolean | null;
};

export type AgentRuntimeParityDetail = AgentRuntimeParityListItem & {
  checks: Record<string, boolean>;
  comparability_checks: Record<string, boolean>;
  cleanup: {
    completed: boolean;
    legacy_completed: boolean;
    native_completed: boolean;
    legacy_creation_indeterminate: boolean;
  };
  provenance: {
    source_revision: string;
    source_dirty: boolean;
    source_fingerprint: string;
    native_worker_ready?: boolean | null;
    native_worker_build_matches?: boolean | null;
    prompt_content_sha256?: string | null;
    persona_content_sha256?: string | null;
    fixture_sha256?: string | null;
  };
  rounds: AgentRuntimeParityRound[];
  turns: AgentRuntimeParityTurn[];
  preflight_error?: Record<string, string> | null;
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
  case_keys?: string[];
  legacy_model?: string;
  legacy_embedding?: string;
  native_conversation_model?: string;
  native_reviewer_model?: string;
  native_embedding_model?: string;
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

export function listAgentRuntimeParityEvaluations(options?: ApiRequestOptions) {
  return requestJson<{ items: AgentRuntimeParityListItem[] }>(
    "/api/v2/test-center/agent-runtime-parity-evaluations",
    options,
  );
}

export function getAgentRuntimeParityEvaluation(runId: string, options?: ApiRequestOptions) {
  return requestJson<AgentRuntimeParityDetail>(
    `/api/v2/test-center/agent-runtime-parity-evaluations/${runId}`,
    options,
  );
}

export function listChatMemoryEvaluations(options?: ApiRequestOptions) {
  return requestJson<{ items: EvaluationListItem[] }>("/api/v2/test-center/chat-memory-evaluations", options);
}

export function getChatMemoryEvaluation(runId: string, options?: ApiRequestOptions) {
  return requestJson<EvaluationDetail>(`/api/v2/test-center/chat-memory-evaluations/${runId}`, options);
}

export function compareChatMemoryEvaluations(
  baselineRunId: string,
  candidateRunId: string,
  options?: ApiRequestOptions,
) {
  const query = new URLSearchParams({
    baseline_run_id: baselineRunId,
    candidate_run_id: candidateRunId,
  });
  return requestJson<EvaluationComparison>(
    `/api/v2/test-center/chat-memory-evaluations/comparison?${query.toString()}`,
    options,
  );
}

export function recordChatMemoryEvaluationDecision(
  runId: string,
  payload: {
    outcome: EvaluationDecisionOutcome;
    expected_provenance_sha256: string;
    expected_evidence_sha256: string;
    baseline_run_id?: string;
    expected_baseline_provenance_sha256?: string;
    expected_baseline_evidence_sha256?: string;
    note: string;
  },
) {
  return requestJson<EvaluationDecision>(
    `/api/v2/test-center/chat-memory-evaluations/${runId}/decisions`,
    { method: "POST", body: payload },
  );
}
