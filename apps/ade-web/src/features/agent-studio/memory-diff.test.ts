import { describe, expect, it } from "vitest";

import { highlightDiff } from "./memory-diff";

describe("Agent Studio memory diff", () => {
  it("renders additions and removals", () => {
    const html = highlightDiff("Dog: Rocky", "Dog: Rocky\nBreed: Husky");
    expect(html).toContain("diff-line-added");
    expect(html).toContain("Breed: Husky");
  });

  it("escapes memory content before rendering HTML", () => {
    const html = highlightDiff("<script>alert(1)</script>", "<img src=x onerror=alert(1)>");
    expect(html).not.toContain("<script>");
    expect(html).not.toContain("<img");
    expect(html).toContain("&lt;");
  });
});
