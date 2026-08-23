"use client";

import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import {
  type CreateTestRunPayload,
  type PlatformArtifact,
  type PlatformRunRecord,
  cancelTestRun,
  createTestRun,
  getTestRun,
  isAbortError,
  listRunArtifacts,
  listTestRuns,
  readRunArtifact,
} from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { isCurrentRequest, type RequestIdentity } from "../../lib/request-identity";
import { getTestCenterCopy } from "./test-center-copy";
import { TestCenterView } from "./test-center-view";

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

export default function TestCenterPage() {
  const { locale } = useI18n();
  const copy = getTestCenterCopy(locale);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [runs, setRuns] = useState<PlatformRunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedRun, setSelectedRun] = useState<PlatformRunRecord | null>(null);
  const selectedRunIdRef = useRef("");
  const selectedRunVersionRef = useRef(0);
  const selectedRunAbortControllerRef = useRef<AbortController | null>(null);
  const artifactAbortControllerRef = useRef<AbortController | null>(null);

  const [artifacts, setArtifacts] = useState<PlatformArtifact[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [artifactContent, setArtifactContent] = useState("");

  const selectedRunSummary = useMemo(() => {
    if (selectedRun) {
      return selectedRun;
    }
    return runs.find((item) => item.run_id === selectedRunId) || null;
  }, [runs, selectedRun, selectedRunId]);

  const currentRunRequest = (runId: string): RequestIdentity => ({
    resourceId: runId,
    version: selectedRunVersionRef.current,
  });

  const isCurrentRunRequest = (identity: RequestIdentity): boolean =>
    isCurrentRequest(identity, selectedRunIdRef.current, selectedRunVersionRef.current);

  const selectRun = (runId: string) => {
    if (runId !== selectedRunIdRef.current) {
      selectedRunIdRef.current = runId;
      selectedRunVersionRef.current += 1;
      selectedRunAbortControllerRef.current?.abort();
      const hadActiveArtifactRequest = artifactAbortControllerRef.current !== null;
      artifactAbortControllerRef.current?.abort();
      selectedRunAbortControllerRef.current = null;
      artifactAbortControllerRef.current = null;
      if (hadActiveArtifactRequest) {
        setBusy(false);
      }
      setSelectedRun(null);
      setArtifacts([]);
      setSelectedArtifactId("");
      setArtifactContent("");
    }
    setSelectedRunId(runId);
  };

  const refreshRuns = async () => {
    const payload = await listTestRuns();
    const items = Array.isArray(payload.items) ? payload.items : [];
    setRuns(items);

    const currentRunId = selectedRunIdRef.current;
    if (!currentRunId && items.length > 0) {
      selectRun(items[0].run_id);
    } else if (currentRunId && !items.some((item) => item.run_id === currentRunId)) {
      selectRun(items[0]?.run_id || "");
    }
  };

  const refreshSelectedRun = async (runId: string, identity = currentRunRequest(runId)) => {
    if (!runId) {
      return false;
    }
    const controller = new AbortController();
    selectedRunAbortControllerRef.current?.abort();
    selectedRunAbortControllerRef.current = controller;
    const [run, artifactPayload] = await Promise.all([
      getTestRun(runId, { signal: controller.signal }),
      listRunArtifacts(runId, { signal: controller.signal }),
    ]);
    if (!isCurrentRunRequest(identity) || selectedRunAbortControllerRef.current !== controller) {
      return false;
    }
    setSelectedRun(run);
    setArtifacts(artifactPayload.items || []);
    return true;
  };

  const refreshRunsEffect = useEffectEvent(refreshRuns);
  const refreshSelectedRunEffect = useEffectEvent(refreshSelectedRun);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        await refreshRunsEffect();
      } catch (exc) {
        if (!cancelled) {
          setError(toErrorMessage(exc));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void run();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const timer = setInterval(() => {
      void refreshRunsEffect().catch(() => undefined);
      if (selectedRunId) {
        void refreshSelectedRunEffect(selectedRunId).catch(() => undefined);
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    const identity = currentRunRequest(selectedRunId);
    void refreshSelectedRunEffect(selectedRunId, identity).catch((exc) => {
      if (isCurrentRunRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    });
  }, [selectedRunId]);

  const onCreateRun = async (payload: CreateTestRunPayload) => {
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const created = await createTestRun(payload);
      setStatus(`${copy.createdRun} ${created.run_id}`);
      selectRun(created.run_id);
      await refreshRuns();
      await refreshSelectedRun(created.run_id);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onCancelSelected = async () => {
    if (!selectedRunId) {
      return;
    }
    const targetRunId = selectedRunId;
    const identity = currentRunRequest(targetRunId);
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const payload = await cancelTestRun(targetRunId);
      if (!isCurrentRunRequest(identity)) {
        return;
      }
      setStatus(`${copy.cancelRequested} ${payload.run_id}`);
      await refreshSelectedRun(targetRunId, identity);
      await refreshRuns();
    } catch (exc) {
      if (isCurrentRunRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      setBusy(false);
    }
  };

  const onReadArtifact = async (artifactId: string) => {
    if (!selectedRunId) {
      return;
    }
    const targetRunId = selectedRunId;
    const identity = currentRunRequest(targetRunId);
    const controller = new AbortController();
    artifactAbortControllerRef.current?.abort();
    artifactAbortControllerRef.current = controller;
    setBusy(true);
    setError("");
    try {
      const payload = await readRunArtifact(targetRunId, artifactId, 250, { signal: controller.signal });
      if (!isCurrentRunRequest(identity) || artifactAbortControllerRef.current !== controller) {
        return;
      }
      setSelectedArtifactId(artifactId);
      setArtifactContent(payload.content || "");
    } catch (exc) {
      if (isCurrentRunRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      if (artifactAbortControllerRef.current === controller) {
        artifactAbortControllerRef.current = null;
        setBusy(false);
      }
    }
  };

  return (
    <TestCenterView
      copy={copy}
      loading={loading}
      busy={busy}
      error={error}
      status={status}
      runs={runs}
      selectedRunId={selectedRunId}
      selectedRunSummary={selectedRunSummary}
      selectedRun={selectedRun}
      artifacts={artifacts}
      selectedArtifactId={selectedArtifactId}
      artifactContent={artifactContent}
      onCreateRun={onCreateRun}
      onRefreshRuns={refreshRuns}
      onLauncherError={setError}
      onSelectRun={selectRun}
      onRefreshSelectedRun={() => void refreshSelectedRun(selectedRunId)}
      onCancelSelectedRun={() => void onCancelSelected()}
      onRefreshArtifacts={() => (selectedRunId ? void refreshSelectedRun(selectedRunId) : undefined)}
      onReadArtifact={(artifactId) => void onReadArtifact(artifactId)}
    />
  );
}
