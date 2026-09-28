// @vitest-environment jsdom
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";

import { AgentStudioView } from "./agent-studio-view";
import type { useAgentStudio } from "./use-agent-studio";

it("gives visible chat fields explicit selectable captions and accessible names", () => {
  const controller = {
    options: null, sessions: [], definitions: [], subjects: [], session: null,
    conversation: null, inspectedSubject: null, error: "", loading: false,
    busy: false, includeArchived: false, title: "New conversation",
    definitionChoice: "__new__", definitionName: "Companion",
    subjectChoice: "__new__", subjectName: "",
  } as unknown as ReturnType<typeof useAgentStudio>;
  const container = document.createElement("div");
  container.innerHTML = renderToStaticMarkup(<AgentStudioView controller={controller} t={(english) => english} />);
  for (const [id, caption] of [
    ["studio-chat-title", "Chat title"],
    ["studio-character-choice", "Character"],
    ["studio-person-choice", "Who is chatting?"],
    ["studio-person-name", "Your name"],
  ]) {
    const control = container.querySelector<HTMLInputElement | HTMLSelectElement>(`#${id}`);
    const captionId = control?.getAttribute("aria-labelledby");
    expect(container.querySelector(`#${captionId}`)?.textContent).toBe(caption);
    expect(control?.parentElement?.tagName).toBe("DIV");
  }
  expect(container.textContent).not.toContain("Stable external key");
  expect(container.textContent).not.toContain("Definition key");
});

it("keeps ordinary character version and persona preview controls available", () => {
  const definition = {
    id: "definition-v1", agent_definition_id: "character-root", definition_key: "character",
    version: 1, name: "Companion", prompt_key: "prompt", prompt_sha256: "a",
    persona_key: "persona", persona_sha256: "b", tool_names: [],
    memory_policy_version: "policy", qualification_state: "qualified",
    deployments: [], archived_at: null, created_at: "2026-09-27T00:00:00Z",
  };
  const subject = { id: "person-1", external_key: "opaque", display_name: "Alex",
    version: 1, archived_at: null, created_at: "2026-09-27T00:00:00Z", updated_at: null };
  const conversation = { id: "chat-1", agent_definition_id: definition.id,
    memory_subject_id: subject.id, title: "Hello", purpose: "agent_studio",
    version: 1, archived_at: null, created_at: "2026-09-27T00:00:00Z" };
  const controller = {
    options: null, sessions: [], definitions: [definition], subjects: [subject],
    session: { agent_definition: definition, memory_subject: subject, conversation, latest_run: null },
    conversation: { ...conversation, messages: [], next_before_sequence: null, summary: null },
    memories: { subject_id: subject.id, facts: [] }, inspectedSubject: null,
    runs: [], events: [], run: null, error: "", loading: false, busy: false,
    includeArchived: false, title: "New conversation", definitionChoice: definition.id,
    subjectChoice: subject.id, subjectRename: "", message: "", activeRun: false,
    prompts: [{ key: "prompt", label: "Prompt", content: "Prompt preview" }],
    personas: [{ key: "persona", label: "Persona", content: "Persona preview" }],
    versionPromptKey: "prompt", versionPersonaKey: "persona", versionName: "Next",
  } as unknown as ReturnType<typeof useAgentStudio>;
  const container = document.createElement("div");
  container.innerHTML = renderToStaticMarkup(<AgentStudioView controller={controller} t={(english) => english} />);
  const management = [...container.querySelectorAll("details")].find((item) => item.querySelector("summary")?.textContent === "Manage character versions");
  expect(management?.textContent).toContain("Open Prompt Center to edit persona");
  expect(management?.textContent).toContain("Prompt preview");
  expect(management?.textContent).toContain("Persona preview");
  expect(management?.querySelector("#studio-version-persona")?.getAttribute("aria-labelledby"))
    .toBe("studio-version-persona-caption");
});
