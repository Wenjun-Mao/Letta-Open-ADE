"use client";

import { useI18n } from "../../lib/i18n";
import { parseToolExamples } from "./formatters";
import { AgentDetailsInspector, AgentSetupControls } from "./inspector";
import { ChatPanel, ExecutionTracePanel } from "./panels";
import { useAgentCreation } from "./use-agent-creation";
import { useAgentInspection } from "./use-agent-inspection";
import { useAgentLifecycle } from "./use-agent-lifecycle";
import { useChatExecution } from "./use-chat-execution";
import { useExecutionTrace } from "./use-execution-trace";
import { useStudioNotices } from "./use-studio-notices";

export default function AgentStudioPage() {
  const { locale } = useI18n();
  const t = (english: string, chinese: string) => (locale === "zh" ? chinese : english);
  const notices = useStudioNotices();
  const lifecycle = useAgentLifecycle({ t, notices });
  const executionTrace = useExecutionTrace({ registerSelectionCleanup: lifecycle.registerSelectionCleanup });
  const chat = useChatExecution({
    t,
    notices,
    selectedAgentId: lifecycle.selectedAgentId,
    selectedAgentArchived: lifecycle.selectedAgentArchived,
    currentAgentRequest: lifecycle.currentAgentRequest,
    isCurrentAgentRequest: lifecycle.isCurrentAgentRequest,
    refreshSelectedAgent: lifecycle.refreshSelectedAgent,
    registerSelectionCleanup: lifecycle.registerSelectionCleanup,
    registerChatHistoryHydrator: lifecycle.registerChatHistoryHydrator,
    recordResult: executionTrace.recordResult,
  });
  const creation = useAgentCreation({ t, notices, onCreated: lifecycle.selectCreatedAgent });
  const inspection = useAgentInspection({
    locale,
    t,
    notices,
    models: creation.models,
    selectedAgentId: lifecycle.selectedAgentId,
    selectedAgentArchived: lifecycle.selectedAgentArchived,
    agentDetails: lifecycle.agentDetails,
    persistentState: lifecycle.persistentState,
    timeoutSeconds: chat.timeoutSeconds,
    retryCount: chat.retryCount,
    currentAgentRequest: lifecycle.currentAgentRequest,
    isCurrentAgentRequest: lifecycle.isCurrentAgentRequest,
    refreshSelectedAgent: lifecycle.refreshSelectedAgent,
    refreshAgentList: lifecycle.refreshAgentList,
    registerSelectionCleanup: lifecycle.registerSelectionCleanup,
    recordResult: executionTrace.recordResult,
  });

  const busy = creation.busy || lifecycle.busy;
  const loading = creation.loading || lifecycle.loading;
  const selectedAgentName = lifecycle.selectedAgentInfo?.name || "";
  const historyCount = Number(lifecycle.persistentState?.conversation_history?.total_persisted || 0);
  const memoryBlocks = lifecycle.persistentState?.memory_blocks || [];
  const personaValue = memoryBlocks.find((block) => block.label === "persona")?.value || "";
  const humanValue = memoryBlocks.find((block) => block.label === "human")?.value || "";
  const humanBefore = String(executionTrace.lastResult?.memory_diff?.old?.human || "");
  const humanAfter = String(executionTrace.lastResult?.memory_diff?.new?.human || "");
  const toolDetailTool = inspection.toolDetailTool;

  return (
    <section className="studio-root">
      <div className="kicker">{t("Merged Workspace", "合并工作区")}</div>
      <h1 className="section-title">{t("Agent Studio", "智能体工作台")}</h1>

      <div className="studio-layout">
        <aside className="card studio-panel">
          <h3>{t("Inspector", "检查面板")}</h3>

          <AgentSetupControls
            t={t}
            locale={locale}
            models={creation.models}
            prompts={creation.prompts}
            personas={creation.personas}
            embeddings={creation.embeddings}
            createName={creation.createName}
            createModel={creation.createModel}
            createPromptKey={creation.createPromptKey}
            createPersonaKey={creation.createPersonaKey}
            createEmbedding={creation.createEmbedding}
            createTemperature={creation.createTemperature}
            createTopP={creation.createTopP}
            createTopK={creation.createTopK}
            busy={busy}
            loading={loading}
            agents={lifecycle.agents}
            includeArchivedAgents={lifecycle.includeArchivedAgents}
            selectedAgentId={lifecycle.selectedAgentId}
            selectedAgentInfo={lifecycle.selectedAgentInfo}
            selectedAgentArchived={lifecycle.selectedAgentArchived}
            selectedAgentName={selectedAgentName}
            historyCount={historyCount}
            onCreateNameChange={creation.setCreateName}
            onCreateModelChange={creation.setCreateModel}
            onCreatePromptKeyChange={creation.setCreatePromptKey}
            onCreatePersonaKeyChange={creation.setCreatePersonaKey}
            onCreateEmbeddingChange={creation.setCreateEmbedding}
            onCreateTemperatureChange={creation.setCreateTemperature}
            onCreateTopPChange={creation.setCreateTopP}
            onCreateTopKChange={creation.setCreateTopK}
            onCreateAgent={creation.create}
            onRefreshAgents={lifecycle.refreshAgents}
            onReloadModels={creation.reloadModels}
            onIncludeArchivedAgentsChange={lifecycle.setIncludeArchivedAgents}
            onSelectAgent={lifecycle.selectAgent}
            onPullExistingInfo={lifecycle.pullExistingInfo}
            onRefreshPersistent={lifecycle.refreshPersistent}
            onArchiveAgent={lifecycle.archiveSelectedAgent}
            onRestoreAgent={lifecycle.restoreSelectedAgent}
            onPurgeAgent={lifecycle.purgeSelectedAgent}
          />

          <AgentDetailsInspector
            t={t}
            locale={locale}
            models={creation.models}
            agentDetails={lifecycle.agentDetails}
            inspectorTab={inspection.inspectorTab}
            selectedAgentId={lifecycle.selectedAgentId}
            selectedAgentArchived={lifecycle.selectedAgentArchived}
            modelEditValue={inspection.modelEditValue}
            modelBusy={inspection.modelBusy}
            personaValue={personaValue}
            humanValue={humanValue}
            revisionLoading={inspection.revisionLoading}
            revisionHistory={inspection.revisionHistory}
            toolSearch={inspection.toolSearch}
            tools={inspection.displayToolCatalog}
            toolBusyId={inspection.toolBusyId}
            toolProbeInput={inspection.toolProbeInput}
            toolProbeExpected={inspection.toolProbeExpected}
            toolProbeBusy={inspection.toolProbeBusy}
            toolProbeResult={inspection.toolProbeResult}
            onInspectorTabChange={inspection.setInspectorTab}
            onModelEditValueChange={inspection.setModelEditValue}
            onApplyModel={inspection.applyModel}
            onOpenEditor={inspection.openEditor}
            onRefreshRevisionHistory={() => inspection.refreshRevisionHistory()}
            onToolSearchChange={inspection.setToolSearch}
            onRefreshTools={() => inspection.refreshToolCatalog()}
            onToggleTool={inspection.toggleTool}
            onViewToolDetails={inspection.setToolDetailTool}
            onToolProbeInputChange={inspection.setToolProbeInput}
            onToolProbeExpectedChange={inspection.setToolProbeExpected}
            onRunToolProbe={inspection.runToolProbe}
          />
        </aside>

        <ChatPanel
          t={t}
          chatScrollRef={chat.chatScrollRef}
          chatHistory={chat.chatHistory}
          timeoutSeconds={chat.timeoutSeconds}
          retryCount={chat.retryCount}
          chatInput={chat.chatInput}
          chatBusy={chat.chatBusy}
          toolProbeBusy={inspection.toolProbeBusy}
          selectedAgentId={lifecycle.selectedAgentId}
          selectedAgentArchived={lifecycle.selectedAgentArchived}
          onTimeoutChange={chat.setTimeoutSeconds}
          onRetryCountChange={chat.setRetryCount}
          onChatInputChange={chat.setChatInput}
          onSendMessage={chat.sendMessage}
        />

        <ExecutionTracePanel
          t={t}
          locale={locale}
          lastLatencyMs={executionTrace.lastLatencyMs}
          timelineFilter={executionTrace.timelineFilter}
          timelineSteps={executionTrace.filteredTimelineSteps}
          hasLastResult={Boolean(executionTrace.lastResult)}
          humanBefore={humanBefore}
          humanAfter={humanAfter}
          showRawPrompt={inspection.showRawPrompt}
          rawPromptLoading={inspection.rawPromptLoading}
          rawPromptMessages={inspection.rawPromptMessages}
          selectedAgentId={lifecycle.selectedAgentId}
          selectedAgentArchived={lifecycle.selectedAgentArchived}
          busy={busy}
          persistentLimit={lifecycle.persistentLimit}
          persistentTab={inspection.persistentTab}
          persistentState={lifecycle.persistentState}
          onTimelineFilterChange={executionTrace.setTimelineFilter}
          onToggleRawPrompt={inspection.toggleRawPrompt}
          onRefreshPersistent={lifecycle.refreshPersistent}
          onPersistentLimitChange={lifecycle.setPersistentLimit}
          onPersistentTabChange={inspection.setPersistentTab}
          onOpenEditor={inspection.openEditor}
        />
      </div>

      {inspection.editorKind ? (
        <div className="editor-overlay">
          <div className="editor-card">
            <h3 style={{ marginTop: 0 }}>{t("Edit", "编辑")} {inspection.editorKind}</h3>
            <textarea
              className="input"
              style={{ minHeight: 260, resize: "vertical" }}
              value={inspection.editorValue}
              onChange={(event) => inspection.setEditorValue(event.target.value)}
            />
            <div className="toolbar" style={{ marginTop: 10, justifyContent: "flex-end" }}>
              <button className="button muted" onClick={inspection.closeEditor} disabled={inspection.editorBusy}>
                {t("Cancel", "取消")}
              </button>
              <button className="button" onClick={() => void inspection.saveEditor()} disabled={inspection.editorBusy}>
                {inspection.editorBusy ? t("Saving...", "保存中...") : t("Save", "保存")}
              </button>
            </div>
          </div>
        </div>
      ) : null}

      {toolDetailTool ? (
        <div
          className="editor-overlay"
          onClick={() => inspection.setToolDetailTool(null)}
          role="dialog"
          aria-modal="true"
          aria-label={t(`Tool details: ${toolDetailTool.name}`, `工具详情：${toolDetailTool.name}`)}
        >
          <div className="editor-card tool-detail-card" onClick={(event) => event.stopPropagation()}>
            <div className="tool-detail-header">
              <div>
                <h3 style={{ margin: 0 }}>{toolDetailTool.name}</h3>
                <div className="tool-detail-meta">
                  <span className="tool-detail-badge">{toolDetailTool.attached_to_agent ? t("Attached", "已挂载") : t("Not Attached", "未挂载")}</span>
                  <span className="tool-detail-badge">{t("Type", "类型")}: {toolDetailTool.tool_type || t("unknown", "未知")}</span>
                  <span className="tool-detail-badge">{t("Source", "来源")}: {toolDetailTool.source_type || t("unknown", "未知")}</span>
                </div>
              </div>
              <button className="button muted" onClick={() => inspection.setToolDetailTool(null)}>
                {t("Close (Esc)", "关闭（Esc）")}
              </button>
            </div>

            {(() => {
              const parsed = parseToolExamples(
                toolDetailTool.description || "",
                t("No description.", "暂无描述。"),
                t("No overview provided.", "未提供概述。"),
              );
              return (
                <>
                  <p className="tool-detail-overview">{parsed.overview}</p>
                  {parsed.examples.length > 0 ? (
                    <>
                      <div className="tool-detail-section-title">{t("Examples", "示例")}</div>
                      {parsed.examples.map((example, index) => (
                        <pre className="code tool-detail-code" key={`${toolDetailTool.id}-example-${index}`}>
                          {example}
                        </pre>
                      ))}
                    </>
                  ) : (
                    <>
                      <div className="tool-detail-section-title">{t("Full Description", "完整说明")}</div>
                      <pre className="code tool-detail-code">{toolDetailTool.description || t("No description.", "暂无描述。")}</pre>
                    </>
                  )}
                </>
              );
            })()}
          </div>
        </div>
      ) : null}

      {notices.status ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#bbf7d0" }}>
          <h3>{t("Status", "状态")}</h3>
          <p className="muted">{notices.status}</p>
        </div>
      ) : null}

      {notices.error ? (
        <div className="card" style={{ marginTop: 12, borderColor: "#fecaca" }}>
          <h3>{t("Error", "错误")}</h3>
          <p className="muted">{notices.error}</p>
        </div>
      ) : null}
    </section>
  );
}
