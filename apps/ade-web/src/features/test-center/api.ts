import { requestJson, type ApiRequestOptions } from "@/shared/api/client";

export type TestRunType = "ade_api_e2e_check" | "ade_mvp_smoke_e2e_check" | "chat_memory_eval";

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
