import { describe, expect, it } from "vitest";

import {
  agentPlatformApiAuthorization,
  agentPlatformApiBaseUrl,
  buildAgentPlatformApiHeaders,
  buildAgentPlatformApiUrl,
} from "./agent-platform-api-proxy";

describe("Agent Platform API proxy URL", () => {
  it("keeps the API path and query string while using the server-side base URL", () => {
    const base = agentPlatformApiBaseUrl("http://agent_platform_api:8284/internal/");
    const target = buildAgentPlatformApiUrl(["agents", "agent-123", "persistent_state"], "?limit=120", base);

    expect(target.toString()).toBe("http://agent_platform_api:8284/internal/api/v1/agents/agent-123/persistent_state?limit=120");
  });

  it("requires a configured server-side base URL", () => {
    expect(() => agentPlatformApiBaseUrl("")).toThrow("AGENT_PLATFORM_API_BASE_URL must be configured");
  });

  it("builds authorization only from the server-side API key", () => {
    expect(agentPlatformApiAuthorization("  trusted-key  ")).toBe("Bearer trusted-key");
    expect(() => agentPlatformApiAuthorization(" ")).toThrow("AGENT_PLATFORM_API_KEY must be configured");
  });

  it("does not let browser credentials override the trusted server key", () => {
    const incoming = new Headers({
      accept: "application/json",
      authorization: "Bearer browser-controlled",
      cookie: "session=browser-controlled",
      "x-request-id": "request-123",
    });
    const headers = buildAgentPlatformApiHeaders(incoming, "Bearer server-controlled");

    expect(headers.get("authorization")).toBe("Bearer server-controlled");
    expect(headers.get("accept")).toBe("application/json");
    expect(headers.get("x-request-id")).toBe("request-123");
    expect(headers.has("cookie")).toBe(false);
  });
});
