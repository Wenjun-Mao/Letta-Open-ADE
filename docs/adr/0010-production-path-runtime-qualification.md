# ADR 0010: Agent Runtime Qualification Uses Production-Path Evidence

- Status: Accepted
- Date: 2026-08-29
- Extends: [ADR 0009](0009-ade-owned-agent-runtime.md)

## Context

The runtime study proved the proposed memory and execution contracts with direct
in-memory adapters. Its live rounds called Model Router directly and fingerprinted
study code. The disabled `/api/v3` implementation now has additional behavior that
those rounds did not exercise: HTTP contracts, asynchronous runs, PostgreSQL
transactions, worker leases, cancellation, normalized events, reviewer commits,
and cleanup.

Carrying the study counters into the production deployment manifest would therefore
claim evidence for code that was never tested. Route aliases also remain mutable and
cannot identify the model artifact, runtime, hardware, sampling, context, and ADE
policy that produced a result.

## Decision

- Only complete rounds through the real `/api/v3` API, worker, and PostgreSQL path
  may qualify an ADE-native runtime deployment.
- Study results remain research evidence. Their counters become stale when the
  manifest is rebound to production policy hashes.
- Qualification binds conversation, reviewer, and retriever roles to exact
  deployment fingerprints and production prompt, tool, schema, and retrieval policy
  bundle hashes.
- One release candidate requires three consecutive passing complete rounds for one
  conversation/reviewer/retriever set. A failed round resets that role's consecutive
  sequence.
- The runner preserves the entire first failed canonical round, then skips later
  primary rounds because that run can no longer establish three consecutive
  passes. Requested compatibility diagnostics may still continue.
- Focused cases, fake transports, unavailable roles, and compatibility-only runs
  never advance qualification.
- A non-empty ordered `case_keys` selection is a focused diagnostic: it runs one
  `live-api-diagnostic` round, skips llama compatibility, records both canonical and
  executed case keys, and cannot emit a promotion proposal. The selected keys must
  retain canonical fixture order.
- Long-history evidence requires both an explicit versioned-summary commitment
  event and preservation of the expected immutable raw-message history.
- llama-server remains compatibility evidence and does not block a separately
  qualified DGX role set.
- A run may emit a content-addressed promotion proposal, but it cannot edit the
  tracked deployment manifest. Promotion requires a separate reviewed check/apply
  command that revalidates every artifact, fingerprint, policy hash, role gate,
  raw event sequence, normalized observation, and deterministic score.
- A changed model, runtime, hardware, sampling, context, prompt, tool, schema, or
  retrieval input creates a fresh qualification lifecycle. Aliases cannot preserve
  qualification across that change.
- Production policy bundles have one path-bound registry in
  `workflows/evals/agent_runtime_v3_acceptance/policy.py`. The checked-in manifest
  and promotion reviewer must both reproduce those hashes.

## Consequences

The first production-path run may expose gaps that the study adapter did not, and no
promotion proposal is expected until those gaps are fixed. Qualification is slower
because it uses real asynchronous turns and persistent state, but its evidence now
matches the code proposed for release.

Acceptance resources use unique run prefixes and are purged transactionally after
artifacts are captured. Cleanup refuses ambiguous ownership and leaves a recovery
manifest rather than risking unrelated state. Test Center cancellation unwinds the
runner through API-level run cancellation and the same scoped cleanup path.

## Guardrails

- Never copy direct-study counters into a production-path qualification summary.
- Never weaken a deterministic contract to qualify a less capable model.
- Never count a partial matrix or a run from a dirty/unidentified build.
- Never allow a focused diagnostic, even one that selects every case, to claim a
  qualification round or promotion proposal.
- Never promote a self-declared case list or a stored pass boolean without
  independently re-scoring the current canonical fixture observations.
- Never auto-promote from Test Center or a background process.
- `promote --check` must be non-mutating; `promote --apply` must re-run the same
  source, artifact, policy, role, and manifest checks before one atomic update.
- Never purge state unless every target is proven to belong to the acceptance run.
