import { describe, expect, it } from "vitest";

import {
  buildWorkspaceLink,
  normalizeScenarioKey,
  resolvePromptCenterLaunchState,
} from "./helpers";

describe("normalizeScenarioKey", () => {
  it("adds the selected scenario prefix and replaces a different scenario prefix", () => {
    expect(normalizeScenarioKey("demo", "comment")).toBe("comment_demo");
    expect(normalizeScenarioKey("chat_demo", "comment")).toBe("comment_demo");
  });

  it("keeps an empty key empty", () => {
    expect(normalizeScenarioKey("   ", "chat")).toBe("");
  });
});

describe("resolvePromptCenterLaunchState", () => {
  it("hydrates a prompt or persona selection from a deep link", () => {
    expect(
      resolvePromptCenterLaunchState(
        "?tab=personas&scenario=chat&key=chat_linxiaotang",
      ),
    ).toEqual({
      tab: "personas",
      scenario: "chat",
      key: "chat_linxiaotang",
    });
  });

  it("falls back safely and never selects personas for Label Lab", () => {
    expect(
      resolvePromptCenterLaunchState(
        "?tab=personas&scenario=label&key=label_generic_entities_v1",
      ),
    ).toEqual({
      tab: "prompts",
      scenario: "label",
      key: "label_generic_entities_v1",
    });
    expect(resolvePromptCenterLaunchState("?tab=nope&scenario=nope")).toEqual({
      tab: "prompts",
      scenario: "chat",
      key: "",
    });
  });
});

describe("buildWorkspaceLink", () => {
  it("opens Agent Studio with the selected system prompt and first active persona", () => {
    expect(
      buildWorkspaceLink({
        tab: "prompts",
        scenario: "chat",
        selectedKey: "chat_custom",
        activePromptKeys: ["chat_default", "chat_custom"],
        activePersonaKeys: ["chat_persona"],
      }),
    ).toEqual({
      href: "/agent-studio?promptKey=chat_custom&personaKey=chat_persona&focus=model",
      destination: "agent-studio",
    });
  });

  it("keeps Comment Lab selections in their respective query parameters", () => {
    expect(
      buildWorkspaceLink({
        tab: "personas",
        scenario: "comment",
        selectedKey: "comment_persona",
        activePromptKeys: ["comment_default"],
        activePersonaKeys: ["comment_persona"],
      }),
    ).toEqual({
      href: "/comment-lab?promptKey=comment_default&personaKey=comment_persona",
      destination: "comment-lab",
    });
  });

  it("does not send a persona parameter to Label Lab", () => {
    expect(
      buildWorkspaceLink({
        tab: "prompts",
        scenario: "label",
        selectedKey: "label_default",
        activePromptKeys: ["label_default"],
        activePersonaKeys: ["chat_persona"],
      }),
    ).toEqual({
      href: "/label-lab?promptKey=label_default",
      destination: "label-lab",
    });
  });
});
