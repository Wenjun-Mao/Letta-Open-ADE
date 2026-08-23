import type { AgentListItem } from "../../lib/api";
import type { AgentItem } from "./types";

export function mapAgentListItems(items: AgentListItem[]): AgentItem[] {
  return items.map((item) => ({
    id: item.id,
    name: item.name || item.id,
    model: item.model || "",
    created_at: item.created_at || "",
    last_updated_at: item.last_updated_at || "",
    last_interaction_at: item.last_interaction_at || "",
    archived: Boolean(item.archived),
  }));
}

export function resolveSelectedAgentId(agents: AgentItem[], selectedAgentId: string): string {
  if (selectedAgentId && agents.some((agent) => agent.id === selectedAgentId)) {
    return selectedAgentId;
  }
  return agents[0]?.id || "";
}
