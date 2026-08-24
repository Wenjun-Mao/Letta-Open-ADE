import { describe, expect, it } from "vitest";

import { parseSchema, stringifySchema } from "./helpers";

describe("stringifySchema", () => {
  it("formats serializable schema objects for the editor", () => {
    expect(stringifySchema({ type: "object", properties: { title: { type: "string" } } })).toBe(
      '{\n  "type": "object",\n  "properties": {\n    "title": {\n      "type": "string"\n    }\n  }\n}',
    );
  });

  it("keeps the editor usable when a value cannot be serialized", () => {
    const circular: { self?: unknown } = {};
    circular.self = circular;

    expect(stringifySchema(circular)).toBe("{}");
  });
});

describe("parseSchema", () => {
  it("accepts JSON objects", () => {
    expect(parseSchema('{"type":"object"}')).toEqual({ type: "object" });
  });

  it.each(["[]", "null", '"string"'])("rejects non-object schema JSON: %s", (value) => {
    expect(() => parseSchema(value)).toThrow("Schema must be a JSON object.");
  });
});
