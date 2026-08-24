# ADR 0004: Frontend Uses A Same-Origin API Proxy

## Status

Accepted and implemented.

## Context

Browser bundles compile `NEXT_PUBLIC_*` values at build time. A runtime Compose
environment cannot safely or reliably retarget a public browser API base URL, and
the browser should not receive privileged API credentials.

## Decision

- Browser API calls use relative, same-origin paths.
- The ADE Web server proxies those paths to ADE API using runtime
  configuration and server-only credentials.
- The backend's CORS policy is narrowed to the deployment boundary rather than
  serving as the browser integration mechanism.

## Consequences

Remote deployment configuration becomes runtime-configurable without rebuilding
the browser bundle. The proxy ignores browser-supplied authorization and cookies,
injects its server-only credential, and forwards request bodies, query strings,
responses, errors, and streaming bodies. Route tests cover those boundaries, and a
repository guardrail rejects reintroduction of a public ADE API base URL.
