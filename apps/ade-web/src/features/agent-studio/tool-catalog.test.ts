import { describe, expect, it } from "vitest";

import { buildDisplayToolCatalog, isToolAttached } from "./tool-catalog";

describe("Agent Studio tool catalog", () => {
  const persistentState = {
    memory_blocks: [],
    tools: [{ id: "tool-b", name: "Beta", description: "" }],
    conversation_history: { total_persisted: 0, displayed: 0, items: [] },
  };

  it("derives attachment from persistent state and sorts attached tools first", () => {
    const catalog = buildDisplayToolCatalog(
      [
        { id: "tool-a", name: "Alpha", description: "", tool_type: "", source_type: "", created_at: "", last_updated_at: "", tags: [] },
        { id: "tool-b", name: "Beta", description: "", tool_type: "", source_type: "", created_at: "", last_updated_at: "", tags: [] },
      ],
      persistentState,
    );

    expect(catalog.map((tool) => [tool.id, tool.attached_to_agent])).toEqual([
      ["tool-b", true],
      ["tool-a", false],
    ]);
    expect(isToolAttached(catalog[0], persistentState)).toBe(true);
  });
});
