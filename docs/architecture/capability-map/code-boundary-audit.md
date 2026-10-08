# ADE Capability-To-Code Boundary Audit

Status: Source-reading audit completed, 2026-10-08; awaiting user review. Recommendations are for
review, not approval to refactor, change product behavior, or deploy.
Executed under the [approved audit plan](../../plans/capability-code-boundary-audit.md).
Source baseline: `0ec2088ece4bc3b7f539bd56e457a5b69ea02245` on retained primary
`main`; working tree was clean at entry. Runtime source has not been edited.

## First Readout

**Do not reorganize the repository wholesale into L1/L2/L3 directories.** The
hierarchy is useful for responsibility and navigation, but the turn deliberately
crosses those boundaries. Existing feature/service owners and transaction owners
are more concrete physical boundaries.

The best-supported next choices are a small contract-import cleanup and clearer
authoring/policy input descriptions. Executor/compaction and frontend-controller
splits are narrower candidates if their maintenance benefit warrants the work.
These are proposals, not changes.

| Priority | Recommendation | Why it matters |
| --- | --- | --- |
| 1 | Clarify the execution-to-finalization contract import | `AttemptResult` has its own module, but worker collaborators import it through the execution implementation. |
| 2 | Clarify authoring versus snapshots, and policy-specific reviewer inputs | Editing active persona content is not creating an immutable definition; typed, natural and historical reviewers receive different inputs. |
| 3 | Consider bounded executor/compaction or frontend-controller splits | Separate protocols/readback responsibilities already have plausible seams; preserve tool-loop and stale-response safeguards. |
| Keep | Retain run/attempt orchestration, acceptance and atomic success finalization | Shared ownership here protects one coherent outcome; separating domain commits would weaken it. |

No runtime defect or release failure is established by these structural findings.
Review details, counterarguments, and verification gaps are in section 5.

## 1. Ownership: L1 And L2

This is containment, not a call sequence. Names/IDs come from
[inventory.json](inventory.json); statuses below are scoped source observations,
not new capability qualification. PC-01 through PC-12 and
[ADR 0061](../../adr/0061-capability-responsibility-map.md) remain unchanged.

| L1 domain | L2 subsystem | Existing physical owners and collaboration |
| --- | --- | --- |
| Character | Persona Definition | Prompt Center/content owns authoring; runtime definition/session services snapshot and bind immutable versions. Definition snapshots also bind deployment/policy, which is not persona content. |
| Character | Conversation Behavior | Runtime `executor.py` produces one candidate through shared CHAR-03/04 generation; curated tools participate in its finite loop. No understanding-to-expression object or separate phase exists. |
| Memory | Recall & Context | Context builders, subject-scoped retrieval, and experimental history reader/ranking/admission collaborate under `TurnExecution`. Evidence selection is not semantic answering. |
| Memory | Retention & Updates | Acceptance captures user text; one policy-bound reviewer proposes changes; validators and commit helpers participate in runtime-owned finalization. |
| Memory | Organization & Maintenance | Fact embeddings and local compaction are prepared during the attempt and stored with success. Additional derived views remain deferred. |
| Interface | Conversation UI | Agent Studio owns user interaction, run monitoring, and persisted state display; it does not generate or commit replies. |
| Interface | Configuration UI | Prompt/persona editing and selected definition/subject configuration precede a turn. Immutable conversation binding is runtime-owned. |
| Interface | Inspection & Evaluation UI | Public retained activity and experimental private captures are different interfaces/data authorities. |
| External Tools | External Information & Actions | EXT-01 is deferred. Internal memory search and deterministic evaluation fixtures are not its implementation. |

Runtime Coordination (SUP-01), State & Storage (SUP-02), Model Access (SUP-03),
Evaluation (SUP-04), Observability (SUP-05), Release & Operations (SUP-06), and
Application Boundary (SUP-07) retain supporting identities, not invented L1 depth.
Schema Content (SUP-08), UI-07, UI-08, UI-09, ADJ-01 and ADJ-02 remain registered but outside
the deep message-journey audit. Model Catalog UI-06 is a direct interface only;
the Model Router service and deployment infrastructure were not fully audited.

## 2. Actual Message Flow And Protected Boundaries

```text
Previously authored content -> immutable definition -> conversation + subject
User text -> UI/proxy/API -> RunService.accept_turn
  [transaction A: pending run + original user message + pending lease + events]
  -> run receipt -> UI monitoring (not a reply)
Worker -> claim/recover -> attempt record and deadline/cancellation/lease control
  -> coherent state -> eligible compaction -> fact/local context selection
  -> optional evaluation history selection/admission/authorization
  -> actual conversation request -> shared generation [optional memory-tool loop]
  -> candidate text -> ONE policy-bound reviewer -> prepared review + embeddings
  -> RunFinalizer.commit_success
  [transaction B: permitted memory/index writes + assistant + optional summary
   + conversation version + attempt/run success + success events + lease release]
  -> UI reloads persisted state -> displays reply
```

