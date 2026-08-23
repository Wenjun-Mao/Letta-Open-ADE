import type { PlatformTool, PersistentState } from "../../lib/api";

function attachedToolIds(persistentState: PersistentState | null): Set<string> {
  return new Set(
    (persistentState?.tools || [])
      .map((tool) => tool.id)
      .filter(Boolean),
  );
}

export function buildDisplayToolCatalog(
  catalog: PlatformTool[],
  persistentState: PersistentState | null,
): PlatformTool[] {
  const attached = attachedToolIds(persistentState);
  return catalog
    .map((tool) => ({ ...tool, attached_to_agent: tool.attached_to_agent ?? attached.has(tool.id) }))
    .sort((left, right) => {
      const leftAttached = Boolean(left.attached_to_agent);
      const rightAttached = Boolean(right.attached_to_agent);
      if (leftAttached !== rightAttached) {
        return leftAttached ? -1 : 1;
      }

      const byName = String(left.name || "").localeCompare(String(right.name || ""), undefined, {
        sensitivity: "base",
      });
      return byName || String(left.id || "").localeCompare(String(right.id || ""));
    });
}

export function isToolAttached(tool: PlatformTool, persistentState: PersistentState | null): boolean {
  return Boolean(tool.attached_to_agent ?? attachedToolIds(persistentState).has(tool.id));
}
