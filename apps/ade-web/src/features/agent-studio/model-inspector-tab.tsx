import type { AgentDetails } from "./api";
import type { OptionEntry } from "@/features/model-catalog/api";
import { formatModelOptionLabel } from "@/shared/generation-controls";
import { formatTimestamp } from "./formatters";
import type { Translate } from "./types";

type SetText = (value: string) => void;

export type ModelInspectorTabProps = {
  t: Translate;
  locale: "en" | "zh";
  models: OptionEntry[];
  agentDetails: AgentDetails;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  modelEditValue: string;
  modelBusy: boolean;
  onModelEditValueChange: SetText;
  onApplyModel: () => Promise<void>;
};

export function ModelInspectorTab({
  t,
  locale,
  models,
  agentDetails,
  selectedAgentId,
  selectedAgentArchived,
  modelEditValue,
  modelBusy,
  onModelEditValueChange,
  onApplyModel,
}: ModelInspectorTabProps) {
  const modelLabel = (option: OptionEntry) =>
    formatModelOptionLabel(option, t(" [Unavailable]", " [不可用]"));

  return (
    <div className="studio-stack">
      <div className="field">
        <span>{t("Agent model override", "智能体模型覆盖")}</span>
        <select className="input" value={modelEditValue} onChange={(event) => onModelEditValueChange(event.target.value)}>
          <option value="">{t("Select model", "选择模型")}</option>
          {models.map((item) => <option key={item.key} value={item.key}>{modelLabel(item)}</option>)}
        </select>
        <button className="button" onClick={() => void onApplyModel()} disabled={modelBusy || !selectedAgentId || !modelEditValue || selectedAgentArchived}>
          {modelBusy ? t("Applying...", "应用中...") : t("Apply Model", "应用模型")}
        </button>
      </div>
      <div className="code">
        {t("Type", "类型")}: {agentDetails.agent_type || t("unknown", "未知")}
        {"\n"}
        {t("Context window", "上下文窗口")}: {agentDetails.context_window_limit ?? "N/A"}
        {"\n"}
        {t("Last interaction", "最近交互")}: {formatTimestamp(agentDetails.last_interaction_at || agentDetails.last_updated_at, locale)}
      </div>
      {agentDetails.llm_config ? <div className="code">{JSON.stringify(agentDetails.llm_config, null, 2)}</div> : null}
    </div>
  );
}
