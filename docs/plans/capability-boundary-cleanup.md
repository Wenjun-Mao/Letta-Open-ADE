# ADE Capability Boundary Cleanup

Status: Implementation in progress, revision 2, 2026-10-08; approved by the user.
Implementation and the described disposable verification resources are authorized.
This follows the completed
[code-boundary audit](../architecture/capability-map/code-boundary-audit.md), rather
than reopening its discovery work or replacing its historical evidence.
The [consultation assessment](../findings/capability-boundary-consultation/assessment.md)
records source-checked refinements from two preserved reports, not implementation
approval. The user's subsequent implementation instruction authorizes this plan.
The sequence remains A1 -> A3 -> A2 -> A4.

Source baseline: primary `main` at
`49b98ede4d47885d3f89a6e0b600e246e2e7eb1e`, clean at planning entry.
Relevant source, callers, fixtures and commands were rechecked for this plan;
runtime tests were not rerun. Refresh this baseline when implementation starts.
Review-integration baseline: `74e993a9b4d50cc367778392aab71937f5b541ff`, also clean;
the intervening changes were documentation-only.
Implementation baseline: clean primary `main` at
`cf9b5bae49414f164cf5b425b3a62740d1abe2ea`. Python/web dependencies and the
cached pgvector PostgreSQL image are available. One writer uses this checkout.

## Outcome And Approach

Make responsibilities and existing internal contracts easier to locate, test
and change without altering product behavior. Keep future replacement of both
Character and Memory possible without pretending this cleanup makes them plug-ins.

Choose **audit-driven cleanup with explicit ownership**. A directory rewrite
matching L1/L2/L3 would add import churn without separating actual contracts.
Designing a generic replacement protocol first would freeze untested assumptions
about Character control, Memory authority and remote transactions. Neither is
needed for the demonstrated problems.

Hindsight is a possible future Memory implementation. `persona_generators` is a
complementary source of persona-generation methods, expressive-behavior techniques
and evaluation lessons, not a promised Character replacement. No vendor API,
shared personality schema or cross-repository dependency is adopted here.

## Authority And Exclusions

Follow [development conventions](../development-conventions.md) and
[ADR 0061](../adr/0061-capability-responsibility-map.md): L1/L2/L3 is responsibility
containment, not directory layout, execution order, deployment or model phases.
The [product contract](../product-contract.md) remains unchanged:

- PC-02/03/04/10/11: preserve subject/character scope, immutable bindings, archive
  eligibility, and authored versus relationship-specific history.
- PC-05/07: preserve semantic review versus structural validation, removal
  semantics, source/version checks and the complete atomic success transaction.
- PC-08/09: retain one ADE API/runtime, PostgreSQL authority, Model Router access,
  retry/deadline/cancellation ownership and finite tool loops.
- PC-01/06/12: no phrase forcing or removed privacy rules; no new Character
  planner, style-rewriting phase or mandatory trait enactment. Grounding,
  conversational judgment and fidelity remain assessment lenses.

Exclude services/repository extraction, Hindsight integration, changes to the
other project, new domain interfaces/DTOs, plugin registries, prompt/schema/model
changes, retrieval/review policy changes, new features or evaluation campaigns.
No public HTTP/UI contract or database schema change is intended. ADR 0060 and
experimental history policies keep their current status. No production deployment,
live model call, release qualification or new worktree follows from this plan.

## Boundary Sketch: Current Contracts, Not A Future SDK

Aliases used below: `runtime:` = `services/ade-api/src/ade_api/features/agent_runtime/`;
`tests:` = `services/ade-api/tests/agent_runtime/`;
`web:` = `apps/ade-web/src/features/agent-studio/`;
`map:` = `docs/architecture/capability-map/`.
All are existing paths unless explicitly marked proposed.

