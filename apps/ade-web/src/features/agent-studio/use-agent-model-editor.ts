"use client";

import { useEffect, useState } from "react";

import { updateAgentModel, type AgentDetails } from "./api";
import { toErrorMessage } from "./formatters";
import type { Translate } from "./types";
import type { StudioNotices } from "./use-studio-notices";

type UseAgentModelEditorArgs = {
  t: Translate;
  notices: StudioNotices;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  agentDetails: AgentDetails | null;
  refreshSelectedAgent: (agentId: string) => Promise<unknown>;
  refreshAgentList: () => Promise<void>;
};

export function useAgentModelEditor({
  t,
  notices,
  selectedAgentId,
  selectedAgentArchived,
  agentDetails,
  refreshSelectedAgent,
  refreshAgentList,
}: UseAgentModelEditorArgs) {
  const [modelEditValue, setModelEditValue] = useState("");
  const [modelBusy, setModelBusy] = useState(false);

  useEffect(() => {
    setModelEditValue(String(agentDetails?.model || ""));
  }, [agentDetails?.id, agentDetails?.model]);

  const reset = () => {
    setModelEditValue("");
  };

  const applyModel = async () => {
    if (!selectedAgentId || !modelEditValue.trim()) {
      return;
    }
    if (selectedAgentArchived) {
      notices.setError(t("Archived agents cannot be mutated. Restore first.", "归档智能体不可修改，请先恢复。"));
      return;
    }
    setModelBusy(true);
    notices.clearError();
    try {
      await updateAgentModel(selectedAgentId, modelEditValue.trim());
      await refreshSelectedAgent(selectedAgentId);
      await refreshAgentList();
      notices.setStatus(t("Agent model updated.", "智能体模型已更新。"));
    } catch (error) {
      notices.setError(toErrorMessage(error));
    } finally {
      setModelBusy(false);
    }
  };

  return {
    modelEditValue,
    modelBusy,
    setModelEditValue,
    reset,
    applyModel,
  };
}
