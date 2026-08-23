import { requestJson } from "./client";
import type { CreateTestRunPayload, PlatformArtifact, PlatformRunRecord } from "./types";
import type { ApiRequestOptions } from "./platform";

export function listTestRuns(options?: ApiRequestOptions) {
  return requestJson<{ items: PlatformRunRecord[] }>("/api/v1/platform/test-runs", options);
}

export function createTestRun(payload: CreateTestRunPayload) {
  return requestJson<PlatformRunRecord>("/api/v1/platform/test-runs", { method: "POST", body: payload });
}

export function getTestRun(runId: string, options?: ApiRequestOptions) {
  return requestJson<PlatformRunRecord>(`/api/v1/platform/test-runs/${runId}`, options);
}

export function cancelTestRun(runId: string) {
  return requestJson<PlatformRunRecord>(`/api/v1/platform/test-runs/${runId}/cancel`, { method: "POST" });
}

export function listRunArtifacts(runId: string, options?: ApiRequestOptions) {
  return requestJson<{ run_id: string; items: PlatformArtifact[] }>(`/api/v1/platform/test-runs/${runId}/artifacts`, options);
}

export function readRunArtifact(runId: string, artifactId: string, maxLines = 400, options?: ApiRequestOptions) {
  return requestJson<{
    run_id: string;
    artifact: PlatformArtifact;
    content: string;
    truncated: boolean;
    line_count: number;
  }>(`/api/v1/platform/test-runs/${runId}/artifacts/${artifactId}?max_lines=${maxLines}`, options);
}
