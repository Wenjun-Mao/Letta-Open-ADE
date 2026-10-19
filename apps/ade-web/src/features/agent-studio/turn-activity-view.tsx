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
  const automatic = context.automatic_memory_ids === null ? t("automatic recall unavailable", "自动查询信息不可用")
    : `${context.automatic_memory_ids.length} ${t("automatically supplied memory IDs", "条自动提供的记忆 ID")}`;
  const searched = context.tool_memory_ids === null ? t("tool recall unavailable", "工具查询信息不可用")
    : `${context.tool_memory_ids.length} ${t("tool-supplied memory IDs", "条工具提供的记忆 ID")}`;

  return <div className="studio-turn-activity">
    <small>{t("Provider requests", "服务商请求")}: {count} · {t("Tools", "工具")}: {toolSummary}</small>
    <details>
      <summary>{t("Turn activity and context", "本轮活动与上下文")}</summary>
      <p>{activity.provider_observed
        ? <>{t("Generation", "生成")}: {provider.generation} · {t("Compaction", "压缩")}: {provider.compaction}{provider.other ? ` · ${t("Other", "其他")}: ${provider.other}` : ""}{activity.provider_complete ? "" : ` · ${t("observed minimum; trace incomplete", "已观测下限；记录不完整")}`}</>
        : t("Provider breakdown unavailable", "请求分类不可用")}</p>
      <p>{t("Context supplied", "提供的上下文")}: {currentChat} · {automatic} · {searched}</p>
      {context.automatic_memory_ids?.length ? <p>{t("Automatic Memory", "自动 Memory")}: {context.automatic_memory_ids.map(short).join(", ")}</p> : null}
      {context.tool_memory_ids?.length ? <p>{t("Tool Memory", "工具 Memory")}: {context.tool_memory_ids.map(short).join(", ")}</p> : null}
      <small>{t("These counts cover ADE reply/compaction calls, not Hindsight extraction or consolidation calls.", "这些计数只涵盖 ADE 回复与压缩请求，不含 Hindsight 抽取或归纳请求。")}</small>
      <small>{t("Supplied context shows availability, not what caused the reply. Search is only one retrieval path.", "提供的上下文表示信息可用，不能证明回复原因。搜索只是其中一种检索路径。")}</small>
    </details>
  </div>;
}
