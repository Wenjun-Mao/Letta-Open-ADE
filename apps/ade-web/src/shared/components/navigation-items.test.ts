import { describe, expect, it } from "vitest";

import { ALL_NAVIGATION_ITEMS, NAVIGATION_GROUPS, buildNavigationGroups } from "./navigation-items";

describe("ADE navigation information architecture", () => {
  it("groups every existing route into one conceptual workspace", () => {
    expect(NAVIGATION_GROUPS.map((group) => group.key)).toEqual([
      "build",
      "content",
      "evaluate",
      "operations",
    ]);
    expect(ALL_NAVIGATION_ITEMS.map((item) => item.href)).toEqual([
      "/",
      "/agent-studio",
      "/comment-lab",
      "/label-lab",
      "/schema-center",
      "/prompt-center",
      "/tool-center",
      "/test-center",
      "/api-docs",
    ]);
  });

  it("keeps behavior evaluation distinct from build, content, and operations", () => {
    const evaluateGroup = NAVIGATION_GROUPS.find((group) => group.key === "evaluate");

    expect(evaluateGroup?.items).toEqual([{ href: "/test-center", key: "testCenter" }]);
  });

  it("adds the native pilot to operations only when its build gate is enabled", () => {
    const operations = buildNavigationGroups(true).find((group) => group.key === "operations");

    expect(operations?.items).toEqual([
      { href: "/native-runtime-preview", key: "nativeRuntimePreview" },
      { href: "/api-docs", key: "apiDocs" },
    ]);
  });
});