These are source-derived calls, not a live trace. Conditional branches are not
mandatory phases, and the chart's fictional examples are not runtime evidence.

| Boundary / source anchor | Producer -> consumer; payload | State, authority, and conditions |
| --- | --- | --- |
| `run_service.py:60` / `RunService.accept_turn` | Accepted text/settings -> run/message repositories; run receipt -> UI | Catalog, policy, archive and worker-readiness gates precede the write. Idempotent replay returns the original run without another user message. |
| `run_service.py:134` | Runtime acceptance -> repositories on one connection | Transaction A locks conversation/subject and stores accepted versions/generation, exact text/hash/role/run attribution, pending lease, and acceptance/message events. No accepted fact or assistant reply yet. |
| `worker_claims.py:32` / `RunClaimer.claim` | Pending/abandoned run -> `ClaimedRun` | Claim/recovery and lease acquisition occur transactionally. Exhausted abandoned work terminates without another attempt. |
| `worker_control.py:55,88`; `worker.py:216` | Claim -> recorded attempt -> `TurnExecution` | ADE owns retries; `retry_count` means additional attempts. Each attempt has an absolute deadline and cancellation/lease monitors. Lost lease forbids this worker's terminal commit. |
| `turn_memory_snapshot.py:23` / `load_turn_state` | Accepted run -> bound definition, conversation, subject, messages, summary, facts/entities | Repeatable-read, read-only snapshot verifies accepted memory generation. Optional history reader/capture has separately guarded availability. |
| `turn_execution.py:92,130`; `memory_policy_binding.py:10` | Bound policy/deployments -> executable attempt | Natural bindings are development-only at execution; history also requires evaluation purpose and matching probe. Router catalog validates deployment identities. |
| `turn_compaction.py:18` / `compact_turn` | Older local messages -> working summary proposal | Before generation and only when eligible. B disables it; A/A0 can withhold it under snapshot pressure. Storage waits for transaction B. |
| `turn_retrieval.py:21,60`; `turn_memory_snapshot.py:102` | Current query/tool query -> embeddings -> subject-bound fact rows | Shared search mechanics enforce generation/space/dimensions. Automatic and discretionary searches have different limits/thresholds; neither retrieves dialogue history. |
| `turn_context_selection.py:56` | Bound persona, current turn, local/fact evidence -> `TurnContextSelection` | Typed and natural builders differ; natural selection preflights reviewer capacity. Persona is supplied, not rewritten. |
| `turn_history_setup.py:46`; `history_attempt.py:64,219` | Scoped evaluation corpus -> ranked/admitted original exchanges -> generation/review | Experimental only. Reader considers newest 128 completed pairs before later exclusions; same workspace/subject/purpose/character root, including archived/versioned chats. Source authorization precedes exposure. |
| `executor.py:124` / `ConversationExecutor.execute` | Serialized messages/tool schemas -> provider -> `ExecutorResult` | One shared CHAR-03/04 invocation path, potentially multiple finite tool-loop requests. Model selects enabled tools; actual result re-enters the next request. Candidate is not yet persisted/displayed. |
| `turn_execution.py:371,403` | Current user and policy-specific references -> one reviewer | Natural replaces typed review, never supplements it as a second reviewer. Their source authority differs, as below. |
| `memory_policy.py:39`; `natural_memory_policy.py:55` | Review decision -> prepared operations | Schema, handles/quotes, ownership, target versions and lifecycle checks; not proof that the model interpreted meaning correctly (PC-05). |
| `turn_embedding_results.py:15` | Value-bearing prepared operations -> aligned vectors | No-value operations carry no vector. Dimensions and embedding identity are preserved for finalization. No independent post-reply indexing loop. |
| `worker_finalization.py:42,51` | `AttemptResult` + claim -> repositories on one connection | Transaction B fences run/cancellation/lease, locks conversation then subject, checks accepted versions/generation and admitted sources, revalidates review, and commits the complete success bundle. |
| `worker_finalization.py:225,264`; `worker.py:237` | Cancellation/failure/lease loss -> terminal metadata or no authority to commit | No success bundle on these paths. Accepted user message remains recorded; failed/pending text must not count as a completed exchange. |
| `worker_finalization.py:207`; `worker.py:254` | Attempt trace/private evidence -> observational retention | Some observations are best-effort after the authoritative transaction; observation failure cannot rewrite the outcome. Success-event storage and trace completeness are not interchangeable. |

