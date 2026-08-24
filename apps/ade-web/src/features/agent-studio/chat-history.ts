import type { PersistentState } from "./api";
import type { ChatEntry } from "./types";

export function hydrateChatHistory(persistentState: PersistentState): ChatEntry[] {
  const hydrated: ChatEntry[] = [];
  for (const item of persistentState.conversation_history?.items || []) {
    const messageType = String(item.message_type || "").toLowerCase();
    const content = String(item.content || "").replace(/\r\n/g, "\n").trim();
    if (!content) {
      continue;
    }
    if (messageType === "user_message") {
      hydrated.push({ id: `${item.id}-u`, role: "user", content, timingMs: null });
    }
    if (messageType === "assistant_message") {
      hydrated.push({ id: `${item.id}-a`, role: "assistant", content, timingMs: null });
    }
  }
  return hydrated;
}
