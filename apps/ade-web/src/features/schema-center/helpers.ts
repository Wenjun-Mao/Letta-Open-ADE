export function toErrorMessage(value: unknown): string {
  return value instanceof Error ? value.message : String(value);
}

export function stringifySchema(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "{}";
  }
}

export function parseSchema(text: string): Record<string, unknown> {
  const parsed = JSON.parse(text) as unknown;
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Schema must be a JSON object.");
  }
  return parsed as Record<string, unknown>;
}
