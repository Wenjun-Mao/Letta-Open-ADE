export type RequestOptions = {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
};

function requireApiPath(path: string): string {
  if (!path.startsWith("/api/v1/")) {
    throw new Error(`API path must start with /api/v1/: ${path}`);
  }
  return path;
}

function errorFromPayload(payloadText: string, fallback: string): Error {
  if (!payloadText) {
    return new Error(fallback);
  }

  try {
    const parsed = JSON.parse(payloadText) as { detail?: unknown };
    const detail = parsed?.detail;
    if (typeof detail === "string" && detail.trim()) {
      return new Error(detail);
    }
    if (detail && typeof detail === "object" && !Array.isArray(detail)) {
      const value = detail as Record<string, unknown>;
      const message = typeof value.message === "string" ? value.message.trim() : "";
      const validationErrors = Array.isArray(value.validation_errors)
        ? value.validation_errors.map((item) => String(item ?? "").trim()).filter(Boolean)
        : [];
      if (message || validationErrors.length) {
        return new Error([message, ...validationErrors].filter(Boolean).join("\n"));
      }
    }
  } catch (error) {
    if (!(error instanceof SyntaxError)) {
      return error instanceof Error ? error : new Error(String(error));
    }
  }

  return new Error(payloadText || fallback);
}

export function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = options.method || "GET";
  const requestPath = requireApiPath(path);
  let response: Response;

  try {
    response = await fetch(requestPath, {
      method,
      cache: "no-store",
      headers: { "Content-Type": "application/json" },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
    });
  } catch (error) {
    if (isAbortError(error)) {
      throw error;
    }
    const message = error instanceof Error ? error.message : String(error ?? "network request failed");
    throw new Error(`${method} ${requestPath} failed: ${message}`);
  }

  if (!response.ok) {
    throw errorFromPayload(await response.text(), `Request failed ${response.status}: ${requestPath}`);
  }

  return (await response.json()) as T;
}
