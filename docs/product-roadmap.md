# ADE Product Roadmap

## Product Outcome

The [product contract](product-contract.md) owns current agreements and exclusions.
This roadmap orders outcomes; milestone scope is not a competing product contract.

ADE helps an operator improve agent behavior with evidence: configure an
experience, run a representative evaluation, inspect reply/tool/memory evidence,
refine the relevant content, and make a clear decision.

The next product goal is 林小棠's continuity in everyday Chinese companionship:
remembering relevant preferences, concerns, conversations, and promises, and
following up naturally. Use the [project tracker](project-tracker.md) for current
status, blockers, next actions, and evidence.

## Milestones

| ID | Outcome | Completion criteria |
| --- | --- | --- |
| M0 | Development foundation | Native ADE and Luna development route verified, with their limits recorded. |
| M1 | Character-continuity baseline | Conversations reviewed; failures attributed to model, prompt, representation, retrieval, or policy; known policy defects covered by regression tests. |
| M2 | Memory approach comparison (deferred) | Original criterion remains: compare ADE and Hindsight against M1 cases for quality, latency, complexity, and recommendation. No comparison winner has been established. |
| M3 | Usable continuity in Agent Studio (Hindsight integration planned) | The [three-stage plan](plans/hindsight-integration.md) connects the product flow, verifies relationship isolation/failures, and proves recovery/fresh-start readiness. PC-02/03/14 supersede the incumbent shared-profile scope; implementation and live qualification remain pending. |
| M4 | Real-use validation | Longer-session trials, deployment-provider validation, and operator review meet agreed acceptance criteria. |

Under [ADR 0022](adr/0022-incumbent-memory-first-product-slice.md), M3's
bounded profile-memory slice established the incumbent development direction.
On 2026-10-12 the user selected Hindsight as default Memory (PC-14) and then
requested the [three-stage integration plan](plans/hindsight-integration.md).
Manual memory removal is deferred from that first integration; Hindsight owns
ordinary conversational updates/corrections, whose quality must still be verified.
The earlier [assessment](findings/hindsight-integration-assessment-2026-10-10.md)
and incumbent M3 plan remain historical inputs, not authority to revive shared
profiles, compatibility paths or another adoption prerequisite. The
original measured M2 comparison remains unexecuted/deferred, with historical
findings preserved; no comparison winner is inferred. Scene-based roleplay
remains deferred.

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

The removal completed live qualification and ledger promotion on 2026-09-08.
The [release ledger](../config/agent-studio/release-evidence.json) records the
qualified implementation; it does not establish today's provider availability.
The current stack has one ADE API, no
alternate runtime, and no retained legacy data-migration, parity, rollback, or custom-tool
authoring path. Historical state is not imported. Recovery is deployment rollback
and PostgreSQL backup/restore.

### Luna Development Route

Delivered on 2026-09-22 for host-only dialogue, memory-review proposals, and
advisory judging with `chat_linxiaotang`. These experiments do not qualify native
persistence, embeddings, Qwen, or tool protocols. See the
[workflow instructions](../workflows/evals/character_memory_dev/README.md).

## Next

- Establish execution authority for the agreed [Hindsight integration plan](plans/hindsight-integration.md): connect
  the full flow, verify isolation/failures, and prove recovery/fresh-start
  readiness in a new isolated OCI stack. Adoption is settled; execution and
  provider/operational permissions remain separate. Closed campaign findings
  remain evidence with unresolved semantic and recovery limits, not an M2 winner.
- Improve the adopted runtime through real product use and evidence-led fixes
  after its implementation and activation are authorized.
- Improve task-specific evaluation where a concrete success contract exists.
- Keep model aliases configurable so providers and underlying local models can
  evolve without source changes.
- Carry useful M3 operator journeys into the new contracts without preserving
  obsolete native fact fields or treating incumbent evidence as new acceptance.

## Later

Decide whether to rename the repository and product vocabulary. This is a
separate coordinated change, not part of the runtime transition.
Scene-based roleplay, voice, avatars, and arbitrary tool authoring remain deferred.

## Non-Goals

- No generic evaluation framework without a concrete workflow.
- No arbitrary user-authored tool execution without an execution and sandbox contract.
- No duplicate runtime, data migration, compatibility alias, or hidden fallback.
- No repository-wide restructuring unless a clear ownership boundary requires it.

See [ADR 0019](adr/0019-ade-steady-state-runtime.md) for the steady-state
architecture and release policy.
