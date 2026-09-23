// @vitest-environment jsdom
import { act, useEffect } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import type { PromptTemplateRecord } from "@/features/prompt-center/api";

import type { AgentStudioSession } from "./types";
import { useDefinitionVersion } from "./use-definition-version";

const api = vi.hoisted(() => ({ listPromptTemplates: vi.fn(), listPersonaTemplates: vi.fn(), createAgentStudioDefinition: vi.fn() }));
vi.mock("@/features/prompt-center/api", () => ({ listPromptTemplates: api.listPromptTemplates, listPersonaTemplates: api.listPersonaTemplates }));
vi.mock("./api", () => ({ createAgentStudioDefinition: api.createAgentStudioDefinition }));

const template = (kind: "prompt" | "persona", content: string): PromptTemplateRecord => ({
  kind, scenario: "chat", key: kind, label: kind, description: "", content, preview: content,
  length: content.length, archived: false, source_path: kind, updated_at: "2026-09-22T00:00:00Z",
});
const definition: AgentStudioSession["agent_definition"] = {
  id: "version-1", agent_definition_id: "definition-1", definition_key: "native", version: 1,
  name: "Native", prompt_key: "prompt", prompt_sha256: "a", persona_key: "persona", persona_sha256: "b",
  tool_names: [], memory_policy_version: "v1", qualification_state: "qualified", archived_at: null,
  created_at: "2026-09-22T00:00:00Z", deployments: (["conversation", "reviewer", "retriever"] as const)
    .map((role) => ({ role, deployment_id: role, route_alias: role, fingerprint: role,
      lifecycle: "active", qualification_state: "qualified", fingerprint_payload: {} })),
};
const session = { agent_definition: definition } as AgentStudioSession;
let root: Root;
let container: HTMLDivElement;
let controller: ReturnType<typeof useDefinitionVersion>;
const setError = vi.fn();
function Probe() {
  const current = useDefinitionVersion({ session, definitions: [definition], refreshWorkspace: vi.fn(),
    setDefinitionChoice: vi.fn(), setBusy: vi.fn(), setError });
  useEffect(() => { controller = current; });
  return null;
}

beforeEach(() => {
  vi.clearAllMocks();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  container = document.createElement("div"); document.body.append(container); root = createRoot(container);
  api.listPromptTemplates.mockResolvedValue({ items: [template("prompt", "old prompt")] });
  api.listPersonaTemplates.mockResolvedValue({ items: [template("persona", "old persona")] });
});
afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = false;
});

it("refreshes an edited Prompt Center preview and requires review before creating a snapshot", async () => {
  await act(async () => { root.render(<Probe />); await Promise.resolve(); });
  expect(controller.personas[0].content).toBe("old persona");
  api.listPersonaTemplates.mockResolvedValue({ items: [template("persona", "edited persona")] });
  await act(async () => { await controller.createDefinitionVersion(); });
  expect(controller.personas[0].content).toBe("edited persona");
  expect(setError).toHaveBeenCalledWith(expect.stringContaining("Review the refreshed previews"));
  expect(api.createAgentStudioDefinition).not.toHaveBeenCalled();
  api.createAgentStudioDefinition.mockResolvedValue({ id: "version-2" });
  await act(async () => { await controller.createDefinitionVersion(); });
  expect(api.createAgentStudioDefinition).toHaveBeenCalledOnce();
});
