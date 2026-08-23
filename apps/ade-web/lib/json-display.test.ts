import { describe, expect, it } from "vitest";

import { asIntegerString, asRecord, prettyJson } from "./json-display";

describe("JSON display helpers", () => {
  it("accepts records but not arrays", () => {
    expect(asRecord({ value: 1 })).toEqual({ value: 1 });
    expect(asRecord([1])).toEqual({});
  });

  it("formats only finite integer counters", () => {
    expect(asIntegerString("12")).toBe("12");
    expect(asIntegerString("12.5")).toBe("");
    expect(asIntegerString("12 tokens")).toBe("");
  });

  it("falls back safely for cyclic values", () => {
    const cyclic: { self?: unknown } = {};
    cyclic.self = cyclic;
    expect(prettyJson(cyclic)).toBe("[object Object]");
  });
});
