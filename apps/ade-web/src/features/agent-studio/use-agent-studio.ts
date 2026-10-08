"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  HISTORY_TRIAL,
  acceptTurn,
  cancelRun,
  createAgentStudioSession,
  getAgentStudioOptions,
  getAgentStudioSession,
  getConversationState,
  getRun,
  getRunEventLog,
  getSubjectMemories,
  listAgentStudioDefinitions,
  listAgentStudioSessions,
  listAgentStudioSubjects,
  listConversationRuns,
  listConversationActivity,
} from "./api";
import { memoryActionDraft, memoryActionOutcome, type PendingMemoryAction } from "./memory-action";
import { sessionDraftPayload } from "./session-draft";
import { useResourceActions } from "./resource-actions";
import { useDefinitionVersion } from "./use-definition-version";
import { useMemoryRemoval, type PendingRemoval } from "./use-memory-removal";
import { useRunMonitor, TERMINAL_RUN_STATUSES } from "./use-run-monitor";
import {
  identityKey,
  isArchived,
  NEW_RESOURCE_VALUE,
  selectedConversationFromQuery,
} from "./selection";
import type {
  AgentDefinition,
  AgentStudioOptions,
  AgentStudioSession,
  ConversationState,
  MemorySubject,
  Run,
  RunEvent,
  SubjectMemories,
  MemoryEvidence,
  TurnActivity,
} from "./types";

function messageFrom(error: unknown): string {
  return error instanceof Error ? error.message : String(error || "Unexpected Agent Studio error.");
}

function clampNumber(value: number, minimum: number, maximum: number): number {
  if (!Number.isFinite(value)) return minimum;
  return Math.max(minimum, Math.min(maximum, value));
}

