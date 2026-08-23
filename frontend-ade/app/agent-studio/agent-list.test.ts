import { describe, expect, it } from "vitest";

import { mapAgentListItems, resolveSelectedAgentId } from "./agent-list";

describe("Agent Studio agent list helpers", () => {
  const agents = mapAgentListItems([
    {
      id: "agent-1",
      name: "",
      model: "model-1",
      created_at: "created",
      last_updated_at: "updated",
      last_interaction_at: "",
      archived: false,
    },
    {
      id: "agent-2",
      name: "Second",
      model: "model-2",
      created_at: "created",
      last_updated_at: "updated",
      last_interaction_at: "later",
      archived: true,
    },
  ]);

  it("normalizes API list items for the selector", () => {
    expect(agents[0]).toMatchObject({ id: "agent-1", name: "agent-1", archived: false });
    expect(agents[1]).toMatchObject({ id: "agent-2", name: "Second", archived: true });
  });

  it("preserves a selected agent only while it remains in the list", () => {
    expect(resolveSelectedAgentId(agents, "agent-2")).toBe("agent-2");
    expect(resolveSelectedAgentId(agents, "removed-agent")).toBe("agent-1");
    expect(resolveSelectedAgentId([], "agent-1")).toBe("");
  });
});
