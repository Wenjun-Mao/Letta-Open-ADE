import { describe, expect, it } from "vitest";

import { memoryActionOutcome, type PendingMemoryAction } from "./memory-action";
import type { Run, RunEvent, SubjectMemories } from "./types";

const action: PendingMemoryAction = { factId: "fact-1", version: 2, operation: "forget", runId: "run-1", outcome: "Waiting for review." };
const run = { id: "run-1", status: "succeeded" } as Run;
const event: RunEvent = {
  id: "event-1", schema_version: 1, run_id: "run-1", sequence: 1, attempt: 1,
  type: "memory.committed", occurred_at: "2026-09-22T00:00:00Z", correlation_id: "run-1",
  causation_id: null, visibility: "operator",
  payload: { fact_id: "fact-1", operation: "forget", fact_version: 3 },
};
const memories = { subject_id: "subject-1", facts: [{ id: "fact-1", revisions: [{ run_id: "run-1", operation: "forget", fact_version: 3 }] }] } as SubjectMemories;

describe("reviewed memory action status", () => {
  it("requires both a matching commit event and a persisted targeted revision", () => {
    expect(memoryActionOutcome(action, run, [event], memories)).toContain("Matching memory revision committed");
    expect(memoryActionOutcome(action, run, [event], null)).toContain("not confirmed changed");
    expect(memoryActionOutcome(action, run, [], memories)).toContain("not confirmed changed");
  });

  it("does not treat no-op, wrong version, cancellation, or another run as success", () => {
    expect(memoryActionOutcome(action, run, [{ ...event, payload: { ...event.payload, fact_version: 4 } }], memories)).toContain("not confirmed changed");
    expect(memoryActionOutcome(action, { ...run, status: "cancelled" }, [event], memories)).toContain("cancelled");
    expect(memoryActionOutcome(action, { ...run, id: "other" }, [event], memories)).toBe("Waiting for review.");
  });
});
