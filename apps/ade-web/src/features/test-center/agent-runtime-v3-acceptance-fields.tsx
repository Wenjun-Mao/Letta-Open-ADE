import type { ModelCatalogEntry } from "@/features/model-catalog/contracts";

import type { TestCenterCopy } from "./test-center-copy";

export type AgentRuntimeV3AcceptanceForm = {
  conversationModelKey: string;
  reviewerModelKey: string;
  embeddingModelKey: string;
  rounds: string;
  timeoutSeconds: string;
  retryCount: string;
  includeLlamaCompatibility: boolean;
};

export const DEFAULT_AGENT_RUNTIME_V3_ACCEPTANCE_FORM: AgentRuntimeV3AcceptanceForm = {
  conversationModelKey: "dgx_vllm::qwen3.6-35b-a3b-fp8",
  reviewerModelKey: "dgx_vllm::qwen3.6-35b-a3b-fp8",
  embeddingModelKey: "dgx_embedding_sidecar::qwen3-embedding-0.6b",
  rounds: "3",
  timeoutSeconds: "180",
  retryCount: "0",
  includeLlamaCompatibility: true,
};

function chooseRoleDeployment(
  current: string,
  preferred: string,
  role: "conversation" | "reviewer" | "retriever",
  deployments: ModelCatalogEntry[],
): string {
  const candidates = deployments.filter((item) => item.deployment?.roles.includes(role));
  const keys = new Set(candidates.map((item) => item.model_key));
  if (keys.has(current)) {
    return current;
  }
  if (keys.has(preferred)) {
    return preferred;
  }
  return candidates[0]?.model_key || current || preferred;
}

export function reconcileAgentRuntimeV3AcceptanceForm(
  current: AgentRuntimeV3AcceptanceForm,
  deployments: ModelCatalogEntry[],
): AgentRuntimeV3AcceptanceForm {
  return {
    ...current,
    conversationModelKey: chooseRoleDeployment(
      current.conversationModelKey,
      DEFAULT_AGENT_RUNTIME_V3_ACCEPTANCE_FORM.conversationModelKey,
      "conversation",
      deployments,
    ),
    reviewerModelKey: chooseRoleDeployment(
      current.reviewerModelKey,
      DEFAULT_AGENT_RUNTIME_V3_ACCEPTANCE_FORM.reviewerModelKey,
      "reviewer",
      deployments,
    ),
    embeddingModelKey: chooseRoleDeployment(
      current.embeddingModelKey,
      DEFAULT_AGENT_RUNTIME_V3_ACCEPTANCE_FORM.embeddingModelKey,
      "retriever",
      deployments,
    ),
  };
}

export function hasAgentRuntimeV3AcceptanceDeployments(
  deployments: ModelCatalogEntry[],
): boolean {
  return (["conversation", "reviewer", "retriever"] as const).every((role) =>
    deployments.some((item) => item.deployment?.roles.includes(role)),
  );
}

function deploymentLabel(entry: ModelCatalogEntry, role: string): string {
  const deployment = entry.deployment;
  if (!deployment) {
    return entry.model_key;
  }
  const roleResult = deployment.qualification.role_results.find((item) => item.role === role);
  const progress = roleResult
    ? `${roleResult.consecutive_passing_rounds}/3`
    : "0/3";
  return `${entry.source_label}: ${entry.provider_model_id} (${deployment.lifecycle}, ${progress})`;
}

type Props = {
  copy: TestCenterCopy;
  deployments: ModelCatalogEntry[];
  form: AgentRuntimeV3AcceptanceForm;
  onChange: (form: AgentRuntimeV3AcceptanceForm) => void;
};

export function AgentRuntimeV3AcceptanceFields({ copy, deployments, form, onChange }: Props) {
  const conversationModels = deployments.filter((item) => item.deployment?.roles.includes("conversation"));
  const reviewerModels = deployments.filter((item) => item.deployment?.roles.includes("reviewer"));
  const embeddingModels = deployments.filter((item) => item.deployment?.roles.includes("retriever"));
  const set = <Key extends keyof AgentRuntimeV3AcceptanceForm>(
    key: Key,
    value: AgentRuntimeV3AcceptanceForm[Key],
  ) => onChange({ ...form, [key]: value });

  return (
    <>
      <p className="muted" style={{ gridColumn: "1 / -1", margin: 0 }}>
        {copy.nativeRuntimeRequirement}
      </p>
      {!hasAgentRuntimeV3AcceptanceDeployments(deployments) ? (
        <p className="muted" style={{ gridColumn: "1 / -1", margin: 0, color: "#b91c1c" }}>
          {copy.nativeRuntimeDeploymentsUnavailable}
        </p>
      ) : null}
      <label className="field">
        <span>{copy.conversationModel}</span>
        <select className="input" value={form.conversationModelKey} onChange={(event) => set("conversationModelKey", event.target.value)}>
          {conversationModels.map((entry) => (
            <option key={entry.model_key} value={entry.model_key}>{deploymentLabel(entry, "conversation")}</option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>{copy.reviewerModel}</span>
        <select className="input" value={form.reviewerModelKey} onChange={(event) => set("reviewerModelKey", event.target.value)}>
          {reviewerModels.map((entry) => (
            <option key={entry.model_key} value={entry.model_key}>{deploymentLabel(entry, "reviewer")}</option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>{copy.retrieverModel}</span>
        <select className="input" value={form.embeddingModelKey} onChange={(event) => set("embeddingModelKey", event.target.value)}>
          {embeddingModels.map((entry) => (
            <option key={entry.model_key} value={entry.model_key}>{deploymentLabel(entry, "retriever")}</option>
          ))}
        </select>
      </label>
      <label className="field">
        <span>{copy.rounds}</span>
        <input className="input" type="number" min={1} max={3} value={form.rounds} onChange={(event) => set("rounds", event.target.value)} />
      </label>
      <label className="field">
        <span>{copy.timeoutSeconds}</span>
        <input className="input" type="number" min={5} max={600} value={form.timeoutSeconds} onChange={(event) => set("timeoutSeconds", event.target.value)} />
      </label>
      <label className="field">
        <span>{copy.retryCount}</span>
        <input className="input" type="number" min={0} max={5} value={form.retryCount} onChange={(event) => set("retryCount", event.target.value)} />
      </label>
      <label className="field checkbox-field">
        <input type="checkbox" checked={form.includeLlamaCompatibility} onChange={(event) => set("includeLlamaCompatibility", event.target.checked)} />
        <span>{copy.llamaCompatibility}</span>
      </label>
    </>
  );
}
