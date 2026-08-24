export function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

export function asIntegerString(value: unknown): string {
  const parsed = Number(String(value ?? "").trim());
  return Number.isFinite(parsed) && Number.isInteger(parsed) ? String(parsed) : "";
}

export function formatLocalTimestamp(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function prettyJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}
