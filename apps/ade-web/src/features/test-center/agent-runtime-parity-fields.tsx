import type { ModelCatalogEntry } from "@/features/model-catalog/contracts";

import type { OptionEntry } from "@/features/model-catalog/api";

import type { TestCenterCopy } from "./test-center-copy";

export type AgentRuntimeParityForm = {
  legacyModel: string;
  legacyEmbedding: string;
  promptKey: string;
  personaKey: string;
  nativeConversationModel: string;
  nativeReviewerModel: string;
  nativeEmbeddingModel: string;
  rounds: string;
  timeoutSeconds: string;
};

export type AgentRuntimeParityOptions = {
  legacyModels: OptionEntry[];
  legacyEmbeddings: OptionEntry[];
  prompts: OptionEntry[];
  personas: OptionEntry[];
  nativeDeployments: ModelCatalogEntry[];
};

export const DEFAULT_AGENT_RUNTIME_PARITY_FORM: AgentRuntimeParityForm = {
  legacyModel: "openai-proxy/dgx_vllm::qwen3.6-35b-a3b-fp8",
  legacyEmbedding: "letta/letta-free",
  promptKey: "chat_v20260516",
  personaKey: "chat_linxiaotang",
  nativeConversationModel: "dgx_vllm::qwen3.6-35b-a3b-fp8",
  nativeReviewerModel: "dgx_vllm::qwen3.6-35b-a3b-fp8",
  nativeEmbeddingModel: "dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B",
  rounds: "3",
  timeoutSeconds: "180",
};

function chooseOption(current: string, preferred: string, options: OptionEntry[]): string {
  const keys = new Set(options.map((option) => option.key));
  if (keys.has(current)) {
    return current;
  }
  if (keys.has(preferred)) {
    return preferred;
  }
  return options[0]?.key || current || preferred;
}

function chooseDeployment(
  current: string,
  preferred: string,
  role: "conversation" | "reviewer" | "retriever",
  deployments: ModelCatalogEntry[],
): string {
  const candidates = deployments.filter((entry) => entry.deployment?.roles.includes(role));
  const keys = new Set(candidates.map((entry) => entry.model_key));
  if (keys.has(current)) {
    return current;
  }
  if (keys.has(preferred)) {
    return preferred;
  }
  return candidates[0]?.model_key || current || preferred;
}

export function reconcileAgentRuntimeParityForm(
  current: AgentRuntimeParityForm,
  options: AgentRuntimeParityOptions,
): AgentRuntimeParityForm {
  return {
    ...current,
    legacyModel: chooseOption(
      current.legacyModel,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.legacyModel,
      options.legacyModels,
    ),
    legacyEmbedding: chooseOption(
      current.legacyEmbedding,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.legacyEmbedding,
      options.legacyEmbeddings,
    ),
    promptKey: chooseOption(
      current.promptKey,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.promptKey,
      options.prompts,
    ),
    personaKey: chooseOption(
      current.personaKey,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.personaKey,
      options.personas,
    ),
    nativeConversationModel: chooseDeployment(
      current.nativeConversationModel,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.nativeConversationModel,
      "conversation",
      options.nativeDeployments,
    ),
    nativeReviewerModel: chooseDeployment(
      current.nativeReviewerModel,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.nativeReviewerModel,
      "reviewer",
      options.nativeDeployments,
    ),
    nativeEmbeddingModel: chooseDeployment(
      current.nativeEmbeddingModel,
      DEFAULT_AGENT_RUNTIME_PARITY_FORM.nativeEmbeddingModel,
      "retriever",
      options.nativeDeployments,
    ),
  };
}

export function hasAgentRuntimeParityInputs(options: AgentRuntimeParityOptions): boolean {
  const requiredNativeRoles = ["conversation", "reviewer", "retriever"] as const;
  return (
    options.legacyModels.length > 0
    && options.legacyEmbeddings.length > 0
    && options.prompts.length > 0
    && options.personas.length > 0
    && requiredNativeRoles.every((role) =>
      options.nativeDeployments.some((entry) => entry.deployment?.roles.includes(role)),
    )
  );
}

