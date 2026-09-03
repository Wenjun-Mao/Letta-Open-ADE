# ADE Product Roadmap

This is the authoritative product direction for Letta Open ADE. It describes
outcomes and decision gates, not a record of every completed task. For the
current authority and runtime boundary, start with the
[ADE System Status Map](architecture/system-status.md). The
[maintenance roadmap](maintenance-roadmap.md) remains a historical cleanup
record and must not be used to choose current product work.

## Product Outcome

ADE helps an operator improve agent behavior with evidence. The intended loop
is: configure an experience, evaluate it against a representative scenario,
inspect the evidence, refine the relevant content, compare the result, and make
a clear keep, promote, or reject decision.

The labs and centers are supporting capabilities, not competing destinations.
Agent Studio, Prompt Center, Model Catalog, and Test Center should make this
one improvement loop easier to complete.

## Delivered Baseline: Agent Behavior Evaluation Loop

The initial Agent Behavior Evaluation Loop is delivered. An operator can
configure a chat evaluation, replay a conversation, inspect turn-level reply,
tool, and memory evidence, review deterministic checks, open the selected
prompt or persona for refinement, and rerun the scenario. The representative
live baseline is recorded in the
[v0.3.0 live behavior baseline](baselines/v0.3.0-live-baseline.md).

Deterministic checks own the official pass/fail outcome. Optional LLM judging is
diagnostic only and must not make a result non-deterministic.

## Delivered: Evaluation Is The Product Spine

The delivered loop is now ADE's primary operator journey rather than one
technical surface among peers.

- Make the behavior-improvement path clear from the dashboard and navigation:
  build an experience, choose content and a model, evaluate, inspect, refine,
  compare, then decide.
- Preserve verified, content-addressed evaluation provenance at run start: resolved model
  identity/capability, prompt and persona revision or content hash, fixture,
  controls, and scoring policy.
- Make baseline-versus-candidate comparisons and the keep/promote/reject
  decision readable without reconstructing raw artifacts.
- Separate behavior-quality evaluation from stack health, smoke checks, runtime
  qualification, and raw diagnostics. Those operational checks remain valuable,
  but they answer a different question.
- Extend the same outcome-oriented evaluation approach to Comment Lab and Label
  Lab only when each has a concrete, task-specific success contract.

### Delivered Decision Gate

This milestone closed when ADE could record exact evaluated inputs, show the
relevant turn and memory evidence, compare a candidate with a baseline, and
state a keep, promote, or reject decision without reconstructing raw artifacts.
Operations and qualification views remain separate from product-quality decisions.

## Delivered: Native Runtime Qualification And Fresh-Start Cutover

Milestones 4 and 5 are complete. Agent Studio now uses the ADE-native `/api/v3`
runtime, its worker, typed memory contracts, and ADE PostgreSQL as its sole product
authority. Letta `0.16.8` is not an Agent Studio request fallback or state authority.
It remains available only through the deliberate release-level rollback lane and for
other retained v2 capabilities until Phase 6.

Phase 4 closed with one reviewed, content-addressed
[release ledger](../config/agent-studio/release-evidence.json) that binds:

- three complete native qualification rounds over the canonical capability matrix;
- three clean schema-v2 paired DGX rounds with native `3/3`, comparable inputs,
  exact zero-retry controls, completed cleanup, and per-round non-regression against
  the observed Letta baseline;
- deterministic retry, timeout, cancellation, idempotency, and event conformance;
- a passing llama-server compatibility round; and
- a successful release-level rollback rehearsal that preserves native state.

Phase 5 activated the exact qualified DGX conversation, reviewer, and retriever
bundle through the evidence gate. The cutover used a fresh, scoped reset and has no
Letta importer, UI/runtime toggle, compatibility authority, per-request fallback, or
dual write. The admin-only reset boundary is idempotent, transactional, limited to
`purpose=agent_studio`, and auditable.

### Delivered Decision Gate

The gate is executable through `make agent-studio-release-gate`; release startup
runs it before bringing up the product lane. Any policy, prompt, tool, schema,
retrieval, deployment-identity, or implementation change outside the explicitly
allowed release-record files invalidates the evidence and requires requalification.

## Now: Stabilize The Native Product Path

Operate the native Agent Studio as the supported product path and learn from normal
use before removing the fallback deployment asset. Keep runtime health, run events,
memory lineage, Test Center evidence, reset receipts, and release-level rollback
observable. Fix defects at their owning contract and requalify changes that affect
the released behavior or evidence boundary.

### Now Decision Gate

Every Agent Studio release must pass the reviewed evidence gate and report a fresh,
source-matched worker. No incident response may silently route a request to Letta,
merge v2 and v3 state, or weaken cleanup and provenance guarantees. Rollback remains
an explicit whole-release operation.

## Next: Remove Legacy Runtime Dependencies

Phase 6 may remove Letta, Redis, rollback-only v2 Agent Studio endpoints, and legacy
evidence only after an explicit traffic and dependency audit proves that no product
capability or required recovery path still depends on them. The removal needs its own
decision, operational checks, and updated recovery plan.

## Later: Rename The Project

After Phase 6 removes Letta from code, runtime, documentation, and operator
vocabulary, decide and execute the project rename as a separate coordinated change.

## Explicit Non-Goals

- Do not claim or attempt native-runtime cutover through roadmap wording alone.
- Do not add a generic evaluation framework before a concrete product workflow
  needs it.
- Do not mix behavioral quality decisions with infrastructure diagnostics.
- Do not reintroduce duplicate Agent Studio runtime authority, legacy import,
  per-request fallback, dual write, or compatibility aliases.
- Do not start another repository-wide restructuring before an outcome or
  authority boundary requires it.

## Durable Sources

- [ADE System Status Map](architecture/system-status.md): current authority,
  runtime status, and direction at a glance.
- [ADR 0009](adr/0009-ade-owned-agent-runtime.md): accepted native-runtime
  design and no-cutover guardrails.
- [ADR 0010](adr/0010-production-path-runtime-qualification.md): production
  qualification and promotion requirements.
- [ADR 0011](adr/0011-agent-runtime-operational-readiness.md): worker and
  provider-failure evidence requirements.
- [ADR 0012](adr/0012-content-addressed-behavior-evaluation-decisions.md):
  evaluated-input provenance and decision ledger trust boundary.
- [ADR 0013](adr/0013-narrow-native-runtime-product-pilot.md): separate pilot,
  atomic session, curated-tool, and exposure-gate contract.
- [ADR 0016](adr/0016-ade-native-agent-studio-cutover.md): fresh-start cutover,
  reset, rollback, and legacy-removal contract.
- [ADR 0017](adr/0017-incumbent-baseline-does-not-veto-native-cutover.md): paired
  baseline, candidate-qualification, and non-regression gate semantics.
- [ADR 0018](adr/0018-evaluation-cleanup-must-prove-absence.md): exact-scope cleanup
  and resource-absence proof required by release evidence.
- [Agent Studio release ledger](../config/agent-studio/release-evidence.json): the
  reviewed, executable record that activated the native product path.