The main transaction evidence is
[acceptance](/Users/wjmao/projects/HU/Letta-Open-ADE/services/ade-api/src/ade_api/features/agent_runtime/run_service.py:134),
[finalization](/Users/wjmao/projects/HU/Letta-Open-ADE/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py:51),
and [memory revision ownership](/Users/wjmao/projects/HU/Letta-Open-ADE/services/ade-api/src/ade_api/features/agent_runtime/persistence/memory.py:346).
Commit helpers receive the caller's connection; they do not start independent
domain transactions. Fact search joins current revision/space-linked embeddings
to fact state; an index is not a second truth authority.

| Bound policy | Generation context / reviewer input | Status and important limits |
| --- | --- | --- |
| Typed | Prompt/persona, active profile, retrieved facts, summary/metadata and local dialogue. Reviewer: current user, up to eight prior user messages, active facts/entities; no candidate reply. | Existing executable typed path. Protocol repair is explicitly bounded by reviewer request settings, not a second semantic reviewer. Serialized tool-follow-up overflow checking is not enabled by this path's `input_token_limit`. |
| Natural A/A0/B | Lifecycle-aware variants; A/A0 depend on full-snapshot fit, B uses selected views/local suffix. Reviewer receives selected originals/current anchor, lifecycle facts/entities and candidate as reference. | Development-only variants. One-call review; structural source binding does not certify interpretation. A/A0 withholding and B compaction differences are intentional policy contracts. |
| History probe | Natural history-capable binding plus admitted original exchanges shared by generation/review; per-dispatch and commit source checks. | Development/evaluation only. Current admission is greedy/capacity-bound. Packet can rebuild before first generation exposure, not after exposure. Joint/neighborhood selection and ADR 0060 whole-selection admission remain proposed. |

## 3. Capability-To-Code And Test Map

Paths below use the canonical inventory aliases: `runtime:` =
`services/ade-api/src/ade_api/features/agent_runtime/`, `tests:` =
`services/ade-api/tests/agent_runtime/`, `web:` = `apps/ade-web/src/features/`,
`api:` = `services/ade-api/src/ade_api/features/`, `repo:` = repository root.
Source suffixes denote baseline line anchors, not new interfaces.
Tests: **E** executed offline; **I** inspected assertions/fixtures but not run;
**P** present/path-checked only. PostgreSQL/browser/live qualification was not run.

L3 name key (not additional modules):

| L1 / L2 | Canonical modules in this audit |
| --- | --- |
| Character / Persona Definition | CHAR-01 Prompt and persona authoring; CHAR-02 Immutable definition binding |
| Character / Conversation Behavior | CHAR-03 Evidence interpretation; CHAR-04 Character expression and continuity; CHAR-05 Curated tool choice and result use |
| Memory / Recall & Context | MEM-01 Scope and eligibility; MEM-02 Candidate search; MEM-03 Evidence selection; MEM-04 Context delivery |
| Memory / Retention & Updates | MEM-05 Source capture; MEM-06 Memory update review; MEM-07 Validation and commit |
| Memory / Organization & Maintenance | MEM-08 Index maintenance; MEM-09 Conversation compaction; MEM-10 Additional derived views (deferred) |
| Interface / relevant UI | UI-01 Conversation workspace; UI-02 Memory and lineage display; UI-03 Turn activity inspection; UI-04 Private evaluation artifact inspection; UI-05 Prompt and persona editor |
| External Tools / External Information & Actions | EXT-01 External information and actions (deferred) |

