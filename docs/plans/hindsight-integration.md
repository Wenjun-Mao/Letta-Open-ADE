# Hindsight Integration: Three-Stage Plan

Updated: 2026-10-12. Status: agreed planning scope; execution not authorized.
The user approved these three planning stages and an isolated OCI test placement,
not implementation, provider calls, installation or deployment. Work serially on
`main` in the primary checkout; scoped verified commits/pushes follow ADR 0048.
No new chat, worktree, Goal campaign or delegated writer is required.

## Outcome And Authority

Deliver one usable ADE conversation path backed by self-hosted Hindsight:
save original messages in ADE, retain them asynchronously, recall within the
same user/character relationship, inspect progress and memories, and retry a
failed lookup without resending the message. Hindsight handles ordinary memory
updates and corrections from conversation; manual removal is deferred.
Then demonstrate isolation, failure handling and recovery before a fresh start.

Authority: [PC-01 through PC-14](../product-contract.md), especially PC-02/03/04/10
for identity/continuity, PC-05/07/08/09/14 for responsibilities and persistence,
PC-06 for excluded semantic policy, PC-11/12 for Character, and PC-13 for hosting.
[ADR 0068](../adr/0068-hindsight-default-memory.md) records the settled decisions;
this plan selects no new product behavior by treating a technical assumption as
an agreement. Its proposed engineering choices become execution inputs only
after approval. Record material contract decisions in ADR 0068 as they settle.

The [assessment](../findings/hindsight-integration-assessment-2026-10-10.md) and
[revision-5 finding](../findings/hindsight-semantic-follow-up-2026-10-11.md) are
historical inputs. Do not reuse their cross-character profile sharing, whole-chat
reprocessing, expired activation clocks or qualification claims. Hindsight
adoption is settled; another vendor-selection experiment is not a prerequisite.

### Scope Boundaries

