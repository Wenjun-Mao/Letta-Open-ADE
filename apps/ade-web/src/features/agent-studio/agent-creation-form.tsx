import type { OptionEntry } from "@/features/model-catalog/api";
import { formatModelOptionLabel } from "@/shared/generation-controls";

import { AgentEvaluationHandoffCard } from "./agent-evaluation-handoff-card";
import type { Translate } from "./types";

type SetText = (value: string) => void;

export type AgentCreationFormProps = {
  t: Translate;
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
  timeoutSeconds: string;
  retryCount: string;
  busy: boolean;
  loading: boolean;
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
};

export function AgentCreationForm({
  t,
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
  timeoutSeconds,
  retryCount,
  busy,
  loading,
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
}: AgentCreationFormProps) {
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

      <AgentEvaluationHandoffCard
        t={t}
        createModel={createModel}
        createPromptKey={createPromptKey}
        createPersonaKey={createPersonaKey}
        createEmbedding={createEmbedding}
        timeoutSeconds={timeoutSeconds}
        retryCount={retryCount}
      />
    </>
  );
}
