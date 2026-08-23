import { describe, expect, it } from "vitest";

import { chooseOptionKey } from "./selection";

describe("chooseOptionKey", () => {
  const options = [{ key: "first" }, { key: "backend-default" }];

  it("keeps a current valid choice", () => {
    expect(chooseOptionKey("backend-default", options, "first")).toBe("backend-default");
  });

  it("uses a valid backend default before the first option", () => {
    expect(chooseOptionKey("", options, "backend-default")).toBe("backend-default");
  });

  it("falls back to the first option only when no preferred key is valid", () => {
    expect(chooseOptionKey("missing", options, "also-missing")).toBe("first");
  });
});