| L3 / support ID | Primary implementation, contributors, and input -> output | Status / existing test evidence |
| --- | --- | --- |
| CHAR-01 | `api:prompt_center/registry.py:150`, `personas/sqlite.py:149`, `personas/store.py:107`; edits -> mutable active authored content. | Implemented mechanics; authoring quality unqualified. Immutable runtime version creation belongs to CHAR-02, not every editor save. |
| CHAR-02 | `runtime:definition_service.py`, `persistence/definitions.py`; content/deployment snapshot -> immutable version/conversation binding. Session services contribute; trial API is an experimental caller. | Implemented mechanics, not cross-version continuity qualification. I `tests:test_resource_service.py`, `persistence/test_agent_studio_postgres.py`. |
| CHAR-03 | `runtime:executor.py:124`; `context.py:163`, `history_admission.py:101` contribute supplied evidence. Actual request -> shared interpretation/answering. | Partial behavioral responsibility; no separately observable intermediate. E `tests:test_executor.py`; P story comparisons are not this audit's semantic evidence. |
| CHAR-04 | Same `runtime:executor.py:124`, bound persona content; exchange/evidence/characterization -> candidate choice and expression. | Partial; same call as CHAR-03. I `tests:persistence/test_postgres_story_continuity.py`; not rerun or generally qualified. |
| CHAR-05 | `runtime:executor.py:91,124`, `tool_policy.py`; enabled registry/model arguments -> validated tool/result/continuation. `turn_retrieval.py:60` contributes Memory execution. | Implemented mechanics, discretionary quality not established. E `tests:test_executor.py`; P `test_tool_policy.py`. |
| MEM-01 | `runtime:turn_memory_snapshot.py:23,102`, `persistence/history.py:27`, `persistence/memory_source_read.py`; scope/lifecycle -> eligible state/source data. | Partial overall: existing fact isolation vs evaluation-bound history. I `tests:persistence/test_postgres_history_reader.py`; P lifecycle tests. |
| MEM-02 | `runtime:turn_retrieval.py:21,60`, `persistence/memory.py:422,463`; history reader/native rank contribute experimental search. Query/eligible state -> candidate facts/exchanges. | Partial aggregate; historical candidate availability is bounded. E executor tool integration; P `tests:test_embeddings.py`, `test_history_native_rank.py`. |
| MEM-03 | `runtime:history_ranking.py`, `history_native_rank.py`, `history_admission.py:177`; fixed pool/query -> chosen originals. | Experimental. P `tests:test_history_ranking_identity.py`, `test_story_correction_comparison.py`; joint/neighborhood implementation not claimed. |
| MEM-04 | `runtime:context.py:163`, `natural_context.py:78`, `turn_context_selection.py:56`, `history_attempt.py:106,219`; selected evidence/budgets -> actual bound consumer requests. | Partial overall. E `tests:test_natural_context.py`, serialized executor checks; P history admission/capacity tests. |
| MEM-05 | `runtime:run_service.py:188`, `worker_finalization.py:128`, `persistence/conversations.py`; accepted text/committed candidate -> original attributed messages. | Implemented. E `tests:test_run_service.py`, `test_worker_finalization.py`; these unit checks do not prove SQL atomicity. |
| MEM-06 | `runtime:reviewer.py:175` or `natural_memory_reviewer.py:94,351`, review schemas/binding; current anchor/references -> proposed change/no change/conflict. | Partial; natural variants experimental. E `tests:test_natural_memory_reviewer.py`; P `test_natural_review_r5_contract.py`. Exact per-policy inputs are in section 2. |
| MEM-07 | `runtime:memory_policy.py:39`, `natural_memory_policy.py:55`, `memory_commit.py:15`, `natural_memory_commit.py:17,96`, `worker_finalization.py:42`; prepared review/source versions -> permitted atomic writes. | Implemented integrity mechanics, not semantic certification. E `tests:test_worker_finalization.py`; I PostgreSQL fencing/atomicity test interfaces. |
| MEM-08 | `runtime:embeddings.py:30,68`, `turn_embedding_results.py:15`, commit helpers and `persistence/memory.py:413`; prepared values/space -> revision-linked vectors. | Implemented. P `tests:test_embeddings.py`, `persistence/test_postgres_memory_lifecycle.py`; provider/retrieval quality not measured. |
| MEM-09 | `runtime:compaction.py`, `turn_compaction.py:18`, `executor.py:275`, `worker_finalization.py:140`; eligible prefix -> working summary -> committed summary/provenance. | Implemented conditional path. E `tests:test_compaction.py`; P `persistence/test_postgres_natural_compaction_packets.py`. |
| MEM-10 / EXT-01 | No implementation/test home: additional derived views / outside information-actions. | Deferred, not missing refactor work. |
| UI-01/02/03/05 | Agent Studio/Prompt Center views/hooks/API boundaries; user actions/configuration and retained state -> presentation. | Implemented mechanics; upstream source/test inspection recorded below. |
| UI-04 / SUP-05 | `runtime:natural_attempt_evidence.py`, `natural_evidence_readback.py`, `history_observations.py`, `provider_tracing.py:24`, `request_counts.py`, `persistence/evaluation_observations.py`; actual packets/state/dispatch -> bounded observations. | Private artifacts experimental; normalized observations implemented. I upstream tests below, other inventory tests P; no private artifact or live trace consumed. |
| SUP-01 | `runtime:application.py:43`, `run_service.py:60`, `worker.py:37`, `worker_claims.py:25`, `worker_control.py:41`, `turn_execution.py:63`, `worker_finalization.py:36`, `retry.py:16`; receipt/claim -> coherent attempt/outcome. | Implemented. E run/finalization/retry checks; P `tests:test_worker.py`. Many collaborators are intentional, not automatically mixed ownership. |
| SUP-02 / records | `runtime:persistence/`, `database_boundary.py`, migration/schema authority; caller-owned connection -> scoped SQL state. | Implemented; metadata scanned, key transactions read. I/P database tests not executed. Six record families are data, not L3 processing modules. |
| SUP-03 | `runtime:router_transport.py:36`, deployment bindings and catalog integration; bound model identity/request -> one transport dispatch/response. | Implemented local boundary. Fixture transport used in E tests; no Model Router service/live provider qualification. |
| SUP-04/06/07 | Evaluation-only fixture/policy activation, existing release gates, and app/auth composition contribute before or around execution. | Source/interface checks only. No experiment, activation, release, or auth qualification. |