| Boundary | Existing exchange and ownership | Cleanup constraint / later question |
| --- | --- | --- |
| Interface -> runtime | `web:api.ts` sends turn requests; runtime returns run receipts; events and persisted readback supply outcomes. | UI does not import a Memory/Character implementation or treat a receipt/candidate as a committed reply. Keep the same endpoints and hook surface. |
| Persona Definition -> bound execution | Prompt Center authors active content; `runtime:definition_service.py` creates immutable snapshots used by the conversation. | Preserve authored intent versus contextual application. A snapshot also contains runtime configuration; it is not a portable persona schema. |
| Memory -> Character, composed by runtime | Request assembly combines independently bound authored characterization, ADE-wide requirements and scoped Memory evidence using actual consumer serialization/capacity rules; memory-search results return through the curated tool loop. | Memory evidence delivery does not own persona authoring or the Character implementation. Preserve source qualifications; do not force summary-only evidence or invent a portable domain API. |
| Character -> runtime | `runtime:executor.py` returns `ExecutorResult` after shared generation/tool execution. | Preserve joint interpretation, choice and expression. A future controller might supply guidance or own generation; this plan does not choose between them or assign future tool-loop ownership. |
| Runtime -> Memory review | `runtime:turn_execution.py` supplies policy-specific inputs to one reviewer; review preparation returns validated proposed operations. | Typed review has no candidate reply; natural review receives it as reference, not factual authority. No second reviewer or new character-state admission policy. |
| Execution -> finalization | `runtime:turn_result.py` owns `AttemptResult`, aggregating concrete generation, context, review, embedding and compaction results. | A1 makes imports explicit, not implementation-independent. Keep this internal coordination aggregate; do not promote it to a cross-domain or network protocol. |
| Finalization -> persistence | Runtime owns the connection and full fenced success transaction; domain helpers use that connection. | Preserve one atomic outcome. A remote Memory store would require an explicit consistency/migration decision, not an adapter claimed to be equivalent. |
| Supporting model access | Conversation, compaction, review and embeddings use traced Model Router transport. Compaction currently uses the conversation deployment and provider adapter. | Separate compaction protocol ownership without a new model role, independent configuration, extra dispatches or a parallel transport/client stack. |

Future replaceability means avoiding new hidden dependencies during this cleanup,
not removing every current coupling. Exact request-capacity admission, concrete
result types and shared transaction ownership remain deliberate constraints.
External Tools stays deferred; tool-invoked memory search is still Memory.

## Ordered Delivery

### 0. Establish The Implementation Baseline

Record HEAD, working-tree changes and available test dependencies. Recheck imports
and callers of the selected seams, including maintained workflows. Run the focused
baseline checks below before edits; distinguish existing failures from regressions.
Do not install dependencies or borrow a running trial/production database silently.
Use one writer, serially on retained `main`; no separate task is needed.

Acceptance: a reproducible baseline, a scoped change list and usable verification
resources. Missing SQL/browser resources leave the dependent verification pending,
not waived. Earlier independent cleanups may still proceed after approval.

### 1. Make The Execution Result Owner Explicit (A1)

Problem: four worker collaborators import `AttemptResult` from `turn_execution.py`
although `turn_result.py` defines it. This is incidental re-export coupling, not a
diagnosed runtime cycle or failure; fix the consumer imports at their actual owner.

Change `runtime:worker.py`, `worker_control.py`, `worker_events.py` and
`worker_finalization.py` to import the result directly from `turn_result.py`.
Keep `TurnExecution` imports where used. Check all repository consumers; do not
add compatibility aliases, move the dataclass, change its fields or claim its
transitive implementation dependencies have disappeared.

Acceptance: no maintained consumer imports `AttemptResult` via execution; import
and app-composition checks pass; worker/finalization/event behavior is unchanged.
Add a focused import-owner regression assertion to the existing runtime tests,
not a general architectural-lint framework. Check the named consumer imports:
importing the defining module already works, and execution may still expose the
type because it uses it. Do not assert that attribute is absent from execution.
Keep this a small independent commit.

### 2. Correct The Responsibility Descriptions (A3)

Problem: aggregate descriptions obscure mutable authoring versus immutable
binding, and reviewer/context inputs that differ by bound policy. The code already
makes these distinctions; fix documentation, not behavior to fit the diagram.

Edit `map:inventory.json` as the canonical source: clarify CHAR-01/02, MEM-04/06
and the retention-flow note/edge that currently implies every reviewer receives a
candidate reply. Identify that edge as natural-policy-only. Retain IDs, names,
ownership, statuses and topology. Cross-link the audit's policy-specific table.
Update the corresponding journey descriptions only where the same ambiguity
appears; preserve the existing correct distinctions and illustrative examples.
Also correct the retention step's wording to put eligible compaction before
generation, and keep request composition distinct from Memory evidence ownership.

