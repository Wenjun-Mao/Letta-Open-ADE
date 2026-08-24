import type { AgentDetails } from "./api";
import type { PromptPersonaRevisionRecord } from "@/features/prompt-center/api";
import { formatTimestamp } from "./formatters";
import type { EditorKind, Translate } from "./types";

export type PromptInspectorTabProps = {
  t: Translate;
  locale: "en" | "zh";
  agentDetails: AgentDetails;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  personaValue: string;
  humanValue: string;
  revisionLoading: boolean;
  revisionHistory: PromptPersonaRevisionRecord[];
  onOpenEditor: (kind: Exclude<EditorKind, null>, value: string) => void;
  onRefreshRevisionHistory: () => Promise<void>;
};

export function PromptInspectorTab({
  t,
  locale,
  agentDetails,
  selectedAgentId,
  selectedAgentArchived,
  personaValue,
  humanValue,
  revisionLoading,
  revisionHistory,
  onOpenEditor,
  onRefreshRevisionHistory,
}: PromptInspectorTabProps) {
  return (
    <div className="studio-stack">
      <div className="toolbar prompt-action-row">
        <button className="prompt-action-button" disabled={selectedAgentArchived} onClick={() => onOpenEditor("system", agentDetails.system || "")}>{t("Edit System Prompt", "编辑 System Prompt")}</button>
        <button className="prompt-action-button" disabled={selectedAgentArchived} onClick={() => onOpenEditor("persona", personaValue)}>{t("Edit Persona", "编辑 Persona")}</button>
        <button className="prompt-action-button" disabled={selectedAgentArchived} onClick={() => onOpenEditor("human", humanValue)}>{t("Edit Human", "编辑 Human")}</button>
        <button className="prompt-action-button" onClick={() => void onRefreshRevisionHistory()} disabled={!selectedAgentId || revisionLoading || selectedAgentArchived}>
          {revisionLoading ? t("Refreshing...", "刷新中...") : t("Refresh Timeline", "刷新时间线")}
        </button>
      </div>
      <div className="code">{agentDetails.system || t("No system prompt.", "暂无 system prompt。")}</div>
      <PromptRevisionTimeline t={t} locale={locale} revisionHistory={revisionHistory} />
    </div>
  );
}

type PromptRevisionTimelineProps = {
  t: Translate;
  locale: "en" | "zh";
  revisionHistory: PromptPersonaRevisionRecord[];
};

function PromptRevisionTimeline({ t, locale, revisionHistory }: PromptRevisionTimelineProps) {
  return (
    <div className="card" style={{ padding: 10 }}>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <strong>{t("Revision Timeline", "修订时间线")}</strong>
        <span className="muted">{revisionHistory.length} {t("record(s)", "条记录")}</span>
      </div>
      {revisionHistory.length === 0 ? (
        <p className="muted" style={{ marginTop: 8 }}>{t("No prompt/persona revisions recorded yet for this agent.", "该智能体尚无 prompt/persona 修订记录。")}</p>
      ) : (
        <div className="studio-stack" style={{ marginTop: 8, maxHeight: 320, overflowY: "auto" }}>
          {revisionHistory.map((record) => (
            <div className="card revision-item" style={{ padding: 10 }} key={record.revision_id}>
              <div className="toolbar" style={{ justifyContent: "space-between" }}>
                <strong>{record.field}</strong>
                <span className="muted">{formatTimestamp(record.recorded_at, locale)}</span>
              </div>
              <p className="muted" style={{ marginTop: 6 }}>
                {t("source", "来源")}: {record.source} | {t("delta", "变更")}: {record.delta_length >= 0 ? `+${record.delta_length}` : record.delta_length}
              </p>
              <details style={{ marginTop: 8 }}>
                <summary>{t("View before/after preview", "查看前后预览")}</summary>
                <div className="code" style={{ marginTop: 8 }}>
                  [{t("before", "变更前")}]
                  {"\n"}
                  {record.before_preview || t("(empty)", "（空）")}
                  {"\n\n"}
                  [{t("after", "变更后")}]
                  {"\n"}
                  {record.after_preview || t("(empty)", "（空）")}
                </div>
              </details>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