### Reverse Source Register

All 94 tracked runtime Python files received AST/import/size inspection, not
full-body review. The disjoint register below accounts for every file. Append
`.py` to each stem; braces abbreviate alternatives. **B** means body/call-path
inspection at the anchors above or below; **M** means metadata/path checks only.
Unlisted body depth must not be inferred from a capability association.

| Existing source group / primary IDs | Count | Runtime filename stems |
| --- | --- | --- |
| API/composition: SUP-07, contributing SUP-01/UI-01/05 | 13 | `__init__, api, api_boundary, agent_studio_api, history_trial_api, application, dependencies, service_protocol, contracts, memory_contracts, presenters, errors, flags` |
| Resource/session lifecycle: CHAR-02, UI-01/02/05, SUP-01 | 5 | `agent_studio_reset, agent_studio_sessions, definition_service, resource_service, evaluation_sessions` |
| Attempt/context/generation: SUP-01, CHAR-03/04/05, MEM-01/02/04/08/09 | 15 | `turn_{compaction,context_selection,deployment,embedding_results,execution,history_setup,memory_snapshot,memory_views,result,retrieval}, context, natural_context, compaction, executor, tool_policy` |
| Run/control: SUP-01/05, contributing MEM-05/07 | 9 | `run_service, worker, worker_{claims,control,events,finalization,health}, retry, events` |
| Review/schema/commit: MEM-06/07, contributing UI-02/SUP-02 | 13 | `fact_registry, memory_{entities,commit,policy,policy_binding,removals,review}, reviewer, natural_memory_{binding,commit,policy,review,reviewer}` |
| History policy: MEM-01/03/04, contributing SUP-04 | 7 | `history_{admission,attempt,capacity,native_rank,ranking,trial}, natural_evaluation_capacity` |
| Observations: SUP-05, contributing UI-03/04 | 6 | `natural_attempt_evidence, natural_evidence_readback, provider_tracing, request_counts, history_observations, turn_activity` |
| Model access: SUP-03, contributing MEM-02/08 | 3 | `embeddings, router_transport, deployments` |
| Release bindings: SUP-06 | 2 | `release_policy, release_evidence` |
| Evaluation tools: SUP-04, contributing CHAR-05; not EXT-01 | 1 | `evaluation_tools` |
| Storage foundation: SUP-02 and six record families | 20 | Root: `bootstrap, database_boundary`. `persistence/`: `__init__, base, conversations, database, definitions, evaluation_observations, history, history_guard, history_lineage, leases, memory, memory_actions, memory_source_read, metadata, runs, validation, workers, workspaces` |

The six persisted identities are REC-DIALOGUE, REC-FACTS, REC-SUMMARY,
REC-DEFINITION, REC-INDEX and REC-RUNS; transient candidates/prepared reviews are
not stores. Source groups above are navigation aids, not adopted packages.
Runtime body inspection covers the section 2 call-path anchors, section 3 primary
builders/review/commit owners, and section 5 findings. Release/schema/auxiliary
helpers without a cited call-path inspection remain M, not deeply qualified.

Direct upstream/readback inspection, including relevant handwritten frontend:

