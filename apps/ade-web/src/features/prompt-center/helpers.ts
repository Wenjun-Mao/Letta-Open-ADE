import type { Scenario } from "@/features/model-catalog/api";

export type CenterTab = "prompts" | "personas";

export type PromptCenterLaunchState = {
  tab: CenterTab;
  scenario: Scenario;
  key: string;
};

const PROMPT_CENTER_TABS = new Set<CenterTab>(["prompts", "personas"]);
const PROMPT_CENTER_SCENARIOS = new Set<Scenario>(["chat", "comment", "label"]);

export function resolvePromptCenterLaunchState(search: string): PromptCenterLaunchState {
  const params = new URLSearchParams(search);
  const requestedTab = (params.get("tab") || "").trim() as CenterTab;
  const requestedScenario = (params.get("scenario") || "").trim() as Scenario;
  const scenario = PROMPT_CENTER_SCENARIOS.has(requestedScenario) ? requestedScenario : "chat";
  const tab = scenario === "label"
    ? "prompts"
    : PROMPT_CENTER_TABS.has(requestedTab)
      ? requestedTab
      : "prompts";

  return {
    tab,
    scenario,
    key: (params.get("key") || "").trim(),
  };
}

export function toErrorMessage(value: unknown): string {
  return value instanceof Error ? value.message : String(value);
}

export function normalizeScenarioKey(key: string, scenario: Scenario): string {
  const normalized = key.trim().toLowerCase();
  if (!normalized) {
    return "";
  }

  const withoutScenarioPrefix = normalized.replace(/^(chat|comment|label)_/, "");
  return `${scenario}_${withoutScenarioPrefix}`;
}

type WorkspaceLinkInput = {
  tab: CenterTab;
  scenario: Scenario;
  selectedKey: string;
  activePromptKeys: string[];
  activePersonaKeys: string[];
};

export function buildWorkspaceLink({
  tab,
  scenario,
  selectedKey,
  activePromptKeys,
  activePersonaKeys,
}: WorkspaceLinkInput): { href: string; destination: "agent-studio" | "comment-lab" | "label-lab" } {
  const promptKey = tab === "prompts" ? selectedKey || activePromptKeys[0] || "" : activePromptKeys[0] || "";
  const personaKey = tab === "personas" ? selectedKey || activePersonaKeys[0] || "" : activePersonaKeys[0] || "";
  const params = new URLSearchParams();
  if (promptKey) {
    params.set("promptKey", promptKey);
  }
  if (personaKey && scenario !== "label") {
    params.set("personaKey", personaKey);
  }
  if (scenario === "comment") {
    return { href: `/comment-lab?${params.toString()}`, destination: "comment-lab" };
  }
  if (scenario === "label") {
    return { href: `/label-lab?${params.toString()}`, destination: "label-lab" };
  }
  params.set("focus", "model");
  return { href: `/agent-studio?${params.toString()}`, destination: "agent-studio" };
}
