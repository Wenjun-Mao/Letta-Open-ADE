import { afterEach, describe, expect, it, vi } from "vitest";

import { requestJson } from "./client";

describe("requestJson", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("uses a same-origin API path for every browser request", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ enabled: true }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await requestJson<{ enabled: boolean }>("/api/v1/platform/capabilities");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/platform/capabilities",
      expect.objectContaining({ method: "GET", cache: "no-store" }),
    );
  });

  it("does not retain handwritten GET responses", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ items: [] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await requestJson("/api/v1/agents?limit=1");
    await requestJson("/api/v1/agents?limit=1");

    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("preserves backend detail messages", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Agent is archived" }), { status: 409 })));

    await expect(requestJson("/api/v1/chat")).rejects.toThrow("Agent is archived");
  });
});