- Start with a new workspace/subject and new Hindsight state. Existing ADE/trial
  data and retained experiment evidence/private files remain untouched. The old
  test containers, network and DB/cache volumes were separately removed by
  [explicit user-approved cleanup](../findings/hindsight-semantic-follow-up-2026-10-11.md#subsequent-authorized-teardown);
  do not depend on them or restore archived test banks into the fresh scope.
- No historical import/backfill, dual writes, native fallback, compatibility
  adapters, second fact store/reviewer or generic Memory backend framework.
- Keep authored personas, immutable definition versions, bounded local dialogue,
  finite curated-tool execution and one ADE-owned product API/runtime.
- No new conversational no-save/consent policy, phrase-specific semantic rule,
  shared profile pool, permanent topic ban or guaranteed historical erasure.
- No manual memory-removal API/UI, removal-preservation acceptance gate or
  guaranteed conversational deletion. The separately proposed removal probe was
  cancelled before startup or provider use; its earlier permission is withdrawn.
- No broad Character/persona redesign, mandatory Hindsight reflect phase,
  general memory editor, old-source rebuild, external-tool feature or M2 winner
  claim. Targeted diagnosis is allowed; changed product intent needs review.
- No production/trial replacement or release-ledger promotion in this plan.
  Stage 3 prepares a separately reviewable fresh-start activation package.

## Source-Grounded Design

Initial baseline: `3491bb9`; final planning review rechecked the relevant runtime,
UI and lifecycle owners at `f0d84df`. No runtime changes or qualification follow
from that review. Paths below are relative to the repository.
Under `services/ade-api/src/ade_api/features/agent_runtime/`:

| Boundary | Current coupling | Planned treatment |
| --- | --- | --- |
| `run_service.py`, `persistence/conversations.py` | Accepted message and run persist together; native memory generation is captured. | Preserve source/idempotency integrity; add durable delivery intent in the same ADE transaction. |
| `turn_execution.py`, `turn_context_selection.py`, `turn_memory_snapshot.py` | Recall, Character sizing and execution depend on native reviewer/fact snapshots. | Compose Character context from scoped Hindsight recall and independent local dialogue, without reviewer-capacity dependencies. |
| `turn_result.py`, `worker_finalization.py`, `worker_events.py` | Success requires native review/embeddings and a memory/reply transaction. | Commit reply, run outcome and reply-delivery intent atomically within ADE; do not fabricate empty review results. |
| `executor.py`, `turn_compaction.py`, `compaction_executor.py` | Provider continuation and local dialogue compaction are already owned here. | Preserve those responsibilities; replace native fact-specific tool/context contracts. |
| `definition_service.py`, `deployments.py`, `contracts.py`, bootstrap/session modules | Definitions and requests require native reviewer/retriever roles. | Replace obsolete fields/bindings directly; preserve persona/version and Character model identity. |
| `memory_contracts.py`, `resource_service.py`, `agent_studio_api.py`, presenters | Inspection is subject-only and assumes native fact revisions/generation. | Require the subject/character relationship for memory, source and delivery-status reads; remove obsolete manual-removal contracts/controls, not existing stored data. |
| `worker.py` | One loop awaits each claimed turn before claiming another. | Give durable delivery independent scheduling/leases so a retain/poll wait cannot occupy the only reply worker or its conversation lease. |
| `agent_studio_reset.py`, `evaluation_sessions.py` | Reset/cleanup assumes one ADE SQL transaction owns all memory state. | Retire the SQL-only product reset from the new path; use exact paired disposable-stack cleanup for integration tests, not a new product erasure feature. |
| `database_boundary.py` | Workspace identity is hard-coded to the default. | Establish a fresh persisted/configured workspace identity consistently; no silent default fallback or unnecessary workspace-management UI. |

The web's `use-agent-studio.ts:146` refreshes chat, memories, runs and activity
through one `Promise.all`; a failed memory read currently aborts the whole refresh.
Split product-state loading from remote-memory inspection so Hindsight failure
cannot hide saved messages, run state or Retry. This is a PC-08/14 boundary fix,
not permission to generate a reply without the required recall.

Additional owners: `persistence/metadata.py` and `services/ade-api/migrations/`
for ADE schema; `platform/settings.py` and `integrations/` for service wiring;
`apps/ade-web/src/features/agent-studio/` for API types, run monitoring, memory
views and Retry; Model Router and its configuration for provider identity.
Follow the [development conventions](../development-conventions.md), including
splitting oversized touched modules instead of adding unrelated responsibilities.

### Proposed Integration Shape

- One Hindsight bank per `(workspace, subject, character root)`, resolved only
  by ADE from persisted ownership. Conversation and persona version are source
  metadata, not new banks. No model/browser-supplied arbitrary bank selection.
  Scope reads, writes and source inspection identically. Initialize and
  verify a new empty bank before treating an empty first recall as successful;
  a missing/deleted established bank is an error, not forgotten history.
  Conversation views derive the pair from their binding; standalone inspection
  explicitly selects both person and character, never all of a person's banks.
  Reject mismatched source/operation IDs and stale cross-selection responses.
- Use a small concrete Hindsight HTTP integration, not the evaluation CLI as a
  production backend. Reuse verified transport/serialization ideas, not its
  shared-profile projection or diagnostic-only runtime. Keep Hindsight access
  behind ADE; banks are not a substitute for authentication/authorization.
- Persist immutable delivery payload identity, source IDs, sequence and hash
  before dispatch. Use a durable ADE outbox with leases and bounded retries;
  preserve order within a relationship while allowing unrelated scopes to
  progress. Separate message acceptance, delivery acknowledgement and completed
  processing. No Hindsight network request belongs inside an ADE SQL transaction.
- Run delivery independently of reply execution with bounded concurrency; no
  microservice framework is needed. Exhausted/uncertain delivery blocks later
  deliveries only in that relationship until reconciliation, not other banks or
  otherwise healthy recall/replies. Expose oldest pending age and the blocked
  item with an operational recovery path; never skip/reorder it silently or
  require restarting a Character reply to retry delivery. Test backlog pressure
  across ADE workers, database pools, Hindsight and the shared model routes.
- Begin source-unit design with immutable per-message deliveries and bounded,
  attributed antecedent context for references such as "yes, that one". Verify
  source attribution, reference resolution, corrections and retry behavior before
  settling the exact native retain mode. Avoid redundant whole-chat processing;
  no removal-specific context barrier or native patch is required by this scope.
  Preserve original message/utterance times on retry; delivery, extraction and
  consolidation timestamps must not silently become dates when events happened.
- Leave extraction, factual updates/corrections and consolidation to Hindsight.
  ADE supplies attributed sources and enforces delivery/ownership integrity, not
  semantic update commands, a parallel reviewer or keyword lifecycle rules.
- Perform normal recall for each reply attempt without waiting for retention.
  Combine bound persona, product instructions, current input, bounded local
  dialogue and relevant memories. Preserve attribution, dates and uncertainty;
  retrieved text is information, not privileged instructions. Bound the complete
  serialized request at every model/tool continuation, not just recall tokens.
- Preserve discretionary `search_memory` through the same scoped Hindsight path;
  do not force it with keywords. Any required lookup failure, including a tool
  lookup, pauses the reply rather than becoming an empty result. No uncommitted
  candidate reply is stored or retained after that failure.
- Retry resumes the saved user input through a new, fenced attempt and fresh
  recall. Define a persistent retryable state, terminal/active distinctions,
  lease release/reacquisition, cancellation, concurrent Retry and stale-worker
  behavior. Reject a stale retry after incompatible conversation changes rather
  than silently moving an old input behind newer messages. Exact API/state names
  are engineering choices, not a reason to append the input again.
- Interface distinguishes queued, processing, completed, failed and uncertain
  delivery states, and recall failure from successful empty recall. Display
  source-backed memories without pretending native fact revisions still exist.
  Label derived observations and link supporting facts where available. Inspection
  is read-only in this scope; do not imply that a user can delete/edit a memory
  or that an ordinary correction erases the original conversation.

## Stage 1: Connect The Complete Flow

**Outcome:** a fresh conversation works end to end with durable background
retention, scoped recall and the actual Agent Studio UI.

1. Establish the pinned contract and fresh schema. Start from Hindsight 0.10.3
   source `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`, already used in the campaigns,
   not a floating latest image. Bind image/source/config identities. Design bank
   ownership, outbox state, reply Retry and schema/API changes before wiring the
   full runtime. Use Alembic on a new isolated ADE database; do not run migrations
   against retained databases or keep unused native code executable for them.
   Before first retention, version the bank's speaker/character identity, Memory
   missions and model/embedding bindings without the old shared-profile classifier.
   Select native consolidation scheduling, including recovery after downtime;
   do not carry over the experiment's manual-only maintenance by default.
2. Resolve the source-unit and retry feasibility gate before dependent rollout.
   Inspect pinned source/API behavior, write fake-transport/SQL tests, then run
   focused synthetic checks under integration execution approval, not the
   cancelled removal-probe permission. Prove reference resolution,
   accepted-user-only retention after a failed reply, committed-reply attribution,
   lost acknowledgement, unchanged payload replay, partial failure and ordinary
   corrections across deliveries. Do not manually repair facts to make a
   correction test pass; capture native retention/consolidation and recall.
3. Implement source delivery and the replacement runtime contract together.
   Bind a caller-generated async operation ID to its immutable payload; poll or
   reconcile that operation after a timeout instead of minting a fresh ID. A
   failed/partially completed operation needs a proven recovery rule before
   retry; same-ID deduplication does not itself repair failed work. Fence duplicate
   workers and stale completion. Define delivery failure visibility and recovery.
4. Replace native review/fact/embedding obligations in admission, definitions,
   context, result and finalization. Keep message integrity, conversation-version
   checks, cancellation, lease fencing and summary provenance. Add committed
   reply delivery in the same ADE transaction as reply/run success. Remove
   superseded code/contracts and update maintained callers, not compatibility
   wrappers. Preserve historical evidence; version historical fixtures explicitly.
   Include inspection, reset and evaluation-cleanup entrypoints in that audit;
   no reachable route may erase ADE mappings while Hindsight work is outstanding.
5. Wire Hindsight recall, Character composition, concrete scoped memory search,
   API status/readback/Retry and Agent Studio. Update OpenAPI, feature READMEs and
   affected tests. Create the integration workflow at
   `workflows/evals/hindsight_integration/` with its fixtures, config, runner,
   README and ignored outputs together; product code must not import the lab.

**Source-unit gate:** demonstrate all required invariants with captured source,
native operation state, retained facts/observations and subsequent recall.
Stable document IDs, append mode or prompt wording alone are insufficient.
If pinned Hindsight cannot satisfy the contract, preserve the counterexample and
propose a bounded native change or explicit tradeoff before dependent work;
do not add a shadow semantic engine or reopen vendor selection. This gate tests
delivery integrity and normal memory behavior, not deferred manual removal.

**Stage exit:** offline tests and real PostgreSQL readback pass; one authorized
Chinese UI journey saves user/reply messages, shows retention progress, then
recalls the learned fact in a second same-character conversation. Generation
does not wait for deliberately delayed retention. No native reviewer/fact write
or fallback executes. Partial Stage 1 success does not qualify later stages.

## Stage 2: Verify Boundaries And Failures

**Outcome:** observable tests show that the new path keeps the agreed promises,
not merely that its HTTP requests succeed. Use synthetic fixtures with explicit
expected distinctions, not altered historical evidence or answer-specific rules.

| Case | Required evidence / acceptance |
| --- | --- |
| Identity and continuity (PC-02/03/04/10) | Same relationship across new chats, ordinary persona versions and archived chats; different character, subject and workspace cannot read/write/inspect the first relationship's facts, sources or derived observations. Include forged source/operation IDs, standalone inspection, rapid UI character switching and missing metadata. |
| Source attribution (PC-03/11/14) | User message retained after failed generation; only committed replies retained; jokes/hypotheticals/solo stories are not asserted as shared events. Reference-only replies resolve against attributed context rather than inventing their subject or speaker. |
| Delivery crashes (PC-05/08/14) | Crash before dispatch, after remote acceptance, before ADE acknowledgement, during polling and after worker lease loss. Restart reconciles the original delivery without loss, duplicate extraction or out-of-order overwrite. Partial extraction remains visible, not completed success. |
| Background progress (PC-09/14) | Sustained synthetic dialogue and one exhausted/uncertain delivery do not block unrelated delivery or healthy reply execution. Observe queue age, blocked scope and reply/recall latency with retention and consolidation active; include compaction pressure, not just one delayed fake. Recovery neither drops a message nor reorders a correction. |
| Recall and Retry (PC-01/14) | Timeout, authentication failure, malformed response and lost service pause generation; successful empty recall works; missing bank is not empty. Concurrent/repeated Retry, reload and stale workers produce one accepted input and at most one committed reply. Pending retention alone does not pause. |
| Natural updates and corrections (PC-01/05/14) | Conversational misspeak correction differs from a genuine later change. Inspect Hindsight facts, observations and recall after retention/consolidation, including delayed/retried delivery; no manual fact repair or ADE semantic override. Preserve original chat and source/time attribution. |
| Context and lifecycle (PC-04/09/12) | Oversized memories, long Chinese dialogue, compaction, tool continuations, cancellation and version races preserve bounded requests, message ordering and source/summary integrity. No silent truncation of mandatory input. |
| Interface truth (PC-07/14) | Real browser covers new conversation, status refresh, failed lookup/Retry, archived-chat continuity and read-only relationship inspection. During a Hindsight outage, reload still shows ADE chat, saved input and run/Retry state; remote-memory failure is not an empty-memory display. No manual removal controls, one-store reset or guaranteed deletion claims. No queued receipt is called completed memory. |
| Model/retention quality (PC-11/12) | Capture actual delivered memories and serialized Character input separately from the reply; assess grounding, judgment and character fidelity separately. Report usage/latency by phase without spending gates or invented billing totals. |

Reproduce representative revision-5 risks under the new character-local scope:
misspeak correction versus genuine preference change, unknown detail versus
invented recollection, hypothetical versus event, solo versus shared history,
and consolidation changing factual meaning. Inspect raw facts and derived
observations before blaming Character. Exercise the Stage-1 versioned Memory
mission and consolidation schedule, including backlog/failure status and recovery
without a manual consolidation command. Do not silently disable a capability
or change inputs after a failure just to claim acceptance.

**Stage exit:** all mechanical/isolation tests pass, real API/UI journeys
are recorded, and remaining semantic defects have source/request/reply evidence
and a named owner. Known semantic failures require a durable fix or explicit
user acceptance of a bounded limitation before fresh-start readiness; a good
recall result or historical campaign pass cannot certify Character quality.
No rerolls of unchanged failures solely to fill time.

## Stage 3: Recovery And Fresh-Start Readiness

**Outcome:** a source-bound package that can start fresh safely and recover both
stores. Readiness is not permission to replace existing services.

1. Back up ADE product state and Hindsight state as a coordinated, documented
   recovery point. Quiesce new writes and drain or explicitly record in-flight
   work on the isolated stack; include outbox/operation identities, bank mapping,
   native learned-memory state, source/config hashes and schema versions. Protect
   credentials separately. A dump with a readable table of contents is not restore proof.
2. Test orderly restart and controlled crash recovery of the integration stack.
   Verify completed and pending deliveries, retryable replies, source identity,
   corrected facts/observations and same-character continuity through public APIs.
   Disable provider dispatch until restored identities and pending operations
   are reconciled; never fall back to bulk replay of original conversations.
3. Restore into separately owned disposable databases/volumes, start the actual
   restored ADE and Hindsight APIs, and repeat readback plus a new turn. Prevent
   restored workers from contacting original banks or running concurrently as
   a second owner. Compare logical/schema state and user-visible invariants,
   not volatile timestamps. Preserve failed evidence; remove only explicitly
   registered disposable resources after proof, never retained volumes.
4. Prepare a fresh-start manifest/runbook: exact source/images, dependency/model
   identities, schema/config, new workspace/subject/banks, ports/auth, health,
   backup/restore, shutdown and rollback. Practice opening an empty workspace
   and using the three-stage flows with disposable synthetic data. Any eventual
   real-use workspace must start empty, not inherit qualification fixtures.
5. Review acceptance and limitations, commit/push scoped work, and publish a
   concise finding with evidence references and missing gates. Stop/drain the
   isolated services after checks unless continued operation is explicitly
   authorized. Preserve data and receipts. Do not edit a release ledger or
   route existing users to the candidate as a side effect of completing tests.

**Rollback:** stop only the new stack, preserve both databases and evidence,
and leave existing services untouched. Within the new stack, roll back only a
proven image/schema/paired-backup combination. Never point the old native Memory
runtime at new Hindsight workspace data. Where reversal is unproven, keep the
candidate stopped and report the recovery requirement rather than guess.

**Stage exit:** fresh source-specific restart, crash and dual-store restore
evidence passes, baseline services/data remain unchanged, and the activation
package is reviewable. Revision-4 logical restore and revision-5 dumps are
historical only. No automatic production cutover is included.

## Environment, Models And Execution Permissions

The user selected a **new isolated OCI stack** for live integration checks.
The user completed the 4-core/24-GB-class upgrade. Read-only `lscpu`, `free -b`
and `df -B1 /mnt/projects` checks on 2026-10-12 confirmed four ARM64 cores,
23.4 GiB total RAM, 21.8 GiB available RAM and 99.4 GiB available disk. This
removes the earlier two-core/about-12-GiB planning constraint, not the need to
measure the full ADE API/worker/web + Hindsight stack at startup and under load.

Use a new Compose project, isolated networks/credentials, fresh ADE and Hindsight
databases/volumes, and unused loopback ports reached by a private tunnel. Do not
reuse the root Compose data binds or closed probe project. Prefer separately
owned database services initially, preserving each pinned extension/version
requirement. Confirm the whole allocation before startup, including browser-test
and serial build peaks. Re-inventory before activation and reserve at least
4 GiB RAM and one core for the host/baseline services in the proposed allocation;
measure build pressure separately from runtime container limits. No fit means
stop and surface the placement/resource choice, not evict baseline services.
Browser interaction can run on the Mac against the OCI stack without a local
Hindsight server. Provider/model traffic still originates from the authorized
isolated runtime.
Baseline checks inspect service identity/health and storage attachments, not
existing conversation contents or database exports. Monitor new-stack headroom,
health and baseline drift; stop owned work on unsafe resource pressure or drift.

Proposed starting model routes, not new globally selected defaults:

| Role | Starting configuration and proof needed |
| --- | --- |
| Character | Existing `deepseek::deepseek-flash` profile through Model Router; retain configured thinking behavior and verify the actual served identity/request. |
| Hindsight extraction/consolidation | Same DeepSeek route, explicit Memory-specific non-thinking/JSON settings as qualified historically; no duplicate ADE reviewer. Requalify serialization and errors on the new path. |
| Embeddings | Existing Spark `Qwen/Qwen3-Embedding-0.6B` route through Model Router; verify dimensions, input limit, query prefix and fingerprint without restarting/changing Spark. |
| Reranking | Pinned CPU BGE-v2-m3 configuration from the experiment; prove Chinese full-reranking health and resource fit, not HTTP 200 alone. |

Record actual model/image/config fingerprints at execution. Account for startup
verification calls and upstream retry behavior as well as ordinary requests.
Do not blindly copy the entire old probe config, shared-profile mission, auth
material, clock or supervision protocol. Keep credentials out of tracked files,
URLs, logs and artifacts; safe diagnostic captures exclude private reasoning.

### Authorization At Handoff

Currently authorized: read-only planning, documentation changes, checks and
scoped commit/push; OCI is the selected future test location, not activated.
The narrow removal-preservation probe was cancelled before any new resource or
provider request was created. Do not reuse its revoked permission for other tests.
Explicit implementation/activation approval must cover the following scope:

- Source/API/schema/UI edits on `main`, removing replaced contracts; offline
  tests and disposable databases; normal verified commits/pushes.
- Staging clean committed source to OCI, public pinned dependency/image/model
  downloads, isolated builds/migrations/service starts, synthetic conversations,
  controlled stops/crashes/restarts and disposable restore/cleanup.
- Existing DeepSeek provider-account use and Spark embedding requests through
  the listed routes, including startup, retention, consolidation and recovery
  tests. No additional provider/account, global model change or historic export.
- New activation-specific service/process identities, a finite host-side safety
  expiry, resource monitoring and owned cleanup that survive client disconnect.
  Choose the operational time window before activation, with shutdown margin;
  do not inherit or extend an old campaign clock or introduce spending gates.
- No existing ADE/trial/experiment service, volume or schema change; no public
  exposure, production cutover, release promotion or perpetual monitor.

Approval of the plan alone is not execution approval. After the above execution
scope is explicitly granted, continue its covered stages, routine diagnosis,
retests and planned rollback without repeated milestone permission requests.
Escalate only for missing authority, a material scope/risk change, an unsatisfied
feasibility gate, baseline drift or an explicitly required limitation waiver.
Prefer serial work; an independent review may later check scope/failure/recovery
coverage without creating parallel writers or reopening settled product choices.

## Verification And Handoff

Start with changed modules' tests and explicit real-PostgreSQL integration tests;
skipped database tests are not a pass. Then run proportional runtime, router,
frontend and OpenAPI checks using the repository's established tools:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime -q
uv run --locked python -m pytest services/model-router/tests -q
npm --prefix apps/ade-web run test
uv run --locked python scripts/export_openapi.py
uv run --locked python scripts/generate_openapi_zh_manual.py
make check
git diff --check
```

The implementation must supply exact workflow-local commands for scoped SQL,
real Hindsight, browser, fault and restore checks. Bind live results to committed
source and actual images/config/models; offline fakes cannot replace those gates.
Known unrelated baseline failures must be diagnosed/reported, not silently
excluded or fixed by rewriting frozen evidence. Update feature READMEs,
architecture/runtime status and OpenAPI when implementation changes their truth.

Final handoff includes stage-by-stage pass/fail/pending, invariant coverage,
source/image/config hashes, safe evidence locations, observed requests/usage,
remaining semantic limitations, unchanged-baseline proof, paired restore proof
and a fresh-start runbook. Keep two conclusions separate: mechanical integration
works versus conversational quality is acceptable. Initial good recall does not
settle known correction, invented-detail or consolidation defects. Record any
accepted limitation explicitly instead of quietly relabeling it out of scope.
Do not label a stage complete while its required
verification remains missing. This planning revision does not execute runtime,
database, browser or live gates.

## Pinned API References

- [Banks](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memory-banks.md): bank isolation and missing-bank behavior; ADE still owns relationship authorization.
- [Retain](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/retain.md): contextual ingestion, replacement/append and async operation IDs; native semantics still require source/delivery verification.
- [Memory curation](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memories.md): facts and derived observations; manual invalidation is a native capability, not a first-integration requirement.
