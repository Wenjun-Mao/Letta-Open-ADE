"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { isCurrentRequest, type RequestIdentity } from "@/shared/request-identity";

import {
  getAgentRuntimeParityEvaluation,
  listAgentRuntimeParityEvaluations,
  type AgentRuntimeParityDetail,
  type AgentRuntimeParityListItem,
} from "./api";

export function useAgentRuntimeParityEvaluations() {
  const [items, setItems] = useState<AgentRuntimeParityListItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [selected, setSelected] = useState<AgentRuntimeParityDetail | null>(null);
  const selectedIdRef = useRef("");
  const selectedVersionRef = useRef(0);
  const detailAbortControllerRef = useRef<AbortController | null>(null);
  const listRequestInFlightRef = useRef(false);

  const selectedSummary = useMemo(
    () => items.find((item) => item.run_id === selectedId) || null,
    [items, selectedId],
  );

  const currentRequest = (runId: string): RequestIdentity => ({
    resourceId: runId,
    version: selectedVersionRef.current,
  });

  const isCurrent = (identity: RequestIdentity): boolean =>
    isCurrentRequest(identity, selectedIdRef.current, selectedVersionRef.current);

  const select = (runId: string) => {
    if (runId !== selectedIdRef.current) {
      selectedIdRef.current = runId;
      selectedVersionRef.current += 1;
      detailAbortControllerRef.current?.abort();
      detailAbortControllerRef.current = null;
      setSelected(null);
    }
    setSelectedId(runId);
  };

  const refresh = async (): Promise<AgentRuntimeParityListItem[]> => {
    if (listRequestInFlightRef.current) return items;
    listRequestInFlightRef.current = true;
    try {
      const payload = await listAgentRuntimeParityEvaluations();
      const nextItems = Array.isArray(payload.items) ? payload.items : [];
      setItems(nextItems);
      const currentId = selectedIdRef.current;
      if (!currentId && nextItems.length) select(nextItems[0].run_id);
      else if (currentId && !nextItems.some((item) => item.run_id === currentId)) {
        select(nextItems[0]?.run_id || "");
      }
      return nextItems;
    } finally {
      listRequestInFlightRef.current = false;
    }
  };

  const refreshSelected = async (
    runId: string,
    identity = currentRequest(runId),
  ): Promise<boolean> => {
    if (!runId) return false;
    const controller = new AbortController();
    detailAbortControllerRef.current?.abort();
    detailAbortControllerRef.current = controller;
    try {
      const detail = await getAgentRuntimeParityEvaluation(runId, { signal: controller.signal });
      if (!isCurrent(identity) || detailAbortControllerRef.current !== controller) return false;
      setSelected(detail);
      return true;
    } finally {
      if (detailAbortControllerRef.current === controller) detailAbortControllerRef.current = null;
    }
  };

  useEffect(() => () => detailAbortControllerRef.current?.abort(), []);

  return {
    items,
    selectedId,
    selected,
    selectedSummary,
    currentRequest,
    isCurrent,
    select,
    refresh,
    refreshSelected,
  };
}
