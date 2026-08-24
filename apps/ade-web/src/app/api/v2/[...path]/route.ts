import { NextRequest } from "next/server";

import {
  HOP_BY_HOP_RESPONSE_HEADERS,
  adeApiAuthorization,
  adeApiBaseUrl,
  buildAdeApiHeaders,
  buildAdeApiUrl,
} from "@/shared/api/server/ade-api-proxy";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

type RouteContext = { params: Promise<{ path: string[] }> };

function proxyError(status: number, detail: string): Response {
  return Response.json({ detail }, { status, headers: { "Cache-Control": "no-store" } });
}

async function proxy(request: NextRequest, context: RouteContext): Promise<Response> {
  let target: URL;
  let authorization: string;
  try {
    const { path } = await context.params;
    target = buildAdeApiUrl(path, request.nextUrl.search, adeApiBaseUrl());
    authorization = adeApiAuthorization();
  } catch (error) {
    return proxyError(500, error instanceof Error ? error.message : "ADE API proxy is not configured.");
  }

  const headers = buildAdeApiHeaders(request.headers, authorization);

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer(),
      cache: "no-store",
      redirect: "manual",
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Unable to reach ADE API.";
    return proxyError(502, `ADE API proxy request failed: ${detail}`);
  }

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, name) => {
    if (!HOP_BY_HOP_RESPONSE_HEADERS.has(name.toLowerCase())) {
      responseHeaders.set(name, value);
    }
  });
  responseHeaders.set("Cache-Control", "no-store");

  return new Response(await upstream.arrayBuffer(), {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
