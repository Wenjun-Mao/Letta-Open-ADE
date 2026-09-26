## Verdict

**Revise and simplify the plan, then proceed with a bounded feasibility experiment. Do not implement all three runtime arms upfront.**

My recommended first contrast is **the existing baseline versus one automatic, bounded historical read**. This answers the first useful question: *Does supplying relevant historical dialogue improve the response enough to justify the added context and review burden?* It does not answer which retrieval trigger is best—and need not yet.

**Keep the narrow read-only `H` extension. Collapse search and read into one operation when discretionary retrieval is introduced.** `H` fills a real gap in the current reviewer contract; a separate search-preview/read protocol has not yet demonstrated a corresponding need.

The proposal already makes several important choices correctly: short-lived PostgreSQL snapshots, frozen corpus membership, whole exchanges, lifecycle annotations, cumulative history limits, independently seeded arms, and no production-indexing prerequisite. Those should survive simplification. The remaining work is mostly **tightening a few integration boundaries**, not designing a memory platform. 

### Inspection scope and authority

I inspected the pinned revision **`cece5bedd6032da3ebc3802c7be604eb505967e6`** through GitHub. I did not substitute `main`, access local services or captures, or execute tests.

The governing distinctions are important: PC-03/04/10 establish character-root continuity and archived-history eligibility; PC-05 assigns semantic judgment to the reviewer; PC-06/09 exclude phrase-based semantic enforcement and additional memory infrastructure. ADR 0035’s amended contract, rather than its historical privacy-validator clauses, governs natural review. ADR 0036 governs discretionary tools rather than phrase-derived requirements.   

## Minimal component and data-flow sketch

For the **first automatic-read experiment**, the implementation can be:

```text
Accepted run
  │ workspace, subject, purpose, immutable definition version → character root
  ▼
Existing load_turn_state() repeatable-read transaction
  ├─ existing local messages, facts, entities, summary, accepted generation
  └─ NEW: bounded successful exchanges + hashes + linked lifecycle descriptors
       transaction closes before provider work
  ▼
One history query/ranker over that frozen corpus
  ▼
One admission function
  ├─ whole exchanges only
  ├─ source-existence check
  ├─ serialized generator AND reviewer capacity checks
  └─ request-local, read-only H bindings
  ▼
Generator, including any existing tool continuations
  ▼
Existing single reviewer receives exactly the admitted H material
  ▼
Existing structural binder and atomic finalizer
```

This builds on an actual existing mechanism: `load_turn_state()` already opens a **repeatable-read, read-only transaction**, checks the accepted subject-memory generation, and materializes the local state before returning. There is no need for a new snapshot service or a global commit counter. 

The existing finalizer already fences cancellation, lease ownership, subject generation and conversation version, and commits memory changes, the assistant message and terminal success in one transaction. Historical recall should not acquire an independent write path. 

A later discretionary arm should call the same reader/admission path through **one `recall_history(query)` operation**, returning complete admitted windows—not previews followed by a second expansion protocol.

## Prioritized findings and minimum falsification tests

### 1. P0 — Reuse the existing snapshot, but freeze annotations with the transcript

**Source fact.** The repository already has the correct short-transaction pattern. The schema also provides the required root join: a conversation binds an `agent_definition_version_id`, and that immutable version identifies its `agent_definition_id` root. Workspace, subject and purpose are separate boundaries.  

**Necessary clarification.** The frozen corpus should be captured inside that existing state-load transaction, including the lifecycle descriptors needed to interpret its linked sources. Otherwise, it is possible to assemble local facts from one snapshot, historical messages from another, and annotations from a third.

The eligibility predicate should bind, server-side:

- The accepted workspace, subject, purpose and **definition root**, not identical definition versions.
- Successful, committed exchanges, not merely persisted user messages or old timestamps.
- Complete user/assistant exchange membership, with local sequence used only within its conversation.

Do **not** apply the character-root restriction to shared subject facts. PC-02 permits shared factual knowledge; PC-03 restricts which transcripts constitute shared experience. These are different scopes. 

