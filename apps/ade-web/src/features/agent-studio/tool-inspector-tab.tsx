import type { RuntimeTool, ToolProbeResult } from "./api";
import { summarizeDescription } from "./formatters";
import type { Translate } from "./types";

type SetText = (value: string) => void;

export type ToolInspectorTabProps = {
  t: Translate;
  selectedAgentId: string;
  selectedAgentArchived: boolean;
  toolSearch: string;
  tools: RuntimeTool[];
  toolBusyId: string;
  toolProbeInput: string;
  toolProbeExpected: string;
  toolProbeBusy: boolean;
  toolProbeResult: ToolProbeResult | null;
  onToolSearchChange: SetText;
  onRefreshTools: () => Promise<boolean | void>;
  onToggleTool: (tool: RuntimeTool) => Promise<void>;
  onViewToolDetails: (tool: RuntimeTool) => void;
  onToolProbeInputChange: SetText;
  onToolProbeExpectedChange: SetText;
  onRunToolProbe: () => Promise<void>;
};

export function ToolInspectorTab({
  t,
  selectedAgentId,
  selectedAgentArchived,
  toolSearch,
  tools,
  toolBusyId,
  toolProbeInput,
  toolProbeExpected,
  toolProbeBusy,
  toolProbeResult,
  onToolSearchChange,
  onRefreshTools,
  onToggleTool,
  onViewToolDetails,
  onToolProbeInputChange,
  onToolProbeExpectedChange,
  onRunToolProbe,
}: ToolInspectorTabProps) {
  return (
    <div className="studio-stack">
      <div className="toolbar">
        <input className="input" value={toolSearch} placeholder={t("Search tools", "搜索工具")} onChange={(event) => onToolSearchChange(event.target.value)} />
        <button className="button muted" onClick={() => void onRefreshTools()} disabled={!selectedAgentId}>{t("Refresh", "刷新")}</button>
      </div>
      <ToolCatalog
        t={t}
        selectedAgentId={selectedAgentId}
        selectedAgentArchived={selectedAgentArchived}
        toolBusyId={toolBusyId}
        tools={tools}
        onToggleTool={onToggleTool}
        onViewToolDetails={onViewToolDetails}
      />
      <ToolProbeForm
        t={t}
        selectedAgentId={selectedAgentId}
        selectedAgentArchived={selectedAgentArchived}
        toolProbeInput={toolProbeInput}
        toolProbeExpected={toolProbeExpected}
        toolProbeBusy={toolProbeBusy}
        toolProbeResult={toolProbeResult}
        onToolProbeInputChange={onToolProbeInputChange}
        onToolProbeExpectedChange={onToolProbeExpectedChange}
        onRunToolProbe={onRunToolProbe}
      />
    </div>
  );
}

type ToolCatalogProps = Pick<
  ToolInspectorTabProps,
  "t" | "selectedAgentId" | "selectedAgentArchived" | "toolBusyId" | "tools" | "onToggleTool" | "onViewToolDetails"
>;

function ToolCatalog({
  t,
  selectedAgentId,
  selectedAgentArchived,
  toolBusyId,
  tools,
  onToggleTool,
  onViewToolDetails,
}: ToolCatalogProps) {
  if (tools.length === 0) {
    return <p className="muted">{t("No tools found.", "未找到工具。")}</p>;
  }

  return (
    <div className="studio-stack">
      {tools.map((tool) => {
        const isAttached = Boolean(tool.attached_to_agent);
        const preview = summarizeDescription(tool.description || "", t("No description.", "暂无描述。"));
        return (
          <div key={tool.id} className="card tool-card" style={{ padding: 10 }}>
            <div className="tool-card-header">
              <strong className="tool-card-name">{tool.name}</strong>
              <button
                className={`button tool-action-button ${isAttached ? "danger" : "success"}`}
                onClick={() => void onToggleTool(tool)}
                disabled={toolBusyId === tool.id || !selectedAgentId || selectedAgentArchived}
              >
                {toolBusyId === tool.id ? t("Working...", "处理中...") : isAttached ? t("Detach", "卸载") : t("Attach", "挂载")}
              </button>
            </div>
            <div className="toolbar tool-card-actions">
              <button className="button muted tool-detail-button" title={t("View full details", "查看完整详情")} onClick={() => onViewToolDetails(tool)}>
                {t("View details", "查看详情")}
              </button>
            </div>
            <p className="muted tool-card-description" style={{ marginTop: 8 }}>{preview}</p>
          </div>
        );
      })}
    </div>
  );
}

type ToolProbeFormProps = Pick<
  ToolInspectorTabProps,
  | "t"
  | "selectedAgentId"
  | "selectedAgentArchived"
  | "toolProbeInput"
  | "toolProbeExpected"
  | "toolProbeBusy"
  | "toolProbeResult"
  | "onToolProbeInputChange"
  | "onToolProbeExpectedChange"
  | "onRunToolProbe"
>;

function ToolProbeForm({
  t,
  selectedAgentId,
  selectedAgentArchived,
  toolProbeInput,
  toolProbeExpected,
  toolProbeBusy,
  toolProbeResult,
  onToolProbeInputChange,
  onToolProbeExpectedChange,
  onRunToolProbe,
}: ToolProbeFormProps) {
  return (
    <div className="card" style={{ padding: 10 }}>
      <h4 style={{ margin: 0 }}>{t("Tool Probe (Phase-2)", "工具探测（Phase-2）")}</h4>
      <p className="muted" style={{ marginTop: 8 }}>{t("Sends a runtime message and reports detected tool calls/returns.", "发送运行时消息，并输出检测到的工具调用/返回统计。")}</p>
      <p className="muted" style={{ marginTop: 8 }}>{t("Uses the shared Agent Studio timeout and retry controls from the Chat panel.", "会使用聊天面板中的共享超时与重试控制。")}</p>
      <label className="field" style={{ marginTop: 8 }}>
        <span>{t("Probe input", "探测输入")}</span>
        <textarea className="input" style={{ minHeight: 84, resize: "vertical" }} value={toolProbeInput} onChange={(event) => onToolProbeInputChange(event.target.value)} />
      </label>
      <label className="field" style={{ marginTop: 8 }}>
        <span>{t("Expected tool name (optional)", "期望工具名（可选）")}</span>
        <input className="input" value={toolProbeExpected} onChange={(event) => onToolProbeExpectedChange(event.target.value)} placeholder={t("e.g. search_documents", "例如 search_documents")} />
      </label>
      <div className="toolbar" style={{ marginTop: 8 }}>
        <button className="button" onClick={() => void onRunToolProbe()} disabled={!selectedAgentId || toolProbeBusy || selectedAgentArchived}>
          {toolProbeBusy ? t("Running...", "运行中...") : t("Run Tool Probe", "运行工具探测")}
        </button>
      </div>
      {toolProbeResult ? (
        <div className="code" style={{ marginTop: 8 }}>
          tool_call_count: {toolProbeResult.tool_call_count}
          {"\n"}
          tool_return_count: {toolProbeResult.tool_return_count}
          {"\n"}
          expected_tool_name: {toolProbeResult.expected_tool_name || t("(none)", "（无）")}
          {"\n"}
          expected_tool_matched: {String(toolProbeResult.expected_tool_matched)}
        </div>
      ) : null}
    </div>
  );
}
