"use client";

import { useEffect, useEffectEvent, useState } from "react";

import { useI18n } from "@/shared/i18n";
import {
  type CreateTestRunPayload,
  type TestCenterOptions,
  cancelTestRun,
  createTestRun,
  getTestCenterOptions,
} from "./api";
import { getTestCenterCopy } from "./test-center-copy";
import { TestCenterView, type TestCenterArea } from "./test-center-view";
import { useTestCenterRuns } from "./use-test-center-runs";

type SelectedRunIds = Record<TestCenterArea, string>;

const EMPTY_SELECTIONS: SelectedRunIds = {
  behavior: "",
  native: "",
  smoke: "",
};

function toErrorMessage(exc: unknown): string {
  return exc instanceof Error ? exc.message : String(exc);
}

function areaForRunType(runType: CreateTestRunPayload["run_type"]): TestCenterArea {
  switch (runType) {
    case "chat_memory_eval":
      return "behavior";
    case "agent_runtime_acceptance":
      return "native";
    case "ade_api_e2e_check":
      return "smoke";
  }
}

export default function TestCenterPage() {
  const { locale } = useI18n();
  const copy = getTestCenterCopy(locale);
  const [activeArea, setActiveArea] = useState<TestCenterArea>("behavior");
  const [selectedRunIds, setSelectedRunIds] = useState<SelectedRunIds>(EMPTY_SELECTIONS);
  const [options, setOptions] = useState<TestCenterOptions | null>(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const selectedRunId = selectedRunIds[activeArea];
  const testRuns = useTestCenterRuns(selectedRunId, setError);

  const loadOptions = async () => {
    setOptionsLoading(true);
    const payload = await getTestCenterOptions();
    setOptions(payload);
    setOptionsLoading(false);
  };
  const loadOptionsEffect = useEffectEvent(loadOptions);

  useEffect(() => {
    void loadOptionsEffect().catch((exc) => {
      setError(toErrorMessage(exc));
      setOptionsLoading(false);
    });
  }, []);

  const selectRun = (runId: string) => {
    setSelectedRunIds((current) => ({ ...current, [activeArea]: runId }));
  };

  const createRun = async (payload: CreateTestRunPayload) => {
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const created = await createTestRun(payload);
      const area = areaForRunType(payload.run_type);
      setSelectedRunIds((current) => ({ ...current, [area]: created.run_id }));
      setStatus(`${copy.createdRun} ${created.run_id}`);
      await testRuns.refreshRuns();
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const cancelSelectedRun = async () => {
    if (!selectedRunId) {
      return;
    }
    setBusy(true);
    setError("");
    setStatus("");
    try {
      const cancelled = await cancelTestRun(selectedRunId);
      setStatus(`${copy.cancelRequested} ${cancelled.run_id}`);
      await Promise.all([testRuns.refreshRuns(), testRuns.refreshSelectedRun()]);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  return (
    <TestCenterView
      activeArea={activeArea}
      artifactContent={testRuns.artifactContent}
      artifacts={testRuns.artifacts}
      busy={busy || testRuns.artifactLoading}
      copy={copy}
      error={error}
      onCancelSelectedRun={() => void cancelSelectedRun()}
      onCreateRun={(payload) => void createRun(payload)}
      onReadArtifact={(artifactId) => void testRuns.readArtifact(artifactId)}
      onRefreshArtifacts={() => void testRuns.refreshSelectedRun()}
      onRefreshRuns={() => void testRuns.refreshRuns()}
      onRefreshSelectedRun={() => void testRuns.refreshSelectedRun()}
      onSelectArea={setActiveArea}
      onSelectRun={selectRun}
      options={options}
      optionsLoading={optionsLoading}
      runs={testRuns.runs}
      selectedArtifactId={testRuns.selectedArtifactId}
      selectedRun={testRuns.selectedRun}
      selectedRunId={selectedRunId}
      selectedRunSummary={testRuns.selectedRunSummary}
      status={status}
    />
  );
}
