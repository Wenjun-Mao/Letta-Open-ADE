import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

const routeContext = {
  params: Promise.resolve({ path: ["runs", "run-1", "events"] }),
};

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("native v3 route proxy", () => {
  it("always forwards to the dedicated native service and exposes SSE chunks without buffering", async () => {
    const encoder = new TextEncoder();
    let streamController: ReadableStreamDefaultController<Uint8Array> | undefined;
    const upstreamBody = new ReadableStream<Uint8Array>({
      start(controller) {
        streamController = controller;
        controller.enqueue(encoder.encode("id: 8\nevent: run.started\ndata: {}\n\n"));
      },
    });
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(upstreamBody, {
        headers: { "Content-Type": "text/event-stream; charset=utf-8" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubEnv("ADE_NATIVE_API_BASE_URL", "http://ade-native-api:8000");
    vi.stubEnv("ADE_API_ADMIN_KEY", "server-secret");

    const response = await GET(
      new NextRequest("http://localhost/api/v3/runs/run-1/events", {
        headers: { "Last-Event-ID": "7" },
      }),
      routeContext,
    );

    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toContain("text/event-stream");
    expect(fetchMock).toHaveBeenCalledOnce();
    const [target, init] = fetchMock.mock.calls[0] as [URL, RequestInit];
    expect(target.toString()).toBe(
      "http://ade-native-api:8000/api/v3/runs/run-1/events",
    );
    const forwardedHeaders = init.headers as Headers;
    expect(forwardedHeaders.get("authorization")).toBe("Bearer server-secret");
    expect(forwardedHeaders.get("last-event-id")).toBe("7");

    const reader = response.body?.getReader();
    expect(reader).toBeDefined();
    const first = await reader!.read();
    expect(new TextDecoder().decode(first.value)).toBe(
      "id: 8\nevent: run.started\ndata: {}\n\n",
    );
    expect(first.done).toBe(false);

    streamController!.enqueue(
      encoder.encode("id: 9\nevent: run.succeeded\ndata: {}\n\n"),
    );
    streamController!.close();
    const second = await reader!.read();
    expect(new TextDecoder().decode(second.value)).toBe(
      "id: 9\nevent: run.succeeded\ndata: {}\n\n",
    );
    await expect(reader!.read()).resolves.toEqual({ done: true, value: undefined });
  });
});