Regenerate `map:inventory.md`, `ade-capability-map.html`, `ade-capability-map.svg`
and any affected journey output from their authored sources, never by editing
generated output. Update assertions to protect the clarified meaning. Keep the
audit's original source baseline/findings historical, with a follow-up link rather
than silently rewriting them as a new audit.

Acceptance: generated and source views agree; typed/natural/history differences
are discoverable; no policy is promoted or model phase invented. Check the actual
built HTML in a browser if visible labels change, not `player-template.html`.

### 3. Separate Compaction Dispatch From Conversation Generation (A2)

Problem: `runtime:executor.py` combines the conversation/tool protocol with a
different compaction prompt, response schema, parser and provenance protocol.
`TurnExecution` already creates separately traced instances, and
`runtime:turn_compaction.py` calls only `compact`. This is a supported internal
seam, not a reason to introduce another service or model call.

Extract `ConversationExecutor.compact` into a focused compaction executor
(`runtime:compaction_executor.py`, proposed). Keep planning, hashes, parsing and
`ModelCompaction` in `runtime:compaction.py`; keep eligibility/deadline policy in
`turn_compaction.py`. Update construction in `turn_execution.py` and the direct
caller/tests. Import `ModelCompaction` from its defining module, not through an
executor. Remove the old method after migrating maintained callers.

The two protocols currently share `_first_choice` and `_merge_usage`. If both
still need them, give only those response-shape/usage mechanics one narrow local
home (`runtime:model_response.py`, proposed) and test their existing semantics.
Do not copy them, make compaction import the conversation implementation, create a
base executor/plugin framework, or move unrelated tools/request builders. Keep
`initial_conversation_request` shared by admission and execution as today.
Preserve copied response message fields required for tool continuation; the shared
helper must not become a destructive normalizer or a dispatch-policy owner.

Acceptance: generation/tool ownership no longer includes the compaction protocol;
each provider-adapter branch preserves its own pre-cleanup request for fixed inputs,
not an identical request across the two intentionally different branches.
Preserve prompt/input/policy/content hashes, request IDs, usage, errors and existing
observer behavior (do not normalize different exception semantics as cleanup).
Preserve the conversation deployment/adapter, tracing stage, remaining timeout,
A/A0 withholding, B disabling, pre-generation timing and success-only persistence.
Use two fixed-input adapter fixtures with independently specified expected payloads
and provenance, not hashes recomputed solely through production helpers. Add small
parameterized checks for malformed envelopes/summary output, token floor/caps,
usage filtering and observer exceptions. Do not multiply every case across policies.

Extend the existing synthetic real-worker PostgreSQL fixture with one summary-bearing
late transaction failure, after the real `create_compaction` has staged writes but
before success commits. Confirm the injection point was reached; disable retries
for this case. On fresh readback, require no new assistant, summary/source bundle,
memory/index changes, conversation-version advance or success-event bundle from
the failed attempt. Preserve prior state and the separately accepted user message;
failure/attempt metadata may still be recorded. A pre-finalizer rejection alone
cannot prove rollback of staged writes. Keep the existing success/fencing checks;
do not add a second mandatory rejection campaign or a new production fault hook.
Use the packet test's existing real construction/trace assertions instead of a
duplicate elaborate mocked construction harness.

### 4. Give Run Monitoring One Focused UI Owner (A4)

Problem: `web:use-agent-studio.ts` combines workspace/draft/evidence coordination
with stream/poll lifecycle. No stale-update bug was established. Extract one
cohesive monitor, not a hook for every diagram box or the whole controller at once.

Use a local run-monitor hook/collaborator (`web:use-run-monitor.ts`, proposed) for
stream/poll handles, active monitor identity, terminal latch/deduplication, guarded
completion sequencing and disposal. Keep the single displayed run/event state in
the controller: acceptance, cancellation and selected refresh legitimately update
it alongside guarded monitor notifications. Do not mirror that state in the hook.

