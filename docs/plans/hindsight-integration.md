# Hindsight Integration: Implementation Plan

Updated: 2026-10-18. The user agreed to the next deliverable: one complete
Hindsight-backed ADE conversation path, inspectable delivery/recall evidence,
and verified capture of the actual Character request. This revision makes
Stage 1 executable in ordered increments and proposes one execution-approval
package. The user subsequently approved M0-M6 and A1-A6 and started the active
implementation goal on 2026-10-18, with GitHub Actions explicitly excluded.
Implementation and its required live verification are now authorized and in progress.

## Outcome, Authority And Domain Boundaries

Stage 1 delivers a fresh ADE conversation path: save original messages, retain
them asynchronously in Hindsight, recall within the same relationship, inspect
progress/memories, and retry failed recall without resending the user message.
It also connects the existing assessment kit to real, complete observations.
Stages 2 and 3 remain later qualification work, not implied by Stage 1 approval.

Authority: [PC-01 through PC-14](../product-contract.md), especially PC-02/03/04/10
for ownership/continuity, PC-05/07/08/09/14 for Memory/persistence, PC-11/12 for
Character, and PC-13 for hosting. [ADR 0068](../adr/0068-hindsight-default-memory.md)
owns settled product decisions; [ADR 0069](../adr/0069-offline-character-assessment-kit.md)
owns the offline kit. Record newly settled durable implementation contracts in
the owning ADR; this plan does not silently amend product intent.

| Responsibility | Question and evidence | What it cannot establish |
| --- | --- | --- |
| Memory | Were attributed sources delivered, interpreted, organized and retrieved correctly? Inspect original sources, native facts/observations and raw recall. | A fluent reply is not Memory qualification. |
| Character | Given its actual inputs, was the response grounded, contextually appropriate and faithful to the persona? Use PC-12's three separate lenses. | A retrieval miss is not automatically a Character defect; good recall is not Character acceptance. |
| Interface | Are saved messages, delivery state, read-only inspection and Retry shown truthfully? Verify API/UI behavior. | A successful HTTP response is not semantic correctness. |
| Runtime and assessment support | Did the normal product path execute, and is the record complete and attributable? Inspect source/request/commit joins. | Capture validity and scripted rehearsal results are not domain-quality scores. |

Keep these conclusions separate in discussion, tests, findings and handoff.
The [historical assessment](../findings/hindsight-integration-assessment-2026-10-10.md)
and [revision-5 findings](../findings/hindsight-semantic-follow-up-2026-10-11.md)
remain bounded evidence. Hindsight adoption is settled; do not restart vendor
selection or inherit the old cross-character profile exception.

## Scope And Exclusions

- Work serially on `main` in the primary checkout. No new development worktree,
  chat, Goal campaign, scheduled automation or parallel implementation writer.
  Scoped commits/pushes follow [ADR 0048](../adr/0048-mainline-development.md).
- Use a new workspace/subject, new relationship banks and fresh isolated databases.
  Do not import existing ADE/trial conversations or archived experiment banks.
  The old OCI experiment stack was separately removed; its retained archives
  are evidence, not a runtime dependency or a source for backfill.
- Preserve authored personas, immutable definition versions, bounded current-chat
  dialogue, compaction provenance, finite tool execution and one ADE product API.
  No broad Character redesign, persona tuning or mandatory reflect stage.
- Replace obsolete native reviewer/fact contracts directly. No dual writes,
  native fallback, generic backend framework, second semantic reviewer or fact store.
  Preserve existing stored data and historical evidence, not executable compatibility.
- No manual memory-removal API/UI, removal-preservation probe, guaranteed deletion,
  conversational no-save policy, cross-character sharing or old-source rebuild.
  Ordinary corrections remain Hindsight's responsibility, not ADE update commands.
- No existing-service replacement, public exposure, new provider/account, paid
  infrastructure upgrade, production cutover or release-ledger promotion.
- GitHub Actions is manual-only. Do not dispatch, retry or restore automatic CI
  without an explicit new user request. Local verification and normal pushes remain.

## Current Source And Owning Boundaries

Rechecked against `bd7c873`; runtime/router/web sources are unchanged since
the prior `f0d84df` review. The separate `145cd25` CI-policy change does not
implement Hindsight. Refresh source status before execution; do not assume
historical deployment, capacity or provider identities are current.

Paths below are under `services/ade-api/src/ade_api/features/agent_runtime/`
unless a different owner is named. Split oversized touched modules along their
responsibilities; do not add a generic cross-domain helper collection.

