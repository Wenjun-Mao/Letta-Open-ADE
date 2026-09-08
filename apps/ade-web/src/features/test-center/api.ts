import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

export type TestRunType =
  | "ade_api_e2e_check"
  | "chat_memory_eval"
  | "agent_runtime_acceptance";

export type TestArtifact = {
  artifact_id: string;
  type: string;
  path: string;
  exists: boolean;
  size_bytes: number;
};

export type TestRunRecord = {
  run_id: string;
  run_type: TestRunType | string;
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

export type TestCenterOption = {
  key: string;
  label: string;
  available: boolean;
};

export type TestCenterCatalogOptions = {
  models: TestCenterOption[];
  embeddings: TestCenterOption[];
  prompts: TestCenterOption[];
  personas: TestCenterOption[];
};

export type ChatMemoryEvaluationDefaults = {
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

export type AgentRuntimeAcceptanceDefaults = {
  conversation_model_key: string;
  reviewer_model_key: string;
  embedding_model_key: string;
  prompt_key: string;
  persona_key: string;
  rounds: number;
  timeout_seconds: number;
  retry_count: number;
  include_llama_compatibility: boolean;
};

export type TestCenterOptions = {
  run_types: TestCenterOption[];
  catalog: TestCenterCatalogOptions;
  chat_memory_eval: {
    defaults: ChatMemoryEvaluationDefaults;
    fixtures: TestCenterOption[];
  };
  agent_runtime_acceptance: {
    defaults: AgentRuntimeAcceptanceDefaults;
    cases: TestCenterOption[];
  };
  current_stack_smoke: {
    run_type: "ade_api_e2e_check";
  };
};

export type CreateTestRunPayload =
  | {
      run_type: "ade_api_e2e_check";
    }
  | {
      run_type: "chat_memory_eval";
      model: string;
      prompt_key: string;
      persona_key: string;
      embedding: string;
      fixture_key: string;
      rounds: number;
      timeout_seconds: number;
      retry_count: number;
      judge_enabled: boolean;
    }
  | {
      run_type: "agent_runtime_acceptance";
      conversation_model_key: string;
      reviewer_model_key: string;
      embedding_model_key: string;
      prompt_key: string;
      persona_key: string;
      rounds: number;
      timeout_seconds: number;
      retry_count: number;
      include_llama_compatibility: boolean;
      case_keys?: string[];
    };

export function getTestCenterOptions(options?: ApiRequestOptions) {
  return requestJson<TestCenterOptions>("/api/v2/test-center/options", options);
}

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
  return requestJson<{ run_id: string; items: TestArtifact[] }>(
    `/api/v2/test-center/runs/${runId}/artifacts`,
    options,
  );
}

export function readRunArtifact(
  runId: string,
  artifactId: string,
  maxLines = 400,
  options?: ApiRequestOptions,
) {
  return requestJson<{ content: string }>(
    `/api/v2/test-center/runs/${runId}/artifacts/${artifactId}?max_lines=${maxLines}`,
    options,
  );
}