Only the controller advances selection/read epochs. Keep their invalidation scopes
distinct: same-conversation read refresh does not end the monitoring lifetime;
A -> B -> A does not revive callbacks from the first visit. Supply an ownership
guard and selected-readback callback, not another epoch system. Both monitor and
controller callbacks must recheck that guard before consequential mutations after
their own awaits; checking only after an awaited callback returns is too late.
The completion callback must not independently own the terminal latch or disposal.
Keep memory-action interpretation in its existing owner: a `null` selected read
is not confirmation of persistence, and confirmation still requires matching
committed-event and refreshed-revision evidence.

Leave workspace loading, draft/resource actions, pagination, evidence navigation,
send/cancel policy and persona binding in their current owners. Preserve the public
`useAgentStudio` return shape, view and API/event-stream contracts. Exact internal
hook signatures are engineering choices; avoid a generic event bus or callbacks
that merely expose every controller setter. If the seam requires splitting the
same lifecycle authority between two owners, record the failed feasibility check
and retain the controller instead of broadening to a state-management rewrite.

Acceptance: selection A -> B rejects late acceptance, stream, poll and terminal
callbacks; same-conversation evidence navigation keeps monitoring; revisiting a
running conversation resumes it. Preserve stable lifecycle callbacks, including
`stopMonitoring`, so ordinary rerenders do not restart monitoring or retrigger
the controller's selection-reset effect. Terminal refresh is deduplicated; a
terminal-fetch failure clears its latch for a later retry as today. Stream failure
retains polling, obsolete reads cannot override new state, and unmount/selection
change closes owned resources. Preserve drafts, edits, cancellation and memory
outcomes. Use deferred responses/fake timers for races including A -> B -> A and
changes during terminal completion; keep tests through `useAgentStudio`, not only
the extracted hook. One synthetic browser walk checks wiring, not every race.
Do not silently strengthen scheduling or swallowed-read-error semantics; separate
an exposed pre-existing defect from an extraction regression before expanding scope.

### 5. Reconcile And Close The Cleanup

Refresh affected source homes with each implementation slice in the canonical
inventory and runtime README; final reconciliation catches omissions rather than
deferring known stale references. Update `docs/codebase-map.md` only where navigation
changes. Link implemented dispositions from the historical audit, preserving its
original evidence/counts.
Record actual changes, checks, skips and unresolved replacement questions in this
plan's execution record; do not create another capability registry or report suite.

K1 stays intact: retain `RunService`, `TurnExecution`, acceptance, atomic session
provisioning, finalization and caller-owned repositories. The other large files
(`agent_studio_sessions.py`, `persistence/memory.py`, `persistence/metadata.py`)
do not become cleanup tasks because of their size alone. No folder regrouping.

Acceptance: every A1-A4 recommendation has an implemented or explicitly deferred
disposition and evidence; K1 invariants hold; no unexplained public schema, prompt,
policy or generated-asset changes. Code is clearer, not certified replaceable.
Leave domain replacement as the next discussion, with concrete remaining coupling
and possible profile/scenario/evaluation exchange rather than a speculative SDK.

## Verification Matrix

Use existing locked environments: `uv run --locked --offline --no-sync python -m
pytest ... -q -p no:cacheprovider` with a temporary UV cache and bytecode disabled.
Unset `ADE_TEST_DATABASE_URL` for offline checks; synthetic transports replace
providers. Inspect any newly selected suite before running it. Use repository npm
scripts with installed dependencies; do not silently sync/install or run live probes.

