"use client";

import { useEffect, useRef, useState } from "react";

import { sendChat, type ChatResult, type PersistentState } from "./api";
import { isAbortError } from "@/shared/api/client";
import { parseIntegerInRange, parsePositiveNumber } from "@/shared/generation-controls";
import type { RequestIdentity } from "@/shared/request-identity";
import { hydrateChatHistory } from "./chat-history";
import { extractAssistantReply, toErrorMessage } from "./formatters";
import {
  AGENT_STUDIO_DEFAULT_RETRY_COUNT,
  AGENT_STUDIO_DEFAULT_TIMEOUT_SECONDS,
  type ChatEntry,
  type Translate,
} from "./types";

type ChatNotices = {
  clear: () => void;
  setError: (error: string) => void;
};

type UseChatExecutionArgs = {
  t: Translate;
  notices: ChatNotices;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  currentAgentRequest: (agentId: string) => RequestIdentity;
  isCurrentAgentRequest: (identity: RequestIdentity) => boolean;
  refreshSelectedAgent: (agentId: string, hydrateChat?: boolean, identity?: RequestIdentity) => Promise<PersistentState | null>;
  registerSelectionCleanup: (cleanup: () => void) => () => void;
  registerChatHistoryHydrator: (hydrator: (persistentState: PersistentState) => void) => () => void;
  recordResult: (result: ChatResult, latencyMs?: number) => void;
};

export function useChatExecution({
  t,
  notices,
  selectedAgentId,
  selectedAgentArchived,
  currentAgentRequest,
  isCurrentAgentRequest,
  refreshSelectedAgent,
  registerSelectionCleanup,
  registerChatHistoryHydrator,
  recordResult,
}: UseChatExecutionArgs) {
  const chatScrollRef = useRef<HTMLDivElement | null>(null);
  const chatAbortControllerRef = useRef<AbortController | null>(null);
  const [chatBusy, setChatBusy] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(AGENT_STUDIO_DEFAULT_TIMEOUT_SECONDS);
  const [retryCount, setRetryCount] = useState(AGENT_STUDIO_DEFAULT_RETRY_COUNT);
  const [chatHistory, setChatHistory] = useState<ChatEntry[]>([]);

  const reset = () => {
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = null;
    setChatBusy(false);
    setChatHistory([]);
  };

  const hydrate = (persistentState: PersistentState) => {
    setChatHistory(hydrateChatHistory(persistentState));
  };

  useEffect(() => {
    const unregisterCleanup = registerSelectionCleanup(reset);
    const unregisterHydrator = registerChatHistoryHydrator(hydrate);
    return () => {
      unregisterCleanup();
      unregisterHydrator();
      chatAbortControllerRef.current?.abort();
    };
  }, [registerChatHistoryHydrator, registerSelectionCleanup]);

  useEffect(() => {
    const node = chatScrollRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [chatHistory]);

  const sendMessage = async () => {
    if (!selectedAgentId) {
      notices.setError(t("Select an agent first.", "请先选择智能体。"));
      return;
    }
    if (selectedAgentArchived) {
      notices.setError(t("Archived agents cannot run chat. Restore first.", "归档智能体不可对话，请先恢复。"));
      return;
    }
    const text = chatInput.trim();
    if (!text) {
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
    chatAbortControllerRef.current?.abort();
    chatAbortControllerRef.current = controller;
    setChatBusy(true);
    notices.clear();
    const startedAt = performance.now();
    setChatHistory((previous) => [
      ...previous,
      { id: `${Date.now()}-user`, role: "user", content: text, timingMs: null },
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
      const elapsedMs = Math.max(0, performance.now() - startedAt);
      const assistant = extractAssistantReply(result);
      setChatHistory((previous) => [
        ...previous,
        {
          id: `${Date.now()}-assistant`,
          role: "assistant",
          content: assistant || t("(No assistant message returned)", "（未返回助手消息）"),
          timingMs: elapsedMs,
        },
      ]);
      recordResult(result, elapsedMs);
      await refreshSelectedAgent(targetAgentId, false, identity);
    } catch (error) {
      if (!isCurrentAgentRequest(identity) || isAbortError(error)) {
        return;
      }
      const elapsedMs = Math.max(0, performance.now() - startedAt);
      const message = toErrorMessage(error);
      setChatHistory((previous) => [
        ...previous,
        { id: `${Date.now()}-error`, role: "assistant", content: t(`Error: ${message}`, `错误：${message}`), timingMs: elapsedMs },
      ]);
      notices.setError(message);
    } finally {
      if (chatAbortControllerRef.current === controller) {
        chatAbortControllerRef.current = null;
        setChatBusy(false);
      }
    }
  };

  return {
    chatScrollRef,
    chatBusy,
    chatInput,
    timeoutSeconds,
    retryCount,
    chatHistory,
    setChatInput,
    setTimeoutSeconds,
    setRetryCount,
    sendMessage,
  };
}
