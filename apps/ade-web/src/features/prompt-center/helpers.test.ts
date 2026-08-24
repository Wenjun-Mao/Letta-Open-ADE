import { describe, expect, it } from "vitest";

import { buildWorkspaceLink, normalizeScenarioKey } from "./helpers";

describe("normalizeScenarioKey", () => {
  it("adds the selected scenario prefix and replaces a different scenario prefix", () => {
    expect(normalizeScenarioKey("demo", "comment")).toBe("comment_demo");
    expect(normalizeScenarioKey("chat_demo", "comment")).toBe("comment_demo");
  });

  it("keeps an empty key empty", () => {
    expect(normalizeScenarioKey("   ", "chat")).toBe("");
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
