"use client";

import { type Dispatch, type RefObject, type SetStateAction } from "react";

import { getSubjectMemories, removeSavedMemory } from "./api";
import { identityKey, isArchived } from "./selection";
import type { AgentStudioSession, MemoryRemovalReceipt, MemorySubject, SubjectMemories } from "./types";

export type PendingRemoval = {
  subjectId: string;
  factId: string;
  version: number;
  generation: number;
  idempotencyKey: string;
  receipt: MemoryRemovalReceipt | null;
  outcome: string;
  unconfirmed: boolean;
};

type RemovalDependencies = {
  session: AgentStudioSession | null;
  inspectedSubject: MemorySubject | null;
  memories: SubjectMemories | null;
  inspectedMemories: SubjectMemories | null;
  removal: PendingRemoval | null;
  setRemoval: Dispatch<SetStateAction<PendingRemoval | null>>;
  selectedIdRef: RefObject<string | null>;
  selectionEpochRef: RefObject<number>;
  subjectInspectEpochRef: RefObject<number>;
  refreshSelected: (conversationId: string) => Promise<SubjectMemories | null>;
  setInspectedMemories: Dispatch<SetStateAction<SubjectMemories | null>>;
  setBusy: Dispatch<SetStateAction<boolean>>;
  setError: Dispatch<SetStateAction<string>>;
};

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unexpected Agent Studio error.");
}

export function useMemoryRemoval({
  session, inspectedSubject, memories, inspectedMemories, removal, setRemoval,
  selectedIdRef, selectionEpochRef, subjectInspectEpochRef,
  refreshSelected, setInspectedMemories, setBusy, setError,
}: RemovalDependencies) {
  async function performRemoval(request: PendingRemoval) {
    const selectedId = session?.conversation.id;
    const epoch = selectionEpochRef.current;
    const inspectEpoch = subjectInspectEpochRef.current;
    const isCurrent = () => selectedId
      ? selectedIdRef.current === selectedId && epoch === selectionEpochRef.current
      : selectedIdRef.current === null && inspectedSubject?.id === request.subjectId
        && inspectEpoch === subjectInspectEpochRef.current;
    setBusy(true);
    setError("");
    try {
      const receipt = await removeSavedMemory(request.subjectId, {
        idempotency_key: request.idempotencyKey,
        expected_memory_generation: request.generation,
        targets: [{ fact_id: request.factId, expected_version: request.version }],
      });
      if (!isCurrent()) return;
      const refreshed = selectedId
        ? await refreshSelected(selectedId)
        : await getSubjectMemories(request.subjectId);
      if (!isCurrent()) return;
      if (!selectedId) setInspectedMemories(refreshed);
      const revision = refreshed?.facts.find((fact) => fact.id === request.factId)?.revisions
        .find((item) => item.action_id === receipt.action_id && receipt.revision_ids.includes(item.id));
      setRemoval({ ...request, receipt, unconfirmed: !revision,
        outcome: revision
          ? `Operator action ${receipt.action_id} committed${receipt.idempotent_replay ? " (historical replay)" : ""}. Current memory was refreshed separately; check its status below.`
          : `Operator action ${receipt.action_id} committed${receipt.idempotent_replay ? " (historical replay)" : ""}, but current readback was not verified. Do not infer current absence.` });
    } catch (exc) {
      if (isCurrent()) {
        setRemoval({ ...request, receipt: null, unconfirmed: true,
          outcome: `Removal outcome unconfirmed: ${errorMessage(exc)}. Retry with the same key to recover the historical receipt, or refresh before a deliberate new action.` });
        if (selectedId) await refreshSelected(selectedId);
        else {
          try {
            const refreshed = await getSubjectMemories(request.subjectId);
            if (isCurrent()) setInspectedMemories(refreshed);
          } catch { /* Keep the action unconfirmed; do not overwrite its recovery key. */ }
        }
      }
    } finally {
      setBusy(false);
    }
  }

  async function removeSavedFact(factId: string, version: number) {
    const subject = inspectedSubject || session?.memory_subject;
    const selectedMemories = inspectedSubject ? inspectedMemories : memories;
    const generation = selectedMemories?.memory_generation;
    const fact = selectedMemories?.facts.find((item) => item.id === factId && item.version === version);
    if (!subject || !fact || fact.status === "forgotten" || isArchived(subject)
      || !Number.isInteger(generation) || !generation || removal?.unconfirmed) return;
    const request: PendingRemoval = {
      subjectId: subject.id, factId, version, generation,
      idempotencyKey: identityKey("memory-removal"), receipt: null,
      outcome: "Removal submitted; awaiting an authoritative action receipt.", unconfirmed: true,
    };
    setRemoval(request);
    await performRemoval(request);
  }

  async function retryRemoval() {
    if (!removal || !removal.unconfirmed || removal.receipt) return;
    await performRemoval(removal);
  }

  return { removeSavedFact, retryRemoval };
}