| Source files / inspected anchor | Primary and contributing IDs; input -> output / limit |
| --- | --- |
| B `api:prompt_center/{registry,personas/sqlite,personas/store,personas/seed}.py`; update anchors above, `seed.py:33`. M `repo:content/personas/personas.jsonl:1` | CHAR-01: editable source/seed -> active authoring. Content presence checked, not persona quality. |
| B `api:prompt_center/{personas_api,contracts}.py:143,58`; `web:prompt-center/api.ts:84`. Interface inspection `web:prompt-center/use-prompt-center.ts:163` | CHAR-01/UI-05: author actions -> Prompt Center CRUD. Does not automatically create a CHAR-02 version. |
| B `runtime:definition_service.py:213`, `persistence/definitions.py:147`, `api:prompt_center/__init__.py:8` | CHAR-02: public content reader -> immutable version. Deployment/policy snapshot is supporting configuration, not characterization. |
| B `runtime:agent_studio_sessions.py:84`, `application.py:96`; `web:agent-studio/{use-definition-version.ts,definition-version.tsx}:63,9` | UI-01/05, CHAR-02: selected authoring/config -> atomic session provisioning or version creation. UI refetches previews; existing version fence is not a template-hash fence. |
| B `web:agent-studio/{use-agent-studio.ts,api.ts,event-stream.ts,agent-studio-view.tsx}:203,122,21,108` | UI-01: submit -> run receipt -> SSE/poll -> persisted terminal readback/display. Selection/read epochs fence stale async updates. |
| B `web:agent-studio/{session-draft.ts,selection.ts,resource-actions.ts}:14,10,31` | UI-01: drafts/selection/actions -> controller requests; existing collaborators, not missing modules. |
| B `runtime:resource_service.py:67,126`; `web:agent-studio/{memory-facts.tsx,use-memory-removal.ts,memory-action.ts}:19,40,19` | UI-02, MEM-07: retained facts/sources -> display/removal or editable correction turn; removals fence fact version and memory generation. |
| B `runtime:turn_activity.py:11`; `web:agent-studio/turn-activity-view.tsx:9` | UI-03/SUP-05: retained observations -> activity. Distinguishes known zero, missing and lower-bound counts. |
| Interface inspection `runtime:natural_attempt_evidence.py:39`; B `natural_evidence_readback.py:25`, `history_observations.py:10` | UI-04/SUP-05: gated private capture -> terminal evidence. Development/evaluation and isolated loopback DB gate; bounded private retention, not hidden reasoning or raw wire/auth capture. |
| B `runtime:{history_trial,history_trial_api}.py:130,27` | SUP-04/UI-05, contributing CHAR-02: explicit pinned evaluation policy -> trial routes; no ordinary default turn activation. |
| B `runtime:{api,agent_studio_api,dependencies,api_boundary}.py:122,80,24,17`; interface inspection `contracts.py:365` | SUP-07/UI-01: role-scoped HTTP contracts -> service calls; accepted turn returns 202, SSE supports Last-Event-ID. |
| B `repo:services/ade-api/src/ade_api/platform/{app,auth}.py:40,42`; `repo:apps/ade-web/src/app/api/v3/[...path]/route.ts:20`, `repo:apps/ade-web/src/shared/api/server/ade-api-proxy.ts:16` | SUP-07: app/router/auth composition and server-held credential -> streaming proxy; no browser-auth forwarding. |

Upstream tests **I**, not executed: Prompt Center `test_content_identity.py` and
`test_persona_registry.py`; Agent Studio `use-definition-version.test.tsx`,
`use-agent-studio.async.test.tsx`, `agent-studio-view.test.tsx`,
`turn-activity-view.test.tsx`; runtime `test_resource_service.py`,
`test_turn_activity.py`, `test_natural_attempt_evidence.py`,
`test_history_observations.py`, `test_agent_studio_options.py`, `test_history_trial.py`,
`test_native_app.py`; web proxy `route.test.ts`. SQL tests inspected include
`persistence/{test_agent_studio_postgres,test_postgres_story_continuity,test_postgres_lock_order,test_postgres_natural_worker_fencing,test_postgres_history_worker,test_postgres_generation_candidate}.py`.
Their assertions cover binding, provisioning/replay, stale UI callbacks, source
readback and fenced outcomes; neither their presence nor this reading proves
cross-version characterization, SQL behavior in this checkout, or release readiness.

## 4. Dependencies Are Not Dataflow

Confirmed local collaboration, distinct from the chronological sequence above:

```text
Application -> public Prompt Center reader contract + narrow runtime services
Worker -> Claimer + AttemptController + Finalizer + Presence
AttemptController -> TurnExecution
TurnExecution -> context/retrieval/compaction/history/review/embedding collaborators
History admission -> exact conversation request builder + reviewer preflight
Executor/Reviewer/EmbeddingClient -> RouterTransport (wrapped by AttemptTrace)
Finalizer -> validation + commit helpers + connection-bound repositories
Repositories -> SQL metadata/base helpers (no domain-owned engine transaction)
```

The history-to-request-builder/preflight dependency is deliberate: admission must
measure what consumers actually serialize, rather than duplicate their wire shapes.
Runtime injection uses public contracts/curated handlers. Where dynamic registry
contents or deployment policy chooses a path, source activation checks establish
possible behavior, not which path a deployed system currently uses.

