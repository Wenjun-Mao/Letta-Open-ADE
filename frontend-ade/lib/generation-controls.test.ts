import { describe, expect, it } from "vitest";

import {
  parseIntegerInRange,
  parseNonNegativeInteger,
  parseOptionalPositiveInteger,
  parsePositiveNumber,
  samplingDefaultString,
} from "./generation-controls";

describe("generation controls", () => {
  it("rejects partial and fractional integer input", () => {
    expect(parseNonNegativeInteger("5junk")).toBeNull();
    expect(parseNonNegativeInteger("2.5")).toBeNull();
    expect(parseNonNegativeInteger("0")).toBe(0);
  });

  it("enforces bounded retry counts", () => {
    expect(parseIntegerInRange("3", 0, 3)).toBe(3);
    expect(parseIntegerInRange("4", 0, 3)).toBeNull();
    expect(parseIntegerInRange("-1", 0, 5)).toBeNull();
  });

  it("handles optional positive integers without accepting junk", () => {
    expect(parseOptionalPositiveInteger(" ")).toBeUndefined();
    expect(parseOptionalPositiveInteger("20")).toBe(20);
    expect(parseOptionalPositiveInteger("20x")).toBeNull();
  });

  it("parses positive decimal controls strictly", () => {
    expect(parsePositiveNumber("0.25")).toBe(0.25);
    expect(parsePositiveNumber("0.25seconds")).toBeNull();
  });

  it("prefers scenario sampling defaults over generic defaults", () => {
    const option = {
      key: "model",
      label: "Model",
      description: "",
      sampling_defaults: { temperature: 0.8 },
      scenario_sampling_defaults: { comment_lab: { temperature: 0.4 } },
    };
    expect(samplingDefaultString(option, "comment_lab", "temperature")).toBe("0.4");
    expect(samplingDefaultString(option, "label_lab", "temperature")).toBe("0.8");
  });
});
