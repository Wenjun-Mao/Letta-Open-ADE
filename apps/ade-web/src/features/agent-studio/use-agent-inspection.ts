"use client";

import { useEffect, useEffectEvent, useState } from "react";

import type { AgentDetails, ChatResult, PersistentState } from "./api";
import { useAgentModelEditor } from "./use-agent-model-editor";
import { usePromptInspection } from "./use-prompt-inspection";
import type { StudioNotices } from "./use-studio-notices";
import { useToolInspection } from "./use-tool-inspection";
import type { InspectorTab, PersistentTab, Translate } from "./types";
import type { RequestIdentity } from "@/shared/request-identity";

type UseAgentInspectionArgs = {
  locale: "en" | "zh";
  t: Translate;
  notices: StudioNotices;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  agentDetails: AgentDetails | null;
  persistentState: PersistentState | null;
  timeoutSeconds: string;
  retryCount: string;
  currentAgentRequest: (agentId: string) => RequestIdentity;
  isCurrentAgentRequest: (identity: RequestIdentity) => boolean;
  refreshSelectedAgent: (agentId: string, hydrateChat?: boolean, identity?: RequestIdentity) => Promise<PersistentState | null>;
  refreshAgentList: () => Promise<void>;
  registerSelectionCleanup: (cleanup: () => void) => () => void;
  recordResult: (result: ChatResult) => void;
};

export function useAgentInspection({
  locale,
  t,
  notices,
  selectedAgentId,
  selectedAgentArchived,
  agentDetails,
  persistentState,
  timeoutSeconds,
  retryCount,
  currentAgentRequest,
  isCurrentAgentRequest,
  refreshSelectedAgent,
  refreshAgentList,
  registerSelectionCleanup,
  recordResult,
}: UseAgentInspectionArgs) {
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("model");
  const [persistentTab, setPersistentTab] = useState<PersistentTab>("summary");
  const modelEditor = useAgentModelEditor({
    t,
    notices,
    selectedAgentId,
    selectedAgentArchived,
    agentDetails,
    refreshSelectedAgent,
    refreshAgentList,
  });
  const promptInspection = usePromptInspection({
    t,
    notices,
    inspectorTab,
    selectedAgentId,
    selectedAgentArchived,
    currentAgentRequest,
    isCurrentAgentRequest,
    refreshSelectedAgent,
  });
  const refreshPromptRevisionsAfterProbe = async (agentId: string, identity: RequestIdentity) => {
    if (inspectorTab === "prompt") {
      await promptInspection.refreshRevisionHistory(agentId, identity);
    }
  };
  const toolInspection = useToolInspection({
    locale,
    t,
    notices,
    inspectorTab,
    selectedAgentId,
    selectedAgentArchived,
    persistentState,
    timeoutSeconds,
    retryCount,
    currentAgentRequest,
    isCurrentAgentRequest,
    refreshSelectedAgent,
    recordResult,
    onProbeCompleted: refreshPromptRevisionsAfterProbe,
  });

  const resetInspection = useEffectEvent(() => {
    modelEditor.reset();
    promptInspection.reset();
    toolInspection.reset();
  });
  const abortActiveToolProbe = useEffectEvent(toolInspection.abortActiveProbe);

  useEffect(() => {
    const unregister = registerSelectionCleanup(() => resetInspection());
    return () => {
      unregister();
      abortActiveToolProbe();
    };
  }, [registerSelectionCleanup]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const focus = (new URLSearchParams(window.location.search).get("focus") || "").trim().toLowerCase();
    if (focus === "prompt" || focus === "tools" || focus === "model") {
      setInspectorTab(focus);
    }
  }, []);

  return {
    inspectorTab,
    persistentTab,
    ...modelEditor,
    ...promptInspection,
    ...toolInspection,
    setInspectorTab,
    setPersistentTab,
  };
}
