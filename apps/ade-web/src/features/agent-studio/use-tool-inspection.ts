"use client";

import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import {
  attachTool,
  detachTool,
  listRuntimeTools,
  testInvokeTool,
  type ChatResult,
  type PersistentState,
  type RuntimeTool,
  type ToolProbeResult,
} from "./api";
import { toErrorMessage } from "./formatters";
import { buildDisplayToolCatalog, isToolAttached } from "./tool-catalog";
import {
  TOOL_PROBE_DEFAULT_EN,
  TOOL_PROBE_DEFAULT_ZH,
  type InspectorTab,
  type Translate,
} from "./types";
import type { StudioNotices } from "./use-studio-notices";
import { isAbortError } from "@/shared/api/client";
import { parseIntegerInRange, parsePositiveNumber } from "@/shared/generation-controls";
import type { RequestIdentity } from "@/shared/request-identity";

type UseToolInspectionArgs = {
  locale: "en" | "zh";
  t: Translate;
  notices: StudioNotices;
  inspectorTab: InspectorTab;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  persistentState: PersistentState | null;
  timeoutSeconds: string;
  retryCount: string;
  currentAgentRequest: (agentId: string) => RequestIdentity;
  isCurrentAgentRequest: (identity: RequestIdentity) => boolean;
  refreshSelectedAgent: (agentId: string, hydrateChat?: boolean, identity?: RequestIdentity) => Promise<unknown>;
  recordResult: (result: ChatResult) => void;
  onProbeCompleted: (agentId: string, identity: RequestIdentity) => Promise<void>;
};

export function useToolInspection({
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
  onProbeCompleted,
}: UseToolInspectionArgs) {
  const toolProbeAbortControllerRef = useRef<AbortController | null>(null);
  const [toolSearch, setToolSearch] = useState("");
  const [toolCatalog, setToolCatalog] = useState<RuntimeTool[]>([]);
  const [toolBusyId, setToolBusyId] = useState("");
  const [toolDetailTool, setToolDetailTool] = useState<RuntimeTool | null>(null);
  const [toolProbeInput, setToolProbeInput] = useState(() => (
    locale === "zh" ? TOOL_PROBE_DEFAULT_ZH : TOOL_PROBE_DEFAULT_EN
  ));
  const [toolProbeExpected, setToolProbeExpected] = useState("");
  const [toolProbeBusy, setToolProbeBusy] = useState(false);
  const [toolProbeResult, setToolProbeResult] = useState<ToolProbeResult | null>(null);

  const reset = () => {
    toolProbeAbortControllerRef.current?.abort();
    toolProbeAbortControllerRef.current = null;
    setToolProbeBusy(false);
    setToolCatalog([]);
    setToolProbeResult(null);
  };

  const abortActiveProbe = () => {
    toolProbeAbortControllerRef.current?.abort();
  };

  useEffect(() => {
    const localizedDefault = locale === "zh" ? TOOL_PROBE_DEFAULT_ZH : TOOL_PROBE_DEFAULT_EN;
    setToolProbeInput((current) => (
      !current.trim() || current === TOOL_PROBE_DEFAULT_EN || current === TOOL_PROBE_DEFAULT_ZH
        ? localizedDefault
        : current
    ));
  }, [locale]);

  const refreshToolCatalog = async (
    agentId = selectedAgentId,
    searchValue = toolSearch,
    identity = currentAgentRequest(agentId),
  ): Promise<boolean | void> => {
    if (!agentId) {
      setToolCatalog([]);
      return;
    }
    const payload = await listRuntimeTools(searchValue, 300, agentId);
    if (!isCurrentAgentRequest(identity)) {
      return false;
    }
    setToolCatalog(payload.items || []);
    return true;
  };

  const refreshToolCatalogEffect = useEffectEvent(refreshToolCatalog);

  useEffect(() => {
    if (inspectorTab === "tools" && selectedAgentId) {
      void refreshToolCatalogEffect(selectedAgentId);
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

  const toggleTool = async (tool: RuntimeTool) => {
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
      await onProbeCompleted(targetAgentId, identity);
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
    toolSearch,
    displayToolCatalog,
    toolBusyId,
    toolDetailTool,
    toolProbeInput,
    toolProbeExpected,
    toolProbeBusy,
    toolProbeResult,
    setToolSearch,
    setToolDetailTool,
    setToolProbeInput,
    setToolProbeExpected,
    reset,
    abortActiveProbe,
    refreshToolCatalog,
    toggleTool,
    runToolProbe,
  };
}
