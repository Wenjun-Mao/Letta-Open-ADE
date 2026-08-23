"use client";

import { useEffect, useEffectEvent, useMemo, useRef, useState } from "react";

import {
  AgentDetails,
  ChatResult,
  OptionEntry,
  PlatformToolTestInvokeResult,
  PromptPersonaRevisionRecord,
  PersistentState,
  PlatformTool,
  attachTool,
  archiveAgent,
  createAgent,
  fetchPromptPersonaRevisions,
  detachTool,
  fetchOptions,
  getAgentDetails,
  getPersistentState,
  getRawPrompt,
  listAgents,
  listTools,
  purgeAgent,
  restoreAgent,
  sendChat,
  testInvokeTool,
  updateAgentModel,
  updateCoreMemoryBlock,
  updateSystemPrompt,
  isAbortError,
} from "../../lib/api";
import { useI18n } from "../../lib/i18n";
import { isCurrentRequest, type RequestIdentity } from "../../lib/request-identity";
import {
  parseIntegerInRange,
  parseOptionalPositiveInteger,
  parseOptionalTemperature,
  parseOptionalTopP,
  parsePositiveNumber,
  samplingDefaultString,
} from "../../lib/generation-controls";
import {
  extractAssistantReply,
  parseToolExamples,
  stepMatchesFilter,
  toErrorMessage,
} from "./formatters";
import { AgentDetailsInspector, AgentSetupControls } from "./inspector";
import { ChatPanel, ExecutionTracePanel } from "./panels";
import {
  AGENT_CREATE_SCENARIO,
  AGENT_STUDIO_DEFAULT_RETRY_COUNT,
  AGENT_STUDIO_DEFAULT_TIMEOUT_SECONDS,
  TOOL_PROBE_DEFAULT_EN,
  TOOL_PROBE_DEFAULT_ZH,
  type AgentItem,
  type ChatEntry,
  type EditorKind,
  type InspectorTab,
  type PersistentTab,
  type TimelineFilter,
} from "./types";

