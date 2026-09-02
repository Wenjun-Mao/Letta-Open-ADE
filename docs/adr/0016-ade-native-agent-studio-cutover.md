# ADR 0016: ADE-Native Agent Studio Uses A Fresh-Start, Evidence-Gated Cutover

- Status: Accepted for implementation; effective cutover remains evidence-gated
- Date: 2026-09-02
- Related: [ADR 0009](0009-ade-owned-agent-runtime.md),
  [ADR 0010](0010-production-path-runtime-qualification.md),
  [ADR 0013](0013-narrow-native-runtime-product-pilot.md), and
  [ADR 0014](0014-curated-tool-invocation-and-external-source-authority.md)

## Context

ADE has accepted an ADE-owned runtime design and implemented a separately gated v3
candidate. Runtime qualification establishes that an exact deployment can satisfy
technical contracts; it does not establish that the native and Letta-backed products
produce equivalent operator outcomes. A product cutover also needs an unambiguous
state boundary and recovery plan. Keeping a permanent toggle, request fallback, or
dual-write path would preserve two conflicting authorities for memory and history.

## Decision

- Once the release gates below pass, Agent Studio becomes exclusively ADE-native v3.
  There is no UI/runtime toggle, per-request fallback, dual write, legacy importer,
  or compatibility authority.
- The initial supported deployment is exactly the qualified DGX conversation,
  reviewer, and retriever bundle. llama-server remains a compatibility deployment,
  not a selectable cutover bundle, until it independently qualifies under the same
  release policy.
- The new product starts with a fresh ADE PostgreSQL Agent Studio store: reusable
  agent definitions, explicit memory subjects, conversations, immutable messages,
  typed facts and revisions, and runs/events. Existing Letta agents are not migrated.
- An admin-only reset is the explicit fresh-start boundary. It is idempotent and
  transactional, affects only `purpose=agent_studio` data, refuses while an active
  run exists, persists a durable receipt, and increments the workspace generation.
- Rollback is a deliberate release-level deployment rollback to the prior v2 UI/API.
  It is never automatic or request-scoped, and it leaves isolated v3 state intact for
  diagnosis and a later explicit reset decision.
- Phase 4 compares product outcomes rather than internal memory representations.
  Test Center owns content-addressed paired native-v3 and Letta-v2 artifacts,
  normalized turn evidence, and comparison results.
- Paired evidence covers only behavior both products expose comparably. Native-only
  subject, correction, compaction, tool, and trace guarantees come from the full
  canonical qualification matrix; exact retry, cancellation, and idempotency
  guarantees come from deterministic conformance tests. The release ledger requires
  all three evidence classes and does not relabel native-only checks as paired.
- Effective cutover requires current qualification or requalification plus three
  clean paired DGX rounds, deterministic conformance, and a successful release-level
  rollback rehearsal. Until those artifacts are reviewed into the content-addressed
  cutover ledger, implementation may proceed but no document, UI, or deployment may
  claim that the cutover is complete.
- The initial product tool scope is subject-bound `search_memory` only. Additional
  curated tools need their own contract, evaluation, and qualification decision.
- Letta, Redis, v2 Agent Studio endpoints, and old evidence stay available during
  Phase 5. Phase 6 removes them only after no product traffic or dependency remains.

## Consequences

The product gains a smaller, inspectable mental model: definitions describe behavior,
subjects own durable facts, conversations own immutable history, and runs/events
explain execution. Operators can reason about corrections and source evidence without
free-text memory blocks, while maintainers gain one timeout, retry, memory, and event
authority.

The transition deliberately has operational cost. ADE must run and monitor both
runtime stacks during Phase 5, preserve paired evidence, operate a guarded reset, and
make rollback as a release decision rather than a hidden request behavior. Users must
create new Agent Studio state after activation; this is a known fresh-start boundary,
not a migration failure.

## Guardrails

- Never claim product parity from unit tests, a single live run, or runtime
  qualification alone.
- Never satisfy a capability with an arbitrary evidence digest; each ledger row must
  point to the required qualification, parity, or conformance receipt.
- Never expose an unqualified model route through Agent Studio configuration.
- Never route one native request to Letta after a provider, tool, or runtime failure.
- Never delete or mutate Letta history as part of the native reset operation.
- Never remove Letta, Redis, v2 endpoints, or historical artifacts during Phase 5.
- Record any deployment, policy, prompt, tool, schema, or retrieval identity change as
  a requalification event before a release claim.
- Follow the executable sequence in the
  [Agent Studio cutover runbook](../operations/agent-studio-cutover.md).