| Owner | Required work and present coupling |
| --- | --- |
| `run_service.py`, `persistence/conversations.py` | Add user-delivery intent to the accepted-message transaction; remove native memory-generation admission dependency. |
| `worker_finalization.py`, `turn_result.py`, `worker_events.py` | Replace required reviewer/fact results; atomically commit reply, outcome and reply-delivery intent within ADE. |
| `turn_execution.py`, `turn_context_selection.py`, `turn_memory_snapshot.py` | Replace native snapshots with scoped recall; compose independently available local dialogue and bind what was delivered. |
| `executor.py`, `turn_compaction.py`, `compaction_executor.py` | Preserve bounded continuation/compaction; route discretionary memory search through the same scope and failure contract. |
| `worker.py`, `persistence/metadata.py`, migrations | Add durable delivery scheduling, leases and mappings without blocking the sole reply-worker loop. |
| `definition_service.py`, `deployments.py`, `contracts.py`, bootstrap/session modules | Remove obsolete reviewer/retriever role obligations; retain Character/persona/model identity. |
| `resource_service.py`, `agent_studio_api.py`, presenters | Change subject-only memory/source/status inspection to authorized subject-and-character ownership. |
| `agent_studio_reset.py`, `evaluation_sessions.py`, `database_boundary.py` | Retire SQL-only reset/purge assumptions and hard-coded workspace identity from the new path. |
| API `platform/settings.py`, `integrations/` | Own concrete Hindsight configuration and transport; product code must not import the evaluation workflow. |
| Model Router `app.py`, `forwarding.py`; runtime `provider_tracing.py` | Current traces lack complete bodies; Router changes model/payload/defaults. Capture actual post-normalization outbound requests, not an earlier approximation. |
| `apps/ade-web/src/features/agent-studio/` | Replace native memory types/controls; separate chat/run loading from fallible remote-memory reads, currently joined by `Promise.all`. |
| `workflows/evals/hindsight_integration/` | Own live collector, manifests, fixtures, tests, commands and ignored evidence; use public product/observation boundaries. |

## Implementation Contracts To Settle In Stage 1

These proposals operationalize existing PC agreements. Exact type/module/API names
are implementation choices. Freeze tested source-unit, operation-recovery, Retry
and observation contracts before dependent implementation; record rationale and
rejected alternatives rather than relying on implicit conventions.

### Memory Ownership And Delivery

1. One bank per persisted `(workspace, subject, character root)`, selected by ADE,
   never by model/browser-supplied bank IDs. Conversations and persona versions
   remain source metadata. Apply the same scope to recall, search, sources,
   observations and delivery inspection. Verify an empty new bank; an established
   bank disappearing is an error, not successful empty recall.
2. Store immutable message/source IDs, speaker, original time, relationship
   sequence, payload hash and operation identity before dispatch. Accepted users
   and committed assistant replies qualify independently; candidates do not.
   Keep delivery acknowledgement, retention and consolidation status distinct.
3. Start with per-message deliveries and bounded, attributed antecedent context
   for references. Earlier excerpts must not become new statements. Prove native
   append/replacement and partial-failure behavior before settling the source unit.
   Reject redundant whole-chat reprocessing and timestamp substitution on retry.
4. An ADE outbox uses independent scheduling, leases and bounded concurrency.
   Preserve relationship order; uncertain/exhausted delivery blocks only later
   deliveries in that relationship, not healthy recall or unrelated work.
   Expose queue age, blocked item, progress and operational reconciliation.
5. No network request inside an ADE transaction. Reconcile a timed-out native
   operation using its original identity and immutable payload, rather than
   blindly submitting again. Same-ID deduplication is not proof of failed-work
   recovery. Fence duplicate workers and stale completion.
6. Hindsight owns extraction, correction and consolidation. Version its identity,
   missions, model/embedding bindings and automatic consolidation schedule before
   ingestion. Demonstrate progress after downtime; do not inherit manual-only
   maintenance, the shared-profile classifier or a duplicate ADE reviewer.

### Reply Execution And Interface

- Recall normally on each attempt without waiting for pending retention. Combine
  characterization, product instructions, current input, bounded local dialogue,
  any current-chat summary and relevant memories. Preserve time/attribution and
  uncertainty; retrieved content is data, not privileged instructions.
- Bound the entire serialized request, including tools/continuations. Preserve
  compaction/source integrity and mandatory-input errors. The user's eight-message
  example was hypothetical, not approval to introduce a new window-count policy.
