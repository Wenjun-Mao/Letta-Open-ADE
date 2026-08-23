"use client";

import { useCallback, useEffect, useEffectEvent, useRef, useState } from "react";

import {
  archiveAgent,
  getAgentDetails,
  getPersistentState,
  isAbortError,
  listAgents,
  purgeAgent,
  restoreAgent,
  type AgentDetails,
  type PersistentState,
} from "../../lib/api";
import { isCurrentRequest, type RequestIdentity } from "../../lib/request-identity";
import { mapAgentListItems, resolveSelectedAgentId } from "./agent-list";
import type { AgentItem, Translate } from "./types";

type AgentLifecycleNotices = {
  clear: () => void;
  clearError: () => void;
  reportError: (error: unknown) => void;
  setError: (message: string) => void;
  setStatus: (status: string) => void;
};

type UseAgentLifecycleArgs = {
  t: Translate;
  notices: AgentLifecycleNotices;
};

export function useAgentLifecycle({ t, notices }: UseAgentLifecycleArgs) {
  const selectedAgentIdRef = useRef("");
  const selectedAgentVersionRef = useRef(0);
  const selectionCleanupsRef = useRef(new Set<() => void>());
  const chatHistoryHydratorRef = useRef<((persistentState: PersistentState) => void) | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [agents, setAgents] = useState<AgentItem[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [includeArchivedAgents, setIncludeArchivedAgents] = useState(false);
  const [persistentLimit, setPersistentLimit] = useState(120);
  const [agentDetails, setAgentDetails] = useState<AgentDetails | null>(null);
  const [persistentState, setPersistentState] = useState<PersistentState | null>(null);
  const clearInitialError = useEffectEvent(notices.clearError);
  const reportInitialError = useEffectEvent(notices.reportError);

  const resetSelectedAgentDetails = () => {
    setAgentDetails(null);
    setPersistentState(null);
  };

  // Consumers register abort/reset handlers in effects, so these functions must
  // remain stable across ordinary Studio rerenders.
  const registerSelectionCleanup = useCallback((cleanup: () => void) => {
    selectionCleanupsRef.current.add(cleanup);
    return () => {
      selectionCleanupsRef.current.delete(cleanup);
    };
  }, []);

  const registerChatHistoryHydrator = useCallback((hydrator: (persistentState: PersistentState) => void) => {
    chatHistoryHydratorRef.current = hydrator;
    return () => {
      if (chatHistoryHydratorRef.current === hydrator) {
        chatHistoryHydratorRef.current = null;
      }
    };
  }, []);

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
      for (const cleanup of selectionCleanupsRef.current) {
        cleanup();
      }
      resetSelectedAgentDetails();
    }
    setSelectedAgentId(agentId);
  };

  const refreshAgentList = async (includeArchived = includeArchivedAgents) => {
    const payload = await listAgents(200, false, includeArchived);
    const mapped = mapAgentListItems(payload.items);
    setAgents(mapped);
    const nextAgentId = resolveSelectedAgentId(mapped, selectedAgentIdRef.current);
    if (nextAgentId !== selectedAgentIdRef.current) {
      selectAgent(nextAgentId);
    }
  };

  const refreshSelectedAgent = async (
    agentId: string,
    hydrateChat = false,
    identity = currentAgentRequest(agentId),
  ): Promise<PersistentState | null> => {
    if (!agentId) {
      return null;
    }
    const [details, persistent] = await Promise.all([
      getAgentDetails(agentId),
      getPersistentState(agentId, persistentLimit),
    ]);
    if (!isCurrentAgentRequest(identity)) {
      return null;
    }
    setAgentDetails(details);
    setPersistentState(persistent);
    if (hydrateChat) {
      chatHistoryHydratorRef.current?.(persistent);
    }
    return persistent;
  };

  const refreshAgentListEffect = useEffectEvent(refreshAgentList);
  const refreshSelectedAgentEffect = useEffectEvent(refreshSelectedAgent);

  useEffect(() => {
    let cancelled = false;
    const loadAgents = async () => {
      setLoading(true);
      clearInitialError();
      try {
        await refreshAgentListEffect(includeArchivedAgents);
      } catch (error) {
        if (!cancelled && !isAbortError(error)) {
          reportInitialError(error);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    void loadAgents();
    return () => {
      cancelled = true;
    };
  }, [includeArchivedAgents]);

  useEffect(() => {
    if (!selectedAgentId) {
      resetSelectedAgentDetails();
      return;
    }
    const identity = currentAgentRequest(selectedAgentId);
    const loadSelectedAgent = async () => {
      try {
        await refreshSelectedAgentEffect(selectedAgentId, false, identity);
      } catch (error) {
        if (isCurrentAgentRequest(identity) && !isAbortError(error)) {
          reportInitialError(error);
        }
      }
    };
    void loadSelectedAgent();
  }, [selectedAgentId]);

  const refreshAgents = async () => {
    setBusy(true);
    notices.clearError();
    try {
      await refreshAgentList();
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const selectCreatedAgent = async (agentId: string) => {
    await refreshAgentList(includeArchivedAgents);
    selectAgent(agentId);
  };

  const pullExistingInfo = async () => {
    if (!selectedAgentId) {
      notices.setError(t("Select an existing agent first.", "请先选择现有智能体。"));
      return;
    }
    setBusy(true);
    notices.clearError();
    try {
      const persistent = await refreshSelectedAgent(selectedAgentId, true);
      if (persistent) {
        notices.setStatus(t("Persistent conversation history hydrated into Studio chat.", "已将持久化对话历史载入工作台聊天区。"));
      }
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const refreshPersistent = async () => {
    if (!selectedAgentId) {
      return;
    }
    setBusy(true);
    notices.clearError();
    try {
      await refreshSelectedAgent(selectedAgentId);
      notices.setStatus(t("Agent persistent state refreshed.", "智能体持久化状态已刷新。"));
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const archiveSelectedAgent = async () => {
    if (!selectedAgentId || selectedAgentInfo?.archived) {
      return;
    }
    setBusy(true);
    notices.clear();
    try {
      await archiveAgent(selectedAgentId);
      await refreshAgentList(includeArchivedAgents);
      notices.setStatus(t("Agent archived. Use Restore to make it active again.", "智能体已归档。可使用 Restore 恢复为活跃状态。"));
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const restoreSelectedAgent = async () => {
    if (!selectedAgentId || !selectedAgentInfo?.archived) {
      return;
    }
    setBusy(true);
    notices.clear();
    try {
      await restoreAgent(selectedAgentId);
      await refreshAgentList(includeArchivedAgents);
      notices.setStatus(t("Agent restored and active again.", "智能体已恢复并重新激活。"));
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const purgeSelectedAgent = async () => {
    if (!selectedAgentId || !selectedAgentInfo?.archived) {
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
    notices.clear();
    try {
      await purgeAgent(targetAgentId);
      selectAgent("");
      await refreshAgentList(includeArchivedAgents);
      notices.setStatus(t("Archived agent permanently deleted.", "已永久删除归档智能体。"));
    } catch (error) {
      notices.reportError(error);
    } finally {
      setBusy(false);
    }
  };

  const selectedAgentInfo = agents.find((agent) => agent.id === selectedAgentId) || null;

  return {
    loading,
    busy,
    agents,
    selectedAgentId,
    selectedAgentInfo,
    selectedAgentArchived: Boolean(selectedAgentInfo?.archived),
    includeArchivedAgents,
    persistentLimit,
    agentDetails,
    persistentState,
    setIncludeArchivedAgents,
    setPersistentLimit,
    selectAgent,
    currentAgentRequest,
    isCurrentAgentRequest,
    registerSelectionCleanup,
    registerChatHistoryHydrator,
    refreshAgentList,
    refreshAgents,
    refreshSelectedAgent,
    selectCreatedAgent,
    pullExistingInfo,
    refreshPersistent,
    archiveSelectedAgent,
    restoreSelectedAgent,
    purgeSelectedAgent,
  };
}
