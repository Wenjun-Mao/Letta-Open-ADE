import { describe, expect, it } from "vitest";

import { parseNativeWorkerHealth } from "./api";

const HEALTH = {
  status: "ready",
  database_ready: true,
  worker_ready: true,
  checked_at: "2026-08-30T00:00:00Z",
  freshness_seconds: 1,
  compatible_worker_count: 1,
  matching_build_worker_count: 1,
  compatibility_fingerprint: "compatibility",
  source_revision: "revision",
  source_dirty: false,
  source_fingerprint: "source",
  latest_heartbeat_at: "2026-08-30T00:00:00Z",
  failure_code: null,
};

describe("native worker health parsing", () => {
  it("accepts the complete readiness contract", () => {
    expect(parseNativeWorkerHealth(HEALTH)).toEqual(HEALTH);
  });

  it("rejects a generic proxy error even when it arrived with status 503", () => {
    expect(() => parseNativeWorkerHealth({ detail: "service unavailable" })).toThrow(
      "health response is invalid",
    );
  });

  it("rejects non-finite readiness counters", () => {
    expect(() => parseNativeWorkerHealth({ ...HEALTH, freshness_seconds: Number.NaN })).toThrow(
      "health response is invalid",
    );
  });
});