- A required recall or `search_memory` failure pauses the reply and exposes Retry.
  No Character error apology, empty-memory substitute or native fallback. Successful
  empty recall is valid; pending retention alone does not pause generation.
- Retry creates a fenced attempt for the same saved input, performs fresh recall,
  and acquires/releases the proper lease. Concurrent Retry, cancellation, stale
  workers and incompatible later conversation changes cannot duplicate or misorder
  input/replies. Delivery retry is a separate operation, not a new conversation turn.
- Proposed pause behavior: release the worker lease but retain the conversation's
  pending-input guard. Require Retry or Cancel before another user turn; cancellation
  keeps the accepted message and its delivery eligibility. Persona/archive/version
  changes that invalidate the saved attempt must reject Retry explicitly.
- Product chat/run state must load even when memory inspection fails. Show queued,
  processing, completed, failed and uncertain delivery truthfully; remote read
  failure is not an empty memory list. Require the selected relationship for all
  source/operation reads and reject stale UI selection responses.
- Retire one-store reset/manual removal controls in this path. Test cleanup owns
  paired disposable resources; it does not create a new product erasure feature.

### Capture And Interpretation

- Capture each real setup/probe request and tool continuation at its final
  provider-facing boundary, with role/phase, attempt, time, served identity,
  payload hash and outcome. Join ADE, Router and upstream IDs where available;
  explain missing provider IDs instead of inventing them.
- Keep setup requests separate from probe requests. The kit's current checks
  expect one current probe user message and cannot certify arbitrary setup traces.
  Add source-linked sidecars or a versioned observation contract for phase grouping,
  completeness and prompt-component provenance; do not weaken checks to import data.
- Identify persona/instructions, current input, local dialogue, summaries, automatic
  recall and tool recall separately. Preserve the exact complete request as well
  as its component manifest; reconstructing an ideal prompt is not capture.
- Source data belongs in the evidence record, not automatically in the probe
  prompt. New-conversation tests must verify absence of source dialogue and copied
  summaries from non-Hindsight input. Original excerpts returned by Hindsight
  remain legitimate retrieval, with their provenance visible.
- A same-chat out-of-window test must also check summaries and assistant
  restatements. If another route still supplies the answer, label that route;
  do not report Hindsight-dependent recall. Keep normal product context enabled.
- Collection is opt-in, operator-authorized and limited to the synthetic isolated
  workspace. Exclude credentials, auth headers and private reasoning at collection;
  restrict files/exports and do not put full captures in ordinary UI activity.
  Missing/unsafe capture stays incomplete, not silently repaired into a pass.
- The collector uses public API/observation surfaces and actual committed records.
  Corrupt joins, missed continuations, reused scopes and incomplete records must
  fail qualification. Offline declaration validation alone is insufficient.

## Stage 1: Ordered Implementation Deliverables

### Execution Checkpoints, 2026-10-19

These are scoped increments, not a claim that M0-M6 is complete.

- The [native source/recovery boundary](../findings/hindsight-native-boundary-2026-10-19.md)
  has actual pinned-runtime receipts, including lost acknowledgement, immutable
  replay, automatic consolidation and failed/partially committed retry. Controlled
  sources do not establish an ADE product conversation or qualify Character.
- The initial persistence/delivery library checkpoint had 23 passing
  application-role PostgreSQL tests and 61 focused offline checks. The subsequent
  reply replacement now wires acceptance/finalization to the outbox, normal
  required automatic/tool recall, paused saved-input Retry, separately bound
  compaction and independent delivery consumers. Controlled public-API/SQL
  verification is not live native product or browser proof. See
  [ADR 0073](../adr/0073-hindsight-reply-runtime.md).
- The focused backend gate passed 173 checks, including 39 application-role
  PostgreSQL tests. Both takeover regressions reproduced before repair. The
  full Agent Runtime sweep was interrupted after a native-era dummy claim omitted
  the new retry-group base and waited indefinitely: 466 passed, 111 skipped,
  80 failed and nine errors were observed, not a complete suite result. Of these,
  44 failures and nine errors are the unchanged frozen `executor.py` mismatch;
  36 failures require current-contract test reconciliation. The dummy was repaired
  without adding a runtime default; frozen evidence was not rebound. Further
  maintained-test reconciliation remains an explicit gate.
- The kit/guardrail run passed 115 tests. A broader Agent Runtime offline run
  produced 521 passed, 99 skipped, 44 failed and nine errors; all 53 failing/error
  test identities were already in the pre-change baseline. Frozen historical
  source mismatches remain visible and were not rebound. This is not a full
  repository pass or a waiver of any new-path gate.
