import type { ScenarioOptions } from "@/features/model-catalog/api";

export type AgentCreationSettings = {
  model: string;
  promptKey: string;
  personaKey: string;
  embedding: string;
  temperature: string;
  topP: string;
  topK: string;
};

const DEFAULT_PROMPT_KEY = "chat_v20260516";
const DEFAULT_PERSONA_KEY = "chat_linxiaotang";

function optionKeyOrDefault(current: string, options: Array<{ key: string }>, fallback: string): string {
  if (current && options.some((option) => option.key === current)) {
    return current;
  }
  return fallback || options[0]?.key || "";
}

function optionKeyOrBlank(current: string, options: Array<{ key: string }>): string {
  return current && options.some((option) => option.key === current) ? current : "";
}

export function resolveInitialAgentCreationSettings(
  options: ScenarioOptions,
  search: string,
): AgentCreationSettings {
  const params = new URLSearchParams(search);
  const requestedPromptKey = (params.get("promptKey") || "").trim();
  const requestedPersonaKey = (params.get("personaKey") || "").trim();

  return {
    model: "",
    promptKey: optionKeyOrDefault(
      requestedPromptKey,
      options.prompts || [],
      options.defaults?.prompt_key || DEFAULT_PROMPT_KEY,
    ),
    personaKey: optionKeyOrDefault(
      requestedPersonaKey,
      options.personas || [],
      options.defaults?.persona_key || DEFAULT_PERSONA_KEY,
    ),
    embedding: options.defaults?.embedding || "",
    temperature: "",
    topP: "",
    topK: "",
  };
}

export function reconcileAgentCreationSettings(
  current: AgentCreationSettings,
  options: ScenarioOptions,
): AgentCreationSettings {
  return {
    model: optionKeyOrBlank(current.model, options.models || []),
    promptKey: optionKeyOrDefault(
      current.promptKey,
      options.prompts || [],
      options.defaults?.prompt_key || DEFAULT_PROMPT_KEY,
    ),
    personaKey: optionKeyOrDefault(
      current.personaKey,
      options.personas || [],
      options.defaults?.persona_key || DEFAULT_PERSONA_KEY,
    ),
    embedding:
      optionKeyOrBlank(current.embedding, options.embeddings || []) ||
      options.defaults?.embedding ||
      "",
    temperature: current.temperature || String(options.agent_studio?.temperature ?? ""),
    topP: current.topP || String(options.agent_studio?.top_p ?? ""),
    topK: current.topK || String(options.agent_studio?.top_k ?? ""),
  };
}
