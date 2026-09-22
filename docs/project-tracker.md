# ADE Project Tracker

Updated: 2026-09-22. Owner: this ADE task, using Relay for delegated reporting.
Direction and milestone completion criteria live in the [roadmap](product-roadmap.md).

## Current Focus

M1: establish a character-continuity baseline for 林小棠 (`chat_linxiaotang`) in
everyday Chinese companionship. Next action: reproduce the two confirmed policy
defects and define representative conversations with observable expectations.

The user authorized continued delivery between checkpoints. Escalate material
scope/tradeoff decisions, unsafe actions, or blockers needing user input. Routine
implementation and verification choices do not need repeated confirmation.

## Milestones

| ID | Status | Dependencies | Next action | Evidence / completion boundary |
| --- | --- | --- | --- | --- |
| M0 | complete | None | Maintain verified foundation | [Native release ledger](../config/agent-studio/release-evidence.json), [ADR 0019](adr/0019-ade-steady-state-runtime.md), [Luna workflow](../workflows/evals/character_memory_dev/README.md), commits `f8de9d7` and `7799439`. |
| M1 | in progress | M0 | Reproduce policy failures; run and review baseline cases | Requires findings report and regression evidence; Luna in-context results alone do not prove persisted memory. |
| M2 | planned | M1 | Specify comparison from baseline findings | Requires evidence-backed selection considering correctness, isolation, forgetting, latency, and maintenance burden. External service adoption is a material decision. |
| M3 | planned | M2 decision | Detail one complete Agent Studio implementation | Requires persisted continuity, source inspection, correction/forgetting, and stable relationship identity across persona edits. |
| M4 | planned | M3 | Define deployment-provider and real-use acceptance cases | Requires longer-session results, deployment-model qualification, and actual operator review. |

## M1 Work Checklist

- [ ] Reproduce whole-message uncertainty false positives, including `Mighty` and a definite fact beside unrelated uncertainty.
- [ ] Reproduce negation-insensitive tool requirements, including requests not to search memory.
- [ ] Fix responsible policy contracts with regression coverage; record durable decisions where needed.
- [ ] Define conversations for preferences, worries/follow-ups, promises, shared conversational experiences, corrections, forgetting, and isolation between users.
- [ ] Review accuracy, unsupported experiences, repetitive callbacks, irrelevant recall, and natural Chinese voice.
- [ ] Separate in-context experiments, persisted-memory tests, and provider qualification in results.
- [ ] Produce a findings report attributing failures and identifying M2 requirements.

## Constraints And Open Questions

- DGX Spark is occupied by other projects. Do not send generation work there
  automatically; Luna is the explicit development lane.
- Native retrieval experiments need a verified embedding provider. The CLI lane
  does not provide embeddings or native tool-call protocol coverage.
- Governed runtime changes require fresh release evidence. Keep implementation
  verification distinct from deployment qualification; never reuse stale approval.
- Decide whether external memory adds enough value after the M1 baseline and M2
  comparison. No adoption has been approved.
- Shared experiences must not become unsupported real-user facts.
- Operator review in M4 cannot be substituted with an automated judge.

## Checkpoint Record

- 2026-09-08: Native transition qualified and promoted; release recorded in the ledger.
- 2026-09-22: Luna workflow delivered at `7799439`; 535 Python tests passed, 5 skipped, and three live development tasks passed. These were in-context generation checks.
- 2026-09-22: Roadmap/tracker established; everyday companionship selected; M1 started. Later milestone detail depends on findings.

## Updating This Tracker

Use `planned`, `in progress`, `blocked`, `complete`, or `deferred`. Update when
work starts, blockers appear, scope changes, or completion is verified. Link the
active plan and evidence; state the next action and remaining limitations. Keep
detailed checklists only for the active milestone. Avoid percentages, duplicate
status documents, and orchestration ledgers.
