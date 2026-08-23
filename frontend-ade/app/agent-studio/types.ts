export type AgentItem = {
  id: string;
  name: string;
  model: string;
  created_at: string;
  last_updated_at: string;
  last_interaction_at: string;
  archived: boolean;
};

export type ChatEntry = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timingMs: number | null;
};

export type InspectorTab = "model" | "prompt" | "tools";
export type PersistentTab = "summary" | "memory" | "history";
export type EditorKind = "system" | "persona" | "human" | null;
export type TimelineFilter = "all" | "assistant" | "tool" | "reasoning";
export type Translate = (english: string, chinese: string) => string;

export const AGENT_CREATE_SCENARIO = "chat" as const;
export const TOOL_PROBE_DEFAULT_EN = "Decide whether to call a tool for this request, then return a concise answer.";
export const TOOL_PROBE_DEFAULT_ZH = "请根据当前问题决定是否需要调用工具，再回答结果。";
export const AGENT_STUDIO_DEFAULT_TIMEOUT_SECONDS = "180";
export const AGENT_STUDIO_DEFAULT_RETRY_COUNT = "0";
