import type { MemoryFact, Run, RunEvent, SubjectMemories } from "./types";

export type PendingMemoryAction = {
  conversationId: string;
  factId: string;
  version: number;
  operation: "correct" | "forget";
  runId: string | null;
  outcome: string;
};

export function memoryActionDraft(fact: MemoryFact, operation: "correct" | "forget"): string {
  const description = `${fact.fact_type} about ${fact.entity_label || fact.entity_kind}: ${fact.value}`;
  return operation === "forget"
    ? `Please remove this saved information from active memory: ${description}. Do not treat this as a request to erase past conversations or revision history.`
    : `Please correct this saved fact: ${description}. The correct information is: `;
}

export function memoryActionOutcome(action: PendingMemoryAction, run: Run, events: RunEvent[], memories: SubjectMemories | null): string {
  if (action.runId !== run.id) return action.outcome;
  if (run.status !== "succeeded") return `Run ${run.status}; saved information was not confirmed changed.`;
  const committed = events.some((event) => event.type === "memory.committed"
    && event.payload.fact_id === action.factId
    && event.payload.operation === action.operation
    && event.payload.fact_version === action.version + 1);
  const revision = memories?.facts.find((fact) => fact.id === action.factId)?.revisions
    .find((item) => item.run_id === run.id && item.operation === action.operation && item.fact_version === action.version + 1);
  return committed && revision
    ? "Matching memory revision committed. Check the refreshed fact history below."
    : "No matching committed revision was verified. Saved information was not confirmed changed.";
}
