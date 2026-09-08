import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import { isAbortError } from "@/shared/api/client";
import {
  type TestArtifact,
  type TestRunRecord,
  getTestRun,
  listRunArtifacts,
  listTestRuns,
  readRunArtifact,
} from "./api";

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export function useTestCenterRuns(selectedRunId: string, onError: (message: string) => void) {
  const [runs, setRuns] = useState<TestRunRecord[]>([]);
  const [selectedRun, setSelectedRun] = useState<TestRunRecord | null>(null);
  const [artifacts, setArtifacts] = useState<TestArtifact[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [artifactContent, setArtifactContent] = useState("");
  const [artifactLoading, setArtifactLoading] = useState(false);
  const selectionVersionRef = useRef(0);
  const selectedRunAbortControllerRef = useRef<AbortController | null>(null);
  const artifactAbortControllerRef = useRef<AbortController | null>(null);

  const selectedRunSummary = useMemo(
    () => selectedRun || runs.find((run) => run.run_id === selectedRunId) || null,
    [runs, selectedRun, selectedRunId],
  );

  const refreshRuns = async () => {
    const payload = await listTestRuns();
    setRuns(Array.isArray(payload.items) ? payload.items : []);
  };

  const refreshSelectedRun = async (runId = selectedRunId, version = selectionVersionRef.current) => {
    if (!runId) {
      return;
    }

    const controller = new AbortController();
    selectedRunAbortControllerRef.current?.abort();
    selectedRunAbortControllerRef.current = controller;
    const [run, artifactPayload] = await Promise.all([
      getTestRun(runId, { signal: controller.signal }),
      listRunArtifacts(runId, { signal: controller.signal }),
    ]);
    if (controller.signal.aborted || version !== selectionVersionRef.current) {
      return;
    }
    setSelectedRun(run);
    setArtifacts(artifactPayload.items || []);
  };

  const refreshRunsEffect = useEffectEvent(refreshRuns);
  const refreshSelectedRunEffect = useEffectEvent(refreshSelectedRun);
  const reportEffectError = useEffectEvent(onError);

  useEffect(() => {
    void refreshRunsEffect().catch((exc) => {
      if (!isAbortError(exc)) {
        reportEffectError(toErrorMessage(exc));
      }
    });
  }, []);

  useEffect(() => {
    selectionVersionRef.current += 1;
    selectedRunAbortControllerRef.current?.abort();
    artifactAbortControllerRef.current?.abort();
    setSelectedRun(null);
    setArtifacts([]);
    setSelectedArtifactId("");
    setArtifactContent("");
    setArtifactLoading(false);

    if (!selectedRunId) {
      return;
    }

    const version = selectionVersionRef.current;
    void refreshSelectedRunEffect(selectedRunId, version).catch((exc) => {
      if (!isAbortError(exc) && version === selectionVersionRef.current) {
        reportEffectError(toErrorMessage(exc));
      }
    });
  }, [selectedRunId]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void refreshRunsEffect().catch(() => undefined);
      if (selectedRunId) {
        void refreshSelectedRunEffect(selectedRunId).catch(() => undefined);
      }
    }, 4000);
    return () => window.clearInterval(timer);
  }, [selectedRunId]);

  const readArtifact = async (artifactId: string) => {
    if (!selectedRunId) {
      return;
    }

    const controller = new AbortController();
    const version = selectionVersionRef.current;
    artifactAbortControllerRef.current?.abort();
    artifactAbortControllerRef.current = controller;
    setArtifactLoading(true);
    try {
      const payload = await readRunArtifact(selectedRunId, artifactId, 250, {
        signal: controller.signal,
      });
      if (controller.signal.aborted || version !== selectionVersionRef.current) {
        return;
      }
      setSelectedArtifactId(artifactId);
      setArtifactContent(payload.content || "");
    } catch (exc) {
      if (!isAbortError(exc) && version === selectionVersionRef.current) {
        onError(toErrorMessage(exc));
      }
    } finally {
      if (artifactAbortControllerRef.current === controller) {
        artifactAbortControllerRef.current = null;
        setArtifactLoading(false);
      }
    }
  };

  return {
    artifactContent,
    artifactLoading,
    artifacts,
    readArtifact,
    refreshRuns,
    refreshSelectedRun,
    runs,
    selectedArtifactId,
    selectedRun,
    selectedRunSummary,
  };
}
