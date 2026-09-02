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

## Now: Complete Native Runtime Product Parity

The ADE-native runtime is an accepted implementation candidate, not the current
product runtime. It has a separate PostgreSQL model, worker, typed-memory contracts,
and a breaking `/api/v3` API. Current Agent Studio, `/api/v2`, and Letta `0.16.8`
remain the product authority until the evidence-gated cutover in
[ADR 0016](adr/0016-ade-native-agent-studio-cutover.md) takes effect.

Phase 4 is a product-outcome comparison, not an attempt to reproduce Letta's internal
blocks or compaction format. Test Center must own content-addressed paired artifacts
for native v3 and Letta v2 using the same fixture, controls, and scoring policy.

- Run three clean paired DGX rounds after every relevant qualification change.
- Pair the common chat and memory outcome against Letta. Prove native-only isolation,
  retrieval, compaction, false-memory prevention, tool behavior, and trace guarantees
  through the canonical native matrix, and prove retry/cancellation/idempotency
  semantics through deterministic conformance tests.
- Keep llama-server as compatibility evidence, not an initial selectable product
  bundle, until it independently qualifies.
- Retain the initial native tool scope: subject-bound `search_memory` only.

### Now Decision Gate

Phase 4 closes only when current qualification, three clean paired DGX rounds, and
deterministic conformance provide one reviewed, content-addressed capability ledger.
Runtime qualification alone does not prove product parity.

## Next: Fresh-Start Agent Studio Cutover

Phase 5 implements the cutover contract in
[ADR 0016](adr/0016-ade-native-agent-studio-cutover.md), but activation remains
evidence-gated. When the Phase 4 gate passes, new Agent Studio usage moves exclusively
to the qualified native DGX bundle and a fresh ADE PostgreSQL store. There is no Letta
importer, UI/runtime toggle, compatibility authority, per-request fallback, or dual
write. The admin-only reset boundary is idempotent, transactional, scoped to
`purpose=agent_studio`, and auditable.

### Next Decision Gate

Effective cutover requires the Phase 4 evidence gate, the exact qualified DGX bundle,
release readiness, and a rehearsed prior-v2 web/API rollback that preserves native
state. Rollback never falls back per request and does not merge or delete v3 state.

## Later: Remove Legacy Runtime Dependencies

Letta, Redis, v2 Agent Studio endpoints, and legacy evidence remain throughout Phase
5. Phase 6 removes them only after no product traffic or deployment dependency
remains, with the removal backed by a separate operational completion check.

## Explicit Non-Goals

- Do not claim or attempt native-runtime cutover through roadmap wording alone.
- Do not add a generic evaluation framework before a concrete product workflow
  needs it.
- Do not mix behavioral quality decisions with infrastructure diagnostics.
- Do not preserve duplicate runtime authority, legacy import, or compatibility
  aliases for a future v3 cutover.
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
  paired-evidence, reset, rollback, and legacy-removal contract.
