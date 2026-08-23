import type { RefObject } from "react";

import type { ChatStep, PersistentState } from "../../lib/api";
import { formatLatency, formatTimestamp, stepTone } from "./formatters";
import { highlightDiff } from "./memory-diff";
import type { ChatEntry, EditorKind, PersistentTab, TimelineFilter } from "./types";

type Translate = (english: string, chinese: string) => string;

type ChatPanelProps = {
  t: Translate;
  chatScrollRef: RefObject<HTMLDivElement | null>;
  chatHistory: ChatEntry[];
  timeoutSeconds: string;
  retryCount: string;
  chatInput: string;
  chatBusy: boolean;
  toolProbeBusy: boolean;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  onTimeoutChange: (value: string) => void;
  onRetryCountChange: (value: string) => void;
  onChatInputChange: (value: string) => void;
  onSendMessage: () => Promise<void>;
};

export function ChatPanel({
  t,
  chatScrollRef,
  chatHistory,
  timeoutSeconds,
  retryCount,
  chatInput,
  chatBusy,
  toolProbeBusy,
  selectedAgentId,
  selectedAgentArchived,
  onTimeoutChange,
  onRetryCountChange,
  onChatInputChange,
  onSendMessage,
}: ChatPanelProps) {
  return (
    <section className="card studio-panel" aria-label={t("Chat workspace", "聊天工作区")}>
      <h3>{t("Chat", "对话")}</h3>
      <div className="chat-scroll" ref={chatScrollRef}>
        {chatHistory.length === 0 ? (
          <p className="muted">{t("Send a message or use Pull Existing Info to hydrate history.", "发送消息，或使用拉取已有信息来载入历史。")}</p>
        ) : (
          chatHistory.map((entry) => (
            <div key={entry.id} className={`chat-row ${entry.role === "user" ? "user" : "assistant"}`}>
              <div className="chat-bubble">
                <div className="chat-meta">
                  <span>{entry.role === "user" ? t("You", "你") : t("Assistant", "助手")}</span>
                  {entry.role === "assistant" && entry.timingMs !== null ? (
                    <span>{formatLatency(entry.timingMs)}</span>
                  ) : null}
                </div>
                <div className="chat-content">{entry.content}</div>
              </div>
            </div>
          ))
        )}
      </div>

      <div className="form-grid" style={{ marginTop: 12 }}>
        <label className="field">
          <span>{t("Timeout (seconds)", "超时时间（秒）")}</span>
          <input
            className="input"
            type="number"
            min={5}
            max={600}
            step={1}
            value={timeoutSeconds}
            onChange={(event) => onTimeoutChange(event.target.value)}
            disabled={chatBusy || toolProbeBusy}
          />
        </label>
        <label className="field">
          <span>{t("Retry Count", "重试次数")}</span>
          <input
            className="input"
            type="number"
            min={0}
            max={5}
            step={1}
            value={retryCount}
            onChange={(event) => onRetryCountChange(event.target.value)}
            disabled={chatBusy || toolProbeBusy}
          />
        </label>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        {t(
          "These settings apply to Chat and Tool Probe. Set retry count to 0 to disable retries.",
          "这些设置会同时作用于聊天与工具探测。将重试次数设为 0 即禁用重试。",
        )}
      </p>
      <div className="toolbar" style={{ marginTop: 12 }}>
        <textarea
          className="input"
          style={{ minHeight: 82, resize: "vertical", flex: 1 }}
          placeholder={t("Type a message (Enter to send)", "输入消息（回车发送）")}
          value={chatInput}
          onChange={(event) => onChatInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void onSendMessage();
            }
          }}
        />
        <button
          className="button"
          onClick={() => void onSendMessage()}
          disabled={chatBusy || !selectedAgentId || selectedAgentArchived}
        >
          {chatBusy ? t("Sending...", "发送中...") : t("Send", "发送")}
        </button>
      </div>
    </section>
  );
}

