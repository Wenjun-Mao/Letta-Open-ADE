"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  acceptTurn,
  cancelRun,
  createAgentStudioSession,
  getAgentStudioOptions,
  getAgentStudioSession,
  getConversationState,
  getRun,
  getRunEventLog,
  retryRun,
  listAgentStudioDefinitions,
  listAgentStudioSessions,
  listAgentStudioSubjects,
  listConversationRuns,
  listConversationActivity,
} from "./api";
import { sessionDraftPayload } from "./session-draft";
import { useResourceActions } from "./resource-actions";
import { useDefinitionVersion } from "./use-definition-version";
import { useRunMonitor, TERMINAL_RUN_STATUSES, QUIESCENT_RUN_STATUSES } from "./use-run-monitor";
import { useRelationshipMemory } from "./use-relationship-memory";
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
  MessageSource,
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
  const readEpochRef = useRef(0);
  const bindingSelectionRef = useRef<string | null>(null);
  const olderPageRef = useRef<{ conversationId: string; cursor: number } | null>(null);
  const evidenceTargetRef = useRef<MessageSource | null>(null);
  const createAttemptRef = useRef<{ signature: string; idempotencyKey: string } | null>(null);
  const turnAttemptRef = useRef<{ signature: string; idempotencyKey: string } | null>(null);
  const retryAttemptRef = useRef<{ runId: string; attempt: number; key: string } | null>(null);

  const [options, setOptions] = useState<AgentStudioOptions | null>(null);
  const [sessions, setSessions] = useState<AgentStudioSession[]>([]);
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [subjects, setSubjects] = useState<MemorySubject[]>([]);
  const [session, setSession] = useState<AgentStudioSession | null>(null);
  const [conversation, setConversation] = useState<ConversationState | null>(null);
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
  const [definitionName, setDefinitionName] = useState("ADE Companion");
  const [definitionKey, setDefinitionKey] = useState(() => identityKey("studio-character"));
  const [subjectChoice, setSubjectChoice] = useState(NEW_RESOURCE_VALUE);
  const [subjectName, setSubjectName] = useState("New memory subject");
  const [subjectKey, setSubjectKey] = useState(() => identityKey("studio-person"));
  const [subjectRename, setSubjectRename] = useState("");
  const [evidenceMessageId, setEvidenceMessageId] = useState("");
  const [evidenceError, setEvidenceError] = useState("");
  const memory = useRelationshipMemory(session);

  const refreshWorkspace = useCallback(async () => {
    setLoading(true);
    try {
      const [nextOptions, nextSessions, nextDefinitions, nextSubjects] = await Promise.all([
        getAgentStudioOptions(),
        listAgentStudioSessions(includeArchived),
        listAgentStudioDefinitions(includeArchived),
        listAgentStudioSubjects(includeArchived),
      ]);
      setOptions(nextOptions);
      setSessions(nextSessions.items);
      setDefinitions(nextDefinitions.items);
      setSubjects(nextSubjects.items);
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
      const [nextConversation, nextRuns, nextActivity] = await Promise.all([
        getConversationState(selectedId, target ? target.message_sequence + 1 : undefined),
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
      return nextConversation;
    } catch (exc) {
      if (selectionEpoch === selectionEpochRef.current && readEpoch === readEpochRef.current && selectedIdRef.current === selectedId
        && (!ownerIsCurrent || ownerIsCurrent())) setError(messageFrom(exc));
      return null;
    }
  }, []);

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
    await refreshSelected(nextRun.conversation_id, isCurrent);
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
    readEpochRef.current += 1;
    bindingSelectionRef.current = null;
    olderPageRef.current = null;
    stopMonitoring();
    setSession(null);
    setConversation(null);
    setRuns([]);
    setRun(null);
    setEvents([]);
    setActivity([]);
    setEvidenceMessageId("");
    setEvidenceError("");
    if (!evidenceTargetRef.current || evidenceTargetRef.current.conversation_id !== nextConversationId) evidenceTargetRef.current = null;
    const params = new URLSearchParams(searchParams.toString());
    if (nextConversationId) params.set("conversation", nextConversationId);
    else params.delete("conversation");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }, [pathname, router, searchParams, stopMonitoring]);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    selectedIdRef.current = conversationId;
    selectionEpochRef.current += 1;
    readEpochRef.current += 1;
    bindingSelectionRef.current = null;
    olderPageRef.current = null;
    stopMonitoring();
    setEvents([]);
    setRun(null);
    setSession(null);
    setConversation(null);
    setRuns([]);
    setActivity([]);
    if (conversationId) void refreshSelected(conversationId);
  }, [conversationId, refreshSelected, stopMonitoring]);

  useEffect(() => {
    const latest = session?.latest_run;
    if (conversationId && session?.conversation.id === conversationId && latest
      && !QUIESCENT_RUN_STATUSES.has(latest.status) && !isMonitoring(latest.id)) {
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

  async function openEvidence(evidence: MessageSource) {
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

  async function sendMessage() {
    const content = message.trim();
    const selected = session;
    if (!selected || !content || isArchived(selected.conversation) || (run && !TERMINAL_RUN_STATUSES.has(run.status))) return;
    const selectedId = selected.conversation.id;
    const selectionEpoch = selectionEpochRef.current;
    const isCurrent = () => selectedIdRef.current === selectedId && selectionEpochRef.current === selectionEpoch;
    const payload = { content, timeout_seconds: clampNumber(timeoutSeconds, 5, 600), retry_count: clampNumber(retryCount, 0, options?.max_retry_count || 5) };
    const signature = JSON.stringify({ conversationId: selectedId, ...payload });
    if (turnAttemptRef.current?.signature !== signature) {
      turnAttemptRef.current = { signature, idempotencyKey: identityKey("turn") };
    }
    const idempotencyKey = turnAttemptRef.current.idempotencyKey;
    let acceptedId: string | null = null;
    setBusy(true);
    setError("");
    setEvents([]);
    setMessage("");
    try {
      const accepted = await acceptTurn(selectedId, {
        ...payload, idempotency_key: idempotencyKey,
      });
      acceptedId = accepted.run_id;
      if (turnAttemptRef.current?.idempotencyKey === idempotencyKey) turnAttemptRef.current = null;
      if (!isCurrent()) return;
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
        if (!acceptedId) setMessage(content);
        setError(messageFrom(exc));
        await refreshSelected(selectedId, isCurrent);
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

  async function retryPausedRun() {
    if (!run || run.status !== "paused") return;
    const saved = run;
    const epoch = selectionEpochRef.current;
    const current = () => selectedIdRef.current === saved.conversation_id && selectionEpochRef.current === epoch;
    if (retryAttemptRef.current?.runId !== saved.id || retryAttemptRef.current.attempt !== saved.attempt_count) {
      retryAttemptRef.current = { runId: saved.id, attempt: saved.attempt_count, key: identityKey("saved-input-retry") };
    }
    setBusy(true);
    setError("");
    try {
      const accepted = await retryRun(saved.id, saved.attempt_count, retryAttemptRef.current.key);
      if (!current()) return;
      if (accepted.run_id !== saved.id) throw new Error("Retry returned an unexpected saved run identity.");
      const next = await getRun(accepted.run_id);
      if (!current()) return;
      if (next.conversation_id !== saved.conversation_id) throw new Error("Retry returned an unexpected conversation identity.");
      setRun(next);
      if (!QUIESCENT_RUN_STATUSES.has(next.status)) monitorRun(next.id, next.conversation_id);
    } catch (exc) {
      if (current()) setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  return {
    options, sessions, definitions, subjects, session, conversation, memory, runs, run, events, activity,
    loading, busy, error, streamWarning, includeArchived, message, timeoutSeconds, retryCount,
    title, definitionChoice, definitionName, definitionKey, subjectChoice, subjectName, subjectKey, subjectRename,
    evidenceMessageId, evidenceError, ...definitionVersion,
    activeRun: Boolean(run && !TERMINAL_RUN_STATUSES.has(run.status)),
    setIncludeArchived, setMessage, setTimeoutSeconds: (value: number) => setTimeoutSeconds(clampNumber(value, 5, 600)),
    setRetryCount: (value: number) => setRetryCount(clampNumber(value, 0, options?.max_retry_count || 5)),
    setTitle, setDefinitionChoice, setDefinitionName, setDefinitionKey, setSubjectChoice, selectSubjectForNewConversation, setSubjectName, setSubjectKey, setSubjectRename,
    selectConversation, refreshWorkspace, createSession, setSessionArchived, setDefinitionArchived, setSubjectArchived,
    renameSubject, sendMessage, cancelActiveRun, retryPausedRun, loadOlderMessages, openEvidence, returnToLatestMessages,
  };
}
