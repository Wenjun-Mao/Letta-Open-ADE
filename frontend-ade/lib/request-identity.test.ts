import { describe, expect, it } from "vitest";

import { isCurrentRequest } from "./request-identity";

describe("isCurrentRequest", () => {
  it("rejects a response after the selected resource changes", () => {
    expect(isCurrentRequest({ resourceId: "agent-a", version: 4 }, "agent-b", 5)).toBe(false);
  });

  it("rejects a superseded refresh for the same resource", () => {
    expect(isCurrentRequest({ resourceId: "run-a", version: 4 }, "run-a", 5)).toBe(false);
  });

  it("accepts the active resource request", () => {
    expect(isCurrentRequest({ resourceId: "run-a", version: 5 }, "run-a", 5)).toBe(true);
  });
});
