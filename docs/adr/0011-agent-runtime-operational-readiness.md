# ADR 0011: Agent Runtime Operational Readiness And Failure Evidence

- Status: Accepted
- Date: 2026-08-30
- Extends: [ADR 0009](0009-ade-owned-agent-runtime.md) and
  [ADR 0010](0010-production-path-runtime-qualification.md)

## Context

The native runtime originally proved successful execution but had two release-
observability gaps. A provider request that failed before an `AttemptResult` existed
left only attempt/run failure events, so operators could not identify the failing
stage or preserve earlier provider exchanges from that attempt. The API health route
also proved only that the HTTP process was running; an idle, absent, stale, or
incompatible worker was indistinguishable until a run remained pending.

Conversation leases cannot solve worker readiness. They exist only while a run is
owned and intentionally disappear when the worker is idle. Provider response bodies
and exception text also cannot be used as diagnostics because they may contain user
content or upstream implementation details.

## Decision

### Provider Failure Evidence

- Each ADE-owned attempt keeps an in-memory, stage-aware provider trace. Stages are
  `catalog`, `compaction`, `retrieval_query`, `conversation`, `tool_retrieval`,
  `reviewer`, and `memory_embeddings`.
- The trace emits causal `model.request.started`, `model.response.completed`,
  `model.request.failed`, and `model.request.cancelled` records with generated request
  IDs, stage, operation, request number, safe model identity, status/retry metadata,
  and latency.
- A completed chat request may additionally retain an allowlisted structural view:
  response-shape version, enum-valued choice/message/content/reasoning/tool-call
  states, capped counts, normalized finish reason, and bounded standard token-usage
  counters. Local validation failures use a stable detail code. Acceptance evidence
  carries that code with the run ID and last provider stage so a cleanup-safe failure
  remains diagnosable without retaining model content.
- If an attempt fails or is cancelled, its partial trace is flushed inside the same
  lease-fenced transaction that finalizes the attempt. The attempt terminal event,
  retry event, and run terminal event continue that causal chain.
- If model execution succeeds but terminal commit loses to cancellation or an
  optimistic conflict, the same lease-fenced fallback persists the completed trace
  before recording the terminal run outcome.
- Successful attempts retain the existing semantic model/tool event writer rather
  than persisting a duplicate low-level trace.
- Trace payloads never store prompts, messages, embedding inputs, tool arguments,
  URLs, headers, credentials, provider response bodies, or exception text. Router
  errors expose stable codes and safe summaries only.

### Worker Readiness

- Worker process presence is independent of per-conversation leases. Each worker boot
  registers one database row and heartbeats while idle or busy; graceful shutdown
  moves it through `draining` to `stopped`.
- A worker is compatible only when its state is `ready`, its database-time heartbeat
  is fresh, and its compatibility fingerprint matches the API. The fingerprint binds
  the worker contract version, Alembic heads, and runtime mode.
- Readiness additionally requires API and worker source revision, clean/dirty state,
  and a SHA-256 fingerprint of every Git-visible file to match. Unknown or malformed
  source identity fails closed. Source identity is stored separately from the
  compatibility fingerprint so diagnostics can distinguish contract mismatch from
  an exact build-content mismatch.
- `GET /api/v3/worker-health` is operator-authenticated and returns one typed body.
  It is `200` only with a fresh matching worker and `503` for missing/stale workers or
  database unavailability. `/api/v2/health` remains unchanged.
- The default process heartbeat is five seconds and staleness is fifteen seconds.
  Configuration must retain at least three heartbeat intervals of tolerance.
- `SIGTERM` marks the worker draining immediately. One active attempt may finish, but
  no later retry or provider attempt may start. Compose grants 650 seconds so the
  maximum 600-second attempt can reach its lease-fenced terminal transaction.

### Qualification Gate

- Native-runtime acceptance performs worker-health preflight before creating any
  definition, subject, conversation, or run.
- Preflight is a content-addressed root artifact, not a scored round. Transport,
  authentication, malformed-response, database, worker, and source-identity failures
  all produce a safe failed receipt and exit with no primary rounds or proposal.
- Passing preflight identity is hash-bound into provenance and promotion proposals.
  Promotion review independently verifies its digest, ready state, worker counts,
  compatibility fingerprint, clean source identity, and run binding.
- Provider request failure/cancellation is always infrastructure failure evidence,
  never a behavioral score observation. Such events make a primary qualification
  round ineligible even if stored normalized scores claim success.

## Rejected Alternatives

### Reuse Conversation Lease Heartbeats

An idle healthy worker owns no conversation lease, and a stale lease describes one
run rather than process compatibility. Reusing it would conflate serialization,
recovery, and deployment health.

### Probe The Worker With Synthetic Runs

Creating resources and model traffic to answer a health check is slow, costly, and
can fail for reasons unrelated to worker process readiness. Boot-scoped presence is
cheaper and directly measures the required process.

### Persist Provider Exceptions Or Bodies

Raw upstream diagnostics are richer but can leak prompts, user data, credentials, or
provider internals into durable run events. Stable codes and bounded metadata are the
correct public evidence boundary.

## Consequences

Operators and Test Center can now distinguish API readiness, database readiness,
worker compatibility, build mismatch, stale presence, and the exact stage of a
provider failure. Acceptance no longer spends model calls when the worker path or
exact image source is known to be unavailable, and promotion evidence is bound to
the process that could actually execute it.

The `ade.worker_instances` table accumulates boot records; stopped/stale-row retention
is an operational cleanup concern, not part of qualification correctness. Health is
still a point-in-time gate rather than a guarantee that a worker cannot fail after a
run begins. Conversation leases, exact retry ownership, terminal transactions, and
fresh qualification rounds remain required.

## Guardrails

- Do not expose worker health without operator authentication.
- Do not use local application time to decide heartbeat freshness when PostgreSQL is
  reachable.
- Do not treat a compatible but different-build worker as release-ready.
- Do not start another provider attempt after a worker enters draining state.
- Do not add provider payloads or exception strings to durable trace events.
- Do not count preflight as a qualification round or create resources before it.
- Do not promote evidence containing a provider request failure or cancellation.
- This decision closes observability blockers; it does not approve Agent Studio
  cutover from Letta to v3.
