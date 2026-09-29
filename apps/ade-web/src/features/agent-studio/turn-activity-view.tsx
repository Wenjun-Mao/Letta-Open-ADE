import type { TurnActivity } from "./types";

type Translate = (english: string, chinese: string) => string;

function short(id: string): string {
  return `${id.slice(0, 8)}…`;
}

export function TurnActivityView({ activity, t }: { activity: TurnActivity; t: Translate }) {
  const provider = activity.provider;
  const observedCount = Object.values(provider).reduce((total, count) => total + count, 0);
  const count = activity.provider_observed
    ? `${activity.provider_complete ? "" : "≥"}${observedCount}`
    : t("unavailable", "不可用");
  const toolSummary = activity.tools.length
    ? activity.tools.map((tool) => {
      const total = tool.succeeded + tool.failed + tool.unresolved;
      const issues = tool.failed || tool.unresolved
        ? ` (${tool.failed} ${t("failed", "失败")}, ${tool.unresolved} ${t("unresolved", "未完成")})`
        : "";
      return `${tool.name} ${total}${issues}`;
    }).join(", ")
    : activity.tools_complete ? t("none", "无") : t("unavailable", "不可用");

  const context = activity.context;
  const currentChat = context.current_chat === null ? t("unavailable", "不可用")
    : context.current_chat ? t("earlier messages in this chat", "本聊天中的先前消息")
      : t("no earlier chat messages", "无先前聊天消息");
  const profile = context.profile_fact_ids === null ? t("profile evidence unavailable", "资料事实证据不可用")
    : `${context.profile_fact_ids.length} ${t("profile fact IDs", "资料事实 ID")}`;
  const history = context.history_run_ids === null ? t("older exchange evidence unavailable", "旧对话证据不可用")
    : `${context.history_run_ids.length} ${t("older exchanges admitted", "条旧对话已纳入")}`;

  return <div className="studio-turn-activity">
    <small>{t("Provider requests", "服务商请求")}: {count} · {t("Tools", "工具")}: {toolSummary}</small>
    <details>
      <summary>{t("Turn activity and context", "本轮活动与上下文")}</summary>
      <p>{activity.provider_observed
        ? <>{t("Generation", "生成")}: {provider.generation} · {t("Review", "审核")}: {provider.reviewer} · {t("Embeddings", "嵌入")}: {provider.embedding}{provider.other ? ` · ${t("Other", "其他")}: ${provider.other}` : ""}{activity.provider_complete ? "" : ` · ${t("observed minimum; trace incomplete", "已观测下限；记录不完整")}`}</>
        : t("Provider breakdown unavailable", "请求分类不可用")}</p>
      <p>{t("Context supplied", "提供的上下文")}: {currentChat} · {profile} · {history}</p>
      {context.profile_fact_ids?.length ? <p>{t("Selected fact IDs", "选中的事实 ID")}: {context.profile_fact_ids.map(short).join(", ")}</p> : null}
      {context.history_sources?.length ? <p>{t("Admitted source chats", "纳入的来源聊天")}: {context.history_sources.map((source, index) => <span key={source.run_id}>{index ? ", " : ""}<a href={`/agent-studio?conversation=${encodeURIComponent(source.conversation_id)}`}>{short(source.run_id)}</a></span>)}</p>
        : context.history_run_ids?.length ? <p>{t("Admitted source runs", "纳入的来源运行")}: {context.history_run_ids.map(short).join(", ")}</p> : null}
      <small>{t("Supplied context shows availability, not what caused the reply. Search is only one retrieval path.", "提供的上下文表示信息可用，不能证明回复原因。搜索只是其中一种检索路径。")}</small>
    </details>
  </div>;
}
