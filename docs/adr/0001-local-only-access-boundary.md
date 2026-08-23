# ADR 0001: Local-Only Access Boundary

## Status

Accepted and implemented for the default local Compose deployment. Public ingress
remains intentionally unsupported.

## Context

ADE can create agents, modify content, run evaluations, and manage tools. Those
operations are not safe to expose as an unauthenticated development service.

## Decision

- Default developer bindings stay local to the host.
- Any non-local deployment must use an explicit authenticated ingress and a
  reviewed, narrow CORS policy.
- Agent Platform routes are separated into reader, operator, and administrator
  capabilities enforced with server-side bearer credentials.
- Health endpoints remain public so container health checks do not need secrets.
- Diagnostics redact credentials and raw provider diagnostics require an explicit
  opt-in plus administrator access.

## Consequences

The local baseline is protected by loopback port bindings, fail-closed API
authentication, narrow CORS configuration, server-only frontend credentials, and
black-box authorization tests. These controls do not make the stack production
ready. A LAN or internet deployment still needs reviewed ingress, TLS, secret
management, rate limits, monitoring, and a deployment-specific threat review.
