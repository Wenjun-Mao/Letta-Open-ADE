"use client";

import { useCallback, useEffect, useRef } from "react";

import { getRun, getRunEventLog } from "./api";
import { openRunEventStream } from "./event-stream";
import type { Run, RunEvent } from "./types";

export const TERMINAL_RUN_STATUSES = new Set(["succeeded", "failed", "cancelled"]);
type OwnershipGuard = () => boolean;
type RunMonitorCallbacks = {
  bindSelection: (conversationId: string) => OwnershipGuard;
  onEvent: (event: RunEvent, isCurrent: OwnershipGuard) => void;
  onSnapshot: (run: Run, events: RunEvent[], isCurrent: OwnershipGuard) => void;
  onComplete: (run: Run, events: RunEvent[], isCurrent: OwnershipGuard) => Promise<void>;
  onWarning: (warning: string) => void;
  onError: (error: unknown) => void;
};

export function useRunMonitor({ bindSelection, onEvent, onSnapshot, onComplete, onWarning, onError }: RunMonitorCallbacks) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const terminalRunRef = useRef("");
  const activeMonitorRef = useRef<{ runId: string } | null>(null);

  const stopMonitoring = useCallback(() => {
    activeMonitorRef.current = null;
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const isMonitoring = useCallback((runId: string) => activeMonitorRef.current?.runId === runId, []);

  const monitorRun = useCallback((runId: string, conversationId: string) => {
    stopMonitoring();
    const monitor = { runId };
    activeMonitorRef.current = monitor;
    const selectionIsCurrent = bindSelection(conversationId);
    const isCurrent = () => activeMonitorRef.current === monitor && selectionIsCurrent();
    terminalRunRef.current = "";
    onWarning("");

    const finishRun = async () => {
      if (!isCurrent() || terminalRunRef.current === runId) return;
      terminalRunRef.current = runId;
      try {
        const [nextRun, eventLog] = await Promise.all([getRun(runId), getRunEventLog(runId)]);
        if (!isCurrent() || nextRun.conversation_id !== conversationId) return;
        onSnapshot(nextRun, eventLog.items, isCurrent);
        // The controller also guards mutations inside its awaited readback.
        await onComplete(nextRun, eventLog.items, isCurrent);
        if (!isCurrent()) return;
        stopMonitoring();
        onWarning("");
      } catch (error) {
        if (isCurrent()) {
          terminalRunRef.current = "";
          onError(error);
        }
      }
    };

    eventSourceRef.current = openRunEventStream(runId, {
      onEvent: (event) => { if (isCurrent()) onEvent(event, isCurrent); },
      onTerminal: () => { if (isCurrent()) void finishRun(); },
      onError: () => { if (isCurrent()) onWarning("Event stream reconnecting; status polling remains active."); },
    });
    pollRef.current = setInterval(() => {
      void Promise.all([getRun(runId), getRunEventLog(runId)])
        .then(([nextRun, eventLog]) => {
          if (!isCurrent() || nextRun.conversation_id !== conversationId) return;
          onSnapshot(nextRun, eventLog.items, isCurrent);
          if (TERMINAL_RUN_STATUSES.has(nextRun.status)) void finishRun();
        })
        .catch((error) => { if (isCurrent()) onError(error); });
    }, 1500);
  }, [bindSelection, onComplete, onError, onEvent, onSnapshot, onWarning, stopMonitoring]);

  useEffect(() => () => stopMonitoring(), [stopMonitoring]);

  return { monitorRun, stopMonitoring, isMonitoring };
}
