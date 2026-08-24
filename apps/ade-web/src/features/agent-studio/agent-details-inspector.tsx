import type { AgentDetails, RuntimeTool, ToolProbeResult } from "./api";
import type { OptionEntry } from "@/features/model-catalog/api";
import type { PromptPersonaRevisionRecord } from "@/features/prompt-center/api";
import { ModelInspectorTab } from "./model-inspector-tab";
import { PromptInspectorTab } from "./prompt-inspector-tab";
import { ToolInspectorTab } from "./tool-inspector-tab";
import type { EditorKind, InspectorTab, Translate } from "./types";

type SetText = (value: string) => void;

type AgentDetailsInspectorProps = {
  t: Translate;
  locale: "en" | "zh";
  models: OptionEntry[];
  agentDetails: AgentDetails | null;
  inspectorTab: InspectorTab;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  modelEditValue: string;
  modelBusy: boolean;
  personaValue: string;
  humanValue: string;
  revisionLoading: boolean;
  revisionHistory: PromptPersonaRevisionRecord[];
  toolSearch: string;
  tools: RuntimeTool[];
  toolBusyId: string;
  toolProbeInput: string;
  toolProbeExpected: string;
  toolProbeBusy: boolean;
  toolProbeResult: ToolProbeResult | null;
  onInspectorTabChange: (tab: InspectorTab) => void;
  onModelEditValueChange: SetText;
  onApplyModel: () => Promise<void>;
  onOpenEditor: (kind: Exclude<EditorKind, null>, value: string) => void;
  onRefreshRevisionHistory: () => Promise<void>;
  onToolSearchChange: SetText;
  onRefreshTools: () => Promise<boolean | void>;
  onToggleTool: (tool: RuntimeTool) => Promise<void>;
  onViewToolDetails: (tool: RuntimeTool) => void;
  onToolProbeInputChange: SetText;
  onToolProbeExpectedChange: SetText;
  onRunToolProbe: () => Promise<void>;
};

export function AgentDetailsInspector({
  t,
  locale,
  models,
  agentDetails,
  inspectorTab,
  selectedAgentId,
  selectedAgentArchived,
  modelEditValue,
  modelBusy,
  personaValue,
  humanValue,
  revisionLoading,
  revisionHistory,
  toolSearch,
  tools,
  toolBusyId,
  toolProbeInput,
  toolProbeExpected,
  toolProbeBusy,
  toolProbeResult,
  onInspectorTabChange,
  onModelEditValueChange,
  onApplyModel,
  onOpenEditor,
  onRefreshRevisionHistory,
  onToolSearchChange,
  onRefreshTools,
  onToggleTool,
  onViewToolDetails,
  onToolProbeInputChange,
  onToolProbeExpectedChange,
  onRunToolProbe,
}: AgentDetailsInspectorProps) {
  if (!agentDetails) {
    return null;
  }

  return (
    <>
      <div className="studio-tabs">
        {(["model", "prompt", "tools"] as const).map((tab) => (
          <button key={tab} className={inspectorTab === tab ? "tab-active" : "tab-item"} onClick={() => onInspectorTabChange(tab)}>
            {tab === "model" ? t("Model", "模型") : tab === "prompt" ? t("Prompt", "提示词") : t("Tools", "工具")}
          </button>
        ))}
      </div>

      {inspectorTab === "model" ? (
        <ModelInspectorTab
          t={t}
          locale={locale}
          models={models}
          agentDetails={agentDetails}
          selectedAgentId={selectedAgentId}
          selectedAgentArchived={selectedAgentArchived}
          modelEditValue={modelEditValue}
          modelBusy={modelBusy}
          onModelEditValueChange={onModelEditValueChange}
          onApplyModel={onApplyModel}
        />
      ) : null}
      {inspectorTab === "prompt" ? (
        <PromptInspectorTab
          t={t}
          locale={locale}
          agentDetails={agentDetails}
          selectedAgentId={selectedAgentId}
          selectedAgentArchived={selectedAgentArchived}
          personaValue={personaValue}
          humanValue={humanValue}
          revisionLoading={revisionLoading}
          revisionHistory={revisionHistory}
          onOpenEditor={onOpenEditor}
          onRefreshRevisionHistory={onRefreshRevisionHistory}
        />
      ) : null}
      {inspectorTab === "tools" ? (
        <ToolInspectorTab
          t={t}
          selectedAgentId={selectedAgentId}
          selectedAgentArchived={selectedAgentArchived}
          toolSearch={toolSearch}
          tools={tools}
          toolBusyId={toolBusyId}
          toolProbeInput={toolProbeInput}
          toolProbeExpected={toolProbeExpected}
          toolProbeBusy={toolProbeBusy}
          toolProbeResult={toolProbeResult}
          onToolSearchChange={onToolSearchChange}
          onRefreshTools={onRefreshTools}
          onToggleTool={onToggleTool}
          onViewToolDetails={onViewToolDetails}
          onToolProbeInputChange={onToolProbeInputChange}
          onToolProbeExpectedChange={onToolProbeExpectedChange}
          onRunToolProbe={onRunToolProbe}
        />
      ) : null}
    </>
  );
}
