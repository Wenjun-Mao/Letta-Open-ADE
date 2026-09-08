# ADE Product Roadmap

## Product Outcome

ADE helps an operator improve agent behavior with evidence: configure an
experience, run a representative evaluation, inspect reply/tool/memory evidence,
refine the relevant content, and make a clear decision.

## Delivered

### Behavior Evaluation Loop

Agent Studio, Prompt Center, Model Catalog, and Test Center support the core
behavior-improvement path. Deterministic checks decide pass/fail; an optional
LLM judge is diagnostic only.

### Native Agent Studio

Agent Studio now runs on the ADE-owned `/api/v3` runtime with PostgreSQL state,
typed memory, curated tools, Model Router, and ADE-owned retry/timeout policy.
The release ledger binds qualification, compatibility, conformance, reviewed
model aliases, and the agent bundle to the released implementation.

### Letta-Removal Milestone

The removal implementation is complete and awaits final live qualification and
ledger promotion. The target stack has one ADE API, no
alternate runtime, and no retained legacy data-migration, parity, rollback, or custom-tool
authoring path. Historical state is not imported. Recovery is deployment rollback
and PostgreSQL backup/restore.

## Next

- Stabilize the native runtime through real product use and evidence-led fixes.
- Improve task-specific evaluation where a concrete success contract exists.
- Keep model aliases configurable so providers and underlying local models can
  evolve without source changes.

## Later

Decide whether to rename the repository and product vocabulary. This is a
separate coordinated change, not part of the runtime transition.

## Non-Goals

- No generic evaluation framework without a concrete workflow.
- No arbitrary user-authored tool execution without an execution and sandbox contract.
- No duplicate runtime, data migration, compatibility alias, or hidden fallback.
- No repository-wide restructuring unless a clear ownership boundary requires it.

See [ADR 0019](adr/0019-ade-steady-state-runtime.md) for the steady-state
architecture and release policy.
