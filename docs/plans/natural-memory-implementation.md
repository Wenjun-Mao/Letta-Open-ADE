# Natural Memory: Bounded Implementation Plan

Status: proposed for Pro/user review, not authorized implementation or live calls.
Plan revision: 2, incorporating the first implementation-plan reviews.
Design authority for review: [revision 4](../architecture/natural-memory-design.md).
Source baseline: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`; revision-3 packet:
`c01f45a045eb0fdd0fc6b3e18add82f2dbb57024`. The handoff pins this plan's later commit.
Rationale: [round-three assessment](../findings/natural-memory-consultation/pro-round3-assessment.md).
Execution corrections: [plan-review assessment](../findings/natural-memory-consultation/pro-plan-review-assessment.md).

## Outcome And Scope

Make Lin Xiaotang understand ordinary durable factual updates and recall relevant
current understanding without command-like user wording. Keep PostgreSQL, immutable
messages, versioned facts, explicit subjects, curated tools, synchronous review,
worker leases/cancellation, and ADE-owned retries. Implement the revised lifecycle,
source authority, write consistency, and operator visibility. Select context policy
only after a bounded comparison; implementation completion is not release approval.

This is the single plan for the new natural-memory scope. The earlier
[M3 UI plan](m3-agent-studio-continuity.md) records delivered work; its composer-only
removal contract is intentionally amended here, not another implementation path.
[Release preparation](m3-provider-neutral-release-preparation.md) still owns provider
qualification/promotion after product acceptance and the separate tool-contract fix.

Excluded: new memory framework/service, general historical-revision search/repair,
cross-conversation raw-transcript retrieval, continuity/event tables, background
review, graphs, inferred biography, global nonuse/erasure, multi-user authentication,
arbitrary tools, automatic provider fallback, and unrelated refactoring. Source-window
research stays deferred; no requirement here silently assumes it is implemented.

## Contract Decisions For The Implementation Handoff

- Mixed natural proposals use add, revise with a closed reason, end, reassert,
  and forget; no regex-selected whole-message mode. Separate independently mutable
  preferences by application-owned assertion IDs, not category alone. Singleton
  identity remains singleton. Matching uncertainty abstains, not destructive merging.
- Same-turn no-save/removal takes precedence for the same assertion across all
  proposal ordering and equivalent restatements. Unrelated additions remain eligible.
  No-save does not automatically delete an existing fact without clear removal intent.
- One derived lifecycle view serves targeting, selective recall, guards, and UI.
  Inactive is not forgotten; descriptors identify the withdrawn assertion without
  claiming it current/true. Forgotten chains never enter model fact selection.
- Bind one coherent memory generation at accepted user input, before provider work.
  All effective memory/identity writers advance it transactionally. Retain exact
  target versions and scope checks. Generation conflict is terminal; same-key replay
  returns that run, and fresh submission requires deliberate user action.
- One complete-message clarification suffix, at most eight prior users, is selected
  once for generation and review. Reserve candidate-reply capacity first. Source
  authority distinguishes user assertion/endorsement from assistant referent; no
  summary, tool output, or assistant claim alone becomes user write evidence.
- Review sees the proposed reply as reference-only. Its claim-specific outcome may
  permit a write, defer an unresolved dependent write, or detect an explicit reply/
  write contradiction. Contradiction fails the atomic attempt; do not fix prose
  silently or add a model call. Unrelated questions/writes remain independent.
- Operator removal shares the mutation boundary but has genuine operator causation,
  not fake runs/quotes. Multi-target removal and action outcome are atomic and
  idempotent. The receipt is historical action success, not proof of current absence.
- Prior narrative is attributed evidence, not certified current by a summary date
  or generation. Full-snapshot admission is control A, not a settled production rule.
  Recent-dialogue-first B must earn adoption through the comparison below.

Record these approved contracts in one concise ADR when implementation is authorized;
do not label a new ADR Accepted during this review checkpoint. Amend references to
ADRs 0021/0022/0026 explicitly; retain their original historical text.

## Affected Boundaries

All runtime paths below are relative to
`services/ade-api/src/ade_api/features/agent_runtime/`.

| Responsibility | Existing entrypoints and planned responsibility |
| --- | --- |
| Domain and review | `contracts.py`, `fact_registry.py`, `memory_review.py`, `memory_policy.py`, `reviewer.py`: lifecycle, scoped assertions, source roles, mixed proposals and consistency outcome |
| Persistence | `persistence/metadata.py`, `persistence/memory.py`, `memory_commit.py`, `persistence/memory_source_read.py`: migration, coherent snapshots, current lifecycle views/indexes, provenance and atomic generation |
| Turn ownership/evidence | `run_service.py`, `turn_execution.py`, `worker_finalization.py`, `retry.py`, `worker_events.py`, `provider_tracing.py`: acceptance fence, bounded work, terminal conflicts and failure-capable diagnostics |
| Context/tools | `context.py`, `compaction.py`, `embeddings.py`, `tool_policy.py`: whole-record packing, shared bundle, lifecycle selection, avoid redundant calls |
| Product API | `agent_studio_api.py`, `resource_service.py`, `presenters.py`, `service_protocol.py`: typed operator removal and lifecycle/source readback |
| Operator UI | `apps/ade-web/src/features/agent-studio/`: lifecycle display, exact citations, explicit removal, conflicts and action replay wording |
| Evaluation | `workflows/evals/character_memory_dev/`: add one native natural-memory diagnostic and colocated fixtures/tests/artifacts, reusing existing API evaluation sessions and request ledger |

Do not create parallel storage or a general strategy framework. Split touched
oversized modules by cohesive responsibility before adding code, using the existing
feature directory. In particular, inspect `contracts.py`, metadata, reviewer,
turn execution, and the Agent Studio hook; avoid a new catch-all helper module.

## Ordered Checkpoints

### 1. Freeze Testable Semantics Before Runtime Edits

Convert the [22 worked arcs](../findings/natural-memory-consultation/design-scenarios.md)
into chronological, isolated fixture branches with exact expected state, source
authority, permissible reply claims, and unsupported labels. Add the round-three
composition cases before implementing fixes. Retain original failed evidence.
Establish current tests, then add failing focused tests for the new contracts.
Reuse the HTTP client/artifact primitives in `workflows/evals/agent_runtime_acceptance/`
where suitable; do not duplicate its runner, promotion machinery, or frozen scoring.
Keep the new diagnostic separate from canonical qualification until explicitly adopted.

Keep deterministic assertions distinct from semantic judgments. Scripted proposals
test storage, fake providers test mechanics, and fixed contexts test generation;
none alone establishes natural extraction/retrieval quality. No provider use here.
Exit: fixtures cover every rule and negative branch without future-turn leakage;
tests fail for the intended missing contract, not unrelated setup failure.
Offline harnesses deny outbound provider requests and use fake transports; loading
the operator's normal environment must not turn a test into an unbudgeted live call.

Freeze the checkpoint-4 paired recipes and checkpoint-6 matrix before generation:
case IDs, eligible evidence/cutoffs, variant, lifecycle state, numeric input/output
allocations, record sizes, expected useful answer and prohibited claims, required
versus diagnostic cells, and stop classification. The same mandatory envelope applies
to A and B; A0 is diagnostic-only. Include answerable dog/interview follow-ups under
unrelated-memory pressure, not only low-load or intentionally unanswerable probes.
Pressure fixtures must exercise A's history-withholding threshold while B's required
bundle and both full reviewer requests fit. If no such region exists at the selected
budgets, report that limitation before live approval, not an invented comparison.
Freeze fixtures/thresholds before observing replies; do not reclassify failures as
outside-envelope afterwards. No live winner is inferred from fake-model tests.

### 2. Lifecycle, Provenance, And One Transaction Boundary

Extend the existing schema through an additive Alembic migration after current
revision `20260902_0006_run_runtime_mode.py`. Preserve IDs, immutable text/revisions,
source links, current values, and embedding-space identity. Changes must cover:

- Separate subject-memory generation and accepted-run generation, distinct from
  subject display-name version. Initialize existing subjects at a documented
  baseline; do not pretend the counter reconstructs historical mutation counts.
- Active/inactive/forgotten projection status, closed terminal/change reasons,
  and stable assertion identity. Existing preference records remain explicitly
  legacy/category-based; no automatic decomposition or invented evidence.
- Revision causation: exactly one conversation-run or typed operator-action origin,
  with ownership constraints. Extend message-source relationships with validated
  authority roles; assistant referents remain attributable but never sole authority.
- One operator-action receipt with request hash, scope, expected generation and
  target versions, terminal outcome and revision IDs. No independent mutable copy
  of lifecycle descriptions; derive those from existing facts/revisions.

Use a short coherent read transaction for the reviewer snapshot; no database lock
spans a provider call. Under finalization locks compare accepted generation and all
targets; commit assistant, revisions, indexes, events, and generation together.
Operator command uses the same ownership/version/lifecycle validation and commit
primitive, without conversation generation. Validate every target before any effect.
Same-key/different-body conflicts; replay returns the recorded outcome. Transaction
failure leaves no partial effects or claimed successful receipt.

Keep historical legacy `correct` reasons unspecified. New location writes mean
reported residence; do not relabel ambiguous old visits. Legacy composite partial
removal needs user-restated retained assertions, not a semantic migration guess.
Terminal descriptors need current-revision index text and embeddings; forgotten
records lose read eligibility even while their audit rows remain. No stale active
embedding may masquerade as an ended assertion. New index writes remain inside the
existing embedding failure/atomicity contract; operator forgetting needs no embedding.

Preserving vectors is not enough: current lookup also filters `retrieval_policy_version`.
Document compatible index/read-policy versions separately from semantic embedding
space. Preserve compatible legacy active-document reads, or require a separately
budgeted reindex before comparison; never relabel incompatible vectors or call
providers inside SQL migration. Populated tests must retrieve legacy active facts,
new current terminal descriptors, and exclude forgotten chains under the new reader.
All variants start from the same coherent populated state, not differently indexed copies.

Exit: fresh and populated isolated PostgreSQL migration tests; add/revise/end/
reassert/forget, source-role constraints, rollback, cancellation/lease fencing,
ABA and identity races, two subjects, operator replay and independent pool readback.
No production volume changes. New tables/foreign keys also update evaluation cleanup
and the existing explicit reset path, with purpose guards and absence verification.
For this campaign, use an exclusively owned disposable database and dispose of it
only after the entire campaign stops and artifacts are retained. If case cleanup is
needed, delete a complete exclusively owned evaluation-subject closure atomically;
do not infer ownership from `purpose=evaluation` alone. Refuse individual conversation
purge when surviving records depend on its sources/revisions. Check active work across
the whole deletion scope, including operator mutations. Test C1/R1 -> C2/R2 -> C1/R3,
operator origins, surviving source/predecessor links and current pointers, not merely
absence of foreign-key errors. No generic graph cleanup framework or product erasure.

### 3. Reviewer And Turn Integration

Replace intent-selected schemas with the mixed proposal contract. Validate exact
source spans/roles, current anchor, bound subject/conversation, compatible scope,
target state/version, one mutation per record, and same-turn no-save exclusions.
Do not rely on new UUIDs to solve semantic duplicates. Stage all proposals before
checking conflicting add/forget intents so order cannot bypass the rule.

Add a bounded, typed claim-consistency result from the same reviewer call with
reason/source references. It must identify affected proposals/claims; free-form
reviewer prose cannot mutate state. Detecting contradiction yields terminal failure,
not a repair call; unresolved reference yields observable per-claim no-write.
Test explicit partial assent, missing framing, quoted/fictional statements, and
negative/no-save clauses. Broader semantic reliability remains an empirical gate.

Enforce accepted generation at initial snapshot and finalization. Exclude generation
and semantic-validation conflicts from retryable transport errors. Preserve accepted
message and failure trace; never auto-create a replacement run or refresh its fence.
Already-started no-op replies can retain the documented stale snapshot behavior.

Exit: fake-provider API-to-worker tests for mixed operations, exact attempts/timeouts,
claim consistency, shared evidence, provider/embedding failure, cancellation and
lease loss. Current reviewer repair stays zero for the DeepSeek lane.

Failed-attempt diagnostics are an explicit deliverable, not success-event reuse.
For opt-in, server-bound synthetic evaluation runs in the isolated database, retain
actual serialized input/bundle manifests, tool evidence, candidate visible reply,
typed review proposals/claim dispositions, and terminal commit outcome even when
finalization fails. Mark absent stages explicitly and rejected candidates as
uncommitted/undelivered. Write only to the existing rooted evaluation artifact path,
never transcript, fact storage or retrieval. Mark excluded authentication/private-
reasoning fields explicitly rather than dumping raw wire bodies. Do not retain secrets
or raw exception text, or enable production prompt logging. Normal events keep safe
bounded reason codes/references. A fake false-veto test must prove evaluable evidence
with zero assistant/memory commit and zero generation advance; cover later embedding/
commit failures too. Failure to retain required evidence makes the cell unscorable,
not successful; an unsafe capture boundary stops the campaign.

### 4. Context Construction And The Bounded Comparison

Implement one assembler with a workflow-controlled comparison input, not a public
policy selector or permanent second runtime. Freeze the recipe before evaluation:

| Variant | Prior dialogue and memory admission | Purpose |
| --- | --- | --- |
| A | Whole active/inactive lifecycle snapshot required before prior dialogue/summary; otherwise explicit withholding | Selectable conservative control |
| A0 | Same prerequisite as A, summary omitted under the paired controls below | Diagnostic-only supplied-summary ablation |
| B | Reserve shared local suffix first; select current active/terminal views within remaining budget; no summary or older raw windows | Selectable recent-first admission package |

Freeze preselection inputs, not identical final prompts:
- A/A0: identical raw-message cutoff, eligible pool, lifecycle snapshot and nonsummary
  section contents/order. Preserve the summary's `through_sequence` boundary even in
  A0; removed summary allocation stays unused. No earlier raw messages or extra facts
  fill the gap. Assert these invariants in serialized manifests. Hand-authored summaries
  test interpretation only; generated-summary production behavior needs real compaction.
- A0/B: identical eligible local pool (at most eight prior users with complete exchanges),
  lifecycle state and total budgets; no older windows in either. Where A0 withholds
  history, use the same selective retrieval/expansion recipe as B within its available
  allocation. Final bundles may differ intentionally. This compares full-versus-selective
  recent-first packages, including retrieval cost, not one isolated Boolean effect.
- A/B product probes use that same local pool and state; A's summary input, if any, is
  declared per cell. A0 results never automatically qualify A. Evidence reuse needs
  identical serialized requests AND relevant processing/commit behavior demonstrated
  per cell, not assumed from the shared prerequisite. Do not build an equivalence framework.

All variants share policy/persona, generation/reviewer models, source boundaries,
full reviewer target visibility, output caps, and total provider-request limits.
Bind the variant through the isolated development/evaluation composition and record
its policy identity, never a model argument or public chat payload. Matching API/
worker instances must use that binding; a release deployment cannot select an
unqualified experimental variant. Do not add automatic A-to-B fallback.
B starts with existing semantic retrieval extended to current lifecycle descriptors,
plus bounded exact-entity expansion using eligible current identities from the
current message/shared bundle. No new reranker, lexical service, graph, or additional
model. Freeze limits/tie-breaking in the fixture config; count records actually
supplied, not candidates. Ambiguous names cannot authorize a write or cross subjects.

Pack whole records/messages. Preserve required policy and current input. Reserve
reviewer input for the maximum permitted user-visible candidate reply using its
own tokenizer/estimator, not assumed equality with generation tokens. Also reserve
reviewer output, schemas, and safety margin. Check actual serialized requests,
including tool continuations. Overflow fails rather than clips evidence or swaps
only the reviewer's bundle. If a shared suffix cannot fit, mark dependent claims
ineligible. Record this as lost continuity, not a passed safety case.

Determine optional narrative eligibility before compaction. A/A0 full-snapshot
turns skip redundant automatic query embedding/search; genuine selective paths
retain it. Optional `search_memory` returns current lifecycle views under the same
scope/version policy. Explicit required-tool requests still execute a real declared
tool contract, not fabricated events. The existing DeepSeek forced-tool mismatch is
separate: do not change thinking mode or weaken its qualification case in this plan.

Offline pressure grid: 0, 12, 48, 128, and 256 eligible records, short and long
assertions, including inactive descriptors. Add exact whole-request boundary tests
just below/above each allocation, not only record counts. Use the same serialized
data and total budget for all variants; count selection/setup overhead. Reviewer
overflow is measured separately and remains a failure for every variant.

Exit: all deterministic boundary tests and paired-control assertions pass;
success and failure artifact manifests show exact sections,
IDs/versions, source roles, bundle membership, omissions, token estimates/usage,
provider counts, and commit outcome. A live winner is not inferred from fake models.

### 5. API And UI Completion

Keep `/api/v3` and existing turn/run/event/cancel routes. Extend subject-memory
readback with `memory_generation`, lifecycle status/reason, identifying descriptors,
and typed message/operator provenance. Existing fields/legacy operation values
remain readable; new values are deliberate client schema extensions, not aliases
that misrepresent history. No public model-supplied subject or operator origin.

Propose one narrow command:
`POST /api/v3/agent-studio/subjects/{subject_id}/memory-removals`.
Input: idempotency key, expected memory generation, nonempty unique fact-ID/version
targets. Bound workspace, purpose and operator authorization are server-validated;
require active eligible product scope and reject another subject's targets. Receipt:
action ID, committed outcome, revision IDs, resulting generation and replay flag.
Use HTTP 409 for generation/target/idempotency conflicts, with structured reasons;
no partial multi-target success. Do not add general manual fact CRUD.
Reuse `require_operator` and existing local deployment/auth controls, including
reader-denied tests; an action's origin field is never authorization.

Agent Studio displays active versus inactive/forgotten audit state without confusing
withdrawn values for current preferences. Removal confirms exact targets and limited
Option A effect, then shows authoritative receipt plus current readback. A replay
cannot claim new absence. Correction remains a natural reviewed turn; no direct
operator correction endpoint. Show terminal conflict and offer deliberate fresh
submission, not an automatic retry or silent composer send.

Separate capabilities: continuation requires a compatible runnable conversation;
direct removal requires active subject scope, operator authority and displayed
generation/target versions, not a runnable selected conversation; reviewed correction
requires an eligible conversation and deliberate turn. Test removal from an old-policy
read-only conversation, including when no runnable conversation exists for that subject.
Replace run-only correct/forget success matching with typed outcomes for run mutations,
operator receipts, per-claim deferral and terminal conflict/capacity/provider failure.
Show action receipt and fresh state separately: restatement racing readback is neither
proof of current absence nor evidence that the historical removal failed.

Render multiple exact user spans and assistant referents with their roles; operator
actions render as actions, not fake messages. Keep archived source viewing read-only,
root/subject boundaries, rapid-switch safety, and persona-version immutability.
Exit: contract/API/hook tests, OpenAPI regeneration/drift, web tests/lint/build,
and built-in-browser journeys on isolated real API/PostgreSQL. Label model stubs.

### 6. Bounded Live Acceptance And Policy Selection

Not authorized by approval to write this plan. After static readiness, submit the
frozen case list, selected routes, isolated DB, ledger location, and exact ceilings
for user approval. Proposed initial ceiling: 96 DeepSeek generation requests and
160 Qwen embedding requests, shared pre-request caps across API/worker/diagnostic.
This is a hard spend bound, not a guarantee that all cases fit. Include setup,
indexing, continuations, compaction, and reviewer calls; no fallback/rerolls. Use
180-second per-turn timeout, zero additional retries and zero reviewer repair.
Before live approval, fake-transport tests must prove that every diagnostic/setup
provider path reserves against that same durable ledger before sending; no standalone
embedding client bypass. Exhaustion stops subsequent probes and preserves incomplete results.

First run eight native natural-update turns: preference add, scoped addition,
natural correction, end/invalidate, clear endorsement, same-turn no-save, explicit
removal, and fresh post-removal restatement. Use source-linked, isolated setup for
cases needing another fact type; distinguish scripted setup from model extraction.
Stop on a boundary violation or failed required state outcome; preserve the evidence.

Then test both selectable A and B on six mandatory response probes: dog clarification,
interview reply, cross-conversation breakup against old local dialogue, residence versus visit,
selective ended-state recall, and irrelevant memory/repetition. Include the frozen
low-load and pressured short-exchange cells from checkpoint 1. Replay identical
synthetic setup per variant, not shared writable state. Add A0/B diagnostic cells
and A/A0 supplied-summary pairs for old dialogue compacted after a change and
end -> forget -> old history; use only manifest-proven equivalent cells to avoid
duplicate calls. A0 is not a third product candidate. Before accepting A, run the
actual compactor on both summary arcs and verify its output plus downstream reply/
review outcomes; scripted summaries cannot substitute. Count every compaction call.
The frozen matrix must distinguish these cells and fit a reviewed request schedule
under the same proposed caps; no automatic cap increase or assumed completion.

Selection gate: zero observed isolation, forgotten-fact-selection, provenance,
atomicity, or exact-retry violations; every required lifecycle outcome must match
its fixture and every predeclared forbidden reply claim must be absent. A bad
control answer is not permission for the same error in B. Every selectable policy
must meet the same predeclared useful-answer criteria on every mandatory case inside
the common frozen envelope, including short exchanges under unrelated pressure,
without skipping review. A relevant supported answer need not recite a fact or match
an exact string. Correct abstention on an unanswerable case differs from withholding
an answer the eligible evidence supports. Record missed writes, false vetoes,
abstentions, withheld context, latency and cost. Report useful delivered answers over
all scheduled required probes, plus executed coverage and failed/vetoed/unrun counts;
never score only delivered replies or label unrun cells observed failures. Review
claims against source, and use blinded human comparison with ties for warmth/relevance. A finite
sample is bounded evidence, not a universal accuracy estimate or release gate pass.

Predeclare stop reasons: isolation/privacy/provenance/atomicity/exact-attempt violations,
failed required mutation state, lost authorization, invalid infrastructure/evidence
capture or budget exhaustion stop the campaign. Ordinary reply-quality failures,
unnecessary clarification or false veto on response-only probes disqualify that
candidate on the required cell but allow remaining authorized comparisons; they
do not justify rerolls. Failure of a required mutation remains a campaign stop.
Report stopped or unscorable cells explicitly. Incomplete required matrix coverage
means no winner, even if the other candidate failed. Never transfer A0's results to A
without the explicit equivalence proof above, or waive compaction because A ran first.

If neither policy passes, or results trade safety for continuity, pause at this
material decision; do not quietly adopt B, expand scope, or consume another budget.
If one or both pass, document each passing policy's tested envelope and reviewer-capacity limit,
including this comparison's exclusion of older raw windows; do not qualify untested
historical coverage through that result. Request product-policy acceptance with the
measured quality/cost tradeoffs; no automatic tie-break adoption. Retain compact evaluators, not unused product
strategy machinery. Only the accepted policy becomes the normal runtime binding.

## Verification, Migration, And Release Boundaries

Run focused tests first, then established commands (during implementation, not now):

```sh
uv run python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/tests
uv run python -m pytest
uv run ruff check services packages workflows scripts tests
uv run python scripts/check_python_format.py --base origin/main
uv run python scripts/export_openapi.py --check
npm --prefix apps/ade-web run test
npm --prefix apps/ade-web run lint
npm --prefix apps/ade-web run build
ADE_ENV_FILE=.env.example docker compose --env-file .env.example config --quiet
make check
```

Set `ADE_REPOSITORY_ROOT` to the retained checkout where required. Run PostgreSQL
tests on explicit disposable URLs, including a separate migration URL; list skipped
tests and fill those gaps. Keep the known stale-policy gate visible and unwaived;
report the full result, not a filtered suite as all-green. Do not rebind historical
release receipts to make source changes appear qualified. No expected new failure
may hide behind that known gate. OpenAPI and source-map checks cannot prove behavior.

Before any eventual populated deployment: verify backup/restore on a cloned volume,
drain workers or explicitly terminate accepted runs with evidence, prevent mixed
old/new writers, migrate, build matching API/worker/web, and run readback checks.
Never truncate/reset production data. Legacy terminal runs retain provenance without
fabricated accepted-memory generations; no in-flight old run crosses the write change.

New behavior needs new immutable policy/definition bindings. Preserve old prompt/
persona versions and conversations; do not silently rewrite them. The proposed
cutover keeps old-policy conversations readable and requires a newly bound
conversation for new semantics, retaining the subject when requested. Test and
explain fresh-send rejection versus historical read/idempotent replay access.
A new conversation shares eligible saved facts, not the old conversation's unsaved
dialogue, summary or missing antecedent for a bare "yes". No silent transcript copy
or promise of seamless continuation. Direct subject removal remains independently
available under checkpoint 5. Do not let unsupported old
workers write the extended store. The current deployed system stays untouched now.

Rollback is a verified matching application/database backup restore or a specifically
tested compatible forward fix, not a guessed destructive downgrade. New writes and
operator receipts can make old binaries incompatible despite additive SQL. Deployment
authorization must include its recovery point/data-loss window; none is assumed here.

After product acceptance, resolve the separate required-tool conformance contract,
then follow fresh qualification and promotion from the release plan. Mark M3 complete
only when its evidence requirements pass. Keep checkpoint commits on the current
branch; merge/push main and remove the branch/worktree only after user-approved,
fully verified delivery. Publishing this review checkpoint is not that cutover.

## Coverage And Stop Conditions

| Cases | Owning checkpoint and required distinction |
| --- | --- |
| Arcs 1-4, 7, 13-16, 22 | 1-3: natural change/error/unknown history, scoped preferences, legacy boundaries, residence versus visit; no inferred preference from consumption |
| Arcs 8, 10-11, 17, 20-21 | 2-3/5: source roles, no-save, endorsement, subject/root isolation, operator causation, concurrency and replay |
| Arcs 2, 5-6, 9, 12, 18-19 | 4/6: evidence availability, current lifecycle recall, context integrity, useful restraint, historical uncertainty; deferred source-search cases stay unsupported |
| New composed cases | 1-6: explicit reply/write contradiction, partial yes/no, unrelated-question false veto, reply reserve, end/forget/old-history exposure, action replay after restatement |

Stop for a semantic scope change, destructive recovery, missing provider authority,
exhausted budget, failing hard boundary, or unresolved context-policy tradeoff.
Do not demand routine confirmation between authorized static checkpoints. Test
granularity/module names remain engineering choices; product semantics, rollout,
live budgets, and acceptance gates do not.
