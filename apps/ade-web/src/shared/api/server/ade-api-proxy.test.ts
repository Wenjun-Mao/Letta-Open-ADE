import { describe, expect, it } from "vitest";

import {
  adeApiAuthorization,
  adeApiBaseUrl,
  adeNativeApiBaseUrl,
  buildAdeApiHeaders,
  buildAdeApiUrl,
  nativePreviewProxyEnabled,
} from "./ade-api-proxy";

describe("ADE API proxy URL", () => {
  it("keeps the API path and query string while using the server-side base URL", () => {
    const base = adeApiBaseUrl("http://ade-api:8000/internal/");
    const target = buildAdeApiUrl(["agent-studio", "agents", "agent-123", "persistent-state"], "?limit=120", base);

    expect(target.toString()).toBe("http://ade-api:8000/internal/api/v2/agent-studio/agents/agent-123/persistent-state?limit=120");
  });

  it("requires a configured server-side base URL", () => {
    expect(() => adeApiBaseUrl("")).toThrow("ADE_API_BASE_URL must be configured");
  });

  it("keeps native v3 traffic on its dedicated server-side base URL", () => {
    const base = adeNativeApiBaseUrl("http://ade-native-api:8000/");
    const target = buildAdeApiUrl(["runs", "run-1", "events"], "", base, "v3");

    expect(target.toString()).toBe("http://ade-native-api:8000/api/v3/runs/run-1/events");
  });

  it("builds authorization only from the server-side API key", () => {
    expect(adeApiAuthorization("  trusted-key  ")).toBe("Bearer trusted-key");
    expect(() => adeApiAuthorization(" ")).toThrow("ADE_API_ADMIN_KEY must be configured");
  });

  it("does not let browser credentials override the trusted server key", () => {
    const incoming = new Headers({
      accept: "application/json",
      authorization: "Bearer browser-controlled",
      cookie: "session=browser-controlled",
      "x-request-id": "request-123",
      "last-event-id": "7",
    });
    const headers = buildAdeApiHeaders(incoming, "Bearer server-controlled");

    expect(headers.get("authorization")).toBe("Bearer server-controlled");
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.get("x-request-id")).toBe("request-123");
    expect(headers.get("last-event-id")).toBe("7");
    expect(headers.has("cookie")).toBe(false);
  });

  it("keeps the native proxy closed unless the server runtime gate is explicit", () => {
    expect(nativePreviewProxyEnabled(undefined)).toBe(false);
    expect(nativePreviewProxyEnabled("false")).toBe(false);
    expect(nativePreviewProxyEnabled(" TRUE ")).toBe(true);
  });
});
