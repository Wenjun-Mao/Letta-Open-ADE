"use client";

import { useEffect, useMemo, useState } from "react";

import type { ChatResult } from "../../lib/api";
import { stepMatchesFilter } from "./formatters";
import type { TimelineFilter } from "./types";

type UseExecutionTraceArgs = {
  registerSelectionCleanup: (cleanup: () => void) => () => void;
};

export function useExecutionTrace({ registerSelectionCleanup }: UseExecutionTraceArgs) {
  const [lastResult, setLastResult] = useState<ChatResult | null>(null);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>("all");

  const reset = () => {
    setLastResult(null);
    setLastLatencyMs(null);
  };

  useEffect(() => registerSelectionCleanup(reset), [registerSelectionCleanup]);

  const filteredTimelineSteps = useMemo(
    () => (lastResult?.sequence || []).filter((step) => stepMatchesFilter(step.type, timelineFilter)),
    [lastResult?.sequence, timelineFilter],
  );

  return {
    lastResult,
    lastLatencyMs,
    timelineFilter,
    filteredTimelineSteps,
    setTimelineFilter,
    recordResult: (result: ChatResult, latencyMs?: number) => {
      setLastResult(result);
      if (latencyMs !== undefined) {
        setLastLatencyMs(latencyMs);
      }
    },
  };
}