- Backend source/API/SQL checks cover required recall and saved-input Retry.
  Relationship-scoped inspection and independent browser Memory loading are now
  implemented under [ADR 0074](../adr/0074-relationship-memory-inspection.md), with
  182 passing focused backend checks (40 application-role SQL cases), frontend
  production build and lint, plus 93 passing frontend tests. The
  [source-bound controlled browser replay](../findings/hindsight-interface-mechanics-2026-10-19.md)
  passed after repairing the Retry-receipt mismatch and intrinsic-width overflow.
  This is Interface/product-persistence mechanics, not native semantic proof.
  Remaining maintained-test reconciliation,
  complete actual-product capture, the six live probe slots and M6
  native product fault/closeout gates remain pending. Do not count this backend
  checkpoint as full M2/M3 or M0-M6 completion.
- Normal-worker private observations and the public-boundary collector now cover
  exact run/attempt/request joins, actual recall snapshots and source/component
  manifests under [ADR 0075](../adr/0075-product-memory-and-request-observations.md).
  Controlled SQL -> normal worker -> real Router -> recording-provider -> public
  collector checks include tools and seven corrupted/missing-join variants.
  The final focused local gate passed 349 checks, including 42 application-role SQL
  cases and supplementary activity/schema checks. OpenAPI generation
  reported no missing Chinese terms. No live provider call occurred in this gate.
  These are capture mechanics, not the six actual native product probes; the
  live demonstration and M6 remain pending. Current governed hashes now include
  the concrete Hindsight integration modules, without rebinding frozen evidence.
- The isolated full-product Compose stack and six-slot actor are implemented
  under [ADR 0076](../adr/0076-isolated-product-actor-and-provenance.md). The actor
  establishes exact user seeds and actual assistant replies through normal ADE,
  then probes a fresh same-bank chat. Completed live records require source-linked
  setup/probe/HTTP/native-readback sidecars on record and reload. Controlled SQL
  tests cover all three cases, tool continuation, rejected private-reasoning
  capture and altered readback files. The focused local gate passed 366 tests,
  including 46 application-role PostgreSQL cases, with no provider requests.
  These are software mechanics only; actual
  six-slot native execution, M6 and maintained-test reconciliation remain pending.
- Four real-SQL regressions reproduced expired ownership inside an old transaction
  and reply finalization blocked past expiry. The wall-clock and final-release
  repair is recorded in [ADR 0077](../adr/0077-database-wall-clock-lease-fences.md).
  The focused gate passed 370 tests, including 50 application-role SQL cases.
  The first full-product image activation was closed without product startup or
  inference; baseline identities/health remained unchanged and no owned container
  remained running. Its build receipts are not repaired-runtime evidence.
- A complete Agent Runtime offline sweep at the actor checkpoint produced
  490 passed, 123 skipped, 96 failed and nine errors. This includes maintained
  tests still using removed caller contracts and frozen historical inputs whose
  source hashes differ. The XML receipt is retained privately; reconciliation
  remains required, with no historical fingerprint rebind or full-suite claim.
- Actual candidate startup found a non-root authoring-directory permission failure
  after the fresh ADE migration. The owning workflow now seeds/hashes private
  authored assets and mounts them at existing registry paths, per
  [ADR 0078](../adr/0078-candidate-authoring-asset-seed.md). It does not chmod the
  image/release or change product registries. The focused gate passed 389 tests,
  including 50 SQL cases, real application-dependency construction and reconciled
  API tests for current compaction/chat inspection and absent purge/reset/removal.
  The failed activation's two startup Router observations remain retained; no
  six-slot product dialogue began. Both databases remain preserved stopped and
  baseline identity/health verified unchanged. Repaired live startup/M5/M6 remain
  pending, as does the rest of maintained-test reconciliation.
- The next actual activation confirmed API startup but failed the fault proxy's
  CPU-bounded health command. [ADR 0079](../adr/0079-cpu-bounded-http-health-probe.md)
  records the measured import cost and same-timeout HTTP probe replacement.
  The failed activation is stopped with baseline identity/health unchanged;
  startup traffic remains retained and no six-slot dialogue began. The final
  focused gate passed 438 checks, including 51 application-role SQL cases.
  Actual session bindings are now checked before any Character seed/probe call,
  with a zero-provider-call mismatched-persona regression. Session, deployment,
  workspace/claim and native-policy rejection tests were reconciled to current
  contracts without restoring retired callers. Remaining full-suite debt,
  repaired live startup, six-slot execution and M6 are still pending.
