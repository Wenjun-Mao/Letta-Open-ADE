import { afterEach, describe, expect, it, vi } from "vitest";

import { createAgentStudioSession, getConversationState, listAgents } from "./api";

afterEach(() => vi.unstubAllGlobals());

function jsonResponse(payload: unknown): Response {
  return new Response(JSON.stringify(payload), { headers: { "Content-Type": "application/json" } });
}

describe("Agent Studio v3 browser client", () => {
  it("uses the session state endpoint with bounded message history", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await getConversationState("conversation/1", 42);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/agent-studio/sessions/conversation%2F1/state?message_limit=120&before_sequence=42",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("creates an atomic session with exactly one new definition and subject", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ conversation: { id: "conversation-1" } }));
    vi.stubGlobal("fetch", fetchMock);
    const payload: Parameters<typeof createAgentStudioSession>[0] = {
      idempotency_key: "session-1", title: "Memory test",
      new_definition: { definition_key: "native", name: "Native", model_key: "model", reviewer_model_key: "reviewer", embedding_model_key: "embedding", prompt_key: "chat", persona_key: "persona", tool_names: ["search_memory"] },
      new_subject: { external_key: "wei", display_name: "Wei" },
    };

    await createAgentStudioSession(payload);

    expect(fetchMock).toHaveBeenCalledWith("/api/v3/agent-studio/sessions", expect.objectContaining({
      method: "POST", body: JSON.stringify(payload),
    }));
  });

  it("keeps the dashboard count on native definitions rather than legacy agents", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ total: 0, items: [] }));
    vi.stubGlobal("fetch", fetchMock);

    await listAgents();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/agent-studio/definitions?limit=200&offset=0",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
