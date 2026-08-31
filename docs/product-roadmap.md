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

## Now: Make Evaluation The Product Spine

Turn the delivered loop into ADE's primary operator journey rather than one
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

### Now Decision Gate

This milestone is ready to close when an operator can make a trustworthy
behavior decision from ADE: the run records the exact evaluated inputs, shows
the relevant turn and memory evidence, compares a candidate with a baseline,
and states the resulting keep, promote, or reject decision. Operations and
qualification views must not be confused with that product-quality decision.

## Next: Qualify The ADE-Native Runtime And Prove A Narrow Product Pilot

The ADE-native runtime is an accepted implementation candidate, not the current
product runtime. It has a separate PostgreSQL model, worker, typed-memory
contracts, a breaking `/api/v3` API, and an implemented separate preview route,
but it remains disabled by default and unqualified. Current Agent Studio,
`/api/v2`, and Letta `0.16.8` remain the product authority.

Next runtime work is evidence and product-contract work, not another broad
rewrite:

- Complete the production-path qualification required by
  [ADR 0010](adr/0010-production-path-runtime-qualification.md), retaining
  reviewed evidence for the exact deployment fingerprints.
- Retain the accepted first-pilot tool scope from
  [ADR 0013](adr/0013-narrow-native-runtime-product-pilot.md): subject-bound
  `search_memory` only, with no arbitrary Tool Center execution.
- Demonstrate a native-only operational path, including worker readiness,
  recovery, cancellation, and the absence of a Letta or Redis dependency for
  that path.
- Qualify and then expose the implemented, deliberately separate v3 pilot around
  agent definitions, memory subjects, conversations, typed memory, and run events.

### Next Decision Gate

The runtime can enter a product pilot only after the required role deployments
have passed three consecutive complete, zero-retry qualification rounds and
reviewed promotion; the first tool contract is approved; and a native-only
operational path has been demonstrated. Passing unit tests, study fixtures, or
focused diagnostics do not satisfy this gate.

## Later: Fresh-Start Cutover And Simplification

Only after the native pilot proves the same operator outcome and a later cutover
ADR is accepted should new Agent Studio usage move to v3. The cutover is
fresh-start: there is no Letta importer, compatibility path, or dual-write
authority. Letta, Redis, v2 Agent Studio execution, and associated Tool Center
runtime behavior are removed only after no product traffic or deployment
dependency remains.

### Later Decision Gate

Cutover requires both the runtime qualification gate and an accepted cutover
ADR that records the product contract, operational rollback/reset boundary,
and removal sequence. Until then, no alias, fallback, or UI default may make
the candidate runtime appear to be the supported Agent Studio path.

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