**Minimum implementation.** Add the bounded history materialization to `load_turn_state()` or a helper called within its connection. Keep the corpus in attempt-local memory. A deterministic presentation order is useful, but neither `created_at` nor an `H` number should claim a global commit ordering.

**Falsification tests.**

A two-connection PostgreSQL test should hold an exchange transaction open before capture and commit it afterward. It must remain absent from every subsequent search in that attempt, even with an earlier creation timestamp.

One parameterized scope fixture should show that an ordinary version update and an archived source remain readable, while another root, subject, workspace or fixture case does not. Include overlapping conversation-local sequence numbers. That tests the boundary without adding a global ordering mechanism.

**Assessment:** this is principally a contract-preservation test, not a discovery that the plan lacks snapshot semantics.

### 2. P0 — “Revalidate before delivery” needs an explicit race boundary

**Source fact.** The plan intentionally freezes content but requires fresh source-existence validation so a purge cannot be bypassed by captured text. It also treats previews as evidence. Those requirements interact whenever evidence survives across requests. 

**Counterexample.**

1. A search preview reaches the generator.
2. Its source is purged.
3. The generator produces a candidate using that preview.
4. The reviewer receives either stale captured text or no corresponding evidence.

Checking only `read_history(reference)` does not resolve this. The model may never request that read, and the executor retains earlier tool results in later requests. 

**Minimum contract.** Define delivery as an explicit authorization checkpoint before an outbound packet containing historical material. Use a fresh existence check, not the original repeatable-read snapshot.

Before first exposure, a legitimately purged window can be omitted with a recorded unavailable/omitted outcome. After exposure, **abort the attempt if a subsequent required check discovers that admitted evidence has disappeared**. That is simpler and safer than stripping history from only the reviewer or generating a replacement answer.

Also define the race limit: a purge committed after an authorization check cannot retroactively unsend an already authorized request. Do not promise perpetual freshness or hold database transactions across provider calls.

Archiving alone must not invalidate an admitted source.

**Falsification test.** Pause immediately before the first generator delivery, and separately after generation but before review. Purge the source. The first case must not expose it; the second must not commit a candidate whose required evidence has become inconsistent. Repeat with archive instead of purge and verify continued eligibility.

**Simplification benefit:** one combined retrieval operation removes the preview/read race, though not the later generator/reviewer race.

### 3. P0 — Lifecycle annotation must follow provenance, not just the current revision’s sources

**Source fact.** The repository stores revision-to-message spans, revision-to-fact links, current revisions and lifecycle status. `list_revision_sources()` validates workspace, subject, purpose and source authority roles, but it is a **fact-revision source reader**, not a character-scoped transcript reader. It also correctly allows operator actions to have no message sources.  

**Concrete trap.** An original assertion links message M to revision R1. An operator later forgets the fact through R2, which has no message source. Looking only at the current revision’s source rows would fail to associate M with the forgotten chain.

**Minimum implementation.** For returned message IDs, resolve their existing source links through the linked revisions to the current fact descriptor. Do not require a new semantic linking system. Do not retrieve forgotten historical revision values as model context; the retained transcript is the separate source the plan deliberately permits.

Attach lifecycle information to the **linked span or claim**, not indiscriminately to the entire exchange. One message can contain both a corrected claim and an unaffected claim.

Three outcomes should remain distinct:

| Situation | Minimum treatment |
|---|---|
| Valid transcript with no known fact linkage | Eligible, with current status explicitly unknown |
| Verified linkage to a corrected, ended or forgotten chain | Include the applicable annotation |
| Verified linkage with inconsistent hash, ownership or required provenance | Integrity failure, not an ordinary empty result |

**Falsification test.** Use one message containing two claims. Correct one and retain the other; then separately test operator removal of the linked fact. Verify that annotations follow the proper source span and that no lookup of a source-less latest revision erases knowledge of the earlier linkage.

The plan’s “omit the window if essential annotations do not fit” rule is worth keeping. Its limitation is equally important: **unlinked later corrections cannot be solved structurally without inventing the semantic subsystem the project excludes.**

### 4. P0 — Keep `H`, but only as a held reply-review reference