export function useAgentStudio() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const conversationId = selectedConversationFromQuery(searchParams.get("conversation"));
  const selectedIdRef = useRef(conversationId);
  const selectionEpochRef = useRef(0);
  const subjectInspectEpochRef = useRef(0);
  const readEpochRef = useRef(0);
  const bindingSelectionRef = useRef<string | null>(null);
  const olderPageRef = useRef<{ conversationId: string; cursor: number } | null>(null);
  const evidenceTargetRef = useRef<MemoryEvidence | null>(null);
  const createAttemptRef = useRef<{ signature: string; idempotencyKey: string } | null>(null);
  const subjectBindingsRef = useRef<AgentStudioSession[]>([]);

  const [options, setOptions] = useState<AgentStudioOptions | null>(null);
  const [sessions, setSessions] = useState<AgentStudioSession[]>([]);
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [subjects, setSubjects] = useState<MemorySubject[]>([]);
  const [session, setSession] = useState<AgentStudioSession | null>(null);
  const [inspectedSubject, setInspectedSubject] = useState<MemorySubject | null>(null);
  const [inspectedMemories, setInspectedMemories] = useState<SubjectMemories | null>(null);
  const [conversation, setConversation] = useState<ConversationState | null>(null);
  const [memories, setMemories] = useState<SubjectMemories | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [activity, setActivity] = useState<TurnActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streamWarning, setStreamWarning] = useState("");
  const [includeArchived, setIncludeArchived] = useState(false);
  const [message, setMessage] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(180);
  const [retryCount, setRetryCount] = useState(0);
  const [title, setTitle] = useState("New conversation");
  const [definitionChoice, setDefinitionChoice] = useState(NEW_RESOURCE_VALUE);
  const [definitionName, setDefinitionName] = useState(HISTORY_TRIAL ? "Lin Xiaotang · historical recall trial" : "ADE Native Companion");
  const [definitionKey, setDefinitionKey] = useState(() => identityKey("studio-character"));
  const [subjectChoice, setSubjectChoice] = useState(NEW_RESOURCE_VALUE);
  const [subjectName, setSubjectName] = useState(HISTORY_TRIAL ? "" : "New memory subject");
  const [subjectKey, setSubjectKey] = useState(() => identityKey("studio-person"));
  const [subjectRename, setSubjectRename] = useState("");
  const [evidenceMessageId, setEvidenceMessageId] = useState("");
  const [evidenceError, setEvidenceError] = useState("");
  const [memoryAction, setMemoryAction] = useState<PendingMemoryAction | null>(null);
  const [removal, setRemoval] = useState<PendingRemoval | null>(null);

  const refreshWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const [nextOptions, nextSessions, nextDefinitions, nextSubjects, allTrialSessions] = await Promise.all([
        getAgentStudioOptions(),
        listAgentStudioSessions(includeArchived),
        listAgentStudioDefinitions(includeArchived),
        listAgentStudioSubjects(includeArchived),
        HISTORY_TRIAL && !includeArchived ? listAgentStudioSessions(true) : Promise.resolve(null),
      ]);
      subjectBindingsRef.current = allTrialSessions?.items || nextSessions.items;
      setOptions(nextOptions);
      setSessions(nextSessions.items);
      setDefinitions(nextDefinitions.items);
      setSubjects(nextSubjects.items);
      setInspectedSubject((current) => current
        ? nextSubjects.items.find((item) => item.id === current.id) || current
        : null);
      setTimeoutSeconds((current) => current || nextOptions.default_timeout_seconds);
      setRetryCount((current) => current || nextOptions.default_retry_count);
      setError("");
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setLoading(false);
    }
  }, [includeArchived]);

  const definitionVersion = useDefinitionVersion({
    session, definitions, refreshWorkspace, setDefinitionChoice, setBusy, setError,
  });

  const refreshSelected = useCallback(async (selectedId: string, ownerIsCurrent?: () => boolean) => {
    if (ownerIsCurrent && !ownerIsCurrent()) return null;
    const selectionEpoch = selectionEpochRef.current;
    const readEpoch = ++readEpochRef.current;
    olderPageRef.current = null;
    try {
      const nextSession = await getAgentStudioSession(selectedId);
      const target = evidenceTargetRef.current?.conversation_id === selectedId ? evidenceTargetRef.current : null;
      const [nextConversation, nextMemories, nextRuns, nextActivity] = await Promise.all([
        getConversationState(selectedId, target ? target.message_sequence + 1 : undefined),
        getSubjectMemories(nextSession.memory_subject.id),
        listConversationRuns(selectedId),
        listConversationActivity(selectedId),
      ]);
      if (selectionEpoch !== selectionEpochRef.current || readEpoch !== readEpochRef.current || selectedIdRef.current !== selectedId
        || (ownerIsCurrent && !ownerIsCurrent())) return null;
      if (target && !nextConversation.messages.some((entry) => entry.id === target.message_id && entry.sequence === target.message_sequence)) {
        setEvidenceError("The cited message could not be verified in its original conversation.");
        evidenceTargetRef.current = null;
        return null;
      }
      setSession(nextSession);
      setConversation(nextConversation);
      setMemories(nextMemories);
      setRuns(nextRuns.items);
      setActivity(nextActivity.items);
      setRun((current) => {
        const latest = nextSession.latest_run;
        if (current?.conversation_id !== selectedId) return latest;
        if (!latest) return current;
        if (current.id !== latest.id) return latest;
        return TERMINAL_RUN_STATUSES.has(current.status) || !TERMINAL_RUN_STATUSES.has(latest.status) ? current : latest;
      });
      setSubjectRename(nextSession.memory_subject.display_name);
      if (bindingSelectionRef.current !== selectedId) {
        bindingSelectionRef.current = selectedId;
        setSubjectChoice(nextSession.memory_subject.id);
        setDefinitionChoice(nextSession.agent_definition.id);
      }
      if (target) {
        setEvidenceMessageId(target.message_id);
        setEvidenceError("");
        evidenceTargetRef.current = null;
        window.requestAnimationFrame(() => document.getElementById(`message-${target.message_id}`)?.scrollIntoView({ block: "center" }));
      }
      return nextMemories;
    } catch (exc) {
      if (selectionEpoch === selectionEpochRef.current && readEpoch === readEpochRef.current && selectedIdRef.current === selectedId
        && (!ownerIsCurrent || ownerIsCurrent())) setError(messageFrom(exc));
      return null;
    }
  }, []);

  const { removeSavedFact, retryRemoval } = useMemoryRemoval({
    session, inspectedSubject, memories, inspectedMemories, removal, setRemoval,
    selectedIdRef, selectionEpochRef, subjectInspectEpochRef,
    refreshSelected, setInspectedMemories, setBusy, setError,
  });
  const { setSessionArchived, setDefinitionArchived, setSubjectArchived, renameSubject } = useResourceActions({
    session, subjectRename, refreshWorkspace, refreshSelected, setBusy, setError,
  });

  const bindMonitorSelection = useCallback((monitoredConversationId: string) => {
    const epoch = selectionEpochRef.current;
    return () => selectedIdRef.current === monitoredConversationId && selectionEpochRef.current === epoch;
  }, []);

  const recordEvent = useCallback((event: RunEvent, isCurrent: () => boolean) => {
    if (!isCurrent()) return;
    setEvents((current) => {
      if (current.some((item) => item.id === event.id)) return current;
      return [...current, event].sort((left, right) => left.sequence - right.sequence);
    });
  }, []);

  const updateMonitoredRun = useCallback((nextRun: Run, nextEvents: RunEvent[], isCurrent: () => boolean) => {
    if (!isCurrent()) return;
    setRun(nextRun);
    setEvents(nextEvents);
  }, []);

  const completeMonitoredRun = useCallback(async (nextRun: Run, nextEvents: RunEvent[], isCurrent: () => boolean) => {
    if (!isCurrent()) return;
    const refreshedMemories = await refreshSelected(nextRun.conversation_id, isCurrent);
    if (!isCurrent()) return;
    setMemoryAction((current) => {
      if (!current || current.runId !== nextRun.id || current.conversationId !== nextRun.conversation_id) return current;
      return { ...current, outcome: memoryActionOutcome(current, nextRun, nextEvents, refreshedMemories) };
    });
  }, [refreshSelected]);

  const reportMonitorError = useCallback((exc: unknown) => setError(messageFrom(exc)), []);
  const { monitorRun, stopMonitoring, isMonitoring } = useRunMonitor({
    bindSelection: bindMonitorSelection, onEvent: recordEvent, onSnapshot: updateMonitoredRun,
    onComplete: completeMonitoredRun, onWarning: setStreamWarning, onError: reportMonitorError,
  });

  const selectConversation = useCallback((nextConversationId: string | null) => {
    if (nextConversationId === selectedIdRef.current) return;
    selectedIdRef.current = nextConversationId;
    selectionEpochRef.current += 1;
    subjectInspectEpochRef.current += 1;
    readEpochRef.current += 1;
    bindingSelectionRef.current = null;
    olderPageRef.current = null;
    stopMonitoring();
    setSession(null);
    setInspectedSubject(null);
    setInspectedMemories(null);
    setConversation(null);
    setMemories(null);
    setRuns([]);
    setRun(null);
    setEvents([]);
    setActivity([]);
    setEvidenceMessageId("");
    setEvidenceError("");
    setMemoryAction(null);
    setRemoval(null);
    if (!evidenceTargetRef.current || evidenceTargetRef.current.conversation_id !== nextConversationId) evidenceTargetRef.current = null;
    const params = new URLSearchParams(searchParams.toString());
    if (nextConversationId) params.set("conversation", nextConversationId);
    else params.delete("conversation");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }, [pathname, router, searchParams, stopMonitoring]);

  async function inspectSubject(subjectId: string) {
    const subject = subjects.find((item) => item.id === subjectId);
    if (!subject) return;
    selectConversation(null);
    const epoch = ++subjectInspectEpochRef.current;
    setRemoval(null);
    setError("");
    setInspectedSubject(subject);
    setInspectedMemories(null);
    try {
      const nextMemories = await getSubjectMemories(subjectId);
      if (subjectInspectEpochRef.current === epoch && selectedIdRef.current === null) {
        setInspectedMemories(nextMemories);
      }
    } catch (exc) {
      if (subjectInspectEpochRef.current === epoch && selectedIdRef.current === null) setError(messageFrom(exc));
    }
  }

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    selectedIdRef.current = conversationId;
    selectionEpochRef.current += 1;
    if (conversationId) {
      subjectInspectEpochRef.current += 1;
      setInspectedSubject(null);
      setInspectedMemories(null);
    }
    readEpochRef.current += 1;
    bindingSelectionRef.current = null;
    olderPageRef.current = null;
    stopMonitoring();
    setEvents([]);
    setRun(null);
    setMemoryAction(null);
    setSession(null);
    setConversation(null);
    setMemories(null);
    setRuns([]);
    setActivity([]);
    if (conversationId) void refreshSelected(conversationId);
  }, [conversationId, refreshSelected, stopMonitoring]);

  useEffect(() => {
    const latest = session?.latest_run;
    if (conversationId && session?.conversation.id === conversationId && latest
      && !TERMINAL_RUN_STATUSES.has(latest.status) && !isMonitoring(latest.id)) {
      monitorRun(latest.id, conversationId);
    }
  }, [conversationId, session?.conversation.id, session?.latest_run, isMonitoring, monitorRun]);

  async function createSession() {
    try {
      const draft = { title, definitionChoice, definitionName, definitionKey,
        subjectChoice, subjectName, subjectKey };
      const signature = JSON.stringify(draft);
      if (createAttemptRef.current?.signature !== signature) {
        createAttemptRef.current = { signature, idempotencyKey: identityKey("studio-session") };
      }
      const payload = sessionDraftPayload(options, draft, createAttemptRef.current.idempotencyKey);
      setBusy(true);
      setError("");
      const created = await createAgentStudioSession(payload);
      createAttemptRef.current = null;
      await refreshWorkspace();
      setDefinitionChoice(created.agent_definition.id);
      setSubjectChoice(created.memory_subject.id);
      setDefinitionKey(identityKey("studio-character"));
      setSubjectKey(identityKey("studio-person"));
      setSubjectName("");
      setTitle("New conversation");
      selectConversation(created.conversation.id);
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  function selectSubjectForNewConversation(subjectId: string) {
    setSubjectChoice(subjectId);
    if (HISTORY_TRIAL && subjectId !== NEW_RESOURCE_VALUE) {
      const prior = subjectBindingsRef.current.find((item) => item.memory_subject.id === subjectId);
      if (prior) setDefinitionChoice(prior.agent_definition.id);
    }
  }

  async function loadOlderMessages() {
    if (!conversation?.next_before_sequence || !session) return;
    const selectedId = session.conversation.id;
    const cursor = conversation.next_before_sequence;
    if (olderPageRef.current?.conversationId === selectedId && olderPageRef.current.cursor === cursor) return;
    const request = { conversationId: selectedId, cursor };
    olderPageRef.current = request;
    const selectionEpoch = selectionEpochRef.current;
    const readEpoch = readEpochRef.current;
    try {
      const older = await getConversationState(selectedId, cursor);
      if (selectedIdRef.current !== selectedId || selectionEpoch !== selectionEpochRef.current || readEpoch !== readEpochRef.current) return;
      setConversation((current) => current && current.id === selectedId && current.next_before_sequence === cursor ? {
        ...current,
        messages: [...new Map([...older.messages, ...current.messages].map((entry) => [entry.id, entry])).values()]
          .sort((left, right) => left.sequence - right.sequence),
        messages_truncated: older.messages_truncated,
        next_before_sequence: older.next_before_sequence,
      } : current);
    } catch (exc) {
      if (selectedIdRef.current === selectedId && selectionEpoch === selectionEpochRef.current && readEpoch === readEpochRef.current) setError(messageFrom(exc));
    } finally {
      if (olderPageRef.current === request) olderPageRef.current = null;
    }
  }

  async function openEvidence(evidence: MemoryEvidence) {
    evidenceTargetRef.current = evidence;
    setEvidenceMessageId("");
    setEvidenceError("");
    if (selectedIdRef.current === evidence.conversation_id) await refreshSelected(evidence.conversation_id);
    else selectConversation(evidence.conversation_id);
  }

  async function returnToLatestMessages() {
    if (!session) return;
    evidenceTargetRef.current = null;
    setEvidenceMessageId("");
    setEvidenceError("");
    await refreshSelected(session.conversation.id);
  }

  function prepareMemoryAction(factId: string, version: number, operation: "correct" | "forget") {
    const fact = memories?.facts.find((item) => item.id === factId && item.version === version && item.status === "active");
    if (!fact || !session || isArchived(session.conversation)) return;
    setMessage(memoryActionDraft(fact, operation));
    setMemoryAction({ conversationId: session.conversation.id, factId, version, operation, runId: null, outcome: "Prepared. Edit this message and send it to request review; no memory has changed yet." });
  }


  async function sendMessage() {
    const content = message.trim();
    const selected = session;
    if (!selected || !content || isArchived(selected.conversation) || (run && !TERMINAL_RUN_STATUSES.has(run.status))) return;
    const selectedId = selected.conversation.id;
    const selectionEpoch = selectionEpochRef.current;
    const actionAtSend = memoryAction;
    const isCurrent = () => selectedIdRef.current === selectedId && selectionEpochRef.current === selectionEpoch;
    setBusy(true);
    setError("");
    setEvents([]);
    setMessage("");
    try {
      const accepted = await acceptTurn(selectedId, {
        content,
        idempotency_key: identityKey("turn"),
        timeout_seconds: clampNumber(timeoutSeconds, 5, 600),
        retry_count: clampNumber(retryCount, 0, options?.max_retry_count || 5),
      });
      if (!isCurrent()) return;
      setMemoryAction((current) => current && actionAtSend && current.conversationId === selectedId
        && current.factId === actionAtSend.factId && current.version === actionAtSend.version
        && current.operation === actionAtSend.operation && current.runId === null
        ? { ...current, runId: accepted.run_id, outcome: "Turn accepted; waiting for review and a committed revision." } : current);
      const [acceptedRun, eventLog] = await Promise.all([getRun(accepted.run_id), getRunEventLog(accepted.run_id)]);
      if (!isCurrent()) return;
      setRun(acceptedRun);
      setEvents(eventLog.items);
      evidenceTargetRef.current = null;
      setEvidenceMessageId("");
      await refreshSelected(selectedId);
      if (isCurrent() && !isMonitoring(accepted.run_id)) monitorRun(accepted.run_id, selectedId);
    } catch (exc) {
      if (isCurrent()) {
        setMessage(content);
        setError(messageFrom(exc));
      }
    } finally {
      setBusy(false);
    }
  }

  async function cancelActiveRun() {
    if (!run || TERMINAL_RUN_STATUSES.has(run.status)) return;
    const selectedId = run.conversation_id;
    const selectionEpoch = selectionEpochRef.current;
    setBusy(true);
    setError("");
    try {
      const cancelled = await cancelRun(run.id);
      if (selectedIdRef.current === selectedId && selectionEpochRef.current === selectionEpoch) setRun(cancelled);
    } catch (exc) {
      if (selectedIdRef.current === selectedId && selectionEpochRef.current === selectionEpoch) setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  return {
    options, sessions, definitions, subjects, session, inspectedSubject, inspectedMemories, conversation, memories, runs, run, events, activity,
    loading, busy, error, streamWarning, includeArchived, message, timeoutSeconds, retryCount,
    title, definitionChoice, definitionName, definitionKey, subjectChoice, subjectName, subjectKey, subjectRename,
    evidenceMessageId, evidenceError, memoryAction, removal, ...definitionVersion,
    activeRun: Boolean(run && !TERMINAL_RUN_STATUSES.has(run.status)),
    setIncludeArchived, setMessage, setTimeoutSeconds: (value: number) => setTimeoutSeconds(clampNumber(value, 5, 600)),
    setRetryCount: (value: number) => setRetryCount(clampNumber(value, 0, options?.max_retry_count || 5)),
    setTitle, setDefinitionChoice, setDefinitionName, setDefinitionKey, setSubjectChoice, selectSubjectForNewConversation, setSubjectName, setSubjectKey, setSubjectRename,
    selectConversation, inspectSubject, refreshWorkspace, createSession, setSessionArchived, setDefinitionArchived, setSubjectArchived,
    renameSubject, sendMessage, cancelActiveRun, loadOlderMessages, openEvidence, returnToLatestMessages, prepareMemoryAction,
    removeSavedFact, retryRemoval,
  };
}
