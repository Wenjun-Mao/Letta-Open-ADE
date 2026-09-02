const API_BASE_URL_ENV = "ADE_API_BASE_URL";
const NATIVE_API_BASE_URL_ENV = "ADE_NATIVE_API_BASE_URL";
const API_KEY_ENV = "ADE_API_ADMIN_KEY";

export function adeApiBaseUrl(value = process.env[API_BASE_URL_ENV]): URL {
  if (!value?.trim()) {
    throw new Error(`${API_BASE_URL_ENV} must be configured for the ADE API proxy.`);
  }

  try {
    return new URL(value);
  } catch {
    throw new Error(`${API_BASE_URL_ENV} must be a valid absolute URL.`);
  }
}

export function adeNativeApiBaseUrl(value = process.env[NATIVE_API_BASE_URL_ENV]): URL {
  if (!value?.trim()) {
    throw new Error(`${NATIVE_API_BASE_URL_ENV} must be configured for the ADE native API proxy.`);
  }

  try {
    return new URL(value);
  } catch {
    throw new Error(`${NATIVE_API_BASE_URL_ENV} must be a valid absolute URL.`);
  }
}

export function adeApiAuthorization(value = process.env[API_KEY_ENV]): string {
  const apiKey = value?.trim();
  if (!apiKey) {
    throw new Error(`${API_KEY_ENV} must be configured for the ADE API proxy.`);
  }
  return `Bearer ${apiKey}`;
}

export function buildAdeApiUrl(
  pathSegments: string[],
  search: string,
  baseUrl = adeApiBaseUrl(),
  version: "v2" | "v3" = "v2",
): URL {
  const target = new URL(baseUrl.toString());
  target.pathname = `${target.pathname.replace(/\/$/, "")}/api/${version}/${pathSegments.map(encodeURIComponent).join("/")}`;
  target.search = search;
  return target;
}

export function buildAdeApiHeaders(
  incoming: Headers,
  authorization = adeApiAuthorization(),
): Headers {
  const headers = new Headers();
  for (const name of ["accept", "content-type", "last-event-id", "x-request-id"]) {
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
