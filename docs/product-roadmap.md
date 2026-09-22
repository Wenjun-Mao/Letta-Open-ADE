# ADE Product Roadmap

## Product Outcome

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
| M2 | Memory approach decision | Minimal ADE extension and Hindsight compared against M1 cases; quality, latency, complexity, and recommendation documented. |
| M3 | Complete Agent Studio experience | Cross-conversation memory, source inspection, correction/forgetting, and relationship continuity across persona edits work. |
| M4 | Real-use validation | Longer-session trials, deployment-provider validation, and operator review meet agreed acceptance criteria. |

M1 is the next implementation priority. Detail later milestones after preceding
results establish what is necessary. Scene-based roleplay is deferred.

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

- Stabilize the native runtime through real product use and evidence-led fixes.
- Improve task-specific evaluation where a concrete success contract exists.
- Keep model aliases configurable so providers and underlying local models can
  evolve without source changes.
- Establish M1's failure cases before adding a new memory service.

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
