"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  acceptTurn,
  archiveAgentStudioDefinition,
  archiveAgentStudioSession,
  archiveAgentStudioSubject,
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
  restoreAgentStudioDefinition,
  restoreAgentStudioSession,
  restoreAgentStudioSubject,
  updateAgentStudioSubject,
} from "./api";
import { openRunEventStream, TERMINAL_RUN_EVENT_TYPES } from "./event-stream";
import { memoryActionOutcome, type PendingMemoryAction } from "./memory-action";
import { useDefinitionVersion } from "./use-definition-version";
import {
  defaultBundle,
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
} from "./types";

const TERMINAL_RUN_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

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
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const terminalRunRef = useRef("");
  const selectedIdRef = useRef(conversationId);
  const selectionEpochRef = useRef(0);
  const evidenceTargetRef = useRef<MemoryEvidence | null>(null);
  const runConversationRef = useRef("");
  const monitorEpochRef = useRef(0);

  const [options, setOptions] = useState<AgentStudioOptions | null>(null);
  const [sessions, setSessions] = useState<AgentStudioSession[]>([]);
  const [definitions, setDefinitions] = useState<AgentDefinition[]>([]);
  const [subjects, setSubjects] = useState<MemorySubject[]>([]);
  const [session, setSession] = useState<AgentStudioSession | null>(null);
  const [conversation, setConversation] = useState<ConversationState | null>(null);
  const [memories, setMemories] = useState<SubjectMemories | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
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
  const [definitionName, setDefinitionName] = useState("ADE Native Companion");
  const [definitionKey, setDefinitionKey] = useState("ade_native_companion");
  const [subjectChoice, setSubjectChoice] = useState(NEW_RESOURCE_VALUE);
  const [subjectName, setSubjectName] = useState("New memory subject");
  const [subjectKey, setSubjectKey] = useState("local-user");
  const [subjectRename, setSubjectRename] = useState("");
  const [evidenceMessageId, setEvidenceMessageId] = useState("");
  const [evidenceError, setEvidenceError] = useState("");
  const [memoryAction, setMemoryAction] = useState<PendingMemoryAction | null>(null);

  const stopMonitoring = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const selectConversation = useCallback((nextConversationId: string | null) => {
    selectedIdRef.current = nextConversationId;
    selectionEpochRef.current += 1;
    stopMonitoring();
    setSession(null);
    setConversation(null);
    setMemories(null);
    setRuns([]);
    setRun(null);
    setEvents([]);
    setEvidenceMessageId("");
    setEvidenceError("");
    setMemoryAction(null);
    if (!evidenceTargetRef.current || evidenceTargetRef.current.conversation_id !== nextConversationId) evidenceTargetRef.current = null;
    const params = new URLSearchParams(searchParams.toString());
    if (nextConversationId) params.set("conversation", nextConversationId);
    else params.delete("conversation");
    const query = params.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);
  }, [pathname, router, searchParams, stopMonitoring]);

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

  const refreshSelected = useCallback(async (selectedId: string) => {
    const epoch = ++selectionEpochRef.current;
    try {
      const nextSession = await getAgentStudioSession(selectedId);
      const target = evidenceTargetRef.current?.conversation_id === selectedId ? evidenceTargetRef.current : null;
      const [nextConversation, nextMemories, nextRuns] = await Promise.all([
        getConversationState(selectedId, target ? target.message_sequence + 1 : undefined),
        getSubjectMemories(nextSession.memory_subject.id),
        listConversationRuns(selectedId),
      ]);
      if (epoch !== selectionEpochRef.current || selectedIdRef.current !== selectedId) return null;
      if (target && !nextConversation.messages.some((entry) => entry.id === target.message_id && entry.sequence === target.message_sequence)) {
        setEvidenceError("The cited message could not be verified in its original conversation.");
        evidenceTargetRef.current = null;
        return null;
      }
      setSession(nextSession);
      setConversation(nextConversation);
      setMemories(nextMemories);
      setRuns(nextRuns.items);
      setRun(nextSession.latest_run);
      setSubjectRename(nextSession.memory_subject.display_name);
      setSubjectChoice(nextSession.memory_subject.id);
      setDefinitionChoice(nextSession.agent_definition.id);
      if (target) {
        setEvidenceMessageId(target.message_id);
        setEvidenceError("");
        evidenceTargetRef.current = null;
        window.requestAnimationFrame(() => document.getElementById(`message-${target.message_id}`)?.scrollIntoView({ block: "center" }));
      }
      return nextMemories;
    } catch (exc) {
      if (epoch === selectionEpochRef.current && selectedIdRef.current === selectedId) setError(messageFrom(exc));
      return null;
    }
  }, []);

  const finishRun = useCallback(async (runId: string) => {
    if (terminalRunRef.current === runId) return;
    const monitoredEpoch = monitorEpochRef.current;
    terminalRunRef.current = runId;
    try {
      const [nextRun, eventLog] = await Promise.all([getRun(runId), getRunEventLog(runId)]);
      if (selectedIdRef.current !== nextRun.conversation_id || runConversationRef.current !== nextRun.conversation_id || monitoredEpoch !== selectionEpochRef.current) return;
      setRun(nextRun);
      setEvents(eventLog.items);
      const refreshedMemories = await refreshSelected(nextRun.conversation_id);
      setMemoryAction((current) => {
        if (selectedIdRef.current !== nextRun.conversation_id) return current;
        if (!current || current.runId !== runId) return current;
        return { ...current, outcome: memoryActionOutcome(current, nextRun, eventLog.items, refreshedMemories) };
      });
      stopMonitoring();
      setStreamWarning("");
    } catch (exc) {
      terminalRunRef.current = "";
      setError(messageFrom(exc));
    }
  }, [refreshSelected, stopMonitoring]);

  const recordEvent = useCallback((event: RunEvent) => {
    setEvents((current) => {
      if (current.some((item) => item.id === event.id)) return current;
      return [...current, event].sort((left, right) => left.sequence - right.sequence);
    });
  }, []);

  const monitorRun = useCallback((runId: string) => {
    stopMonitoring();
    monitorEpochRef.current = selectionEpochRef.current;
    terminalRunRef.current = "";
    setStreamWarning("");
    eventSourceRef.current = openRunEventStream(runId, {
      onEvent: (event) => { if (selectedIdRef.current === runConversationRef.current && monitorEpochRef.current === selectionEpochRef.current) recordEvent(event); },
      onTerminal: () => void finishRun(runId),
      onError: () => { if (selectedIdRef.current === runConversationRef.current && monitorEpochRef.current === selectionEpochRef.current) setStreamWarning("Event stream reconnecting; status polling remains active."); },
    });
    pollRef.current = setInterval(() => {
      void Promise.all([getRun(runId), getRunEventLog(runId)])
        .then(([nextRun, eventLog]) => {
          if (selectedIdRef.current !== nextRun.conversation_id || runConversationRef.current !== nextRun.conversation_id || monitorEpochRef.current !== selectionEpochRef.current) return;
          setRun(nextRun);
          setEvents(eventLog.items);
          if (TERMINAL_RUN_STATUSES.has(nextRun.status)) void finishRun(runId);
        })
        .catch((exc) => { if (selectedIdRef.current === runConversationRef.current) setError(messageFrom(exc)); });
    }, 1500);
  }, [finishRun, recordEvent, stopMonitoring]);

  useEffect(() => {
    void refreshWorkspace();
  }, [refreshWorkspace]);

  useEffect(() => {
    selectedIdRef.current = conversationId;
    selectionEpochRef.current += 1;
    stopMonitoring();
    setEvents([]);
    setRun(null);
    setMemoryAction(null);
    setSession(null);
    setConversation(null);
    setMemories(null);
    setRuns([]);
    if (conversationId) void refreshSelected(conversationId);
  }, [conversationId, refreshSelected, stopMonitoring]);

  useEffect(() => () => stopMonitoring(), [stopMonitoring]);

  async function createSession() {
    const bundle = defaultBundle(options);
    if (!bundle) {
      setError("No configured Agent Studio bundle is available.");
      return;
    }
    if (!title.trim()) {
      setError("Conversation title is required.");
      return;
    }
    if (definitionChoice === NEW_RESOURCE_VALUE && (!definitionName.trim() || !definitionKey.trim())) {
      setError("A definition name and key are required.");
      return;
    }
    if (subjectChoice === NEW_RESOURCE_VALUE && (!subjectName.trim() || !subjectKey.trim())) {
      setError("A memory subject name and external key are required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await createAgentStudioSession({
        idempotency_key: identityKey("studio-session"),
        title: title.trim(),
        ...(definitionChoice === NEW_RESOURCE_VALUE
          ? { new_definition: {
            definition_key: definitionKey.trim(),
            name: definitionName.trim(),
            model_key: bundle.model_key,
            reviewer_model_key: bundle.reviewer_model_key,
            embedding_model_key: bundle.embedding_model_key,
            prompt_key: bundle.prompt_key,
            persona_key: bundle.persona_key,
            tool_names: bundle.tool_names.filter((tool): tool is "search_memory" | "get_weather" => tool === "search_memory" || tool === "get_weather"),
          } }
          : { agent_definition_id: definitionChoice }),
        ...(subjectChoice === NEW_RESOURCE_VALUE
          ? { new_subject: { external_key: subjectKey.trim(), display_name: subjectName.trim() } }
          : { memory_subject_id: subjectChoice }),
      });
      await refreshWorkspace();
      selectConversation(created.conversation.id);
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  async function loadOlderMessages() {
    if (!conversation?.next_before_sequence || !session) return;
    const selectedId = session.conversation.id;
    const epoch = selectionEpochRef.current;
    try {
      const older = await getConversationState(selectedId, conversation.next_before_sequence);
      if (selectedIdRef.current !== selectedId || epoch !== selectionEpochRef.current) return;
      setConversation((current) => current && current.id === selectedId ? {
        ...current,
        messages: [...older.messages, ...current.messages],
        messages_truncated: older.messages_truncated,
        next_before_sequence: older.next_before_sequence,
      } : current);
    } catch (exc) {
      if (selectedIdRef.current === selectedId) setError(messageFrom(exc));
    }
  }

  async function openEvidence(evidence: MemoryEvidence) {
    evidenceTargetRef.current = evidence;
    setEvidenceMessageId("");
    setEvidenceError("");
    if (selectedIdRef.current === evidence.conversation_id) await refreshSelected(evidence.conversation_id);
    else selectConversation(evidence.conversation_id);
  }

  function prepareMemoryAction(factId: string, version: number, operation: "correct" | "forget") {
    const fact = memories?.facts.find((item) => item.id === factId && item.version === version && item.status === "active");
    if (!fact || !session || isArchived(session.conversation)) return;
    const instruction = operation === "forget"
      ? `Please remove this saved information from active memory: ${fact.fact_type} about ${fact.entity_label || fact.entity_kind}: ${fact.value}. Do not treat this as a request to erase past conversations or revision history.`
      : `Please correct this saved fact: ${fact.fact_type} about ${fact.entity_label || fact.entity_kind}: ${fact.value}. The correct information is: `;
    setMessage(instruction);
    setMemoryAction({ factId, version, operation, runId: null, outcome: "Prepared. Edit this message and send it to request review; no memory has changed yet." });
  }


  async function setSessionArchived(archived: boolean) {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      if (archived) await archiveAgentStudioSession(session.conversation.id);
      else await restoreAgentStudioSession(session.conversation.id);
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  async function setDefinitionArchived(archived: boolean) {
    const rootId = session?.agent_definition.agent_definition_id;
    if (!rootId) return;
    setBusy(true);
    setError("");
    try {
      if (archived) await archiveAgentStudioDefinition(rootId);
      else await restoreAgentStudioDefinition(rootId);
      await Promise.all([refreshWorkspace(), refreshSelected(session!.conversation.id)]);
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  async function setSubjectArchived(archived: boolean) {
    if (!session) return;
    setBusy(true);
    setError("");
    try {
      if (archived) await archiveAgentStudioSubject(session.memory_subject.id);
      else await restoreAgentStudioSubject(session.memory_subject.id);
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  async function renameSubject() {
    if (!session || !subjectRename.trim() || subjectRename.trim() === session.memory_subject.display_name) return;
    setBusy(true);
    setError("");
    try {
      await updateAgentStudioSubject(session.memory_subject.id, {
        display_name: subjectRename.trim(),
        expected_version: session.memory_subject.version,
      });
      await Promise.all([refreshWorkspace(), refreshSelected(session.conversation.id)]);
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage() {
    const content = message.trim();
    const selected = session;
    if (!selected || !content || isArchived(selected.conversation) || (run && !TERMINAL_RUN_STATUSES.has(run.status))) return;
    setBusy(true);
    setError("");
    setEvents([]);
    setMessage("");
    try {
      const accepted = await acceptTurn(selected.conversation.id, {
        content,
        idempotency_key: identityKey("turn"),
        timeout_seconds: clampNumber(timeoutSeconds, 5, 600),
        retry_count: clampNumber(retryCount, 0, options?.max_retry_count || 5),
      });
      runConversationRef.current = selected.conversation.id;
      setMemoryAction((current) => current && current.runId === null ? { ...current, runId: accepted.run_id, outcome: "Turn accepted; waiting for review and a committed revision." } : current);
      const [acceptedRun, eventLog] = await Promise.all([getRun(accepted.run_id), getRunEventLog(accepted.run_id)]);
      if (selectedIdRef.current !== selected.conversation.id) return;
      setRun(acceptedRun);
      setEvents(eventLog.items);
      await refreshSelected(selected.conversation.id);
      if (selectedIdRef.current === selected.conversation.id) monitorRun(accepted.run_id);
    } catch (exc) {
      if (selectedIdRef.current === selected.conversation.id) {
        setMessage(content);
        setError(messageFrom(exc));
      }
    } finally {
      setBusy(false);
    }
  }

  async function cancelActiveRun() {
    if (!run || TERMINAL_RUN_STATUSES.has(run.status)) return;
    setBusy(true);
    setError("");
    try {
      setRun(await cancelRun(run.id));
    } catch (exc) {
      setError(messageFrom(exc));
    } finally {
      setBusy(false);
    }
  }

  return {
    options, sessions, definitions, subjects, session, conversation, memories, runs, run, events,
    loading, busy, error, streamWarning, includeArchived, message, timeoutSeconds, retryCount,
    title, definitionChoice, definitionName, definitionKey, subjectChoice, subjectName, subjectKey, subjectRename,
    evidenceMessageId, evidenceError, memoryAction, ...definitionVersion,
    activeRun: Boolean(run && !TERMINAL_RUN_STATUSES.has(run.status)),
    setIncludeArchived, setMessage, setTimeoutSeconds: (value: number) => setTimeoutSeconds(clampNumber(value, 5, 600)),
    setRetryCount: (value: number) => setRetryCount(clampNumber(value, 0, options?.max_retry_count || 5)),
    setTitle, setDefinitionChoice, setDefinitionName, setDefinitionKey, setSubjectChoice, setSubjectName, setSubjectKey, setSubjectRename,
    selectConversation, refreshWorkspace, createSession, setSessionArchived, setDefinitionArchived, setSubjectArchived,
    renameSubject, sendMessage, cancelActiveRun, loadOlderMessages, openEvidence, prepareMemoryAction,
  };
}