function deploymentLabel(entry: ModelCatalogEntry, role: string): string {
  const deployment = entry.deployment;
  if (!deployment) {
    return entry.model_key;
  }
  const qualification = deployment.qualification.role_results.find((result) => result.role === role);
  const progress = qualification ? `${qualification.consecutive_passing_rounds}/3` : "0/3";
  return `${entry.source_label}: ${entry.provider_model_id} (${deployment.lifecycle}, ${progress})`;
}

type Props = {
  copy: TestCenterCopy;
  options: AgentRuntimeParityOptions;
  form: AgentRuntimeParityForm;
  onChange: (form: AgentRuntimeParityForm) => void;
};

export function AgentRuntimeParityFields({ copy, options, form, onChange }: Props) {
  const nativeConversationModels = options.nativeDeployments.filter((entry) => entry.deployment?.roles.includes("conversation"));
  const nativeReviewerModels = options.nativeDeployments.filter((entry) => entry.deployment?.roles.includes("reviewer"));
  const nativeEmbeddingModels = options.nativeDeployments.filter((entry) => entry.deployment?.roles.includes("retriever"));
  const set = <Key extends keyof AgentRuntimeParityForm>(key: Key, value: AgentRuntimeParityForm[Key]) =>
    onChange({ ...form, [key]: value });

  return (
    <>
      <p className="muted" style={{ gridColumn: "1 / -1", margin: 0 }}>
        {copy.parityRequirement}
      </p>
      {!hasAgentRuntimeParityInputs(options) ? (
        <p className="muted" style={{ gridColumn: "1 / -1", margin: 0, color: "#b91c1c" }}>
          {copy.parityInputsUnavailable}
        </p>
      ) : null}
      <label className="field">
        <span>{copy.parityPrompt}</span>
        <select className="input" value={form.promptKey} onChange={(event) => set("promptKey", event.target.value)}>
          {options.prompts.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.parityPersona}</span>
        <select className="input" value={form.personaKey} onChange={(event) => set("personaKey", event.target.value)}>
          {options.personas.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.parityLegacyModel}</span>
        <select className="input" value={form.legacyModel} onChange={(event) => set("legacyModel", event.target.value)}>
          {options.legacyModels.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.parityLegacyEmbedding}</span>
        <select className="input" value={form.legacyEmbedding} onChange={(event) => set("legacyEmbedding", event.target.value)}>
          {options.legacyEmbeddings.map((option) => <option key={option.key} value={option.key}>{option.label}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.parityNativeConversationModel}</span>
        <select className="input" value={form.nativeConversationModel} onChange={(event) => set("nativeConversationModel", event.target.value)}>
          {nativeConversationModels.map((entry) => <option key={entry.model_key} value={entry.model_key}>{deploymentLabel(entry, "conversation")}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.parityNativeReviewerModel}</span>
        <select className="input" value={form.nativeReviewerModel} onChange={(event) => set("nativeReviewerModel", event.target.value)}>
          {nativeReviewerModels.map((entry) => <option key={entry.model_key} value={entry.model_key}>{deploymentLabel(entry, "reviewer")}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.parityNativeEmbeddingModel}</span>
        <select className="input" value={form.nativeEmbeddingModel} onChange={(event) => set("nativeEmbeddingModel", event.target.value)}>
          {nativeEmbeddingModels.map((entry) => <option key={entry.model_key} value={entry.model_key}>{deploymentLabel(entry, "retriever")}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{copy.rounds}</span>
        <select className="input" value={form.rounds} onChange={(event) => set("rounds", event.target.value)}>
          <option value="1">{copy.parityRoundsOne}</option>
          <option value="2">{copy.parityRoundsTwo}</option>
          <option value="3">{copy.parityRoundsThree}</option>
        </select>
      </label>
      <label className="field">
        <span>{copy.timeoutSeconds}</span>
        <input
          className="input"
          type="number"
          min="5"
          max="600"
          value={form.timeoutSeconds}
          onChange={(event) => set("timeoutSeconds", event.target.value)}
          aria-describedby="parity-controls-help"
        />
      </label>
      <label className="field">
        <span>{copy.retryCount}</span>
        <input className="input" type="number" value="0" disabled aria-describedby="parity-controls-help" />
      </label>
      <p id="parity-controls-help" className="muted" style={{ gridColumn: "1 / -1", margin: 0 }}>
        {copy.parityRetryLocked}
      </p>
    </>
  );
}