Independent AST verification: 94 runtime files, 19,712 physical lines, 386 distinct
internal import edges; 382 after excluding `TYPE_CHECKING`. The latter graph is
acyclic. The all-import graph contains a type-only cycle through
`provider_tracing.py:14`; do not diagnose a runtime cycle from that graph alone.
Outbound ADE imports are 17 edges to platform `auth`, `settings`, `project_paths`
and `openapi_metadata` (the latter three metadata/interface depth), plus two edges to
Prompt Center's public package interface, with no sibling-feature-internal imports.
That scoped result excludes browser dependencies, application-wide cycles and
dynamic dispatch. Runtime HTTP transport still calls Model Router.

Inventory references: all 106 code and 60 test occurrences resolve (84/52 unique
paths, four directory references). Direct references name 47/94 runtime files;
the inventory is selective, not a file ledger or test coverage measurement.

## 5. Findings And Refactor Candidates

### A1. Clarify A Contract's Import Owner

Observed: [turn_result.py:18](/Users/wjmao/projects/HU/Letta-Open-ADE/services/ade-api/src/ade_api/features/agent_runtime/turn_result.py:18)
defines `AttemptResult`, yet `worker.py:22`, `worker_control.py:18`,
`worker_events.py:10`, and `worker_finalization.py:25` import it through
`turn_execution.py`. The contract module exists but consumers still depend on its
implementation's incidental re-export. This adds import coupling/navigation cost;
it does not establish a cycle or runtime failure.

Recommendation: a small direct-import cleanup, not another abstraction. Keep
`TurnExecution` imports where execution is actually used. Benefit: explicit
execution/finalization seam; low expected effort, high confidence in observation.
Alternative: incidental re-export is currently working and may be intentional
compatibility for callers; inspect all imports before changing it. Preserve the
result shape, orchestration, transactions, and PC-05/08/09. Checks: import/app
composition plus existing worker/finalization/executor tests; SQL tests for any
unintended behavior changes. This audit made no import edits.

### A2. Split Candidate: Conversation Versus Compaction Dispatch

Observed: [executor.py:124](/Users/wjmao/projects/HU/Letta-Open-ADE/services/ade-api/src/ade_api/features/agent_runtime/executor.py:124)
owns dialogue/tool execution, while `ConversationExecutor.compact` at line 275
owns a different response schema, prompt, serialization, parse and provenance.
`TurnExecution` already constructs separately traced conversation/compaction
executors (lines 156/164); `turn_compaction.py:62` calls only the compaction API.
The file's tool registry and request builders also have consumers outside the loop.

Recommendation: consider extracting only compaction dispatch behind its existing
caller/contract, keeping shared character generation intact. Benefit: summary
protocol edits need not touch tool-loop code; medium expected effort/confidence
in benefit. Counterargument: transport/response handling is genuinely shared and
current tests work; avoid duplicating helpers or creating a framework to separate
two methods. PC-09/12 does not require a new call, service, or background worker.
Preserve prompt/request hashes, source lineage, conditional pre-generation timing,
and atomic summary finalization. E executor/compaction checks are available;
PostgreSQL summary/packet guards and import consumers must be verified in any
approved refactor. No extraction is authorized by this report.

### A3. Clarify Aggregated Input/Status Descriptions

Observed: CHAR-01 says "versioned authored characterization", but Prompt Center
updates active content in place (`registry.py:198`, `personas/store.py:119`);
immutable definition creation is explicit CHAR-02 work. This is wording ambiguity,
not a newly diagnosed snapshot defect. The MEM-06 input names a reference-only candidate reply, while
the typed call at `turn_execution.py:403` does not receive it. MEM-04 combines
several builders with different capacity/withholding behavior. The journey README
already explains these distinctions; its aggregation is not evidence of a bad
runtime abstraction. Stale baseline dates likewise do not alone prove stale code.

Recommendation: when updating the inventory, make policy-specific input scope
directly discoverable and cross-link the exact boundaries in section 2; do not
change inventory status or runtime to fit a simpler universal pipeline. Distinguish
active authoring from immutable runtime binding (PC-04/12). Low effort,
high confidence in the description difference. Validate renderer/source/status
consistency; qualification remains separate. PC-05/09/12 protects one reviewer
and joint generation. Canonical inventory/chart corrections are proposed only.

### A4. Split Candidate: Frontend Readback And Monitoring

Observed: `web:agent-studio/use-agent-studio.ts` has 516 lines, combining workspace
loading/selection, pagination, drafts, evidence navigation, run monitoring and
submission/cancellation. `refreshSelected:203`, `finishRun:262` and `monitorRun:296`
share selection/read-epoch guards. Existing draft/selection/action collaborators
already separate some concerns; no stale-update defect was established.

