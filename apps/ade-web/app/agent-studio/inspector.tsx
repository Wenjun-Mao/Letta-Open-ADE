import type {
  AgentDetails,
  OptionEntry,
  PlatformTool,
  PlatformToolTestInvokeResult,
  PromptPersonaRevisionRecord,
} from "../../lib/api";
import { formatModelOptionLabel } from "../../lib/generation-controls";
import { formatTimestamp, shortId, summarizeDescription } from "./formatters";
import type { AgentItem, EditorKind, InspectorTab } from "./types";

type Translate = (english: string, chinese: string) => string;
type SetText = (value: string) => void;

type AgentSetupControlsProps = {
  t: Translate;
  locale: "en" | "zh";
  models: OptionEntry[];
  prompts: OptionEntry[];
  personas: OptionEntry[];
  embeddings: OptionEntry[];
  createName: string;
  createModel: string;
  createPromptKey: string;
  createPersonaKey: string;
  createEmbedding: string;
  createTemperature: string;
  createTopP: string;
  createTopK: string;
  busy: boolean;
  loading: boolean;
  agents: AgentItem[];
  includeArchivedAgents: boolean;
  selectedAgentId: string;
  selectedAgentInfo: AgentItem | null;
  selectedAgentArchived: boolean;
  selectedAgentName: string;
  historyCount: number;
  onCreateNameChange: SetText;
  onCreateModelChange: SetText;
  onCreatePromptKeyChange: SetText;
  onCreatePersonaKeyChange: SetText;
  onCreateEmbeddingChange: SetText;
  onCreateTemperatureChange: SetText;
  onCreateTopPChange: SetText;
  onCreateTopKChange: SetText;
  onCreateAgent: () => Promise<void>;
  onRefreshAgents: () => Promise<void>;
  onReloadModels: () => Promise<void>;
  onIncludeArchivedAgentsChange: (value: boolean) => void;
  onSelectAgent: SetText;
  onPullExistingInfo: () => Promise<void>;
  onRefreshPersistent: () => Promise<void>;
  onArchiveAgent: () => Promise<void>;
  onRestoreAgent: () => Promise<void>;
  onPurgeAgent: () => Promise<void>;
};

