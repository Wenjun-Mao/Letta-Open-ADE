"use client";

import { useEffect, useRef, useState } from "react";

import {
  DEFAULT_CONVERSATION_MODEL,
  DEFAULT_EMBEDDING_MODEL,
  acceptNativeTurn,
  cancelNativeRun,
  createNativePreviewSession,
  getNativeConversationState,
  getNativeRun,
  getNativeSubjectMemories,
  getNativeWorkerHealth,
  type NativeConversationState,
  type NativePreviewSession,
  type NativeRun,
  type NativeRunEvent,
  type NativeSubjectMemories,
  type NativeWorkerHealth,
} from "./api";
import { openNativeRunEventStream } from "./event-stream";

const TERMINAL_RUN_STATUSES = new Set(["succeeded", "failed", "cancelled"]);

function nextIdentity(): string {
  return globalThis.crypto?.randomUUID?.() || `preview-${Date.now()}`;
}

export function useNativeRuntimePreview(enabled: boolean) {
  const [health, setHealth] = useState<NativeWorkerHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [streamWarning, setStreamWarning] = useState("");
  const [sessionIdentity, setSessionIdentity] = useState("");
  const [session, setSession] = useState<NativePreviewSession | null>(null);
  const [conversation, setConversation] = useState<NativeConversationState | null>(null);
  const [memories, setMemories] = useState<NativeSubjectMemories | null>(null);
  const [run, setRun] = useState<NativeRun | null>(null);
  const [events, setEvents] = useState<NativeRunEvent[]>([]);
  const [message, setMessage] = useState("");
  const [name, setName] = useState("Native Memory Preview");
  const [subjectDisplayName, setSubjectDisplayName] = useState("Preview User");
  const [modelKey, setModelKey] = useState(DEFAULT_CONVERSATION_MODEL);
  const [reviewerModelKey, setReviewerModelKey] = useState(DEFAULT_CONVERSATION_MODEL);
  const [embeddingModelKey, setEmbeddingModelKey] = useState(DEFAULT_EMBEDDING_MODEL);
  const [promptKey, setPromptKey] = useState("chat_v20260516");
  const [personaKey, setPersonaKey] = useState("chat_linxiaotang");
  const [timeoutSeconds, setTimeoutSeconds] = useState(180);
  const [retryCount, setRetryCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const terminalRunRef = useRef("");

  function stopMonitoring() {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function refreshHealth() {
    if (!enabled) {
      return;
    }
    setHealthLoading(true);
    try {
      setHealth(await getNativeWorkerHealth());
    } catch (exc) {
      setHealth(null);
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setHealthLoading(false);
    }
  }

  async function refreshSessionState(activeSession = session) {
    if (!activeSession) {
      return;
    }
    const [nextConversation, nextMemories] = await Promise.all([
      getNativeConversationState(activeSession.conversation.id),
      getNativeSubjectMemories(activeSession.memory_subject.id),
    ]);
    setConversation(nextConversation);
    setMemories(nextMemories);
  }

  async function finishRun(runId: string) {
    if (terminalRunRef.current === runId) {
      return;
    }
    terminalRunRef.current = runId;
    try {
      setRun(await getNativeRun(runId));
      await refreshSessionState();
      stopMonitoring();
      setStreamWarning("");
    } catch (exc) {
      terminalRunRef.current = "";
      setError(exc instanceof Error ? exc.message : String(exc));
    }
  }

  function recordEvent(event: NativeRunEvent) {
    setEvents((current) => {
      if (current.some((item) => item.id === event.id)) {
        return current;
      }
      return [...current, event].sort((left, right) => left.sequence - right.sequence);
    });
  }

  function monitorRun(runId: string) {
    stopMonitoring();
    terminalRunRef.current = "";
    setStreamWarning("");
    eventSourceRef.current = openNativeRunEventStream(runId, {
      onEvent: recordEvent,
      onTerminal: () => void finishRun(runId),
      onError: () => setStreamWarning("Event stream reconnecting; status polling remains active."),
    });
    pollRef.current = setInterval(() => {
      void getNativeRun(runId)
        .then((nextRun) => {
          setRun(nextRun);
          if (TERMINAL_RUN_STATUSES.has(nextRun.status)) {
            void finishRun(runId);
          }
        })
        .catch((exc) => setError(exc instanceof Error ? exc.message : String(exc)));
    }, 1500);
  }

  useEffect(() => {
    if (!enabled) {
      return;
    }
    setSessionIdentity(nextIdentity());
    void refreshHealth();
    return stopMonitoring;
    // The preview is a build-time gated route; it never toggles within one mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  async function createSession() {
    if (!sessionIdentity || health?.status !== "ready") {
      return;
    }
    setBusy(true);
    setError("");
    try {
      const created = await createNativePreviewSession({
        idempotency_key: sessionIdentity,
        name,
        subject_display_name: subjectDisplayName,
        model_key: modelKey,
        reviewer_model_key: reviewerModelKey,
        embedding_model_key: embeddingModelKey,
        prompt_key: promptKey,
        persona_key: personaKey,
      });
      setSession(created);
      await refreshSessionState(created);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  function resetSession() {
    stopMonitoring();
    setSessionIdentity(nextIdentity());
    setSession(null);
    setConversation(null);
    setMemories(null);
    setRun(null);
    setEvents([]);
    setMessage("");
    setError("");
    setStreamWarning("");
  }

  async function sendMessage() {
    const content = message.trim();
    if (!session || !content || (run && !TERMINAL_RUN_STATUSES.has(run.status))) {
      return;
    }
    setBusy(true);
    setError("");
    setEvents([]);
    setMessage("");
    try {
      const accepted = await acceptNativeTurn(session.conversation.id, {
        content,
        idempotency_key: nextIdentity(),
        timeout_seconds: timeoutSeconds,
        retry_count: retryCount,
      });
      const acceptedRun = await getNativeRun(accepted.run_id);
      setRun(acceptedRun);
      monitorRun(accepted.run_id);
      await refreshSessionState();
    } catch (exc) {
      setMessage(content);
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  async function cancelRun() {
    if (!run || TERMINAL_RUN_STATUSES.has(run.status)) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      setRun(await cancelNativeRun(run.id));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : String(exc));
    } finally {
      setBusy(false);
    }
  }

  return {
    health,
    healthLoading,
    busy,
    error,
    streamWarning,
    session,
    conversation,
    memories,
    run,
    events,
    message,
    name,
    subjectDisplayName,
    modelKey,
    reviewerModelKey,
    embeddingModelKey,
    promptKey,
    personaKey,
    timeoutSeconds,
    retryCount,
    setMessage,
    setName,
    setSubjectDisplayName,
    setModelKey,
    setReviewerModelKey,
    setEmbeddingModelKey,
    setPromptKey,
    setPersonaKey,
    setTimeoutSeconds,
    setRetryCount,
    refreshHealth,
    createSession,
    resetSession,
    sendMessage,
    cancelRun,
  };
}
