"use client";

import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import {
  type ChatMemoryEvaluationConfig,
  type CreateTestRunPayload,
  type EvaluationDecisionOutcome,
  type TestArtifact,
  type TestRunRecord,
  cancelTestRun,
  createTestRun,
  getTestRun,
  listRunArtifacts,
  listTestRuns,
  readRunArtifact,
  recordChatMemoryEvaluationDecision,
} from "./api";
import { isAbortError } from "@/shared/api/client";
import { useI18n } from "@/shared/i18n";
import { isCurrentRequest, type RequestIdentity } from "@/shared/request-identity";
import { getTestCenterCopy } from "./test-center-copy";
import { TestCenterView } from "./test-center-view";
import {
  isEvaluationRunning,
  toChatMemoryEvaluationForm,
  type ChatMemoryEvaluationForm,
} from "./chat-memory-evaluation-helpers";
import { useChatMemoryEvaluations } from "./use-chat-memory-evaluations";
import { useAgentRuntimeParityEvaluations } from "./use-agent-runtime-parity-evaluations";

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

  const [runs, setRuns] = useState<TestRunRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState("");
  const [selectedRun, setSelectedRun] = useState<TestRunRecord | null>(null);
  const selectedRunIdRef = useRef("");
  const selectedRunVersionRef = useRef(0);
  const selectedRunAbortControllerRef = useRef<AbortController | null>(null);
  const artifactAbortControllerRef = useRef<AbortController | null>(null);

  const [artifacts, setArtifacts] = useState<TestArtifact[]>([]);
  const [selectedArtifactId, setSelectedArtifactId] = useState("");
  const [artifactContent, setArtifactContent] = useState("");
  const [launcherPreset, setLauncherPreset] = useState<ChatMemoryEvaluationForm | null>(null);
  const evaluations = useChatMemoryEvaluations();
  const parityEvaluations = useAgentRuntimeParityEvaluations();
  const selectedParityEvaluationId = parityEvaluations.selectedId;
  const selectedParityEvaluationSummary = parityEvaluations.selectedSummary;
  const selectedParityRunId = selectedParityEvaluationSummary?.run_id || "";
  const selectedParityReady = Boolean(selectedParityEvaluationSummary?.ready);
  const selectedParityEvidenceSha256 = selectedParityEvaluationSummary?.artifact_digests?.evidence_sha256 || "";

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
  const refreshEvaluationsEffect = useEffectEvent(evaluations.refreshEvaluations);
  const refreshSelectedEvaluationEffect = useEffectEvent(evaluations.refreshSelectedEvaluation);
  const refreshComparisonEffect = useEffectEvent(evaluations.refreshComparison);
  const refreshParityEvaluationsEffect = useEffectEvent(parityEvaluations.refresh);
  const refreshSelectedParityEvaluationEffect = useEffectEvent(parityEvaluations.refreshSelected);
  const loadSelectedParityEvaluationEffect = useEffectEvent((runId: string) => {
    const identity = parityEvaluations.currentRequest(runId);
    void refreshSelectedParityEvaluationEffect(runId, identity).catch((exc) => {
      if (parityEvaluations.isCurrent(identity) && !isAbortError(exc)) setError(toErrorMessage(exc));
    });
  });
  const loadSelectedEvaluationEffect = useEffectEvent((runId: string, ready: boolean) => {
    if (!ready || !runId) {
      return;
    }
    const identity = evaluations.currentEvaluationRequest(runId);
    void refreshSelectedEvaluationEffect(runId, identity).catch((exc) => {
      if (evaluations.isCurrentEvaluationRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    });
  });

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setError("");
      try {
        await Promise.all([
          refreshRunsEffect(),
          refreshEvaluationsEffect(),
          refreshParityEvaluationsEffect(),
        ]);
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
      if (evaluations.items.some(isEvaluationRunning)) {
        void refreshEvaluationsEffect().catch(() => undefined);
      }
      if (parityEvaluations.items.some((item) => ["queued", "running"].includes(item.run_status))) {
        void refreshParityEvaluationsEffect().catch(() => undefined);
      }
      const selectedEvaluation = evaluations.selectedEvaluationSummary;
      if (selectedEvaluation?.ready && isEvaluationRunning(selectedEvaluation)) {
        loadSelectedEvaluationEffect(selectedEvaluation.run_id, true);
      }
    }, 4000);
    return () => clearInterval(timer);
  }, [evaluations.items, evaluations.selectedEvaluationSummary, parityEvaluations.items, selectedRunId]);

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

  useEffect(() => {
    if (!selectedParityReady || !selectedParityRunId) return;
    loadSelectedParityEvaluationEffect(selectedParityRunId);
  }, [
    selectedParityEvaluationId,
    selectedParityRunId,
    selectedParityReady,
    selectedParityEvidenceSha256,
  ]);

  useEffect(() => {
    if (selectedParityEvaluationId && selectedParityEvaluationId !== selectedRunIdRef.current) {
      selectRun(selectedParityEvaluationId);
    }
  }, [selectedParityEvaluationId]);

  useEffect(() => {
    loadSelectedEvaluationEffect(
      evaluations.selectedEvaluationId,
      Boolean(evaluations.selectedEvaluationSummary?.ready),
    );
  }, [
    evaluations.selectedEvaluationId,
    evaluations.selectedEvaluationSummary?.ready,
    evaluations.selectedEvaluationSummary?.run_status,
  ]);

  useEffect(() => {
    const candidate = evaluations.selectedEvaluationSummary;
    if (
      !candidate?.ready
      || !candidate.provenance
      || !evaluations.baselineRunId
      || evaluations.baselineRunId === candidate.run_id
    ) {
      void refreshComparisonEffect("", "");
      return;
    }
    void refreshComparisonEffect(evaluations.baselineRunId, candidate.run_id).catch((exc) => {
      if (!isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    });
  }, [
    evaluations.baselineRunId,
    evaluations.selectedEvaluationSummary,
    evaluations.selectedEvaluationSummary?.provenance?.provenance_sha256,
    evaluations.selectedEvaluationSummary?.ready,
    evaluations.selectedEvaluationSummary?.run_id,
  ]);

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
      if (payload.run_type === "chat_memory_eval") {
        const evaluationItems = await evaluations.refreshEvaluations();
        if (evaluationItems.some((item) => item.run_id === created.run_id)) {
          evaluations.selectEvaluation(created.run_id);
        }
      } else if (payload.run_type === "agent_runtime_parity_eval") {
        await parityEvaluations.refresh();
        parityEvaluations.select(created.run_id);
      }
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

  const onRerunEvaluationSetup = (config: ChatMemoryEvaluationConfig) => {
    setLauncherPreset(toChatMemoryEvaluationForm(config));
    setStatus(copy.rerunPrepared);
    setError("");
  };

  const onRecordEvaluationDecision = async (
    outcome: EvaluationDecisionOutcome,
    note: string,
  ) => {
    const evaluation = evaluations.selectedEvaluation;
    const provenance = evaluation?.provenance;
    if (!evaluation || !provenance || !evaluation.evidence_sha256) {
      setError(copy.decisionNeedsProvenance);
      return;
    }
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const selectedBaseline = evaluations.items.find(
        (item) => item.run_id === evaluations.baselineRunId,
      );
      const baselineProvenanceSha256 =
        selectedBaseline?.provenance?.provenance_sha256;
      const baselineEvidenceSha256 = selectedBaseline?.evidence_sha256;
      const baselineRunId = (
        selectedBaseline
        && baselineProvenanceSha256
        && baselineEvidenceSha256
        && selectedBaseline.run_id !== evaluation.run_id
          ? selectedBaseline.run_id
          : undefined
      );
      await recordChatMemoryEvaluationDecision(evaluation.run_id, {
        outcome,
        expected_provenance_sha256: provenance.provenance_sha256,
        expected_evidence_sha256: evaluation.evidence_sha256,
        baseline_run_id: baselineRunId,
        expected_baseline_provenance_sha256: baselineRunId
          ? baselineProvenanceSha256 ?? undefined
          : undefined,
        expected_baseline_evidence_sha256: baselineRunId
          ? baselineEvidenceSha256 ?? undefined
          : undefined,
        note,
      });
      setStatus(copy.decisionRecorded);
      await evaluations.refreshEvaluations();
      if (outcome === "promote") {
        evaluations.selectBaseline(evaluation.run_id);
      }
      await evaluations.refreshSelectedEvaluation(evaluation.run_id);
      await evaluations.refreshComparison(
        outcome === "promote" ? evaluation.run_id : evaluations.baselineRunId,
        evaluation.run_id,
      );
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
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
      evaluationItems={evaluations.items}
      selectedEvaluationId={evaluations.selectedEvaluationId}
      selectedEvaluationSummary={evaluations.selectedEvaluationSummary}
      selectedEvaluation={evaluations.selectedEvaluation}
      evaluationBaselineRunId={evaluations.baselineRunId}
      evaluationComparison={evaluations.comparison}
      parityEvaluationItems={parityEvaluations.items}
      selectedParityEvaluationId={parityEvaluations.selectedId}
      selectedParityEvaluationSummary={parityEvaluations.selectedSummary}
      selectedParityEvaluation={parityEvaluations.selected}
      launcherPreset={launcherPreset}
      onCreateRun={onCreateRun}
      onRefreshRuns={refreshRuns}
      onLauncherError={setError}
      onSelectRun={selectRun}
      onRefreshSelectedRun={() => void refreshSelectedRun(selectedRunId)}
      onCancelSelectedRun={() => void onCancelSelected()}
      onRefreshArtifacts={() => (selectedRunId ? void refreshSelectedRun(selectedRunId) : undefined)}
      onReadArtifact={(artifactId) => void onReadArtifact(artifactId)}
      onSelectEvaluation={(runId) => {
        evaluations.selectEvaluation(runId);
        if (runs.some((run) => run.run_id === runId)) {
          selectRun(runId);
        }
      }}
      onSelectEvaluationBaseline={evaluations.selectBaseline}
      onRecordEvaluationDecision={(outcome, note) => void onRecordEvaluationDecision(outcome, note)}
      onRefreshEvaluations={() => void evaluations.refreshEvaluations().catch((exc) => setError(toErrorMessage(exc)))}
      onRerunEvaluationSetup={onRerunEvaluationSetup}
      onSelectParityEvaluation={(runId) => {
        parityEvaluations.select(runId);
        if (runId) selectRun(runId);
      }}
      onRefreshParityEvaluation={() => {
        void parityEvaluations.refresh().then(() => {
          const runId = parityEvaluations.selectedId;
          if (!runId) return;
          return parityEvaluations.refreshSelected(runId);
        }).catch((exc) => setError(toErrorMessage(exc)));
      }}
    />
  );
}
