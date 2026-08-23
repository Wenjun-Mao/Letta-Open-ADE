# ADR 0002: One Retry Owner And A Transparent Router

## Status

Accepted and implemented.

## Context

Retry behavior at a router, SDK, and feature service can multiply one user action
into several provider calls. That breaks the request-scoped retry controls shown
by ADE and makes latency, cost, and failure behavior unpredictable.

## Decision

- The feature/application request policy owns transient-provider retry counts.
- `retry_count` means additional attempts after the initial request.
- The model router forwards a request once and does not add an undisclosed retry.
- Each layer must preserve timeout and retry intent without silently broadening it.

## Consequences

Tests must count upstream attempts for zero and nonzero retries. Provider-specific
compatibility retries require an explicit, separately documented exception rather
than becoming a general retry policy.

The model router uses a lifespan-managed shared HTTP client and makes one forwarding
attempt. Agent Studio forwards request-scoped timeout and retry values to the Letta
SDK, while Comment Lab and Label Lab own their bounded transient-failure loops.
Attempt-count tests cover zero and nonzero retries so a future transport wrapper
cannot silently multiply calls.
