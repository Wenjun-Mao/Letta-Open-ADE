"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { isAbortError } from "@/shared/api/client";
import { isCurrentRequest, type RequestIdentity } from "@/shared/request-identity";

import {
  getChatMemoryEvaluation,
  listChatMemoryEvaluations,
  type EvaluationDetail,
  type EvaluationListItem,
} from "./api";

export function useChatMemoryEvaluations() {
  const [items, setItems] = useState<EvaluationListItem[]>([]);
  const [selectedEvaluationId, setSelectedEvaluationId] = useState("");
  const [selectedEvaluation, setSelectedEvaluation] = useState<EvaluationDetail | null>(null);
  const selectedEvaluationIdRef = useRef("");
  const selectedEvaluationVersionRef = useRef(0);
  const selectedEvaluationAbortControllerRef = useRef<AbortController | null>(null);
  const listRequestInFlightRef = useRef(false);

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
    };
  }, []);

  return {
    items,
    selectedEvaluationId,
    selectedEvaluation,
    selectedEvaluationSummary,
    currentEvaluationRequest,
    isCurrentEvaluationRequest,
    selectEvaluation,
    refreshEvaluations,
    refreshSelectedEvaluation,
    isAbortError,
  };
}