- The next stack passed startup, but actual public preflight rejected its ready
  worker because API/worker Memory endpoints differed. No dialogue slot started.
  ADR 0076 records the shared-endpoint correction; the resolved-Compose check
  reproduced the mismatch before the fix. The failed activation is stopped;
  all six baseline identities/health are unchanged. A separate immutable
  closeout correction distinguishes stopped-candidate health from baseline health.
  Maintained non-SQL runtime tests now pass (510, three evidence-absence skips);
  the unfiltered sweep still fails 44 checks plus nine errors, all in the three
  frozen historical story modules. Their source hashes/inputs remain untouched.
  The 231 workflow/Router/guard checks and 50 selected application-role SQL checks
  passed (the adjacent deployment-helper test makes 51 in that invocation).
  Timing additionally exposed all-completed retry backoff: each of three new
  half-second control-signal regressions failed, then passed with FIRST_COMPLETED.
  The existing historical reviewer-budget helper remains tested with its owner;
  no retired native reviewer or cutover gate was restored. M5/M6 remain pending.
  The final combined non-SQL gate passed 743 checks with three evidence-absence
  skips; the final selected SQL-only invocation passed 50 checks. Full-suite
  green remains unestablished because frozen historical replay still rejects drift.

Each deliverable includes focused tests, a source checkpoint and an updated
workflow runbook. Dependencies are explicit; none requires a fresh permission
request once the execution package below is approved.

### M0: Freeze Contracts And Establish A Reproducible Baseline

Inspect current owners, pinned native API/source and existing test failures.
Specify relationship mapping, outbox/reconciliation and reply-Retry transitions,
transaction boundaries, capture access and complete-request joins. Record durable
choices in ADR 0068 or the owning observation ADR, not a second product contract.
Prepare owned-resource manifests, offline fixtures and exact local/OCI commands.
Record `ITERATION_BASE` before each increment for changed-file verification.

Exit: contracts and failure tables are source-backed; targeted baseline results
are recorded; unrelated historical failures are distinguished from new regressions.
No provider call is needed for this step. Native feasibility remains M1, not assumed.

### M1: Prove The Native Source And Recovery Contract

Pin Hindsight 0.10.3 source `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`.
Use fake transport/SQL tests first, then the approved fresh OCI stack for bounded
native checks: reference-only input, original-time attribution, user-only retention
after failed generation, committed-reply attribution, correction versus change,
lost acknowledgement, immutable replay and failed/partial operation recovery.
Verify automatic consolidation, Chinese reranking and actual embedding identity.

Exit: the proposed source/recovery contract has source, operation-state and
readback evidence. Direct native probes qualify this boundary only, not ADE's
product flow. Diagnose/fix within the approved contract and repeat affected checks;
an unresolvable mismatch blocks dependent work, not permission to invent a
semantic bypass, silently weaken expectations or reopen vendor selection.

### M2: Implement ADE Persistence And Durable Delivery

Build fresh workspace/bank ownership, outbox schema/repositories and independent
delivery scheduling. Extend the accepted-user transaction and committed-reply
transaction, with immutable payload identity, order, lease fencing and readbacks.
Replace native reviewer/fact requirements across maintained runtime callers,
definitions, finalization, inspection and cleanup; remove superseded executable
paths rather than return fake empty review objects. Keep historical data intact.

Exit: real disposable PostgreSQL tests prove atomic source/delivery intent,
idempotent acceptance/finalization, concurrent worker fencing, restart reconciliation,
failed-generation user eligibility and unrelated-relationship progress. A blocked
delivery neither occupies the sole reply worker nor silently loses subsequent work.

### M3: Connect Scoped Recall And The Normal Reply Path

Wire scoped automatic/tool recall, complete context sizing, existing Character
execution, persistent pause/Retry, cancellation and final commit. Bind source,
persona/model versions and request identities. Do not wait for retention or add
test-only generation semantics. Keep current-chat compaction and source provenance.

Exit: successful empty recall generates normally; lookup failure produces no
committed reply; Retry preserves one accepted user message and at most one reply.
Delayed retention does not block healthy replies. Wrong relationship, missing
established bank, stale retries and tool-lookup failure are covered.

### M4: Complete Agent Studio And Public Inspection

Update API/OpenAPI contracts, definitions/bootstrap, client types, polling and
read-only memories/sources/delivery views. Separate ADE state from remote-memory
loading; show pause/Retry and processing/failure state. Retire obsolete reset and
manual-removal controls. Preserve established visual design and responsive behavior.

