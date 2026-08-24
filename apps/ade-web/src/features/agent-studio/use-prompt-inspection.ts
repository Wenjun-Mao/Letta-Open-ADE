"use client";

import { useEffect, useEffectEvent, useState } from "react";

import {
  getRawPrompt,
  updateCoreMemoryBlock,
  updateSystemPrompt,
} from "./api";
import { toErrorMessage } from "./formatters";
import type { EditorKind, InspectorTab, Translate } from "./types";
import type { StudioNotices } from "./use-studio-notices";
import { fetchPromptPersonaRevisions, type PromptPersonaRevisionRecord } from "@/features/prompt-center/api";
import { isAbortError } from "@/shared/api/client";
import type { RequestIdentity } from "@/shared/request-identity";

type UsePromptInspectionArgs = {
  t: Translate;
  notices: StudioNotices;
  inspectorTab: InspectorTab;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  currentAgentRequest: (agentId: string) => RequestIdentity;
  isCurrentAgentRequest: (identity: RequestIdentity) => boolean;
  refreshSelectedAgent: (agentId: string, hydrateChat?: boolean, identity?: RequestIdentity) => Promise<unknown>;
};

export function usePromptInspection({
  t,
  notices,
  inspectorTab,
  selectedAgentId,
  selectedAgentArchived,
  currentAgentRequest,
  isCurrentAgentRequest,
  refreshSelectedAgent,
}: UsePromptInspectionArgs) {
  const [showRawPrompt, setShowRawPrompt] = useState(false);
  const [rawPromptLoading, setRawPromptLoading] = useState(false);
  const [rawPromptMessages, setRawPromptMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [revisionLoading, setRevisionLoading] = useState(false);
  const [revisionHistory, setRevisionHistory] = useState<PromptPersonaRevisionRecord[]>([]);
  const [editorKind, setEditorKind] = useState<EditorKind>(null);
  const [editorValue, setEditorValue] = useState("");
  const [editorBusy, setEditorBusy] = useState(false);

  const reset = () => {
    setRawPromptLoading(false);
    setRevisionLoading(false);
    setRawPromptMessages([]);
    setRevisionHistory([]);
  };

  const refreshRevisionHistory = async (
    agentId = selectedAgentId,
    identity = currentAgentRequest(agentId),
  ) => {
    if (!agentId) {
      setRevisionHistory([]);
      return;
    }
    setRevisionLoading(true);
    try {
      const payload = await fetchPromptPersonaRevisions(agentId, "", 120);
      if (isCurrentAgentRequest(identity)) {
        setRevisionHistory(payload.items || []);
      }
    } catch (error) {
      if (isCurrentAgentRequest(identity) && !isAbortError(error)) {
        notices.setError(toErrorMessage(error));
      }
    } finally {
      if (isCurrentAgentRequest(identity)) {
        setRevisionLoading(false);
      }
    }
  };

  const refreshRevisionHistoryEffect = useEffectEvent(refreshRevisionHistory);

  useEffect(() => {
    if (inspectorTab === "prompt" && selectedAgentId) {
      void refreshRevisionHistoryEffect(selectedAgentId);
    }
  }, [inspectorTab, selectedAgentId]);

  const loadRawPrompt = async () => {
    if (!selectedAgentId) {
      return;
    }
    const identity = currentAgentRequest(selectedAgentId);
    setRawPromptLoading(true);
    try {
      const payload = await getRawPrompt(selectedAgentId);
      if (isCurrentAgentRequest(identity)) {
        setRawPromptMessages(Array.isArray(payload.messages) ? payload.messages : []);
      }
    } catch (error) {
      if (isCurrentAgentRequest(identity) && !isAbortError(error)) {
        notices.setError(toErrorMessage(error));
      }
    } finally {
      if (isCurrentAgentRequest(identity)) {
        setRawPromptLoading(false);
      }
    }
  };

  const toggleRawPrompt = async () => {
    const next = !showRawPrompt;
    setShowRawPrompt(next);
    if (next && rawPromptMessages.length === 0) {
      await loadRawPrompt();
    }
  };

  const openEditor = (kind: Exclude<EditorKind, null>, value: string) => {
    setEditorKind(kind);
    setEditorValue(value);
    notices.clear();
  };

  const closeEditor = () => {
    setEditorKind(null);
    setEditorValue("");
  };

  const saveEditor = async () => {
    if (!selectedAgentId || !editorKind) {
      return;
    }
    if (selectedAgentArchived) {
      notices.setError(t("Archived agents cannot be mutated. Restore first.", "归档智能体不可修改，请先恢复。"));
      return;
    }
    const value = editorValue.trim();
    if (!value) {
      notices.setError(t("Editor value cannot be empty.", "编辑内容不能为空。"));
      return;
    }

    setEditorBusy(true);
    notices.clearError();
    try {
      if (editorKind === "system") {
        await updateSystemPrompt(selectedAgentId, value);
      }
      if (editorKind === "persona") {
        await updateCoreMemoryBlock(selectedAgentId, "persona", value);
      }
      if (editorKind === "human") {
        await updateCoreMemoryBlock(selectedAgentId, "human", value);
      }
      await refreshSelectedAgent(selectedAgentId);
      if (inspectorTab === "prompt") {
        await refreshRevisionHistory(selectedAgentId);
      }
      closeEditor();
      const label = editorKind === "system" ? "system" : editorKind === "persona" ? "persona" : "human";
      notices.setStatus(t(`${label} updated successfully.`, `${label} 已更新。`));
    } catch (error) {
      notices.setError(toErrorMessage(error));
    } finally {
      setEditorBusy(false);
    }
  };

  return {
    showRawPrompt,
    rawPromptLoading,
    rawPromptMessages,
    revisionLoading,
    revisionHistory,
    editorKind,
    editorValue,
    editorBusy,
    setEditorValue,
    reset,
    refreshRevisionHistory,
    toggleRawPrompt,
    openEditor,
    closeEditor,
    saveEditor,
  };
}