| Slice | Existing checks and required additions |
| --- | --- |
| A1 | Import/app composition and `tests:test_worker.py`, `test_worker_events.py`, `test_worker_finalization.py`, `test_native_app.py`; targeted consumer-import assertion. Defer broader unchanged runtime checks to the combined run. |
| A2 offline | `tests:test_compaction.py`, `test_executor.py`, `test_memory_policy_binding.py`, `test_natural_context.py`, `test_natural_evaluation_capacity.py`, `test_history_admission.py`, plus worker/finalization checks. Add exact adapter request/provenance and small error/caller cases before extraction. |
| A2 SQL | `tests:persistence/test_postgres_natural_compaction_packets.py` plus the one late-transaction rollback case above and existing `test_postgres_natural_worker_fencing.py`. `test_postgres_lock_order.py` is a useful available-environment regression, not a new extraction-specific gate or a substitute for the rollback case. |
| A4 | `npm --prefix apps/ade-web run test -- src/features/agent-studio`, then web lint/build. Deterministic tests cover late poll/completion, duplicate terminal, fetch failure/retry, disposal and stable rerenders. One synthetic browser smoke covers actual wiring, selection, evidence navigation and terminal readback; do not manually repeat every race. |
| A3 / map updates | `map:render.py --check`, `test_render.py`, `test_map.cjs`. Only if journey sources/generators or their output are affected: journey `review.py`, `build.py --check`, `test_review.py`, `test_build.py`, `test_example.py`, `test_player.cjs`, `test_guide.cjs`, `test_examples.cjs`. Regenerate changed views; inspect changed visible labels in built HTML, sharing the browser session where practical. |
| Final | Relevant focused checks together plus `tests:test_run_service.py` and `test_retry.py`, changed Python files through Ruff/import checks, handwritten web suite/lint/build if changed, source/link/status consistency, scoped diff and `git diff --check`. Avoid duplicate broad runs without an intervening relevant change. |

Follow the existing [disposable PostgreSQL recipe](../../workflows/evals/character_memory_dev/README.md)
with a uniquely owned loopback database/container, existing migrations and no
production credentials/data. Worker tests require an idle database; suites that
leave pending runs must not share its claim pool. Provision separate fresh test
databases as needed. Do not reuse historical example names or active trial stores.
Browser verification uses a task-owned loopback preview and synthetic/mocked API
responses, never the deployed app or a live-model-backed conversation.

A skipped SQL/browser check is not a pass. If resources are unavailable, retain
independently verified slices and report the dependent slice as pending; do not
claim full cleanup completion. Mechanics do not establish personality quality,
retrieval sufficiency, production equivalence or new release qualification.

## Permissions, Publication And Rollback

| Action | Authority |
| --- | --- |
| Save/review this plan, README link, verified documentation commit and normal push | Granted for this planning iteration under current repository conventions. |
| Implement slices 0-5 and focused regression tests | Granted by the user's implementation instruction, 2026-10-08; serial covered work needs no renewed per-slice approval. |
| Disposable loopback PostgreSQL, existing migrations within that database, synthetic local preview/browser checks, cleanup of those owned resources | Included in the proposed implementation scope. Use installed/cached tooling only; no existing service restart, borrowed database or production migration. |
| Commits and normal pushes of completed verified implementation slices | Pre-approved publication policy and authorized implementation scope. |
| Dependency installation/download, new task/worktree, remote services/accounts, live provider calls, deployment or changes outside this scope | Not authorized. Surface only an actual uncovered need or material design change. |

Commit bounded verified slices independently so a source regression can be
reverted without undoing unrelated work. Roll back only this iteration's scoped
changes/commits; no force push, hard reset or destruction of user data. No database
schema migration or data conversion is delivered. Stop/remove only test resources
created and recorded by this work. Re-run the relevant checks after a rollback.

Existing ADRs govern this behavior-preserving cleanup. Record a new durable
contract/authority change only if explicitly selected later; do not introduce one
under a refactor label. No new replacement architecture ADR is adopted by planning.

## Execution Record

The initial planning and consultation iterations performed documentation/source
checks only. Their historical checks are retained below.
Initial planning checks resolved 19 local Markdown links, 16 existing aliased source
references and 26 verification-script/test references across this plan and its
README entry; the three proposed module paths are explicitly distinguished.
Revision 2 incorporates the linked consultation assessment: explicit UI state and
lifecycle ownership, runtime composition wording, exact per-adapter characterization,
one compaction-bearing rollback check, and change-proportional verification. These
are revised proposed obligations, not tests implemented or results reproduced.

Implementation baseline checks: 87 runtime tests, 35 Agent Studio tests and
18 map tests passed using installed dependencies, offline Python execution and
synthetic fixtures. FastAPI emitted its existing TestClient deprecation warning.
A1 is complete: the four consumers import directly from `turn_result.py`, the
runtime README/inventory identify that owner, and four import-owner assertions
protect the seam. Verification: 25 worker/event/finalization/app tests, 18 map
tests and three connected-map tests passed; changed Python files passed Ruff.
A3, A2 and A4 remain pending.
