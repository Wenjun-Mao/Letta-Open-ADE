import type { ToolCenterItem } from "./api";

export const DEFAULT_TOOL_SOURCE = `def my_custom_tool(input_text: str) -> str:
    \"\"\"Describe what this tool does.\"\"\"
    return f\"echo: {input_text}\"
`;

export type ViewMode = "create" | "edit";

export function toErrorMessage(value: unknown): string {
  return value instanceof Error ? value.message : String(value);
}

export function getToolIdentifier(item: Pick<ToolCenterItem, "slug" | "tool_id">): string {
  return item.slug || item.tool_id;
}

export function parseTags(value: string): string[] {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

export function isPrimaryActionDisabled({
  busy,
  loading,
  mode,
  selected,
}: {
  busy: boolean;
  loading: boolean;
  mode: ViewMode;
  selected: Pick<ToolCenterItem, "managed" | "archived"> | null;
}): boolean {
  return (
    busy ||
    loading ||
    (mode === "create"
      ? Boolean(selected && !selected.managed)
      : Boolean(!selected?.managed || selected.archived))
  );
}