Recommendation: consider one bounded epoch-aware readback or monitoring extraction,
not one hook per L3 box. Medium expected effort/confidence in benefit; alternative:
the controller deliberately coordinates one selected workspace and splitting it
can scatter its lifecycle. Preserve the public hook/view contract, stale-response
fences, terminal refresh, stream/poll fallback and editable drafts (PC-04/07/09).
Affected consumers: `agent-studio-view.tsx`, API/event-stream helpers and async
tests. Run existing `use-agent-studio.async.test.tsx` and view tests plus browser
interaction before calling any approved extraction complete; neither was run here.

### Size Signals, Not Automatic Splits

| Production file over 500 lines | Lines | Reviewed responsibility / conclusion |
| --- | --- | --- |
| `runtime:agent_studio_sessions.py` | 578 | Body: purpose-scoped provisioning/replay/lifecycle/readback. `create:84` uses one transaction at line 99 for definition/subject/conversation; preserve atomic idempotent provisioning. Administrative helpers could be considered separately, not independent domain commits. |
| `runtime:executor.py` | 568 | Body: tool loop/request builders plus compaction dispatch; A2 is a protocol-local candidate, not a size-only extraction. |
| `runtime:persistence/memory.py` | 527 | Body: subject/entity/fact state, revision/source lineage, aligned index queries. Keep caller-owned transaction and current-revision joins; no second memory authority. |
| `runtime:persistence/metadata.py` | 828 | Metadata plus representative schema inspection: 22 SQLAlchemy table declarations. Individual constraints not fully audited. A schema-only file is not proven mixed domain behavior; defer any schema-layout change. |
| `web:agent-studio/use-agent-studio.ts` | 516 | Body: selected-workspace async coordination; A4 identifies a narrower potential seam. |

### K1. Keep Cohesive Coordination And Transaction Owners

Keep `RunService`, `TurnExecution`, worker collaborators, and the success transaction
as explicit coordinators. Shared files are not automatically misplaced L3 modules.
Keep Memory review preparation separate from persistence authority, facts separate
from original dialogue, immutable persona binding separate from mutable subject
state, and observation failure separate from run outcome. Do not create a universal
Memory service or a three-phase character engine to mimic the diagram.

Folder regrouping alone is not supported as a first step: established prefixes
already identify collaborators and import movement adds churn. Use the reverse
register for navigation first, then regroup only where repeated change/test work
demonstrates a concrete benefit. A directory tree is not selected here.

## 6. Verification And Evidence Limits

Executed, with existing environment/no dependency sync, temporary UV cache and
pytest cache disabled:

```sh
env UV_CACHE_DIR=/private/tmp/ade-audit-uv-cache PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline --no-sync python -m pytest services/ade-api/tests/agent_runtime/test_run_service.py services/ade-api/tests/agent_runtime/test_worker_finalization.py services/ade-api/tests/agent_runtime/test_executor.py services/ade-api/tests/agent_runtime/test_retry.py -q -p no:cacheprovider
env UV_CACHE_DIR=/private/tmp/ade-audit-uv-cache PYTHONDONTWRITEBYTECODE=1 uv run --locked --offline --no-sync python -m pytest services/ade-api/tests/agent_runtime/test_compaction.py services/ade-api/tests/agent_runtime/test_natural_memory_reviewer.py services/ade-api/tests/agent_runtime/test_natural_context.py -q -p no:cacheprovider
```

Results: **35 passed + 30 passed = 65**, no failures/skips in those selected files.
Fixtures replace transport/repositories; root `conftest.py` disables the live router.
This checks selected mechanics, not PostgreSQL transaction/locking behavior,
browser pixels, actual provider output, personality, semantic sufficiency, or
release qualification. Database/live suites were deliberately not executed,
not silently counted as passed. No production database, provider, service restart,
migration, deployment, or private evidence access was performed.

Documentation checks passed: aliased paths/line bounds, local Markdown links,
all registered IDs and complete/disjoint 94-file reverse coverage. The existing
`render.py --check` passed: 35 pieces, six record families, three flows and 136
unique source/test references; generated views were not modified. Independent
read-only review checked structural counts/register/qualification wording; its
one executor-construction anchor correction was verified and applied.

## 7. Review Gate

Discuss section 1 first, then section 2, then the module map/findings. Decide
between keeping code as-is with this map, approving A1 as a small cleanup, or
separately planning A2 or A4 with preserved contracts and checks. A3 can be a narrow
documentation correction after review. Do not combine all candidates into a
repository-wide rewrite. Audit completion is not refactor approval.