**Source fact.** The current wire contract permits conflict references only to `F` and `E`. Its write evidence modes separately accept direct current quotes, earlier `U` support or earlier `A` support. The binding map orders those local messages by conversation sequence and requires them to precede the current message.  

Therefore, **putting cross-chat history into `source_messages` is the wrong shortcut**. A valid historical message with sequence 200 cannot be compared with sequence 1 in the new chat. More importantly, doing so would make it eligible for existing write-support modes.

`H` is justified because a reply can contradict historical dialogue without contradicting any held profile fact or identity. Removing `H` entirely would either leave that contradiction ungroundable or tempt the implementation to misuse `U/A/F/E`.

**Minimum extension.**

Add a request-local history map separate from `messages`, `targets` and `identities`. Retain server-owned message identity, role, content hash and source scope. Expose only the bounded attributed content and its handles.

Extend the **existing conflict decision**, not the write modes, to bind an exact candidate quote to a held historical source span. No durable history object, new fact target, fourth evidence mode or second reviewer is needed.

There is also a concrete plumbing requirement: `TurnExecution` currently passes the original `natural_source_messages` to the reviewer; captured executor `tool_evidence` is not supplied as review context. A discretionary implementation must explicitly carry the admitted history forward. The automatic first arm avoids that late-arrival complexity.  

**Minimum tests.**

A historical `H` reference used as a write-support handle must fail. An unknown or ambiguous historical quote must fail binding. A grounded `H` conflict plus an otherwise valid write must reject the entire attempt in either decision order.

Use the existing atomic worker tests as patterns: they distinguish uncommitted candidates, committed messages, rejected writes and post-review failures through database readback. They do not yet test historical evidence. 

**Semantic limitation, not a missing validator:** a reviewer could still cite a genuine current question as “direct” authority while incorrectly importing a value from history. Preventing `H` handles in writes does not prove that this laundering never happens. Test retrieval-only resurrection versus fresh explicit restatement as live complete-delta cases; do not add phrase rules to simulate semantic proof.

### 5. P0 — Admission must cover both serialized packets, not just excerpt text

**Source fact.** Natural context already has whole-record selection, mandatory-context checks and recipe-specific lifecycle withholding. Reviewer preflight and execution share a request builder. However, the executor appends assistant/tool messages and then checks the serialized continuation; it does **not** implement a rolling eviction policy for optional history.   

**Counterexample.** A window fits its text allowance, but its annotations, tool schema, tool-call arguments, retained continuation material and reviewer envelope push one actual request over its input limit.

**Minimum implementation.** Use one admission routine against the actual serialized generator and projected reviewer requests, using the repository’s existing estimator and output reserves. Admit fewer whole windows or report omission. Do not introduce an eviction framework merely to avoid a capacity failure.

For a discretionary extension, count all admitted historical material against the same attempt allowance. Repeated results must not obtain a fresh allowance; deduplicating previously supplied exchanges is sufficient. Every visible preview would need the same treatment—which is another reason to eliminate previews initially.

Preserve the recipe’s lifecycle-withholding rule. History must not sneak into a continuation after A/A0 has withheld prior narrative.

Historical roles should be **labels inside source data**, not executable replay of archived system instructions or tool calls.

**Falsification test.** Add Chinese text, JSON escaping, long annotations and repeated/overlapping windows near the boundary. Inspect the actual initial request, continuation and reviewer packet. Assert that mandatory material survives, `H` content and annotations agree, and the limit is not silently enlarged.

The existing context tests already exercise whole-record admission and A/A0 withholding boundaries; extend those tests rather than create a parallel capacity harness. 

### 6. P0 — The generic tool exception wrapper conflicts with the proposed fatal-error contract

**Source fact.** `_execute_tool()` converts every ordinary exception raised by a handler into an unsuccessful `ToolResult` with a provider-unavailable message. Consequently, a history handler’s scope/hash validation error, optimistic-lock error or deadline error can be presented as optional unavailability. Existing executor tests deliberately cover ordinary provider failure and failed argument validation, but these are different paths.  

