"use client";

import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import {
  attachTool,
  detachTool,
  fetchPromptPersonaRevisions,
  getRawPrompt,
  isAbortError,
  listTools,
  testInvokeTool,
  updateAgentModel,
  updateCoreMemoryBlock,
  updateSystemPrompt,
  type AgentDetails,
  type ChatResult,
  type OptionEntry,
  type PersistentState,
  type PlatformTool,
  type PlatformToolTestInvokeResult,
  type PromptPersonaRevisionRecord,
} from "../../lib/api";
import { parseIntegerInRange, parsePositiveNumber } from "../../lib/generation-controls";
import type { RequestIdentity } from "../../lib/request-identity";
import { buildDisplayToolCatalog, isToolAttached } from "./tool-catalog";
import {
  TOOL_PROBE_DEFAULT_EN,
  TOOL_PROBE_DEFAULT_ZH,
  type EditorKind,
  type InspectorTab,
  type PersistentTab,
  type Translate,
} from "./types";
import { toErrorMessage } from "./formatters";

type InspectionNotices = {
  clear: () => void;
  clearError: () => void;
  setError: (error: string) => void;
  setStatus: (status: string) => void;
};

type UseAgentInspectionArgs = {
  locale: "en" | "zh";
  t: Translate;
  notices: InspectionNotices;
  models: OptionEntry[];
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
  models,
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
  const toolProbeAbortControllerRef = useRef<AbortController | null>(null);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("model");
  const [persistentTab, setPersistentTab] = useState<PersistentTab>("summary");
  const [modelEditValue, setModelEditValue] = useState("");
  const [modelBusy, setModelBusy] = useState(false);
  const [showRawPrompt, setShowRawPrompt] = useState(false);
  const [rawPromptLoading, setRawPromptLoading] = useState(false);
  const [rawPromptMessages, setRawPromptMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [revisionLoading, setRevisionLoading] = useState(false);
  const [revisionHistory, setRevisionHistory] = useState<PromptPersonaRevisionRecord[]>([]);
  const [toolSearch, setToolSearch] = useState("");
  const [toolCatalog, setToolCatalog] = useState<PlatformTool[]>([]);
  const [toolBusyId, setToolBusyId] = useState("");
  const [toolDetailTool, setToolDetailTool] = useState<PlatformTool | null>(null);
  const [toolProbeInput, setToolProbeInput] = useState(() => (
    locale === "zh" ? TOOL_PROBE_DEFAULT_ZH : TOOL_PROBE_DEFAULT_EN
  ));
  const [toolProbeExpected, setToolProbeExpected] = useState("");
  const [toolProbeBusy, setToolProbeBusy] = useState(false);
  const [toolProbeResult, setToolProbeResult] = useState<PlatformToolTestInvokeResult | null>(null);
  const [editorKind, setEditorKind] = useState<EditorKind>(null);
  const [editorValue, setEditorValue] = useState("");
  const [editorBusy, setEditorBusy] = useState(false);

  const reset = () => {
    toolProbeAbortControllerRef.current?.abort();
    toolProbeAbortControllerRef.current = null;
    setToolProbeBusy(false);
    setRawPromptLoading(false);
    setRevisionLoading(false);
    setModelEditValue("");
    setRawPromptMessages([]);
    setRevisionHistory([]);
    setToolCatalog([]);
    setToolProbeResult(null);
  };

  useEffect(() => {
    const unregister = registerSelectionCleanup(reset);
    return () => {
      unregister();
      toolProbeAbortControllerRef.current?.abort();
    };
  }, [registerSelectionCleanup]);

  useEffect(() => {
    setModelEditValue(String(agentDetails?.model || ""));
  }, [agentDetails?.id, agentDetails?.model]);

  useEffect(() => {
    const localizedDefault = locale === "zh" ? TOOL_PROBE_DEFAULT_ZH : TOOL_PROBE_DEFAULT_EN;
    setToolProbeInput((current) => (
      !current.trim() || current === TOOL_PROBE_DEFAULT_EN || current === TOOL_PROBE_DEFAULT_ZH
        ? localizedDefault
        : current
    ));
  }, [locale]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const focus = (new URLSearchParams(window.location.search).get("focus") || "").trim().toLowerCase();
    if (focus === "prompt" || focus === "tools" || focus === "model") {
      setInspectorTab(focus);
    }
  }, []);

  const refreshToolCatalog = async (
    agentId = selectedAgentId,
    searchValue = toolSearch,
    identity = currentAgentRequest(agentId),
  ): Promise<boolean | void> => {
    if (!agentId) {
      setToolCatalog([]);
      return;
    }
    const payload = await listTools(searchValue, 300, agentId);
    if (!isCurrentAgentRequest(identity)) {
      return false;
    }
    setToolCatalog(payload.items || []);
    return true;
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

  const refreshToolCatalogEffect = useEffectEvent(refreshToolCatalog);
  const refreshRevisionHistoryEffect = useEffectEvent(refreshRevisionHistory);

  useEffect(() => {
    if (!selectedAgentId) {
      return;
    }
    if (inspectorTab === "tools") {
      void refreshToolCatalogEffect(selectedAgentId);
    }
    if (inspectorTab === "prompt") {
      void refreshRevisionHistoryEffect(selectedAgentId);
    }
  }, [inspectorTab, selectedAgentId]);

  useEffect(() => {
    if (!toolDetailTool) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setToolDetailTool(null);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [toolDetailTool]);

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

  const toggleTool = async (tool: PlatformTool) => {
    if (!selectedAgentId) {
      return;
    }
    if (selectedAgentArchived) {
      notices.setError(t("Archived agents cannot change tools. Restore first.", "归档智能体不可变更工具，请先恢复。"));
      return;
    }
    setToolBusyId(tool.id);
    notices.clearError();
    try {
      if (isToolAttached(tool, persistentState)) {
        await detachTool(selectedAgentId, tool.id);
        notices.setStatus(t(`Detached tool ${tool.name}`, `已卸载工具 ${tool.name}`));
      } else {
        await attachTool(selectedAgentId, tool.id);
        notices.setStatus(t(`Attached tool ${tool.name}`, `已挂载工具 ${tool.name}`));
      }
      await refreshToolCatalog(selectedAgentId);
      await refreshSelectedAgent(selectedAgentId);
    } catch (error) {
      notices.setError(toErrorMessage(error));
    } finally {
      setToolBusyId("");
    }
  };

  const runToolProbe = async () => {
    if (!selectedAgentId) {
      notices.setError(t("Select an agent first.", "请先选择智能体。"));
      return;
    }
    if (selectedAgentArchived) {
      notices.setError(t("Archived agents cannot run tool probe. Restore first.", "归档智能体不可运行工具探测，请先恢复。"));
      return;
    }
    const input = toolProbeInput.trim();
    if (!input) {
      notices.setError(t("Tool probe input cannot be empty.", "工具探测输入不能为空。"));
      return;
    }
    const parsedTimeoutSeconds = parsePositiveNumber(timeoutSeconds);
    if (parsedTimeoutSeconds === null) {
      notices.setError(t("Timeout must be a positive number.", "超时时间必须是正数。"));
      return;
    }
    const parsedRetryCount = parseIntegerInRange(retryCount, 0, 5);
    if (parsedRetryCount === null) {
      notices.setError(t("Retry count must be an integer between 0 and 5.", "重试次数必须是 0 到 5 之间的整数。"));
      return;
    }

    const targetAgentId = selectedAgentId;
    const identity = currentAgentRequest(targetAgentId);
    const controller = new AbortController();
    toolProbeAbortControllerRef.current?.abort();
    toolProbeAbortControllerRef.current = controller;
    setToolProbeBusy(true);
    notices.clear();
    try {
      const payload = await testInvokeTool({
        agent_id: targetAgentId,
        input,
        expected_tool_name: toolProbeExpected.trim() || undefined,
        timeout_seconds: parsedTimeoutSeconds,
        retry_count: parsedRetryCount,
        signal: controller.signal,
      });
      if (!isCurrentAgentRequest(identity) || toolProbeAbortControllerRef.current !== controller) {
        return;
      }
      setToolProbeResult(payload);
      recordResult(payload.result);
      notices.setStatus(
        t(
          `Tool probe completed: ${payload.tool_call_count} tool call(s), ${payload.tool_return_count} return(s).`,
          `工具探测完成：${payload.tool_call_count} 次工具调用，${payload.tool_return_count} 次工具返回。`,
        ),
      );
      await refreshSelectedAgent(targetAgentId, false, identity);
      if (inspectorTab === "prompt") {
        await refreshRevisionHistory(targetAgentId, identity);
      }
    } catch (error) {
      if (isCurrentAgentRequest(identity) && !isAbortError(error)) {
        notices.setError(toErrorMessage(error));
      }
    } finally {
      if (toolProbeAbortControllerRef.current === controller) {
        toolProbeAbortControllerRef.current = null;
        setToolProbeBusy(false);
      }
    }
  };

  const displayToolCatalog = useMemo(
    () => buildDisplayToolCatalog(toolCatalog, persistentState),
    [persistentState, toolCatalog],
  );

  return {
    inspectorTab,
    persistentTab,
    modelEditValue,
    modelBusy,
    showRawPrompt,
    rawPromptLoading,
    rawPromptMessages,
    revisionLoading,
    revisionHistory,
    toolSearch,
    displayToolCatalog,
    toolBusyId,
    toolDetailTool,
    toolProbeInput,
    toolProbeExpected,
    toolProbeBusy,
    toolProbeResult,
    editorKind,
    editorValue,
    editorBusy,
    setInspectorTab,
    setPersistentTab,
    setModelEditValue,
    setToolSearch,
    setToolDetailTool,
    setToolProbeInput,
    setToolProbeExpected,
    setEditorValue,
    refreshToolCatalog,
    refreshRevisionHistory,
    toggleRawPrompt,
    openEditor,
    closeEditor,
    applyModel,
    saveEditor,
    toggleTool,
    runToolProbe,
  };
}
