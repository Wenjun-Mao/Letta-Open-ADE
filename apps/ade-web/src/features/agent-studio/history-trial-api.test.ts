import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("uses evaluation trial resource URLs only in the explicit trial build", async () => {
  vi.stubEnv("NEXT_PUBLIC_HISTORY_TRIAL", "1");
  vi.resetModules();
  const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ total: 0, items: [] }), {
    headers: { "Content-Type": "application/json" },
  }));
  vi.stubGlobal("fetch", fetchMock);
  const { HISTORY_TRIAL, listAgentStudioSessions, listConversationRuns } = await import("./api");

  await listAgentStudioSessions();
  await listConversationRuns("chat-1");

  expect(HISTORY_TRIAL).toBe(true);
  expect(fetchMock).toHaveBeenNthCalledWith(1,
    "/api/v3/history-trial/sessions?limit=200&offset=0",
    expect.objectContaining({ method: "GET" }),
  );
  expect(fetchMock).toHaveBeenNthCalledWith(2,
    "/api/v3/conversations/chat-1/runs",
    expect.objectContaining({ method: "GET" }),
  );
});
