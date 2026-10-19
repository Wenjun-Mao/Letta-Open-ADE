import { afterEach, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
  vi.resetModules();
});

it("cannot redirect the maintained client into retired trial routes", async () => {
  vi.stubEnv("NEXT_PUBLIC_HISTORY_TRIAL", "1");
  vi.resetModules();
  const fetchMock = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ total: 0, items: [] }), {
    headers: { "Content-Type": "application/json" },
  }));
  vi.stubGlobal("fetch", fetchMock);
  const { listAgentStudioSessions, listConversationRuns } = await import("./api");

  await listAgentStudioSessions();
  await listConversationRuns("chat-1");

  expect(fetchMock).toHaveBeenNthCalledWith(1,
    "/api/v3/agent-studio/sessions?limit=200&offset=0",
    expect.objectContaining({ method: "GET" }),
  );
  expect(fetchMock).toHaveBeenNthCalledWith(2,
    "/api/v3/conversations/chat-1/runs",
    expect.objectContaining({ method: "GET" }),
  );
});
