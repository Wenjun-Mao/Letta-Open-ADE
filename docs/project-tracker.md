# ADE Project Tracker

Updated: 2026-09-23. Owner: this ADE task, using Relay for delegated reporting.
Direction and milestone completion criteria live in the [roadmap](product-roadmap.md).

## Current Focus

[ADR 0025](adr/0025-deepseek-development-lane.md) replaces Luna as the
current development-generation lane: official DeepSeek API,
`deepseek-flash`, thinking enabled/high by default, and Spark embeddings through the
existing retriever source. [ADR 0027](adr/0027-provider-neutral-release-and-embedding-space.md)
now selects DeepSeek conversation/reviewer plus Qwen retriever as the *new
unqualified release candidate*. This supersedes the earlier development-only
restriction for this selected candidate, not the requirement for fresh
qualification and promotion. The historical schema-v3 release ledger and
DGX/llama receipts remain unchanged; neither route has been promoted. The
Qwen endpoint may move only with an updated manifest binding, compatibility
review, and fresh qualification. No live calls were made during this
contract-preparation checkpoint. The Luna/AppServer feasibility experiment in
[ADR 0024](adr/0024-local-luna-agent-backend-feasibility.md) is on hold with
its four starts unspent. DeepSeek remains unqualified; it is
not a Spark chat fallback or evidence that the M2
ADE/Hindsight comparison was run. Initial synthetic smoke is bounded by
eight DeepSeek generation requests including continuations, four Spark
embeddings, no rerolls, and 180 seconds per request. The
[synthetic smoke](findings/deepseek-development-smoke.md) spent all eight DeepSeek
generation requests and three Spark embeddings with zero rerolls, passed native
required-tool and typed reviewer checks, and completed one synthetic Agent Studio
HTTP API/worker/persistence turn in a disposable database. Existing
release evidence is not rebound; the governed policy-freshness gate remains
expectedly stale.

The separately approved [Stage A provider-neutral preflight](findings/stage-a-provider-neutral-preflight-2026-09-23.md)
ran once on a clean isolated development-mode API/worker host. Two correction
turns and the 13-fact setup passed, but the scored deep-search turn failed:
DeepSeek returned no required `search_memory` call, and the runtime rejected
it as `conversation_required_tool_missing`. The retained preflight ledger
spent 7/32 DeepSeek and 7/32 Qwen requests, with no reroll. Stage B and
release qualification remain blocked; no route was promoted.

[ADR 0022](adr/0022-incumbent-memory-first-product-slice.md) is accepted:
retain ADE's current memory store for the bounded
[M3 usable-profile-memory slice](plans/m3-agent-studio-continuity.md). The
original measured M2 ADE/Hindsight comparison is deferred, not complete; no
comparative quality winner is claimed. M3 implementation is in progress.
The [M3 native/real-UI finding](findings/m3-native-acceptance-2026-09-23.md)
records 22/24 separately authorized DeepSeek generations and 14/24 Spark
embeddings, supported profile-fact continuity and isolated subjects, and two
misleading generated promises after removal/unsupported concern. The shared
prompt contract now states the limits. Two separately budgeted, one-shot
post-fix native/UI regressions passed the reply boundary and persistence
checks at 4/6 generation and 2/6 embedding calls; the failed turns were not
rerolled. Positive semantic retrieval and broader provider reliability remain
open. Release still needs a production chat-target/availability decision and
fresh governed qualification; selected DeepSeek is not production-approved.

M2: compare the smallest ADE extension with Hindsight against M1's 林小棠
(`chat_linxiaotang`) continuity cases. See the
[M2 plan](plans/m2-memory-approach-comparison.md) and
[interim findings](findings/m2-memory-approach-comparison.md). The initial
provider-independent source-contract mapping, fixed test specification,
structural checks, external capability review, and bounded Luna development
evidence are complete. No native ADE/Hindsight candidate comparison has been
executed. Identical provider-backed experiments are pending authority and
availability. Fresh native release qualification remains pending; it is not
waived by this development evidence.

Historical GPT-6 Luna development evidence remains available, but new Luna
calls are on hold under ADR 0025. The authorized single
smoke call on 2026-09-22 completed transport validation in 6.705 seconds but
returned plain text instead of required JSON; task validation failed. Access
was demonstrated, not workflow qualification. No retry or fallback was made.
Evidence: `workflows/evals/character_memory_dev/outputs/gpt6-luna-smoke-20260922/`
(ignored). Diagnose the output-format contract before any newly budgeted call;
do not weaken validation or relabel this result. The structured-output follow-up
now passes per-task JSON Schema through the CLI and records `json-schema-v1`;
92 focused tests and workflow Ruff checks pass. A subsequent authorized three-call
smoke passed dialogue, memory-review and advisory-judge transport/task validation
with `json-schema-v1`, medium effort, 180-second caps and zero adapter retries.
Records: `outputs/gpt6-schema-{dialogue,review,judge}-20260922/` under the workflow.
The judge input preserves the actual dialogue reply. These are task-shape smoke
checks (the dialogue fixture includes expectations), not blind quality scores or
native runtime qualification. Future manifests record `schema_smoke_verified`;
earlier artifacts retain the qualification state at their launch.
Historical M1/M2 GPT-5.6 Luna
captures and comparison inputs remain frozen.