export default function AgentStudioPage() {
  const { locale } = useI18n();
  const t = (en: string, zh: string) => (locale === "zh" ? zh : en);

  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const selectedAgentIdRef = useRef("");
  const selectedAgentVersionRef = useRef(0);
  const chatAbortControllerRef = useRef<AbortController | null>(null);
  const toolProbeAbortControllerRef = useRef<AbortController | null>(null);

  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [editorBusy, setEditorBusy] = useState(false);
  const [modelBusy, setModelBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [toolProbeBusy, setToolProbeBusy] = useState(false);
  const [rawPromptLoading, setRawPromptLoading] = useState(false);
  const [revisionLoading, setRevisionLoading] = useState(false);
  const [toolBusyId, setToolBusyId] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");

  const [models, setModels] = useState<OptionEntry[]>([]);
  const [embeddings, setEmbeddings] = useState<OptionEntry[]>([]);
  const [prompts, setPrompts] = useState<OptionEntry[]>([]);
  const [personas, setPersonas] = useState<OptionEntry[]>([]);

  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [includeArchivedAgents, setIncludeArchivedAgents] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("model");
  const [persistentTab, setPersistentTab] = useState<PersistentTab>("summary");
  const [timelineFilter, setTimelineFilter] = useState<TimelineFilter>("all");
  const [persistentLimit, setPersistentLimit] = useState(120);

  const [createName, setCreateName] = useState("ade-agent");
  const [createModel, setCreateModel] = useState("");
  const [createPromptKey, setCreatePromptKey] = useState("chat_v20260516");
  const [createPersonaKey, setCreatePersonaKey] = useState("chat_linxiaotang");
  const [createEmbedding, setCreateEmbedding] = useState("");
  const [createTemperature, setCreateTemperature] = useState("");
  const [createTopP, setCreateTopP] = useState("");
  const [createTopK, setCreateTopK] = useState("");
  const [modelEditValue, setModelEditValue] = useState("");

  const [chatInput, setChatInput] = useState("");
  const [runtimeTimeoutSeconds, setRuntimeTimeoutSeconds] = useState(AGENT_STUDIO_DEFAULT_TIMEOUT_SECONDS);
  const [runtimeRetryCount, setRuntimeRetryCount] = useState(AGENT_STUDIO_DEFAULT_RETRY_COUNT);
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([]);

  const [agentDetails, setAgentDetails] = useState<AgentDetails | null>(null);
  const [persistentState, setPersistentState] = useState<PersistentState | null>(null);
  const [lastResult, setLastResult] = useState<ChatResult | null>(null);
  const [lastLatencyMs, setLastLatencyMs] = useState<number | null>(null);

  const [showRawPrompt, setShowRawPrompt] = useState(false);
  const [rawPromptMessages, setRawPromptMessages] = useState<Array<{ role: string; content: string }>>([]);

  const [toolSearch, setToolSearch] = useState("");
  const [toolCatalog, setToolCatalog] = useState<PlatformTool[]>([]);
  const [toolDetailTool, setToolDetailTool] = useState<PlatformTool | null>(null);
  const [toolProbeInput, setToolProbeInput] = useState(() => (locale === "zh" ? TOOL_PROBE_DEFAULT_ZH : TOOL_PROBE_DEFAULT_EN));
  const [toolProbeExpected, setToolProbeExpected] = useState("");
  const [toolProbeResult, setToolProbeResult] = useState<PlatformToolTestInvokeResult | null>(null);
  const [revisionHistory, setRevisionHistory] = useState<PromptPersonaRevisionRecord[]>([]);

  const [editorKind, setEditorKind] = useState<EditorKind>(null);
  const [editorValue, setEditorValue] = useState("");

  const historyCount = Number(persistentState?.conversation_history?.total_persisted || 0);
  const memoryBlocks = persistentState?.memory_blocks || [];
  const persistentTools = persistentState?.tools;
  const humanBefore = String(lastResult?.memory_diff?.old?.human || "");
  const humanAfter = String(lastResult?.memory_diff?.new?.human || "");

  const selectedAgentName = useMemo(() => {
    const found = agents.find((item) => item.id === selectedAgentId);
    return found ? found.name : "";
  }, [agents, selectedAgentId]);

  const selectedAgentInfo = useMemo(() => {
    return agents.find((item) => item.id === selectedAgentId) || null;
  }, [agents, selectedAgentId]);
  const selectedAgentArchived = Boolean(selectedAgentInfo?.archived);

  const attachedToolIds = useMemo(() => {
    const ids = new Set<string>();
    for (const tool of persistentTools || []) {
      if (tool.id) {
        ids.add(tool.id);
      }
    }
    return ids;
  }, [persistentTools]);

  const displayToolCatalog = useMemo(() => {
    const normalized = toolCatalog.map((tool) => ({
      ...tool,
      attached_to_agent: tool.attached_to_agent ?? attachedToolIds.has(tool.id),
    }));

    normalized.sort((left, right) => {
      const leftAttached = Boolean(left.attached_to_agent);
      const rightAttached = Boolean(right.attached_to_agent);
      if (leftAttached !== rightAttached) {
        return leftAttached ? -1 : 1;
      }

      const byName = String(left.name || "").localeCompare(String(right.name || ""), undefined, {
        sensitivity: "base",
      });
      if (byName !== 0) {
        return byName;
      }

      return String(left.id || "").localeCompare(String(right.id || ""));
    });

    return normalized;
  }, [attachedToolIds, toolCatalog]);

  const filteredTimelineSteps = useMemo(() => {
    const sequence = lastResult?.sequence || [];
    return sequence.filter((step) => stepMatchesFilter(step.type, timelineFilter));
  }, [lastResult?.sequence, timelineFilter]);

  const openEditor = (kind: Exclude<EditorKind, null>, value: string) => {
    setEditorKind(kind);
    setEditorValue(value);
    setStatus("");
    setError("");
  };

  const closeEditor = () => {
    setEditorKind(null);
    setEditorValue("");
  };

  const hydrateChatFromPersistent = (payload: PersistentState) => {
    const items = payload.conversation_history?.items || [];
    const hydrated: ChatEntry[] = [];
    for (const item of items) {
      const messageType = String(item.message_type || "").toLowerCase();
      const content = String(item.content || "").replace(/\r\n/g, "\n").trim();
      if (!content) {
        continue;
      }
      if (messageType === "user_message") {
        hydrated.push({
          id: `${item.id}-u`,
          role: "user",
          content,
          timingMs: null,
        });
      }
      if (messageType === "assistant_message") {
        hydrated.push({
          id: `${item.id}-a`,
          role: "assistant",
          content,
          timingMs: null,
        });
      }
    }
    setChatHistory(hydrated);
  };

  const resetSelectedAgentState = () => {
    setAgentDetails(null);
    setPersistentState(null);
    setChatHistory([]);
    setLastResult(null);
    setLastLatencyMs(null);
    setRawPromptMessages([]);
    setToolCatalog([]);
    setToolProbeResult(null);
    setRevisionHistory([]);
    setModelEditValue("");
  };

  const currentAgentRequest = (agentId: string): RequestIdentity => ({
    resourceId: agentId,
    version: selectedAgentVersionRef.current,
  });

  const isCurrentAgentRequest = (identity: RequestIdentity): boolean =>
    isCurrentRequest(identity, selectedAgentIdRef.current, selectedAgentVersionRef.current);

  const selectAgent = (agentId: string) => {
    if (agentId !== selectedAgentIdRef.current) {
      selectedAgentIdRef.current = agentId;
      selectedAgentVersionRef.current += 1;
      chatAbortControllerRef.current?.abort();
      toolProbeAbortControllerRef.current?.abort();
      chatAbortControllerRef.current = null;
      toolProbeAbortControllerRef.current = null;
      setChatBusy(false);
      setToolProbeBusy(false);
      setRawPromptLoading(false);
      setRevisionLoading(false);
      resetSelectedAgentState();
    }
    setSelectedAgentId(agentId);
  };

  const refreshAgentList = async (includeArchived = includeArchivedAgents) => {
    const payload = await listAgents(200, false, includeArchived);
    const mapped = payload.items.map((item) => ({
      id: item.id,
      name: item.name || item.id,
      model: item.model || "",
      created_at: item.created_at || "",
      last_updated_at: item.last_updated_at || "",
      last_interaction_at: item.last_interaction_at || "",
      archived: Boolean(item.archived),
    }));
    setAgents(mapped);

    const hasSelected = mapped.some((item) => item.id === selectedAgentId);
    if (!selectedAgentId && mapped.length > 0) {
      selectAgent(mapped[0].id);
      return;
    }
    if (!hasSelected) {
      const nextAgentId = mapped[0]?.id || "";
      selectAgent(nextAgentId);
      if (!nextAgentId) {
        resetSelectedAgentState();
      }
    }
  };

  const refreshCreationOptions = async (forceRefresh = false) => {
    const optionsPayload = await fetchOptions(AGENT_CREATE_SCENARIO, forceRefresh ? { refresh: true } : undefined);

    const nextModels = optionsPayload.models || [];
    const nextEmbeddings = optionsPayload.embeddings || [];
    const nextPrompts = optionsPayload.prompts || [];
    const nextPersonas = optionsPayload.personas || [];

    setModels(nextModels);
    setEmbeddings(nextEmbeddings);
    setPrompts(nextPrompts);
    setPersonas(nextPersonas);

    setCreateModel((current) => (current && nextModels.some((item) => item.key === current) ? current : ""));
    setCreatePromptKey((current) => {
      if (current && nextPrompts.some((item) => item.key === current)) {
        return current;
      }
      return optionsPayload.defaults?.prompt_key || nextPrompts[0]?.key || "chat_v20260516";
    });
    setCreatePersonaKey((current) => {
      if (current && nextPersonas.some((item) => item.key === current)) {
        return current;
      }
      return optionsPayload.defaults?.persona_key || nextPersonas[0]?.key || "chat_linxiaotang";
    });
    setCreateEmbedding((current) => {
      if (current && nextEmbeddings.some((item) => item.key === current)) {
        return current;
      }
      return optionsPayload.defaults?.embedding || "";
    });
    setCreateTemperature((current) => current || String(optionsPayload.agent_studio?.temperature ?? ""));
    setCreateTopP((current) => current || String(optionsPayload.agent_studio?.top_p ?? ""));
    setCreateTopK((current) => current || String(optionsPayload.agent_studio?.top_k ?? ""));
  };

  const refreshToolCatalog = async (
    agentId: string,
    searchValue = toolSearch,
    identity = currentAgentRequest(agentId),
  ) => {
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

  const refreshRevisionHistory = async (agentId: string, identity = currentAgentRequest(agentId)) => {
    if (!agentId) {
      setRevisionHistory([]);
      return;
    }

    setRevisionLoading(true);
    try {
      const payload = await fetchPromptPersonaRevisions(agentId, "", 120);
      if (!isCurrentAgentRequest(identity)) {
        return;
      }
      setRevisionHistory(payload.items || []);
    } catch (exc) {
      if (isCurrentAgentRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      if (isCurrentAgentRequest(identity)) {
        setRevisionLoading(false);
      }
    }
  };

  const refreshSelectedAgent = async (
    agentId: string,
    hydrateChat = false,
    identity = currentAgentRequest(agentId),
  ) => {
    if (!agentId) {
      return;
    }

    const [details, persistent] = await Promise.all([
      getAgentDetails(agentId),
      getPersistentState(agentId, persistentLimit),
    ]);
    if (!isCurrentAgentRequest(identity)) {
      return false;
    }

    setAgentDetails(details);
    setPersistentState(persistent);
    setModelEditValue(String(details.model || ""));
    if (hydrateChat) {
      hydrateChatFromPersistent(persistent);
    }

    if (inspectorTab === "tools") {
      await refreshToolCatalog(agentId, toolSearch, identity);
    }
    return true;
  };

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
    } catch (exc) {
      if (isCurrentAgentRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      if (isCurrentAgentRequest(identity)) {
        setRawPromptLoading(false);
      }
    }
  };

  const selectAgentEffect = useEffectEvent(selectAgent);
  const refreshAgentListEffect = useEffectEvent(refreshAgentList);
  const refreshSelectedAgentEffect = useEffectEvent(refreshSelectedAgent);
  const refreshToolCatalogEffect = useEffectEvent(refreshToolCatalog);
  const refreshRevisionHistoryEffect = useEffectEvent(refreshRevisionHistory);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      setLoading(true);
      setError("");
      try {
        const [optionsPayload, agentsPayload] = await Promise.all([
          fetchOptions(AGENT_CREATE_SCENARIO),
          listAgents(200, false, false),
        ]);
        if (cancelled) {
          return;
        }

        setModels(optionsPayload.models || []);
        setEmbeddings(optionsPayload.embeddings || []);
        setPrompts(optionsPayload.prompts || []);
        setPersonas(optionsPayload.personas || []);

        const params = typeof window !== "undefined" ? new URLSearchParams(window.location.search) : null;
        const requestedPromptKey = (params?.get("promptKey") || "").trim();
        const requestedPersonaKey = (params?.get("personaKey") || "").trim();

        const promptKeys = (optionsPayload.prompts || []).map((item) => item.key);
        const personaKeys = (optionsPayload.personas || []).map((item) => item.key);

        const resolvedPromptKey =
          requestedPromptKey && promptKeys.includes(requestedPromptKey)
            ? requestedPromptKey
            : optionsPayload.defaults?.prompt_key || optionsPayload.prompts?.[0]?.key || "chat_v20260516";

        const resolvedPersonaKey =
          requestedPersonaKey && personaKeys.includes(requestedPersonaKey)
            ? requestedPersonaKey
            : optionsPayload.defaults?.persona_key || optionsPayload.personas?.[0]?.key || "chat_linxiaotang";

        setCreateModel("");
        setCreatePromptKey(resolvedPromptKey);
        setCreatePersonaKey(resolvedPersonaKey);
        setCreateEmbedding(optionsPayload.defaults?.embedding || "");

        const mapped = agentsPayload.items.map((item) => ({
          id: item.id,
          name: item.name || item.id,
          model: item.model || "",
          created_at: item.created_at || "",
          last_updated_at: item.last_updated_at || "",
          last_interaction_at: item.last_interaction_at || "",
          archived: Boolean(item.archived),
        }));
        setAgents(mapped);
        if (mapped.length > 0) {
          selectAgentEffect(mapped[0].id);
        }
      } catch (exc) {
        if (!cancelled) {
          setError(toErrorMessage(exc));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const localizedDefaultProbeInput = locale === "zh" ? TOOL_PROBE_DEFAULT_ZH : TOOL_PROBE_DEFAULT_EN;
    setToolProbeInput((current) => {
      if (!current.trim() || current === TOOL_PROBE_DEFAULT_EN || current === TOOL_PROBE_DEFAULT_ZH) {
        return localizedDefaultProbeInput;
      }
      return current;
    });
  }, [locale]);

  useEffect(() => {
    void refreshAgentListEffect(includeArchivedAgents);
  }, [includeArchivedAgents]);

  useEffect(() => {
    if (!selectedAgentId) {
      resetSelectedAgentState();
      return;
    }
    const identity = currentAgentRequest(selectedAgentId);
    const run = async () => {
      try {
        const refreshed = await refreshSelectedAgentEffect(selectedAgentId, false, identity);
        if (refreshed && isCurrentAgentRequest(identity)) {
          setRawPromptMessages([]);
        }
      } catch (exc) {
        if (isCurrentAgentRequest(identity) && !isAbortError(exc)) {
          setError(toErrorMessage(exc));
        }
      }
    };
    void run();
  }, [selectedAgentId]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    const params = new URLSearchParams(window.location.search);
    const focus = (params.get("focus") || "").trim().toLowerCase();
    if (focus === "prompt") {
      setInspectorTab("prompt");
    }
    if (focus === "tools") {
      setInspectorTab("tools");
    }
    if (focus === "model") {
      setInspectorTab("model");
    }
  }, []);

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
    const node = chatScrollRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [chatHistory]);

  useEffect(() => {
    const selected = models.find((item) => item.key === createModel);
    if (!selected) {
      return;
    }
    const nextTemperature = samplingDefaultString(selected, "agent_studio", "temperature");
    const nextTopP = samplingDefaultString(selected, "agent_studio", "top_p");
    const nextTopK = samplingDefaultString(selected, "agent_studio", "top_k");
    if (nextTemperature !== null) {
      setCreateTemperature(nextTemperature);
    }
    if (nextTopP !== null) {
      setCreateTopP(nextTopP);
    }
    setCreateTopK(nextTopK ?? "");
  }, [createModel, models]);

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
    return () => {
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [toolDetailTool]);

  const onCreateAgent = async () => {
    if (!createModel.trim()) {
      setError(t("Please select a model before creating an agent.", "创建智能体前请先选择模型。"));
      return;
    }
    const parsedTemperature = parseOptionalTemperature(createTemperature);
    if (parsedTemperature === null) {
      setError(t("Temperature must be between 0 and 2.", "Temperature 必须在 0 到 2 之间。"));
      return;
    }
    const parsedTopP = parseOptionalTopP(createTopP);
    if (parsedTopP === null) {
      setError(t("Top P must be greater than 0 and at most 1.", "Top P 必须大于 0 且不超过 1。"));
      return;
    }
    const parsedTopK = parseOptionalPositiveInteger(createTopK);
    if (parsedTopK === null) {
      setError(t("Top K must be a positive integer, or blank to use the model default.", "Top K 必须是正整数，或留空使用模型默认值。"));
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      const created = await createAgent({
        scenario: AGENT_CREATE_SCENARIO,
        name: createName.trim() || "ade-agent",
        model: createModel,
        prompt_key: createPromptKey,
        persona_key: createPersonaKey,
        embedding: createEmbedding.trim() || null,
        temperature: parsedTemperature,
        top_p: parsedTopP,
        top_k: parsedTopK,
      });

      await refreshAgentList(includeArchivedAgents);
      selectAgent(created.id);
      setChatHistory([]);
      setLastResult(null);
      setRawPromptMessages([]);
      setStatus(t(`Created agent ${created.name} (${created.id})`, `已创建智能体 ${created.name} (${created.id})`));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onReloadModels = async () => {
    setBusy(true);
    setError("");
    try {
      await refreshCreationOptions(true);
      setStatus(t("Model options reloaded from backend.", "模型选项已从后端重新加载。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onArchiveAgent = async () => {
    if (!selectedAgentId || selectedAgentArchived) {
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      await archiveAgent(selectedAgentId);
      await refreshAgentList(includeArchivedAgents);
      setStatus(t("Agent archived. Use Restore to make it active again.", "智能体已归档。可使用 Restore 恢复为活跃状态。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onRestoreAgent = async () => {
    if (!selectedAgentId || !selectedAgentArchived) {
      return;
    }

    setBusy(true);
    setError("");
    setStatus("");
    try {
      await restoreAgent(selectedAgentId);
      await refreshAgentList(includeArchivedAgents);
      setStatus(t("Agent restored and active again.", "智能体已恢复并重新激活。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onPurgeAgent = async () => {
    if (!selectedAgentId || !selectedAgentArchived) {
      return;
    }

    const confirmed = window.confirm(
      t(
        "This will permanently delete the archived agent and cannot be undone. Continue?",
        "这将永久删除已归档智能体且不可恢复。是否继续？",
      ),
    );
    if (!confirmed) {
      return;
    }

    const targetAgentId = selectedAgentId;
    setBusy(true);
    setError("");
    setStatus("");
    try {
      await purgeAgent(targetAgentId);
      selectAgent("");
      resetSelectedAgentState();
      await refreshAgentList(includeArchivedAgents);
      setStatus(t("Archived agent permanently deleted.", "已永久删除归档智能体。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onSendMessage = async () => {
    if (!selectedAgentId) {
      setError(t("Select an agent first.", "请先选择智能体。"));
      return;
    }
    if (selectedAgentArchived) {
      setError(t("Archived agents cannot run chat. Restore first.", "归档智能体不可对话，请先恢复。"));
      return;
    }
    const text = chatInput.trim();
    if (!text) {
      return;
    }
    const parsedTimeoutSeconds = parsePositiveNumber(runtimeTimeoutSeconds);
    if (parsedTimeoutSeconds === null) {
      setError(t("Timeout must be a positive number.", "超时时间必须是正数。"));
      return;
    }
    const parsedRetryCount = parseIntegerInRange(runtimeRetryCount, 0, 5);
    if (parsedRetryCount === null) {
      setError(t("Retry count must be an integer between 0 and 5.", "重试次数必须是 0 到 5 之间的整数。"));
      return;
    }

    const targetAgentId = selectedAgentId;
    const identity = currentAgentRequest(targetAgentId);
    const controller = new AbortController();
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = controller;
    setChatBusy(true);
    setError("");
    setStatus("");
    const startedAt = performance.now();
    setChatHistory((prev) => [
      ...prev,
      {
        id: `${Date.now()}-user`,
        role: "user",
        content: text,
        timingMs: null,
      },
    ]);
    setChatInput("");

    try {
      const result = await sendChat(targetAgentId, text, {
        timeout_seconds: parsedTimeoutSeconds,
        retry_count: parsedRetryCount,
        signal: controller.signal,
      });
      if (!isCurrentAgentRequest(identity) || chatAbortControllerRef.current !== controller) {
        return;
      }
      const assistant = extractAssistantReply(result);
      const elapsedMs = Math.max(0, performance.now() - startedAt);

      setChatHistory((prev) => [
        ...prev,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: assistant || t("(No assistant message returned)", "（未返回助手消息）"),
          timingMs: elapsedMs,
        },
      ]);
      setLastResult(result);
      setLastLatencyMs(elapsedMs);

      await refreshSelectedAgent(targetAgentId, false, identity);
    } catch (exc) {
      if (!isCurrentAgentRequest(identity) || isAbortError(exc)) {
        return;
      }
      const elapsedMs = Math.max(0, performance.now() - startedAt);
      setChatHistory((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          role: "assistant",
          content: t(`Error: ${toErrorMessage(exc)}`, `错误：${toErrorMessage(exc)}`),
          timingMs: elapsedMs,
        },
      ]);
      setError(toErrorMessage(exc));
    } finally {
      if (chatAbortControllerRef.current === controller) {
        chatAbortControllerRef.current = null;
        setChatBusy(false);
      }
    }
  };

  const onPullExistingInfo = async () => {
    if (!selectedAgentId) {
      setError(t("Select an existing agent first.", "请先选择现有智能体。"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      await refreshSelectedAgent(selectedAgentId, true);
      setStatus(t("Persistent conversation history hydrated into Studio chat.", "已将持久化对话历史载入工作台聊天区。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const onApplyModel = async () => {
    if (!selectedAgentId || !modelEditValue.trim()) {
      return;
    }
    if (selectedAgentArchived) {
      setError(t("Archived agents cannot be mutated. Restore first.", "归档智能体不可修改，请先恢复。"));
      return;
    }
    setModelBusy(true);
    setError("");
    try {
      await updateAgentModel(selectedAgentId, modelEditValue.trim());
      await refreshSelectedAgent(selectedAgentId, false);
      await refreshAgentList(includeArchivedAgents);
      setStatus(t("Agent model updated.", "智能体模型已更新。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setModelBusy(false);
    }
  };

  const onSaveEditor = async () => {
    if (!selectedAgentId || !editorKind) {
      return;
    }
    if (selectedAgentArchived) {
      setError(t("Archived agents cannot be mutated. Restore first.", "归档智能体不可修改，请先恢复。"));
      return;
    }
    const value = editorValue.trim();
    if (!value) {
      setError(t("Editor value cannot be empty.", "编辑内容不能为空。"));
      return;
    }

    setEditorBusy(true);
    setError("");
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
      await refreshSelectedAgent(selectedAgentId, false);
      if (inspectorTab === "prompt") {
        await refreshRevisionHistory(selectedAgentId);
      }
      closeEditor();
      const editorLabel =
        editorKind === "system"
          ? t("system", "system")
          : editorKind === "persona"
            ? t("persona", "persona")
            : t("human", "human");
      setStatus(t(`${editorLabel} updated successfully.`, `${editorLabel} 已更新。`));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setEditorBusy(false);
    }
  };

  const onToggleTool = async (tool: PlatformTool) => {
    if (!selectedAgentId) {
      return;
    }
    if (selectedAgentArchived) {
      setError(t("Archived agents cannot change tools. Restore first.", "归档智能体不可变更工具，请先恢复。"));
      return;
    }
    setToolBusyId(tool.id);
    setError("");
    try {
      const isAttached = Boolean(tool.attached_to_agent ?? attachedToolIds.has(tool.id));
      if (isAttached) {
        await detachTool(selectedAgentId, tool.id);
        setStatus(t(`Detached tool ${tool.name}`, `已卸载工具 ${tool.name}`));
      } else {
        await attachTool(selectedAgentId, tool.id);
        setStatus(t(`Attached tool ${tool.name}`, `已挂载工具 ${tool.name}`));
      }
      await refreshToolCatalog(selectedAgentId);
      await refreshSelectedAgent(selectedAgentId, false);
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setToolBusyId("");
    }
  };

  const onToggleRawPrompt = async () => {
    const next = !showRawPrompt;
    setShowRawPrompt(next);
    if (next && rawPromptMessages.length === 0) {
      await loadRawPrompt();
    }
  };

  const onRunToolProbe = async () => {
    if (!selectedAgentId) {
      setError(t("Select an agent first.", "请先选择智能体。"));
      return;
    }
    if (selectedAgentArchived) {
      setError(t("Archived agents cannot run tool probe. Restore first.", "归档智能体不可运行工具探测，请先恢复。"));
      return;
    }

    const input = toolProbeInput.trim();
    if (!input) {
      setError(t("Tool probe input cannot be empty.", "工具探测输入不能为空。"));
      return;
    }
    const parsedTimeoutSeconds = parsePositiveNumber(runtimeTimeoutSeconds);
    if (parsedTimeoutSeconds === null) {
      setError(t("Timeout must be a positive number.", "超时时间必须是正数。"));
      return;
    }
    const parsedRetryCount = parseIntegerInRange(runtimeRetryCount, 0, 5);
    if (parsedRetryCount === null) {
      setError(t("Retry count must be an integer between 0 and 5.", "重试次数必须是 0 到 5 之间的整数。"));
      return;
    }

    const targetAgentId = selectedAgentId;
    const identity = currentAgentRequest(targetAgentId);
    const controller = new AbortController();
    toolProbeAbortControllerRef.current?.abort();
    toolProbeAbortControllerRef.current = controller;
    setToolProbeBusy(true);
    setError("");
    setStatus("");

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
      setLastResult(payload.result || null);
      setStatus(
        t(
          `Tool probe completed: ${payload.tool_call_count} tool call(s), ${payload.tool_return_count} return(s).`,
          `工具探测完成：${payload.tool_call_count} 次工具调用，${payload.tool_return_count} 次工具返回。`,
        ),
      );
      await refreshSelectedAgent(targetAgentId, false, identity);
      if (inspectorTab === "prompt") {
        await refreshRevisionHistory(targetAgentId, identity);
      }
    } catch (exc) {
      if (isCurrentAgentRequest(identity) && !isAbortError(exc)) {
        setError(toErrorMessage(exc));
      }
    } finally {
      if (toolProbeAbortControllerRef.current === controller) {
        toolProbeAbortControllerRef.current = null;
        setToolProbeBusy(false);
      }
    }
  };

  const onRefreshPersistent = async () => {
    if (!selectedAgentId) {
      return;
    }
    setBusy(true);
    setError("");
    try {
      await refreshSelectedAgent(selectedAgentId, false);
      setStatus(t("Agent persistent state refreshed.", "智能体持久化状态已刷新。"));
    } catch (exc) {
      setError(toErrorMessage(exc));
    } finally {
      setBusy(false);
    }
  };

  const personaValue = memoryBlocks.find((block) => block.label === "persona")?.value || "";
  const humanValue = memoryBlocks.find((block) => block.label === "human")?.value || "";

  return (
    <section className="studio-root">
      <div className="kicker">{t("Merged Workspace", "合并工作区")}</div>
      <h1 className="section-title">{t("Agent Studio", "智能体工作台")}</h1>

      <div className="studio-layout">
        <aside className="card studio-panel">
          <h3>{t("Inspector", "检查面板")}</h3>

          <AgentSetupControls
            t={t}
            locale={locale}
            models={models}
            prompts={prompts}
            personas={personas}
            embeddings={embeddings}
            createName={createName}
            createModel={createModel}
            createPromptKey={createPromptKey}
            createPersonaKey={createPersonaKey}
            createEmbedding={createEmbedding}
            createTemperature={createTemperature}
            createTopP={createTopP}
            createTopK={createTopK}
            busy={busy}
            loading={loading}
            agents={agents}
            includeArchivedAgents={includeArchivedAgents}
            selectedAgentId={selectedAgentId}
            selectedAgentInfo={selectedAgentInfo}
            selectedAgentArchived={selectedAgentArchived}
            selectedAgentName={selectedAgentName}
            historyCount={historyCount}
            onCreateNameChange={setCreateName}
            onCreateModelChange={setCreateModel}
            onCreatePromptKeyChange={setCreatePromptKey}
            onCreatePersonaKeyChange={setCreatePersonaKey}
            onCreateEmbeddingChange={setCreateEmbedding}
            onCreateTemperatureChange={setCreateTemperature}
            onCreateTopPChange={setCreateTopP}
            onCreateTopKChange={setCreateTopK}
            onCreateAgent={onCreateAgent}
            onRefreshAgents={() => refreshAgentList()}
            onReloadModels={onReloadModels}
            onIncludeArchivedAgentsChange={setIncludeArchivedAgents}
            onSelectAgent={selectAgent}
            onPullExistingInfo={onPullExistingInfo}
            onRefreshPersistent={onRefreshPersistent}
            onArchiveAgent={onArchiveAgent}
            onRestoreAgent={onRestoreAgent}
            onPurgeAgent={onPurgeAgent}
          />

          <AgentDetailsInspector
            t={t}
            locale={locale}
            models={models}
            agentDetails={agentDetails}
            inspectorTab={inspectorTab}
            selectedAgentId={selectedAgentId}
            selectedAgentArchived={selectedAgentArchived}
            modelEditValue={modelEditValue}
            modelBusy={modelBusy}
            personaValue={personaValue}
            humanValue={humanValue}
            revisionLoading={revisionLoading}
            revisionHistory={revisionHistory}
            toolSearch={toolSearch}
            tools={displayToolCatalog}
            toolBusyId={toolBusyId}
            toolProbeInput={toolProbeInput}
            toolProbeExpected={toolProbeExpected}
            toolProbeBusy={toolProbeBusy}
            toolProbeResult={toolProbeResult}
            onInspectorTabChange={setInspectorTab}
            onModelEditValueChange={setModelEditValue}
            onApplyModel={onApplyModel}
            onOpenEditor={openEditor}
            onRefreshRevisionHistory={() => refreshRevisionHistory(selectedAgentId)}
            onToolSearchChange={setToolSearch}
            onRefreshTools={() => refreshToolCatalog(selectedAgentId)}
            onToggleTool={onToggleTool}
            onViewToolDetails={setToolDetailTool}
            onToolProbeInputChange={setToolProbeInput}
            onToolProbeExpectedChange={setToolProbeExpected}
            onRunToolProbe={onRunToolProbe}
          />
        </aside>

        <ChatPanel
          t={t}
          chatScrollRef={chatScrollRef}
          chatHistory={chatHistory}
          timeoutSeconds={runtimeTimeoutSeconds}
          retryCount={runtimeRetryCount}
          chatInput={chatInput}
          chatBusy={chatBusy}
          toolProbeBusy={toolProbeBusy}
          selectedAgentId={selectedAgentId}
          selectedAgentArchived={selectedAgentArchived}
          onTimeoutChange={setRuntimeTimeoutSeconds}
          onRetryCountChange={setRuntimeRetryCount}
          onChatInputChange={setChatInput}
          onSendMessage={onSendMessage}
        />

        <ExecutionTracePanel
          t={t}
          locale={locale}
          lastLatencyMs={lastLatencyMs}
          timelineFilter={timelineFilter}
          timelineSteps={filteredTimelineSteps}
          hasLastResult={Boolean(lastResult)}
          humanBefore={humanBefore}
          humanAfter={humanAfter}
          showRawPrompt={showRawPrompt}
          rawPromptLoading={rawPromptLoading}
          rawPromptMessages={rawPromptMessages}
          selectedAgentId={selectedAgentId}
          selectedAgentArchived={selectedAgentArchived}
          busy={busy}
          persistentLimit={persistentLimit}
          persistentTab={persistentTab}
          persistentState={persistentState}
          onTimelineFilterChange={setTimelineFilter}
          onToggleRawPrompt={onToggleRawPrompt}
          onRefreshPersistent={onRefreshPersistent}
          onPersistentLimitChange={setPersistentLimit}
          onPersistentTabChange={setPersistentTab}
          onOpenEditor={openEditor}
        />
      </div>

      {editorKind ? (
        <div className="editor-overlay">
          <div className="editor-card">
            <h3 style={{ marginTop: 0 }}>{t("Edit", "编辑")} {editorKind}</h3>
            <textarea
              className="input"
              style={{ minHeight: 260, resize: "vertical" }}
              value={editorValue}
              onChange={(e) => setEditorValue(e.target.value)}
            />
            <div className="toolbar" style={{ marginTop: 10, justifyContent: "flex-end" }}>
              <button className="button muted" onClick={closeEditor} disabled={editorBusy}>
                {t("Cancel", "取消")}
              </button>
              <button className="button" onClick={() => void onSaveEditor()} disabled={editorBusy}>
                {editorBusy ? t("Saving...", "保存中...") : t("Save", "保存")}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {toolDetailTool ? (
        <div
          className="editor-overlay"
          onClick={() => setToolDetailTool(null)}
          role="dialog"
          aria-modal="true"
          aria-label={t(`Tool details: ${toolDetailTool.name}`, `工具详情：${toolDetailTool.name}`)}
        >
          <div className="editor-card tool-detail-card" onClick={(event) => event.stopPropagation()}>
            <div className="tool-detail-header">
              <div>
                <h3 style={{ margin: 0 }}>{toolDetailTool.name}</h3>
                <div className="tool-detail-meta">
                  <span className="tool-detail-badge">{toolDetailTool.attached_to_agent ? t("Attached", "已挂载") : t("Not Attached", "未挂载")}</span>
                  <span className="tool-detail-badge">{t("Type", "类型")}: {toolDetailTool.tool_type || t("unknown", "未知")}</span>
                  <span className="tool-detail-badge">{t("Source", "来源")}: {toolDetailTool.source_type || t("unknown", "未知")}</span>
                </div>
              </div>
              <button className="button muted" onClick={() => setToolDetailTool(null)}>
                {t("Close (Esc)", "关闭（Esc）")}
              </button>
            </div>

            {(() => {
              const parsed = parseToolExamples(
                toolDetailTool.description || "",
                t("No description.", "暂无描述。"),
                t("No overview provided.", "未提供概述。"),
              );
              return (
                <>
                  <p className="tool-detail-overview">{parsed.overview}</p>
                  {parsed.examples.length > 0 ? (
                    <>
                      <div className="tool-detail-section-title">{t("Examples", "示例")}</div>
                      {parsed.examples.map((example, idx) => (
                        <pre className="code tool-detail-code" key={`${toolDetailTool.id}-example-${idx}`}>
                          {example}
                        </pre>
                      ))}
                    </>
                  ) : (
                    <>
                      <div className="tool-detail-section-title">{t("Full Description", "完整说明")}</div>
                      <pre className="code tool-detail-code">{toolDetailTool.description || t("No description.", "暂无描述。")}</pre>
                    </>
                  )}
                </>
              );
            })()}
          </div>
        </div>
      ) : null}

      {status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <h3>{t("Status", "状态")}</h3>
          <p className="muted">{status}</p>
        </div>
      ) : null}

      {error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <h3>{t("Error", "错误")}</h3>
          <p className="muted">{error}</p>
        </div>
      ) : null}
    </section>
  );
}