**Minimum correction.** Expected history unavailability should be converted to a nonfatal result at the reader boundary. Structural integrity errors, generation conflicts and deadline/cancellation outcomes must retain their existing fatal meaning through the executor.

This needs a small explicit distinction—not a configurable retry/fallback framework. Preserve ownership: `AttemptController` owns the attempt deadline and cancellation/lease monitoring; the worker owns the configured retry sequence. The history reader should own neither.  

**Falsification test.** Under `retry_count=0`, inject ordinary read unavailability, scope/hash failure, generation conflict and timeout separately. Only ordinary unavailability should permit an existing-context answer. Fatal cases must not trigger another generation attempt, a repair reviewer, or an assistant/memory commit.

This is an actual integration trap in the inspected code, not production-scale hardening.

## Ranking feasibility: feasible to measure, but do not inherit the fact recipe unchanged

The plan correctly separates ranking selection from retrieval-trigger comparison. Keep that separation.

There is a repository-specific detail to amend: `embeddings.py` defines a fact-oriented identity with `document_format="typed-fact-lines-v1"`, a query instruction requesting durable user facts, and a fact-retrieval distance threshold. Reusing the embedding **route and model artifact** is sensible; treating these fact-specific retrieval semantics as an already validated transcript recipe is not. 

The minimum ranking probe needs only a bounded corpus, one literal matcher and one semantic scorer. Batch-embed the frozen transcript windows through the existing route, retain them in probe-local memory, and record a small recipe identity covering source hashes, document formatting, query formatting, model/artifact identity and dimensions. Do not mix those results into stored fact embeddings or silently change the existing fact-space identity.

Do not copy the fact threshold without testing it. For initial feasibility, retaining scores and source-hit ranks is more informative than pretending an inherited threshold means “no relevant history.”

Separate **corpus coverage failure** from **ranking failure**: a needed exchange outside the declared bounded corpus cannot be recovered by a better ranker. Also separate ranking-selection fixtures from scored dialogue cases; otherwise choosing the ranker on the eventual answers contaminates the comparison.

A useful Mandarin contrast is an earlier discussion about anxiety before an interview followed by a later paraphrase such as “上次让我紧张的那件事后来解决了”. Include a newer unrelated distractor and an assistant suggestion that the user never endorsed. This tests semantic retrieval and attribution without a production index.

**No production indexing, backfill or permanent transcript-vector schema is required to measure this bounded question.**

## The three-arm comparison: sound for strategy selection, excessive for the first decision

The plan already controls several major problems: equivalent independent initial state, chronological execution, one fixed ranking implementation, shared maximum history allowance, no rerolls, and separate retrieval/dialogue scoring. These are strengths, not omissions. 

However, automatic versus discretionary retrieval is an **end-to-end strategy comparison**, not a clean experiment on trigger timing. The arms can differ in query wording, information available when forming that query, selected passages, tool instructions, round trips and remaining context capacity. The proposal acknowledges different passages; the conclusion must acknowledge the other differences too.

### Smallest useful sequence

**First: baseline versus automatic recall.** Use one deterministic query construction from the current message and admitted local context, one selected ranker, one bounded return and the same `H`-capable reviewer policy in both arms—the baseline receives empty history. This avoids confounding a reviewer-policy change with retrieval itself.

For the first paired measurements, independently seed the **same historical prefix before each target turn**. A long chronological rollout can also be valuable, but once earlier arm outputs and writes diverge, later differences are trajectory effects rather than an isolated retrieval delta.

**Only then: discretionary recall, when the remaining decision requires it.** Expose one combined operation. A one-retrieval-per-attempt probe is initially enough to test whether model discretion reduces inappropriate callbacks or improves query selection. It also avoids implementing iterative search refinement before proving its necessity.

Two operations become justified only when observations show that a small result list frequently lets the model select a materially better window than a bounded combined return. With the current requirement that previews themselves carry attribution, annotations and reviewer visibility, the “cheap preview” is already much of an evidence packet.

### Specific leakage and fairness checks

Future exclusion must cover **facts, lifecycle descriptors, summaries and query construction**, not just transcript messages. A target-time corpus is still contaminated if its current fact descriptor reflects a correction from a later fixture turn.