The existing typed-fact add/correct/forget path and subject-filtered pgvector
query now have an isolated PostgreSQL regression with separate committed
transitions and fresh connection read-backs, using synthetic vectors. It
verifies persistence, revision/source lineage, current-revision selection,
forgotten-fact exclusion, and subject isolation. It does not qualify embedding
quality, model extraction, native runtime behavior, or Hindsight. `ade-api`
declares SQLAlchemy's `asyncio` extra so locked installs include the `greenlet`
runtime dependency required by `AsyncEngine` on this Mac architecture.

A separate ADE-only M2 context-conditioning slice has now passed four serial
GPT-6 Luna dialogue probes. Each prompt was built from active preference facts
read back from committed PostgreSQL state for that probe's subject plus a new
question; scripted typed writes were explicitly not model extraction. The
sample showed red-tea recall, corrected green-tea recall, no tea preference
resurrection after forget, and the separate subject's folk-music preference.
This remains development evidence, not semantic retrieval, extraction,
security, native-runtime, or ADE/Hindsight comparison evidence; exact source
and revision IDs and claim review are in [M2 findings](findings/m2-memory-approach-comparison.md).

For future delegation, follow Relay's current model-choice guide: GPT-6 Luna /
high for bounded implementation and focused verification; GPT-6 Sol / medium
for challenging integration, or high for difficult architecture/high-risk work.
Check tool support before dispatch and disclose unavailable selectors. This
supersedes the previous Terra default, not the experimental generation lane's
separately specified medium reasoning setting.

The user authorized continued delivery between checkpoints. Escalate material
scope/tradeoff decisions, unsafe actions, or blockers needing user input. Routine
implementation and verification choices do not need repeated confirmation.

## Milestones

| ID | Status | Dependencies | Next action | Evidence / completion boundary |
| --- | --- | --- | --- | --- |
| M0 | complete | None | Maintain verified foundation | [Native release ledger](../config/agent-studio/release-evidence.json), [ADR 0019](adr/0019-ade-steady-state-runtime.md), [Luna workflow](../workflows/evals/character_memory_dev/README.md), commits `f8de9d7` and `7799439`. |
| M1 | complete | M0 | Director review and M2 comparison definition | [Findings](findings/m1-character-continuity-baseline.md), policy tests, and ten serial Luna records. Implementation baseline is complete; native persistence/provider qualification remains pending. |
| M2 | deferred | M1 | Reopen at the mandatory end-of-M3 capability review if a measured service comparison is justified and authorized | [Interim findings](findings/m2-memory-approach-comparison.md) and [Luna evidence](findings/m2-luna-development-evidence.md) preserve the original evidence. The original ADE/Hindsight quality, latency and maintenance comparison was not executed. |
| M3 | in progress | [ADR 0022](adr/0022-incumbent-memory-first-product-slice.md) | Independent review of selected-route static checkpoint; separately authorize and budget fresh qualification | [M3 finding](findings/m3-native-acceptance-2026-09-23.md), [continuity plan](plans/m3-agent-studio-continuity.md), and [release-preparation plan](plans/m3-provider-neutral-release-preparation.md). Real UI/native reviewer and persistence covered typed fact/correction/removal, subject isolation, and archived old-page citation. Two original reply failures remain recorded; two distinct post-fix cases passed. DeepSeek/Qwen are unqualified candidates. Positive semantic retrieval, long-session reliability, character-private relationship continuity, and governed release qualification are not established. Persona-version UI/API evidence is inherited. |
| M4 | planned | M3 | Define deployment-provider and real-use acceptance cases | Requires longer-session results, deployment-model qualification, and actual operator review. |

## Original M2 Work Checklist (Deferred)

- [x] Map current ADE representation and contracts to every M1 requirement.
- [x] Add a compact, repeatable workflow-local test specification and structural checks.
- [x] Inspect and cite pinned official Hindsight retain/recall, isolation,
  lifecycle, provenance, dependency, and provider evidence.
- [x] Record common budget, quality-layer, latency, and operational comparison.
- [x] Record exact blocked live experiments and a confidence-qualified recommendation.
- [x] Run the bounded 14-session Luna-only source-extraction, supplied-context dialogue, and preference-intent contrast matrix; retain its non-native limits.
- [ ] Run identical provider-backed ADE/Hindsight experiments before selecting a memory approach.

## Constraints And Open Questions

