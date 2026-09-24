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
  if (run.status !== "succeeded") return `Run ${run.status}${run.error_code ? ` (${run.error_code})` : ""}; saved information was not confirmed changed. A fresh submission must be deliberate.`;
  const matchingOperation = (operation: string) => operation === action.operation || (action.operation === "correct" && operation === "revise");
  const committed = events.some((event) => event.type === "memory.committed"
    && event.payload.fact_id === action.factId
    && typeof event.payload.operation === "string" && matchingOperation(event.payload.operation)
    && event.payload.fact_version === action.version + 1);
  const revision = memories?.facts.find((fact) => fact.id === action.factId)?.revisions
    .find((item) => item.run_id === run.id && matchingOperation(item.operation) && item.fact_version === action.version + 1);
  const deferred = events.find((event) => event.type === "memory.deferred");
  if (deferred && !committed && !revision) return `Reviewer deferred a claim (${String(deferred.payload.reason || "unresolved")}); no matching write was confirmed.`;
  return committed && revision
    ? "Matching memory revision committed. Check the refreshed fact history below."
    : "No matching committed revision was verified. Saved information was not confirmed changed.";
}
