const API_BASE_URL_ENV = "AGENT_PLATFORM_API_BASE_URL";
const API_KEY_ENV = "AGENT_PLATFORM_API_KEY";

export function agentPlatformApiBaseUrl(value = process.env[API_BASE_URL_ENV]): URL {
  if (!value?.trim()) {
    throw new Error(`${API_BASE_URL_ENV} must be configured for the ADE API proxy.`);
  }

  try {
    return new URL(value);
  } catch {
    throw new Error(`${API_BASE_URL_ENV} must be a valid absolute URL.`);
  }
}

export function agentPlatformApiAuthorization(value = process.env[API_KEY_ENV]): string {
  const apiKey = value?.trim();
  if (!apiKey) {
    throw new Error(`${API_KEY_ENV} must be configured for the ADE API proxy.`);
  }
  return `Bearer ${apiKey}`;
}

export function buildAgentPlatformApiUrl(pathSegments: string[], search: string, baseUrl = agentPlatformApiBaseUrl()): URL {
  const target = new URL(baseUrl.toString());
  target.pathname = `${target.pathname.replace(/\/$/, "")}/api/v1/${pathSegments.map(encodeURIComponent).join("/")}`;
  target.search = search;
  return target;
}

export function buildAgentPlatformApiHeaders(
  incoming: Headers,
  authorization = agentPlatformApiAuthorization(),
): Headers {
  const headers = new Headers();
  for (const name of ["accept", "content-type", "x-request-id"]) {
    const value = incoming.get(name);
    if (value) {
      headers.set(name, value);
    }
  }
  headers.set("authorization", authorization);
  return headers;
}

export const HOP_BY_HOP_RESPONSE_HEADERS = new Set([
  "connection",
  "content-encoding",
  "content-length",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
]);