- DGX Spark chat is occupied by other projects. Do not send generation work
  there; DeepSeek is the explicit development lane. The Spark embedding
  sidecar is separately authorized and available.
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
- 2026-09-22: M2 interim structural evidence, a repeatable chronological input specification with isolated case state, and compact structural checks completed; see [findings](findings/m2-memory-approach-comparison.md). No candidate comparison was executed; provider-backed comparison and any external-service decision remain pending.
- 2026-09-22: M2 Luna-only development matrix completed with fourteen serial captures, including a factual-recall versus recommendation contrast; see [Luna findings](findings/m2-luna-development-evidence.md). This supplied-context evidence does not test native persistence, retrieval, or Hindsight.
- 2026-09-22: GPT-6 Luna configured for future development calls without a live generation run. Entitlement and transport qualification remain pending a separately agreed budget; frozen M1/M2 GPT-5.6 Luna evidence remains historically labeled and separate.
- 2026-09-22: Added and passed isolated PostgreSQL coverage for the supported typed-fact add/correct/forget path across two conversations and two subjects. Synthetic vectors validate SQL selection and filtering only; semantic retrieval/provider and Hindsight comparison remain pending.
- 2026-09-22: Changed the lifecycle test to commit each transition and read committed state through separate connections; test URLs now fail closed unless they target a passwordless loopback database with a unique M2 test name. Added SQLAlchemy's asyncio extra to `ade-api` and synced the lockfile after confirming the documented `greenlet` requirement.
- 2026-09-22: Added the workflow-local PostgreSQL read-back dialogue slice. The fake-dialogue DB pipeline check and chronological input tests passed before exactly four one-shot subscription Luna calls; all task validations passed. Findings record exact contexts, replies, and source/revision IDs. This does not close the provider-backed ADE/Hindsight comparison.
- 2026-09-22: Accepted ADR 0022 and began the narrower M3 usable-profile-memory slice. The original M2 comparison is deferred with its earlier evidence intact. M3 UI/API, native behavioral and release readiness are separate gates; no new model calls are authorized for implementation.
- 2026-09-22: M3 UI/API checkpoint: subject reuse/isolation, boundary-checked historical citations, reviewed correction/removal drafts, and immutable persona version selection implemented. Mock-backed browser journeys and isolated PostgreSQL provenance tests passed; an opt-in native chronological diagnostic was added without executing provider calls. Broad policy fingerprint checks remain failed and unwaived. [M3 plan](plans/m3-agent-studio-continuity.md) records the end-of-slice capability review and remaining gates.
- 2026-09-23: M3 synthetic native and real-UI checkpoint: 11 one-attempt turns under a durable 22-generation/14-embedding spend, exact revision-confirmed correction/removal, active-profile cross-conversation recall, simultaneous subject isolation, and archived older-message citation. Two generated replies overpromised removal/future concern behavior; [ADR 0026](adr/0026-memory-removal-reply-boundary.md) records the shared prompt correction and unrerolled evidence. No positive semantic retrieval, relationship schema, long-session operator acceptance, fresh qualified-provider matrix, conformance, ledger promotion, or release is claimed. [Finding](findings/m3-native-acceptance-2026-09-23.md) and [M3 plan](plans/m3-agent-studio-continuity.md) hold exact boundaries for director review.
- 2026-09-23: Separate post-fix regression spent 4/6 DeepSeek generations and 2/6 Spark embeddings under a new durable ledger. Real UI removal of B's pre-existing committed preference produced a `forget` revision and a pending/limited reply; a fresh subject's unsupported check-in request produced no fact and no promise of future outreach. One planned run per case, no retries/rerolls; original 22/24 and 14/24 ledger and failed replies remain unchanged. Read-only release trace: DGX chat + Spark retriever and local llama compatibility are the checked-in target, not provider-name invariants; current release promotion nevertheless requires passing llama compatibility. Await director/user choice to make incumbent chat endpoints and call budget available or explicitly approve a different production target. No route switch or qualification was performed.
- 2026-09-23: [ADR 0028](adr/0028-agent-runtime-qualification-request-ledger.md) adds static, shared pre-request caps to standard API/worker construction and a budgeted full-matrix preflight. Cross-process/restart and fake-provider tests pass; the canonical workflow is now governed source. Proposed stage limits remain unapproved, no clean qualification or release-mode host has run, and the historical release ledger is untouched. [Release-preparation plan](plans/m3-provider-neutral-release-preparation.md) records exact staged synthetic cases and remaining canary/host gates.

## Updating This Tracker

Use `planned`, `in progress`, `blocked`, `complete`, or `deferred`. Update when
work starts, blockers appear, scope changes, or completion is verified. Link the
active plan and evidence; state the next action and remaining limitations. Keep
detailed checklists only for the active milestone. Avoid percentages, duplicate
status documents, and orchestration ledgers.