Exit: browser/API checks exercise a Chinese conversation, new same-character chat,
status updates and outage/reload/Retry. Changing subject/character cannot show a
stale result or expose another relationship through forged source/operation IDs.
No UI claim confuses queued delivery, completed processing and semantic correctness.

### M5: Connect Live Capture And Run A Small Real Demonstration

Implement the collector and phase/component manifests under the existing kit,
using verified public observation boundaries. Test capture completeness with a
recording fake server and the actual Router's post-normalization path, including
tool continuation, failed requests and commit correlation. Reject incomplete input.

Freeze the existing `q01-relevant`, `q02-correction` and `q02-change` cases,
two repeats each, with exact runtime/persona/model/config identities before running.
Use a fresh relationship per attempt. Send exact user seeds through ADE and retain
all actual assistant replies; do not inject authored answers into product history.
Use actor-only exports; evaluator rubrics and calibration replies never enter
Character or Memory input.
Observe processing completion as an evaluation step, then start a fresh probe
conversation without source dialogue/summary carryover. This does not add a
retention wait to ordinary replies. Record every attempt, not only successes.

Exit: six planned probe slots are accounted for, with real sources, native Memory
readbacks/recall, actual Character requests and committed replies or explicit
failures. At least one successful cross-conversation flow must be observed to
claim it works. Report correction/change counterexamples separately; no claim
of general Memory reliability or Character acceptance follows from this small set.
Human reviews may remain unreviewed in the kit; AI advice is not a human verdict.

### M6: Close The Stage-1 Safety And Evidence Gates

Exercise representative owned-stack faults: interrupted delivery/reconciliation,
recall outage and Retry, failed generation, restart, cancellation and stale-worker
commit rejection. Include negative subject/character/workspace access and one
deliberately delayed retention path. Use deterministic fault injection before live
faults; do not disrupt Spark, provider accounts or baseline OCI services.

Capture a coordinated recovery point for ADE and Hindsight, including in-flight
operation identities; preserve evidence and document restart/shutdown procedures.
Restore only if needed for owned-stack repair under the approval package; this
does not replace Stage 3's deliberate paired-restore qualification. Stop/drain
new services at closeout, preserve retained evidence/data and verify baseline health.
Rollback stops only the candidate. Restore only a proven image/schema/paired-backup
combination; never point the old native runtime at the new Hindsight workspace.
If reversal is unproven, preserve the candidate stopped rather than guess.

Exit: relevant offline/SQL/API/browser gates pass; stage evidence is source-bound;
no native fallback or duplicate reviewer executes; remaining semantic findings
have a named domain and evidence. Mechanical completion, Memory findings,
Character review status and readiness are reported separately. Unresolved required
gates remain failed/pending, not quietly waived to finish the milestone.

## Later Stages: Retained Direction, Outside This Execution Package

**Stage 2: broader boundaries and quality.** Expand isolation across archived
chats/persona versions, inspection/forged IDs and races; delivery crash points,
sustained backlog and model/DB contention; malformed/auth/timeout failures;
long Chinese context, compaction and tools; UI truth under outages. Inspect
native Memory facts/observations/recall for correction, attribution, uncertainty
and consolidation behavior. Separately calibrate human Character judgments and
run the full frozen assessment baseline with repeats and unseen variants.
Controlled-history cases do not prove product establishment of that history.

Stage 2 exit: required mechanical/isolation gates pass; Memory findings and
Character lens judgments are independently recorded. Known semantic failures
need a durable fix or explicit bounded acceptance before fresh-start readiness.
Human absence does not block recording evidence or other engineering work, but
cannot be replaced with fabricated human calibration/acceptance.

**Stage 3: recovery and fresh-start readiness.** Quiesce/drain or record in-flight
work; back up both stores, mappings and operation identities. Restore into new
owned databases with dispatch disabled until reconciliation, prevent simultaneous
owners, then run the actual restored APIs and a new turn. Do not bulk-replay old
conversations as recovery. Verify logical/schema state and user-visible invariants,
not volatile timestamps. Prepare a pinned source/image/config/model manifest,
auth/ports, backup/restore/shutdown runbook and a clean real-use workspace proposal.

Stage 3 exit: fresh restart/crash/paired-restore proof, unchanged baseline and a
reviewable activation package. Historical restores/dumps do not qualify it.
Production cutover, release promotion and continued unattended service operation
still need separate authority.