type ExecutionTracePanelProps = {
  t: Translate;
  locale: "en" | "zh";
  lastLatencyMs: number | null;
  timelineFilter: TimelineFilter;
  timelineSteps: ChatStep[];
  hasLastResult: boolean;
  humanBefore: string;
  humanAfter: string;
  showRawPrompt: boolean;
  rawPromptLoading: boolean;
  rawPromptMessages: Array<{ role: string; content: string }>;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  busy: boolean;
  persistentLimit: number;
  persistentTab: PersistentTab;
  persistentState: PersistentState | null;
  onTimelineFilterChange: (filter: TimelineFilter) => void;
  onToggleRawPrompt: () => Promise<void>;
  onRefreshPersistent: () => Promise<void>;
  onPersistentLimitChange: (value: number) => void;
  onPersistentTabChange: (tab: PersistentTab) => void;
  onOpenEditor: (kind: Exclude<EditorKind, null>, value: string) => void;
};

export function ExecutionTracePanel({
  t,
  locale,
  lastLatencyMs,
  timelineFilter,
  timelineSteps,
  hasLastResult,
  humanBefore,
  humanAfter,
  showRawPrompt,
  rawPromptLoading,
  rawPromptMessages,
  selectedAgentId,
  selectedAgentArchived,
  busy,
  persistentLimit,
  persistentTab,
  persistentState,
  onTimelineFilterChange,
  onToggleRawPrompt,
  onRefreshPersistent,
  onPersistentLimitChange,
  onPersistentTabChange,
  onOpenEditor,
}: ExecutionTracePanelProps) {
  const memoryBlocks = persistentState?.memory_blocks || [];

  return (
    <aside className="card studio-panel">
      <h3>{t("Execution Trace", "执行轨迹")}</h3>
      {lastLatencyMs !== null ? (
        <p className="muted">{t("Last response latency", "最近响应延迟")}: {formatLatency(lastLatencyMs)}</p>
      ) : null}
      <div className="toolbar" style={{ marginTop: 8 }}>
        {(["all", "assistant", "tool", "reasoning"] as const).map((filter) => (
          <button
            key={filter}
            className={timelineFilter === filter ? "button" : "button muted"}
            onClick={() => onTimelineFilterChange(filter)}
          >
            {filter === "all"
              ? t("All", "全部")
              : filter === "assistant"
                ? t("Assistant", "助手")
                : filter === "tool"
                  ? t("Tool", "工具")
                  : t("Reasoning", "推理")}
          </button>
        ))}
      </div>

      {timelineSteps.length ? (
        <div className="studio-stack" style={{ marginTop: 8 }}>
          {timelineSteps.map((step, index) => (
            <div className={stepTone(step.type)} key={`${step.type}-${index}`}>
              <div className="timeline-type">{step.type}</div>
              {step.name ? <div className="timeline-name">{step.name}</div> : null}
              {step.content ? <div className="timeline-content">{step.content}</div> : null}
              {step.arguments || step.tool_arguments ? (
                <pre className="code">{String(step.arguments || step.tool_arguments || "")}</pre>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <p className="muted">{t("No runtime steps yet.", "暂无运行步骤。")}</p>
      )}

      {hasLastResult ? (
        <div className="studio-stack" style={{ marginTop: 10 }}>
          <h4 style={{ margin: 0 }}>{t("Human Memory Diff", "Human 记忆差异")}</h4>
          <div className="code memory-diff" dangerouslySetInnerHTML={{ __html: highlightDiff(humanBefore, humanAfter) }} />
        </div>
      ) : null}

      <hr className="studio-divider" />

      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <h4 style={{ margin: 0 }}>{t("Raw Prompt Context", "原始 Prompt 上下文")}</h4>
        <button className="button muted" onClick={() => void onToggleRawPrompt()}>
          {showRawPrompt ? t("Hide", "隐藏") : t("Show", "显示")}
        </button>
      </div>
      {showRawPrompt ? (
        rawPromptLoading ? (
          <p className="muted">{t("Loading raw prompt...", "加载原始 prompt 中...")}</p>
        ) : (
          <div className="studio-stack">
            {rawPromptMessages.length === 0 ? (
              <p className="muted">{t("No prompt payload loaded.", "未加载到 prompt 载荷。")}</p>
            ) : (
              rawPromptMessages.map((message, index) => (
                <div className="code" key={`${message.role}-${index}`}>
                  [{message.role}]
                  {"\n"}
                  {message.content}
                </div>
              ))
            )}
          </div>
        )
      ) : null}

      <hr className="studio-divider" />

      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <h4 style={{ margin: 0 }}>{t("Persistent State", "持久化状态")}</h4>
        <button className="button muted" onClick={() => void onRefreshPersistent()} disabled={!selectedAgentId || busy}>
          {t("Refresh", "刷新")}
        </button>
      </div>
      <div className="toolbar" style={{ marginTop: 8 }}>
        <label className="field" style={{ width: 150 }}>
          <span>{t("History limit", "历史上限")}</span>
          <input
            className="input"
            type="number"
            min={10}
            max={500}
            value={persistentLimit}
            onChange={(event) => onPersistentLimitChange(Math.max(10, Math.min(500, Number(event.target.value) || 120)))}
          />
        </label>
      </div>

      <div className="studio-tabs" style={{ marginTop: 10 }}>
        {(["summary", "memory", "history"] as const).map((tab) => (
          <button
            key={tab}
            className={persistentTab === tab ? "tab-active" : "tab-item"}
            onClick={() => onPersistentTabChange(tab)}
          >
            {tab === "summary"
              ? t("Summary", "摘要")
              : tab === "memory"
                ? t("Memory", "记忆")
                : t("History", "历史")}
          </button>
        ))}
      </div>

      {persistentTab === "summary" && persistentState ? (
        <div className="code" style={{ marginTop: 8 }}>
          {t("Agent", "智能体")}: {persistentState.agent?.id || "N/A"}
          {"\n"}
          {t("Name", "名称")}: {persistentState.agent?.name || "N/A"}
          {"\n"}
          {t("Model", "模型")}: {persistentState.agent?.model || "N/A"}
          {"\n"}
          {t("History rows", "历史条数")}: {persistentState.conversation_history?.displayed || 0} / {persistentState.conversation_history?.total_persisted || 0}
          {"\n"}
          {t("Counts by type", "按类型统计")}:
          {"\n"}
          {JSON.stringify(persistentState.conversation_history?.counts_by_type || {}, null, 2)}
        </div>
      ) : null}

      {persistentTab === "memory" ? (
        <div className="studio-stack" style={{ marginTop: 8 }}>
          {memoryBlocks.map((block) => (
            <div key={block.label} className="card" style={{ padding: 10 }}>
              <div className="toolbar" style={{ justifyContent: "space-between" }}>
                <strong>{block.label}</strong>
                {block.label === "persona" || block.label === "human" ? (
                  <button
                    className="button muted"
                    disabled={selectedAgentArchived}
                    onClick={() => onOpenEditor(block.label === "persona" ? "persona" : "human", block.value)}
                  >
                    {t("Edit", "编辑")}
                  </button>
                ) : null}
              </div>
              {block.description ? <p className="muted" style={{ marginTop: 8 }}>{block.description}</p> : null}
              <div className="code" style={{ marginTop: 8 }}>{block.value}</div>
            </div>
          ))}
        </div>
      ) : null}

      {persistentTab === "history" && persistentState ? (
        <div className="studio-stack" style={{ marginTop: 8, maxHeight: 500, overflowY: "auto" }}>
          {(persistentState.conversation_history?.items || []).map((item) => (
            <div className="card" style={{ padding: 10 }} key={`${item.id}-${item.created_at}`}>
              <div className="toolbar" style={{ justifyContent: "space-between" }}>
                <strong>{item.message_type}</strong>
                <span className="muted">{formatTimestamp(item.created_at, locale)}</span>
              </div>
              <div className="code" style={{ marginTop: 8 }}>{item.content}</div>
            </div>
          ))}
        </div>
      ) : null}
    </aside>
  );
}
