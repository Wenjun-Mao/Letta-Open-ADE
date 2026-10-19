import { afterEach, describe, expect, it, vi } from "vitest";

import { createAgentStudioSession, getConversationState, listAgents, getRelationshipMemories, getMemorySource, retryMemoryDelivery, retryRun } from "./api";
import type { MemoryDelivery } from "./types";

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
      new_definition: { definition_key: "native", name: "Native", model_key: "model", compaction_model_key: "compaction", prompt_key: "chat", persona_key: "persona", tool_names: ["search_memory"] },
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

  it("requires subject and character for source reads and fences delivery Retry", async () => {
    const fetchMock = vi.fn().mockImplementation(async () => jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);
    await getRelationshipMemories("subject/1", "root/2", 100);
    await getMemorySource("subject/1", "root/2", "document/3");
    await retryMemoryDelivery("subject/1", "root/2", { operation_id: "operation-1", check_count: 5 } as MemoryDelivery);
    expect(fetchMock).toHaveBeenNthCalledWith(1, "/api/v3/memory/subjects/subject%2F1/characters/root%2F2/memories?limit=100&offset=100", expect.objectContaining({ method: "GET" }));
    expect(fetchMock).toHaveBeenNthCalledWith(2, "/api/v3/memory/subjects/subject%2F1/characters/root%2F2/sources/document%2F3", expect.objectContaining({ method: "GET" }));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/memory/subjects/subject%2F1/characters/root%2F2/deliveries/operation-1/retry",
      expect.objectContaining({ method: "POST", body: JSON.stringify({ expected_check_count: 5 }) }),
    );
  });

  it("retries a saved run without posting a new user message", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);
    await retryRun("run/1", 2, "same-key");
    expect(fetchMock).toHaveBeenCalledExactlyOnceWith("/api/v3/runs/run%2F1/retry", expect.objectContaining({
      method: "POST", body: JSON.stringify({ expected_attempt_count: 2, idempotency_key: "same-key" }),
    }));
  });
});
