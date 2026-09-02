import type { AgentStudioBundle, AgentStudioOptions, AgentStudioSession, MemorySubject } from "./types";

export const NEW_RESOURCE_VALUE = "__new__";

export function selectedConversationFromQuery(value: string | null): string | null {
  const candidate = value?.trim() || "";
  return candidate || null;
}

export function defaultBundle(options: AgentStudioOptions | null): AgentStudioBundle | null {
  if (!options) return null;
  return options.bundles.find((bundle) => bundle.key === options.default_bundle_key) || options.bundles[0] || null;
}

export function activeSessionForConversation(
  sessions: AgentStudioSession[],
  conversationId: string | null,
): AgentStudioSession | null {
  if (!conversationId) return null;
  return sessions.find((session) => session.conversation.id === conversationId) || null;
}

export function isArchived(resource: { archived_at: string | null }): boolean {
  return Boolean(resource.archived_at);
}

export function defaultSubjectLabel(subject: MemorySubject): string {
  return subject.display_name.trim() || subject.external_key;
}

export function identityKey(prefix: string): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