## Environment And Model Envelope

Use the previously selected OCI ARM host via `150.136.50.36_OCI_ARM`, not a local
Mac Hindsight server. The 2026-10-12 read-only check found four ARM64 cores,
23.4 GiB RAM and 99.4 GiB free under `/mnt/projects`; these are historical figures.
Before each activation, inventory capacity, ports, baseline container identities,
health and storage attachments without reading baseline conversations/databases.

Use a new Compose project, isolated network/credentials, owned fresh ADE and
Hindsight databases/volumes, unused loopback ports and private SSH tunnels.
Do not use root Compose data binds, shared PostgreSQL or the retired probe stack.
Reserve at least one core and 4 GiB RAM for the host/baseline; size the full stack,
serial builds and model downloads, monitor disk/health pressure, and stop owned
work before harming baseline services. Resource limits and failure thresholds
must be recorded before startup; inability to fit is not authority to evict work.
Mac browser automation may use the private tunnel. Keep live provider/model
traffic in the authorized isolated runtime, not ad hoc laptop experiments.

| Role | Approved-package starting route, to verify at activation |
| --- | --- |
| Character | Existing `deepseek::deepseek-flash` via isolated Model Router; retain configured thinking behavior and bind actual served identity. |
| Context compaction | Bind a compaction profile on the same DeepSeek route for the candidate; preserve summarization/provenance behavior and capture its requests separately from Character replies. |
| Memory extraction/consolidation | Same provider route with explicit Memory-specific non-thinking/JSON settings; requalify serialization/errors, no duplicate ADE reviewer. |
| Embeddings | Existing Spark `Qwen/Qwen3-Embedding-0.6B` route; verify dimensions, limit, query prefix and fingerprint, without restarting or changing Spark. |
| Reranking | Pinned CPU BGE-v2-m3 from the experiment; verify complete Chinese reranking and fit, not HTTP health alone. |

Use public pinned downloads and existing credential bindings; never print/copy
secrets into Git, URLs or evidence. Record image/source/config/model hashes,
all observed requests/retries, token usage and latency by role. Do not invent
billing totals, add spending gates, substitute a provider or quietly change persona.

## One Execution-Approval Package

**Granted, 2026-10-18:** the user explicitly approved M0-M6 and A1-A6 and requested
implementation through Relay Direct, with no GitHub Actions. This covers
their routine dependencies, diagnosis, repairs, retests and safe closeout.
No repeated permission at each milestone, service rebuild or fresh fixture.

| ID | Permission requested together for Stage 1 |
| --- | --- |
| A1: source and local verification | Edit source/API/schema/UI and maintained tests/docs on primary `main`; remove superseded contracts; install locked project dependencies; use owned disposable local PostgreSQL or OCI databases; commit and normally push verified scoped iterations. No GitHub Actions. |
| A2: isolated operations | SSH inventory/staging of clean committed source, pinned dependency/image/model downloads, isolated builds/migrations/starts, private tunnels and Mac browser interaction. Create only registered candidate resources and narrowly owned safety scripts/timers. No host reboot, firewall/public-DNS change, shared-service edit or new infrastructure purchase. |
| A3: existing inference | Use the listed DeepSeek account, Spark embedding route and CPU reranker for startup, native feasibility, real product turns, consolidation, diagnostics and recovery checks with synthetic data. Existing credentials only; no new account/provider/global model default. |
| A4: repair and retest | Diagnose and repair in owning ADE/Router/workflow modules and, if proven necessary, a source-pinned isolated Hindsight patch preserving the contract. Rebuild/redeploy only the candidate, adjust bounded operational settings, and rerun affected checks with preserved failures and new source-bound receipts. No answer-specific patches, manual fact repair or expectation changes to manufacture success. |
| A5: recovery and cleanup | Controlled stops/crashes/restarts, outbox reconciliation, paired backups and repair restores into new owned resources; remove only manifest-registered synthetic resources after preserving needed evidence and proving no external dependents. Never touch baseline/retained volumes, revoke shared credentials, prune broadly or replay history as recovery. |
| A6: bounded autonomy | Choose/re-arm finite activation leases and perform covered recovery without renewed user approval. Maintain durable progress/failure checkpoints, stop safely when unattended or unhealthy, and continue independent authorized work while a specific dependency is unavailable. No semantic waivers, new scheduled Codex automation or automatic expansion into Stages 2/3. |

### Safety Leases Are Not Repeated Approval Gates

