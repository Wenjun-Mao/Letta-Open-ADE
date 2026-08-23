import { describe, expect, it } from "vitest";

import { hydrateChatHistory } from "./chat-history";

describe("Agent Studio chat history hydration", () => {
  it("keeps user and assistant messages while excluding empty and non-chat rows", () => {
    const entries = hydrateChatHistory({
      memory_blocks: [],
      conversation_history: {
        total_persisted: 4,
        displayed: 4,
        items: [
          { id: "1", created_at: "", role: "user", message_type: "user_message", content: " hello\r\nworld " },
          { id: "2", created_at: "", role: "assistant", message_type: "assistant_message", content: " reply " },
          { id: "3", created_at: "", role: "tool", message_type: "tool_return", content: "ignored" },
          { id: "4", created_at: "", role: "assistant", message_type: "assistant_message", content: "  " },
        ],
      },
    });

    expect(entries).toEqual([
      { id: "1-u", role: "user", content: "hello\nworld", timingMs: null },
      { id: "2-a", role: "assistant", content: "reply", timingMs: null },
    ]);
  });
});
