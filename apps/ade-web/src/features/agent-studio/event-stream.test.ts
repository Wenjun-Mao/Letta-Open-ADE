import { describe, expect, it } from "vitest";

import { parseRunEvent, TERMINAL_RUN_EVENT_TYPES } from "./event-stream";

describe("Agent Studio run event stream", () => {
  it("parses the normalized v3 event envelope", () => {
    const event = parseRunEvent(JSON.stringify({
      id: "event-1", schema_version: 1, run_id: "run-1", sequence: 7, attempt: 1,
      type: "memory.committed", occurred_at: "2026-09-02T00:00:00Z", correlation_id: "run-1",
      causation_id: null, visibility: "operator", payload: { operation: "add" },
    }));

    expect(event.sequence).toBe(7);
    expect(event.type).toBe("memory.committed");
  });

  it("rejects malformed event payloads and recognizes every terminal event", () => {
    expect(() => parseRunEvent(JSON.stringify({ type: "run.started" }))).toThrow("invalid");
    expect([...TERMINAL_RUN_EVENT_TYPES].sort()).toEqual(["run.cancelled", "run.completed", "run.failed"]);
  });
});
