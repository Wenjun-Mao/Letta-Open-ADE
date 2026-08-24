import { describe, expect, it } from "vitest";

import { DEFAULT_TOOL_SOURCE, getToolIdentifier, isPrimaryActionDisabled, parseTags } from "./helpers";

describe("parseTags", () => {
  it("trims and omits empty comma-separated values", () => {
    expect(parseTags(" search, ,utility,  search ")).toEqual(["search", "utility", "search"]);
  });
});

describe("getToolIdentifier", () => {
  it("uses a managed slug before the provider tool id", () => {
    expect(getToolIdentifier({ slug: "custom_search", tool_id: "tool-123" })).toBe("custom_search");
    expect(getToolIdentifier({ tool_id: "tool-123" })).toBe("tool-123");
  });
});

describe("isPrimaryActionDisabled", () => {
  it("protects built-in and archived tools while allowing new managed tools", () => {
    expect(isPrimaryActionDisabled({ busy: false, loading: false, mode: "create", selected: null })).toBe(false);
    expect(
      isPrimaryActionDisabled({
        busy: false,
        loading: false,
        mode: "create",
        selected: { managed: false, archived: false },
      }),
    ).toBe(true);
    expect(
      isPrimaryActionDisabled({
        busy: false,
        loading: false,
        mode: "edit",
        selected: { managed: true, archived: true },
      }),
    ).toBe(true);
  });
});

describe("DEFAULT_TOOL_SOURCE", () => {
  it("retains the starter function shown for a new custom tool", () => {
    expect(DEFAULT_TOOL_SOURCE).toContain("def my_custom_tool(input_text: str) -> str:");
  });
});
