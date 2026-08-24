import { formatTimestamp, shortId } from "./formatters";
import type { AgentItem, Translate } from "./types";

type SetText = (value: string) => void;

export type AgentSelectionControlsProps = {
  t: Translate;
  locale: "en" | "zh";
  busy: boolean;
  agents: AgentItem[];
  includeArchivedAgents: boolean;
  selectedAgentId: string;
  selectedAgentInfo: AgentItem | null;
  selectedAgentArchived: boolean;
  selectedAgentName: string;
  historyCount: number;
  onIncludeArchivedAgentsChange: (value: boolean) => void;
  onSelectAgent: SetText;
  onPullExistingInfo: () => Promise<void>;
  onRefreshPersistent: () => Promise<void>;
  onArchiveAgent: () => Promise<void>;
  onRestoreAgent: () => Promise<void>;
  onPurgeAgent: () => Promise<void>;
};

export function AgentSelectionControls({
  t,
  locale,
  busy,
  agents,
  includeArchivedAgents,
  selectedAgentId,
  selectedAgentInfo,
  selectedAgentArchived,
  selectedAgentName,
  historyCount,
  onIncludeArchivedAgentsChange,
  onSelectAgent,
  onPullExistingInfo,
  onRefreshPersistent,
  onArchiveAgent,
  onRestoreAgent,
  onPurgeAgent,
}: AgentSelectionControlsProps) {
  return (
    <>
      <label className="field">
        <span>{t("Existing agents", "已有智能体")}</span>
        <label className="field" style={{ marginTop: 6 }}>
          <span>
            <input
              type="checkbox"
              checked={includeArchivedAgents}
              onChange={(event) => onIncludeArchivedAgentsChange(event.target.checked)}
              style={{ marginRight: 8 }}
            />
            {t("Include archived agents", "显示已归档智能体")}
          </span>
        </label>
        <select className="input" value={selectedAgentId} onChange={(event) => onSelectAgent(event.target.value)}>
          <option value="">{t("Select agent", "选择智能体")}</option>
          {agents.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name} ({item.model}){item.archived ? t(" [Archived]", " [已归档]") : ""}
            </option>
          ))}
        </select>
      </label>

      {selectedAgentInfo ? (
        <div className="code" style={{ marginTop: 8 }}>
          {t("ID", "ID")}: {shortId(selectedAgentInfo.id)}
          {"\n"}
          {t("Status", "状态")}: {selectedAgentInfo.archived ? t("Archived", "已归档") : t("Active", "活跃")}
          {"\n"}
          {t("Created", "创建时间")}: {formatTimestamp(selectedAgentInfo.created_at, locale)}
          {"\n"}
          {t("Last interaction", "最近交互")}: {formatTimestamp(selectedAgentInfo.last_interaction_at || selectedAgentInfo.last_updated_at, locale)}
        </div>
      ) : null}

      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button muted" onClick={() => void onPullExistingInfo()} disabled={!selectedAgentId || busy}>
          {t("Pull Existing Info", "拉取已有信息")}
        </button>
        <button className="button muted" onClick={() => void onRefreshPersistent()} disabled={!selectedAgentId || busy}>
          {t("Refresh Selected", "刷新当前智能体")}
        </button>
      </div>

      <div className="toolbar" style={{ marginTop: 8 }}>
        <button className="button muted" onClick={() => void onArchiveAgent()} disabled={!selectedAgentId || busy || selectedAgentArchived}>
          {t("Archive Agent", "归档智能体")}
        </button>
        <button className="button muted" onClick={() => void onRestoreAgent()} disabled={!selectedAgentId || busy || !selectedAgentArchived}>
          {t("Restore Agent", "恢复智能体")}
        </button>
        <button className="button danger" onClick={() => void onPurgeAgent()} disabled={!selectedAgentId || busy || !selectedAgentArchived}>
          {t("Purge Agent", "彻底删除")}
        </button>
      </div>

      <p className="muted" style={{ marginTop: 10 }}>
        {t("Selected", "当前")}: {selectedAgentName || t("none", "无")}
        {selectedAgentArchived ? t(" (archived)", "（已归档）") : ""}
      </p>
      <p className="muted">{t("Conversation rows", "对话条数")}: {historyCount}</p>
    </>
  );
}