Execution authority, once granted, lasts for M0-M6 until completed, cancelled or
changed by the user; it does not inherit an old campaign clock. Each activation
has an immutable manifest, owned resource IDs, a host-enforced finite expiry and
shutdown margin. Proposed maximum lease: 12 hours, with at least one hour reserved
for drain/evidence capture. Schedule new work only if its deadline fits.

At expiry/loss of supervision, stop new provider dispatch and owned workers/services,
preserve both stores and record incomplete operations. The active agent may
start a fresh activation under the same grant after checking baseline/headroom,
reconciling pending work and verifying there is no concurrent owner. Do not
rewrite an expired manifest, silently extend an admitted operation or rely on
client connectivity as the only shutdown mechanism. Prove the safety stop with
fakes before any live activation. No perpetual provider loop or rerolls solely
to fill time; justified diagnostic retests are not an arbitrary request-count gate.
Already accepted upstream work must be accounted for and reconciled; a local
shutdown is not proof that a remote inference request was cancelled.

### Decisions Delegated Versus Escalations

Autonomous choices include module/schema/API names, exact unused ports and owned
paths, bounded retries/concurrency/timeouts, immutable source/config versions,
test order, synthetic fixtures, safe patch/rebuild cycles and scoped publication.
For every failure, state cause/evidence/owning layer before fixing it. Capture
reusable insights, review their boundaries and promote stable decisions.

Seek new authority only for changed product meaning, a contract that cannot be
met without a tradeoff, new accounts/paid capacity, baseline/retained-data changes,
public exposure/cutover, semantic limitation acceptance, or a user-requested CI run.
If credentials, capacity or a service are unavailable, preserve evidence and
continue independent covered work; do not switch providers or claim completion.
Human review can stay pending while engineering proceeds. Permission cannot
override native tool restrictions or guarantee execution while the agent is offline.

Suggested handoff: "Implement M0-M6 under permissions A1-A6. Continue covered
repairs, retests and safe activation renewal without milestone approvals.
Keep CI manual-only and do not run it. Stop before Stages 2/3 or product cutover."

## Verification, Publication And Handoff

Run changed-module tests first, then disposable real-PostgreSQL checks with
`ADE_TEST_DATABASE_URL` bound to an exclusively owned database. Verify test
execution counts; a skipped database test is not proof. Follow with proportional
runtime/router/frontend/OpenAPI checks and the workflow-local live/API/browser
commands supplied by M0-M5. Commands below run locally, not GitHub Actions:

```sh
uv run --locked python -m pytest workflows/evals/hindsight_integration -q
uv run --locked python -m pytest services/ade-api/tests/agent_runtime -q
uv run --locked python -m pytest services/model-router/tests -q
uv run --locked ruff check services packages workflows scripts tests
uv run --locked python scripts/check_python_format.py --base "$ITERATION_BASE"
npm --prefix apps/ade-web run test
npm --prefix apps/ade-web run lint
npm --prefix apps/ade-web run build
uv run --locked python scripts/export_openapi.py --check
uv run --locked python scripts/generate_openapi_zh_manual.py
git diff --check
```

Use current-source broad pytest discovery excluding generated `*/outputs/*`
copies; do not mistake tests inside historical source archives for current tests.
The kit's October 13 checkpoint found pre-existing failures with the kit both
included and excluded. Refresh the comparison; do not rebind frozen historical
fingerprints or falsify evidence to turn the suite green. Retire tests of removed
contracts explicitly while preserving historical records and replay boundaries.
Generate/review OpenAPI artifacts when contracts change; report all material gaps.

After each completed increment, commit/push scoped changes and verify upstream.
Inspect all workflow triggers before publication; they must remain manual-only.
Do not run, rerun or schedule CI. Staging committed source to OCI need not depend
on hosted CI. Never force-push or publish credentials/private evidence.

Handoff includes milestone status, exact source/image/config/model bindings,
tests and missing gates, source/delivery/recall/request/commit evidence references,
observed usage/latency, unchanged-baseline proof and safe shutdown/recovery records.
Report Memory findings, Character review state and capture completeness separately.
A real request/reply capture is not a calibrated quality baseline. Preserve failed
attempts and unknowns; do not label required verification complete when absent.

## Pinned References

- [Bank ownership](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memory-banks.md).
- [Retain and operation semantics](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/retain.md).
- [Native facts and observations](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memories.md).
- [Assessment kit procedure and current limitations](../../workflows/evals/hindsight_integration/README.md).
- [Character review method](../architecture/capability-map/character-assessment.md#repeatable-review-method).
