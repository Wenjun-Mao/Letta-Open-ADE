import { afterEach, describe, expect, it, vi } from "vitest";

import { requestJson } from "./client";

describe("requestJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses a same-origin API path for every browser request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ enabled: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await requestJson<{ status: string }>("/api/v2/health");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v2/health",
      expect.objectContaining({ method: "GET", cache: "no-store" }),
    );
  });

  it("does not retain handwritten GET responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await requestJson("/api/v3/agent-studio/sessions?limit=1");
    await requestJson("/api/v3/agent-studio/sessions?limit=1");

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("allows the v3 same-origin proxy", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ status: "ready" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await requestJson("/api/v3/worker-health");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v3/worker-health",
      expect.objectContaining({ method: "GET", cache: "no-store" }),
    );
  });

  it("preserves backend detail messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Agent is archived" }), { status: 409 })));

    await expect(requestJson("/api/v3/conversations/conversation-1/turns")).rejects.toThrow("Agent is archived");
  });
});
