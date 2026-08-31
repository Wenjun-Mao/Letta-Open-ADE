"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { isAbortError } from "@/shared/api/client";
import { isCurrentRequest, type RequestIdentity } from "@/shared/request-identity";

import {
  compareChatMemoryEvaluations,
  getChatMemoryEvaluation,
  listChatMemoryEvaluations,
  type EvaluationComparison,
  type EvaluationDetail,
  type EvaluationListItem,
} from "./api";

export function useChatMemoryEvaluations() {
  const [items, setItems] = useState<EvaluationListItem[]>([]);
  const [selectedEvaluationId, setSelectedEvaluationId] = useState("");
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluationDetail | null>(null);
  const [baselineRunId, setBaselineRunId] = useState("");
  const [comparison, setComparison] = useState<EvaluationComparison | null>(null);
  const selectedEvaluationIdRef = useRef("");
  const selectedEvaluationVersionRef = useRef(0);
  const selectedEvaluationAbortControllerRef = useRef<AbortController | null>(null);
  const listRequestInFlightRef = useRef(false);
  const comparisonAbortControllerRef = useRef<AbortController | null>(null);

  const selectedEvaluationSummary = useMemo(
    () => items.find((item) => item.run_id === selectedEvaluationId) || null,
    [items, selectedEvaluationId],
  );

  const currentEvaluationRequest = (runId: string): RequestIdentity => ({
    resourceId: runId,
    version: selectedEvaluationVersionRef.current,
  });

  const isCurrentEvaluationRequest = (identity: RequestIdentity): boolean =>
    isCurrentRequest(identity, selectedEvaluationIdRef.current, selectedEvaluationVersionRef.current);

  const selectEvaluation = (runId: string) => {
    if (runId !== selectedEvaluationIdRef.current) {
      selectedEvaluationIdRef.current = runId;
      selectedEvaluationVersionRef.current += 1;
      selectedEvaluationAbortControllerRef.current?.abort();
      selectedEvaluationAbortControllerRef.current = null;
      setSelectedEvaluation(null);
    }
    setSelectedEvaluationId(runId);
  };

  const refreshEvaluations = async (): Promise<EvaluationListItem[]> => {
    if (listRequestInFlightRef.current) {
      return items;
    }
    listRequestInFlightRef.current = true;
    try {
      const payload = await listChatMemoryEvaluations();
      const nextItems = Array.isArray(payload.items) ? payload.items : [];
      setItems(nextItems);

      const readyBaselineIds = new Set(
        nextItems.filter((item) => item.ready && item.provenance).map((item) => item.run_id),
      );
      setBaselineRunId((current) => {
        if (current && readyBaselineIds.has(current)) {
          return current;
        }
        return nextItems.find((item) => item.preferred_baseline && item.ready && item.provenance)?.run_id
          || nextItems.find((item) => item.ready && item.provenance)?.run_id
          || "";
      });

      const currentId = selectedEvaluationIdRef.current;
      if (!currentId && nextItems.length > 0) {
        selectEvaluation(nextItems[0].run_id);
      } else if (currentId && !nextItems.some((item) => item.run_id === currentId)) {
        selectEvaluation(nextItems[0]?.run_id || "");
      }
      return nextItems;
    } finally {
      listRequestInFlightRef.current = false;
    }
  };

  const selectBaseline = (runId: string) => {
    comparisonAbortControllerRef.current?.abort();
    comparisonAbortControllerRef.current = null;
    setComparison(null);
    setBaselineRunId(runId);
  };

  const refreshComparison = async (
    baselineId: string,
    candidateId: string,
  ): Promise<boolean> => {
    if (!baselineId || !candidateId || baselineId === candidateId) {
      comparisonAbortControllerRef.current?.abort();
      comparisonAbortControllerRef.current = null;
      setComparison(null);
      return false;
    }
    const controller = new AbortController();
    comparisonAbortControllerRef.current?.abort();
    comparisonAbortControllerRef.current = controller;
    try {
      const nextComparison = await compareChatMemoryEvaluations(
        baselineId,
        candidateId,
        { signal: controller.signal },
      );
      if (comparisonAbortControllerRef.current !== controller) {
        return false;
      }
      setComparison(nextComparison);
      return true;
    } finally {
      if (comparisonAbortControllerRef.current === controller) {
        comparisonAbortControllerRef.current = null;
      }
    }
  };

  const refreshSelectedEvaluation = async (
    runId: string,
    identity = currentEvaluationRequest(runId),
  ): Promise<boolean> => {
    if (!runId) {
      return false;
    }
    const controller = new AbortController();
    selectedEvaluationAbortControllerRef.current?.abort();
    selectedEvaluationAbortControllerRef.current = controller;
    try {
      const evaluation = await getChatMemoryEvaluation(runId, { signal: controller.signal });
      if (!isCurrentEvaluationRequest(identity) || selectedEvaluationAbortControllerRef.current !== controller) {
        return false;
      }
      setSelectedEvaluation(evaluation);
      return true;
    } finally {
      if (selectedEvaluationAbortControllerRef.current === controller) {
        selectedEvaluationAbortControllerRef.current = null;
      }
    }
  };

  useEffect(() => {
    return () => {
      selectedEvaluationAbortControllerRef.current?.abort();
      comparisonAbortControllerRef.current?.abort();
    };
  }, []);

  return {
    items,
    selectedEvaluationId,
    selectedEvaluation,
    selectedEvaluationSummary,
    baselineRunId,
    comparison,
    currentEvaluationRequest,
    isCurrentEvaluationRequest,
    selectEvaluation,
    selectBaseline,
    refreshEvaluations,
    refreshSelectedEvaluation,
    refreshComparison,
    isAbortError,
  };
}
