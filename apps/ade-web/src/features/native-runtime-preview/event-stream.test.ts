import { describe, expect, it } from "vitest";

import { parseNativeRunEvent, TERMINAL_NATIVE_EVENT_TYPES } from "./event-stream";

describe("native runtime event stream", () => {
  it("parses the normalized event envelope", () => {
    const event = parseNativeRunEvent(JSON.stringify({
      id: "event-1",
      schema_version: 1,
      run_id: "run-1",
      sequence: 7,
      attempt: 1,
      type: "memory.committed",
      occurred_at: "2026-08-30T00:00:00Z",
      correlation_id: "run-1",
      causation_id: null,
      visibility: "operator",
      payload: { operation: "add" },
    }));

    expect(event.sequence).toBe(7);
    expect(event.type).toBe("memory.committed");
  });

  it("identifies every terminal run event", () => {
    expect([...TERMINAL_NATIVE_EVENT_TYPES].sort()).toEqual([
      "run.cancelled",
      "run.completed",
      "run.failed",
    ]);
  });
});