export function AgentSetupControls({
  t,
  locale,
  models,
  prompts,
  personas,
  embeddings,
  createName,
  createModel,
  createPromptKey,
  createPersonaKey,
  createEmbedding,
  createTemperature,
  createTopP,
  createTopK,
  busy,
  loading,
  agents,
  includeArchivedAgents,
  selectedAgentId,
  selectedAgentInfo,
  selectedAgentArchived,
  selectedAgentName,
  historyCount,
  onCreateNameChange,
  onCreateModelChange,
  onCreatePromptKeyChange,
  onCreatePersonaKeyChange,
  onCreateEmbeddingChange,
  onCreateTemperatureChange,
  onCreateTopPChange,
  onCreateTopKChange,
  onCreateAgent,
  onRefreshAgents,
  onReloadModels,
  onIncludeArchivedAgentsChange,
  onSelectAgent,
  onPullExistingInfo,
  onRefreshPersistent,
  onArchiveAgent,
  onRestoreAgent,
  onPurgeAgent,
}: AgentSetupControlsProps) {
  const modelLabel = (option: OptionEntry) =>
    formatModelOptionLabel(option, t(" [Unavailable]", " [不可用]"));

  return (
    <>
      <div className="form-grid">
        <label className="field">
          <span>{t("New agent name", "新建智能体名称")}</span>
          <input className="input" value={createName} onChange={(event) => onCreateNameChange(event.target.value)} />
        </label>
        <label className="field">
          <span>{t("Model", "模型")}</span>
          <select className="input" value={createModel} onChange={(event) => onCreateModelChange(event.target.value)}>
            <option value="">{t("Select model", "选择模型")}</option>
            {models.map((item) => <option key={item.key} value={item.key}>{modelLabel(item)}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{t("Prompt", "提示词")}</span>
          <select className="input" value={createPromptKey} onChange={(event) => onCreatePromptKeyChange(event.target.value)}>
            {prompts.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{t("Persona", "Persona")}</span>
          <select className="input" value={createPersonaKey} onChange={(event) => onCreatePersonaKeyChange(event.target.value)}>
            {personas.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{t("Embedding", "向量模型")}</span>
          <select className="input" value={createEmbedding} onChange={(event) => onCreateEmbeddingChange(event.target.value)}>
            <option value="">{t("Use server default", "使用服务端默认值")}</option>
            {embeddings.map((item) => <option key={item.key} value={item.key}>{item.label}</option>)}
          </select>
        </label>
        <label className="field">
          <span>{t("Temperature (optional)", "Temperature（可选）")}</span>
          <input
            className="input"
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={createTemperature}
            onChange={(event) => onCreateTemperatureChange(event.target.value)}
            placeholder={t("Use model default", "使用模型默认值")}
          />
        </label>
        <label className="field">
          <span>{t("Top P (optional)", "Top P（可选）")}</span>
          <input
            className="input"
            type="number"
            min={0.01}
            max={1}
            step={0.05}
            value={createTopP}
            onChange={(event) => onCreateTopPChange(event.target.value)}
            placeholder={t("Use model default", "使用模型默认值")}
          />
        </label>
        <label className="field">
          <span>{t("Top K (optional)", "Top K（可选）")}</span>
          <input
            className="input"
            type="number"
            min={1}
            step={1}
            value={createTopK}
            onChange={(event) => onCreateTopKChange(event.target.value)}
            placeholder={t("Use model default", "使用模型默认值")}
          />
        </label>
      </div>

      <div className="toolbar" style={{ marginTop: 10 }}>
        <button className="button" onClick={() => void onCreateAgent()} disabled={busy || loading}>
          {busy ? t("Creating...", "创建中...") : t("Create Agent", "创建智能体")}
        </button>
        <button className="button muted" onClick={() => void onRefreshAgents()} disabled={busy || loading}>
          {t("Refresh Agents", "刷新智能体列表")}
        </button>
        <button className="button muted" onClick={() => void onReloadModels()} disabled={busy || loading}>
          {t("Reload Models", "重新加载模型")}
        </button>
      </div>

      <hr className="studio-divider" />

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
  tools: PlatformTool[];
  toolBusyId: string;
  toolProbeInput: string;
  toolProbeExpected: string;
  toolProbeBusy: boolean;
  toolProbeResult: PlatformToolTestInvokeResult | null;
  onInspectorTabChange: (tab: InspectorTab) => void;
  onModelEditValueChange: SetText;
  onApplyModel: () => Promise<void>;
  onOpenEditor: (kind: Exclude<EditorKind, null>, value: string) => void;
  onRefreshRevisionHistory: () => Promise<void>;
  onToolSearchChange: SetText;
  onRefreshTools: () => Promise<boolean | void>;
  onToggleTool: (tool: PlatformTool) => Promise<void>;
  onViewToolDetails: (tool: PlatformTool) => void;
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

  const modelLabel = (option: OptionEntry) =>
    formatModelOptionLabel(option, t(" [Unavailable]", " [不可用]"));

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
      ) : null}

      {inspectorTab === "prompt" ? (
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
        </div>
      ) : null}

      {inspectorTab === "tools" ? (
        <div className="studio-stack">
          <div className="toolbar">
            <input className="input" value={toolSearch} placeholder={t("Search tools", "搜索工具")} onChange={(event) => onToolSearchChange(event.target.value)} />
            <button className="button muted" onClick={() => void onRefreshTools()} disabled={!selectedAgentId}>{t("Refresh", "刷新")}</button>
          </div>
          {tools.length === 0 ? (
            <p className="muted">{t("No tools found.", "未找到工具。")}</p>
          ) : (
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
          )}

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
        </div>
      ) : null}
    </>
  );
}