A shared history allowance also does not by itself equalize capacity. Record actual serialized generator/reviewer sizes, tool-schema overhead, retained local evidence and any omissions. Do not enlarge the discretionary arm’s packet limits to accommodate its extra protocol material, and do not artificially pad the baseline or equalize request counts.

Finally, distinguish “relevant source supplied but ignored,” “wrong source retrieved,” “no discretionary call,” “reviewer veto,” and “setup/capacity failure.” A single aggregate success score would obscure the next smallest correction.

## Baseline prerequisite: retain its diagnostic value, narrow its blocking scope

The short native fact-only sequence is useful before making claims about **end-to-end improvement**. It can reveal that a proposed recall comparison is actually measuring reviewer truncation, invalid lifecycle operations or failed setup. The plan appropriately refuses to treat reviewer-only replay success as a qualified default. 

But I would **not block the reader, PostgreSQL isolation tests or ranking feasibility on a flawless live baseline**. Those can produce useful results independently.

The narrower gate should be:

> Before scoring committed dialogue outcomes, establish a traceable native control under the exact frozen evaluation binding, and disclose its failures. Before that, source-integrity and retrieval experiments may proceed without claiming dialogue quality.

Do not turn “baseline prerequisite” into “first solve general factual extraction.” Equally, failed candidate-only runs must not be relabeled as successful product outcomes.

## Keep, simplify, defer

| Keep | Simplify now | Defer |
|---|---|---|
| Existing repeatable-read state load and generation fencing | One cohesive reader; one combined recall operation | Separate search-preview/read protocol |
| Root-scoped transcript isolation; archived and ordinary-version eligibility | Baseline versus automatic recall first | Discretionary and iterative retrieval until needed |
| Whole exchanges and linked lifecycle annotations | One shared admission path and request-local `H` map | Persistent transcript indexes and backfill |
| One reviewer; exact binding; atomic conflict rejection | Extend only the existing conflict branch for `H` | New write modes, episodes, notes or semantic linkage systems |
| Immutable evaluation binding and observational receipts | Short native control as a scoring prerequisite | Production defaults and release promotion |

## Execution-dependent unknowns

Inspection cannot establish whether the bounded corpus will contain the needed sources, whether transcript embeddings retrieve Mandarin paraphrases well, whether annotations are sufficient for natural temporal interpretation, or whether the reviewer improves net outcomes rather than adding false vetoes and output pressure.

Likewise, the PostgreSQL tests I inspected are **test definitions**, several explicitly requiring a separately supplied disposable database. They are not evidence that these tests ran at this revision or that the proposed history behavior passes them. Existing cancellation and commit-readback tests provide useful patterns, not historical-recall qualification.  

### Paths inspected

All at the pinned commit:

- **Authority:** `docs/plans/natural-history-recall.md`, `docs/product-contract.md`, `docs/adr/README.md`, and ADRs `0035-compact-natural-review-and-observational-dispatch.md` and `0036-discretionary-curated-tools-and-structured-requirements.md`.
- **Runtime**, under `services/ade-api/src/ade_api/features/agent_runtime/`: the nine requested files; additionally `turn_memory_snapshot.py`, `natural_memory_policy.py`, `embeddings.py`, `worker.py`, `worker_control.py` and `worker_finalization.py`. Inspection of the large files focused on their relevant execution, table-definition and helper sections.
- **Tests**, under `services/ade-api/tests/agent_runtime/`: `test_natural_context.py`, `test_natural_memory_reviewer.py`, selected sections of `test_executor.py`, `test_natural_memory_contract_gaps.py`, `persistence/test_postgres_natural_worker.py` and `persistence/test_postgres_natural_worker_fencing.py`. I did not treat historical/red-contract tests as authority over the amended ADRs.

**Bottom line:** build the bounded reader and a single automatically admitted historical packet first. Keep `H` as a narrow, structurally bound conflict reference. Spend implementation complexity on isolation, evidence consistency, capacity and failure propagation—not on a two-step retrieval interface or three competing runtime paths before historical context has demonstrated value. **The stale policy-fingerprint release gate remains unwaived.**