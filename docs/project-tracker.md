# ADE Project Tracker

Updated: 2026-09-22. Owner: this ADE task, using Relay for delegated reporting.
Direction and milestone completion criteria live in the [roadmap](product-roadmap.md).

## Current Focus

M2: compare the smallest ADE extension with Hindsight against M1's 林小棠
(`chat_linxiaotang`) continuity cases. See the
[M2 plan](plans/m2-memory-approach-comparison.md) and
[interim findings](findings/m2-memory-approach-comparison.md). The initial
provider-independent source-contract mapping, fixed test specification,
structural checks, and external capability review are complete. No candidate
comparison has been executed. Identical provider-backed experiments are pending
authority and availability. Fresh native release qualification remains pending;
it is not waived by this development evidence.

The user authorized continued delivery between checkpoints. Escalate material
scope/tradeoff decisions, unsafe actions, or blockers needing user input. Routine
implementation and verification choices do not need repeated confirmation.

## Milestones

| ID | Status | Dependencies | Next action | Evidence / completion boundary |
| --- | --- | --- | --- | --- |
| M0 | complete | None | Maintain verified foundation | [Native release ledger](../config/agent-studio/release-evidence.json), [ADR 0019](adr/0019-ade-steady-state-runtime.md), [Luna workflow](../workflows/evals/character_memory_dev/README.md), commits `f8de9d7` and `7799439`. |
| M1 | complete | M0 | Director review and M2 comparison definition | [Findings](findings/m1-character-continuity-baseline.md), policy tests, and ten serial Luna records. Implementation baseline is complete; native persistence/provider qualification remains pending. |
| M2 | in progress | M1 | Run identical provider-backed ADE/Hindsight cases when authorized and available | [Interim findings](findings/m2-memory-approach-comparison.md) record structural evidence and precise live prerequisites. Requires measured correctness, isolation, forgetting, latency, and maintenance comparison before any external-service decision. |
| M3 | planned | M2 decision | Detail one complete Agent Studio implementation | Requires persisted continuity, source inspection, correction/forgetting, and stable relationship identity across persona edits. |
| M4 | planned | M3 | Define deployment-provider and real-use acceptance cases | Requires longer-session results, deployment-model qualification, and actual operator review. |

## M2 Work Checklist

- [x] Map current ADE representation and contracts to every M1 requirement.
- [x] Add a compact, repeatable workflow-local test specification and structural checks.
- [x] Inspect and cite pinned official Hindsight retain/recall, isolation,
  lifecycle, provenance, dependency, and provider evidence.
- [x] Record common budget, quality-layer, latency, and operational comparison.
- [x] Record exact blocked live experiments and a confidence-qualified recommendation.
- [ ] Run identical provider-backed ADE/Hindsight experiments before selecting a memory approach.

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
- 2026-09-22: M1 baseline completed in this worktree: ten serial Luna development records validated, two policy defects fixed with native regressions, and [findings](findings/m1-character-continuity-baseline.md) recorded. This invalidates the prior governed-policy fingerprint; native release requalification is pending, not waived.
- 2026-09-22: M2 comparison started with the [plan](plans/m2-memory-approach-comparison.md). No memory architecture has been selected or adopted.
- 2026-09-22: M2 interim structural evidence, a repeatable input specification, and compact structural checks completed; see [findings](findings/m2-memory-approach-comparison.md). No candidate comparison was executed; provider-backed comparison and any external-service decision remain pending.

## Updating This Tracker

Use `planned`, `in progress`, `blocked`, `complete`, or `deferred`. Update when
work starts, blockers appear, scope changes, or completion is verified. Link the
active plan and evidence; state the next action and remaining limitations. Keep
detailed checklists only for the active milestone. Avoid percentages, duplicate
status documents, and orchestration ledgers.
