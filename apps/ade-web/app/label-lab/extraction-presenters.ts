import type { LabelExtractionResult } from "../../lib/api";

export function formatGroupLabel(key: string): string {
  return key
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

export function normalizeExtractionGroups(
  value: LabelExtractionResult,
): Array<{ key: string; items: string[] }> {
  return Object.entries(value || {})
    .filter(([key, items]) => key.trim().length > 0 && Array.isArray(items))
    .map(([key, items]) => ({
      key,
      items: items
        .map((item) => String(item ?? "").trim())
        .filter((item) => item.length > 0),
    }));
}
