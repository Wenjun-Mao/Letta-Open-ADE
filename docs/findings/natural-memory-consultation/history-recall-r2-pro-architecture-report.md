## Verdict

**Conditional go for the bounded automatic-recall probe. Revision 2 has the right scope and is substantially ready; I would close one small deadline-ownership gap before runtime integration, not send it through another architecture redesign.**

Proceeding with the reader, snapshot tests and ranking-feasibility work does **not** need to wait for general memory-quality qualification. Before H3, explicitly bind the **new finalization source-validation read** to a deadline: the existing attempt timeout does not currently cover `commit_success()`. That is the one remaining implementation-contract gap I would treat as blocking integration.

The major earlier concerns are now specified adequately: one coherent snapshot, source-relative lifecycle annotations, a matched empty-history control, a distinct transcript embedding recipe, separate read-only `H` grounding, and bounded purge checks. These need implementation tests—not another mechanism or another reviewer. The plan itself correctly labels them as proposed contracts rather than implemented guarantees. 

**Inspection:** GitHub access succeeded at **`8e298881e4165128c5a680a0b02c1789c894d8ff`**. I inspected the requested runtime paths and selected relevant tests, then read the prior assessment to check closure. I did not substitute `main`, execute tests, call providers, or access databases, services or private captures. The path inventory appears below.

## Minimum implementation shape

The smallest coherent implementation remains:

```text
Accepted run
  ↓
Existing load_turn_state() transaction
  ├─ mandatory local state and accepted subject generation
  └─ bounded eligible exchanges + source-relative annotations
  ↓ transaction closes
Frozen transcript ranker
  ↓
Existing base context, then one optional-history admission pass
  ↓
One frozen H packet, separate from writable U/A/F/E bindings
  ↓
Source authorization → generation and any existing continuations
  ↓
Source authorization → existing single reviewer
  ↓
Deadline-bounded source check → existing atomic finalization
```

`load_turn_state()` already uses a short repeatable-read, read-only transaction and checks the accepted subject-memory generation. The proposed reader fits inside that connection; no snapshot service or global commit counter is needed. 

Likewise, the existing finalizer already owns the terminal transaction and checks cancellation, lease ownership, conversation version and subject generation. Keep those responsibilities there. Historical evidence should arrive as a small held-source collection, not as new writable provenance or a second transaction coordinator. 

## 1. Remaining integration blocker: finalization does not inherit the attempt timeout

**Exact references:** plan §5 and H3; `worker_control.py::AttemptController.execute_attempt`; `worker.py::_process_claim`; `worker_finalization.py::RunFinalizer.commit_success`.

**Source fact.** `execute_attempt()` creates an absolute monotonic deadline and monitors the execution task against the attempt timeout. It returns the result after that task finishes. The worker subsequently calls `commit_success()` **outside** that monitored execution and outside `execute_with_retries()`. The finalizer currently receives no deadline.  

**Consequence.** Adding an awaited source-existence query inside finalization does not automatically satisfy the plan’s statement that timeout uses the existing attempt deadline. A stalled new query would not be bounded by that timeout. This is a source-derived integration risk, not an observed historical-recall failure.

**Minimum correction.** Carry the successful attempt’s absolute deadline to the new finalization validation step and bound that read by the remaining time. An expired or failed required check must prevent the success transaction from committing; it must not become optional unavailability.

Do **not** move all of `commit_success()` into the generation retry loop. That would expand the change and complicate the existing distinction between a failed pre-commit operation and a lost acknowledgment after a successful commit.

**Minimal falsification test.** Use a fake provider producing a valid reply and `decisions: []`. Block the finalization history check until the remaining deadline expires. Assert no assistant message or new revision commits, no second generation/reviewer dispatch occurs, and the outcome is not recorded as a successful optional-read fallback. Retain the existing post-commit acknowledgment-loss test, which checks that an already committed result remains authoritative. 

This can be closed in H1/H3’s implementation contract. It does not justify blocking H2.

## 2. Snapshot and scope: the contract is sufficient; preserve it literally

**Exact references:** plan §1/H2; `turn_memory_snapshot.py::load_turn_state`; the definition-version, conversation, message and run tables in `persistence/metadata.py`.

Revision 2 correctly distinguishes three things that should not be collapsed:

**Transcript ownership** is workspace + subject + purpose + character root. **Shared facts** remain subject-scoped. **Snapshot membership** is successful exchanges visible to the state-load transaction, not messages whose timestamps happen to be earlier.

The schema supports the intended root join: a conversation identifies its immutable definition version, and that version identifies its definition root. There is no reason to compare persona text, require identical versions, restore an archived conversation, or restrict shared facts to one character. 

**Keep the already-specified PostgreSQL test**, with one useful detail: the transaction that commits after capture should contain a completed exchange with **no fact mutation**. That ensures the test proves frozen transcript membership rather than accidentally relying on subject-generation changes to reject the attempt.

Also verify that changing a later fixture turn cannot change any earlier target’s facts, annotations, summaries or ranking inputs. Revision 2 explicitly includes those inputs in target-time isolation; this is no longer a missing contract. 

**Small implementation precaution:** ordinary optional-history failure must not cause a second `load_turn_state()` that silently substitutes a newer local snapshot. Materialize the mandatory state before the optional history stage, or otherwise preserve it across the chosen recoverable-failure boundary. The minimum test compares the returned mandatory state before and after an injected optional-read failure.

**Assessment:** no new snapshot mechanism or plan blocker.

## 3. Source-relative annotations: keep the meaning, avoid a graph framework

**Exact references:** plan §2/H2; `persistence/memory_source_read.py::list_revision_sources`; revision/source/predecessor tables; `memory_removals.py`.

The proposed source-relative envelope is justified. The removal implementation creates a `forget` revision with an `action_id`, null value and predecessor link, without requiring message evidence. Therefore, “read the latest revision’s sources” really would miss the relationship between an old quoted assertion and its later operator removal. 

Revision 2 also fixes the subtler case:

```text
Original coffee report
    → correction/invalidation
    → later coffee assertion
```

A matching latest value must not erase the intervening dispute. The plan now preserves transitions relative to the original source rather than supplying only a latest-status label. That is a necessary distinction, not speculative memory architecture. 

**Simplify the representation.** A bounded collection of revision records and predecessor edges is enough. Do not enumerate every possible path as a separately rendered timeline or introduce a reusable graph service. Deduplicate shared nodes, retain the necessary edges, and omit the optional window when its complete required envelope exceeds the frozen bound.

The envelope must distinguish a source’s authority role. A user antecedent or assistant referent linked to a revision does not make every sentence in that exchange an independently asserted fact. The existing source reader already enforces distinctions among those roles. 

**Minimal falsification tests.** One fixture can cover most of this: an exchange containing two claims, only one subsequently corrected; a later return to the original value; and a separate source-less removal variant. Assert that annotations apply to the linked claim, preserve the intervening transition, and do not expose forgotten revision values. A small branching fixture should verify preservation of recorded edges or explicit whole-window omission—not invented linearization.

Unlinked corrections remain an empirical retrieval/interpretation limitation. They are not permission to add semantic-linking rules.

## 4. `H` is appropriately narrow, but finalization must check it even when there are no writes

**Exact references:** plan §4/H3; `natural_memory_binding.py`; `natural_memory_review.py::NaturalConflict`; `natural_memory_policy.py`; `natural_memory_commit.py::revalidate_bound_natural_review`.

**Source fact.** Current write-support handles are `U/A`, and their binding uses conversation-local sequence comparisons. Current conflict references are `F/E`. A distinct `H` collection is therefore the smallest safe way to introduce cross-chat reply evidence without making it writable support.  

Keep the proposed extension confined to the existing conflict decision. No new write mode, stored history object, fact type or second reviewer is necessary.

**Important implementation gate already implied by §5:** historical-source validation must be independent of `review.operations`.

The existing commit revalidator loops over write operations and their sources; `commit_natural_memory_review()` returns immediately for an empty operation set. Neither is an appropriate place to hide the only check of admitted history. A perfectly ordinary successful recall is expected to have no memory mutation. 

**Minimum correction in the implementation sketch:** retain admitted historical identities separately in the attempt result and check them unconditionally when nonempty, before success persistence, regardless of reviewer writes.

**Minimal falsification test.** Produce a history-dependent answer with `decisions: []`, purge its admitted source after review but before finalization, and assert rejection. This catches an implementation that passes all mutation-source tests while neglecting read-only evidence.

The proposed acknowledgment/restatement contrasts are also worth keeping. The binder can enforce that `H1` cannot appear as `U1` support; it cannot prove that a real current quote semantically authorizes the proposed value. The current policy deliberately assigns that interpretation to the reviewer. Existing tests likewise distinguish structural acceptance from model judgment.  

Accordingly, test the full sequence—historical quotation, acknowledgment, explicit current restatement—and inspect every resulting delta. Do not introduce a ban on short affirmations or on later legitimate writes about a formerly removed topic.

## 5. Deferring the tool-wrapper correction is safe—but only outside the authorization path

**Exact references:** plan §5; `executor.py::ConversationExecutor.execute` and `_execute_tool`; `natural_memory_reviewer.py::NaturalMemoryReviewer.review`.

**Yes, the deferral is appropriate for automatic-only recall.** `_execute_tool()` catches ordinary handler exceptions and converts them into unsuccessful provider-unavailable results. An automatic reader called before generation does not need to enter that wrapper. Argument validation is outside the handler catch, and it would be inaccurate to claim that the wrapper universally swallows cancellation. 

However, automatic-only does **not** mean executor changes can be omitted entirely. The fixed historical packet can remain in subsequent generation requests after an existing tool call. Each such dispatch needs the planned fresh authorization check.

**Minimum implementation:** an awaited, fatal pre-dispatch guard in the executor’s request loop, plus the corresponding check before reviewer dispatch. Reuse the same checker; do not make it a tool or a new service.

Do not overload observation callbacks for this. The reviewer explicitly ignores `observe_request` exceptions, and its existing test requires capture failure not to veto success. Required evidence authorization has the opposite failure contract.  

**Minimal falsification test.** Admit history, let generation request an existing tool, then make source loss visible before the continuation. Assert that the continuation is not dispatched and no reply commits. Run the same fault before review. Separately inject an observation failure and verify that it does not change an otherwise valid outcome.

For source-bearing **corpus embedding requests**, apply §5’s outbound-packet authorization rule too. That does not mean every embedded candidate becomes a finalization dependency: finalization should depend on the admitted response evidence, not every unused ranking candidate.

The bounded race guarantee is sufficient. Do not add long-held source locks to promise that a purge occurring after authorization can retroactively invalidate an already sent request.

## 6. Capacity and matched controls: test actual packets, not merely matching settings

**Exact references:** plan §4/H4; `natural_context.py`; `turn_execution.py`; generator and reviewer request builders.

The plan correctly protects the control’s local/fact context from displacement and forbids bypassing A/A0 narrative withholding. Existing context tests provide a useful foundation for whole-record admission and withholding behavior.  

Two implementation details deserve explicit tests.

**First, freeze one canonical admitted `H` packet.** Render it consistently for generation and review, with the same text, roles and annotations. Do not independently renumber handles or reconstruct annotations after generation.

**Second, identical seeded prefixes do not alone guarantee identical base context.** `TurnExecution` can perform target-turn compaction for A/A0, producing another model-generated input before the historical intervention. Variant B skips that compaction path. 

The smallest paired experiment should therefore use one fixed recipe and targets that do not require fresh compaction, or use already frozen equivalent summaries. Choosing B for this probe would be a simple experimental choice, not a production-default decision. There is no need for a new summary-sharing mechanism.

**Minimal falsification test.** Compare the two initial requests after removing only the `H` field and consistently normalizing fixture identities. Check local-message selection, fact values/order, instructions, reviewer policy and configured limits. Add a history window that fits raw text but exceeds the serialized reviewer envelope; it must be omitted before exposure rather than displacing control context.

Preserve the existing actual-request checks on continuations. The executor includes retained assistant/tool messages in its serialized limit check; its tests also demonstrate retained provider reasoning material in a continuation. That overhead cannot be ignored merely because the historical packet is fixed.  

Finally, reviewer preflight currently projects the candidate with `"x" * (4 * candidate_reply_reserve)`. That is a projection, not proof that every actual candidate serializes within the reserve. Keep the final actual reviewer check and count an overflow as a capacity failure. Do not strip already exposed evidence or add an eviction/repair subsystem to conceal it. 

## Ranking and evaluation: adequate for feasibility, without additional arms

### The transcript recipe protects existing fact embeddings

Revision 2 now explicitly avoids reusing the fact query instruction, fact document format, fact vector table and fact threshold. That matches the repository: `QWEN_FACT_SPACE`, `qwen_query_text()` and the automatic distance threshold are fact-specific, whereas `EmbeddingClient` can be reused as transport. 

A small recipe record and probe-local vectors are sufficient. No permanent transcript schema or production index is required.

**Minimum regression test:** run transcript preparation against a fake embedding transport and verify that fact-query payloads, fact-space identity and existing fact-vector rows remain unchanged. A changed transcript recipe must invalidate its own vectors, not rebind the fact space.

### Holdouts and paired prefixes are now specified correctly

Keep the separation between ranking-development fixtures and scored dialogue cases. Minimum sufficient evidence sets should be **scoring expectations**, never hidden inputs to window selection.

The matched comparison estimates the effect of **adding an automatically retrieved, annotated packet under a common reviewer policy**. It does not isolate the contribution of raw text versus annotations, and it does not establish the best trigger. Neither narrower attribution is necessary to answer this probe’s question.

Paired target turns and trajectory tests should remain separate. Revision 2 explicitly does this and preserves failed dependencies as unrun continuations. No third arm or artificial request-count equalization is needed. 

### Reuse the harness, not historical mutation-only scoring

There is one concrete reuse trap in `natural_live_results.py`: `mutation_state_matches()` rejects results without committed revision IDs. That is suitable for its historical mutation cases, not for successful read-only recall. The same module’s `verify_attempt_safety()` is closer to the structural check needed here. 

**Minimal scoring test:** a committed, grounded recall with zero revisions can succeed; the same answer with an unintended extra preference addition must fail complete-delta scoring.

The proposed stage accounting is sufficient: corpus, retrieval, admission, candidate, review, and delivery/persistence. Keep candidate-only quality distinct from delivered success, false reviewer veto distinct from retrieval failure, and missing evidence distinct from a verified outcome. Do not add another accounting service. 

## Keep / simplify / defer

| Keep | Simplify | Defer |
|---|---|---|
| Coherent snapshot, character-root transcript boundary, subject-scoped facts and archived eligibility | One bounded reader using the existing connection | Production indexing, backfill and freshness infrastructure |
| Source-relative lifecycle annotations and narrow `H` conflicts | Bounded records/edges, not a generic graph or generated timeline | Semantic linkage, new fact types, episodes and writable notes |
| Shared admission, fatal authorization checks and atomic finalization | One fixed recipe and matched base packet | Discretionary retrieval and preview/read protocols |
| Separate ranking holdouts, paired targets and short trajectories | Existing harness with complete-delta and no-write scoring | Extra reviewers, additional experimental arms and general quality certification |

The short native control is now a useful scoring prerequisite rather than an unnecessarily broad blocker. Reader tests and ranking feasibility can proceed independently; delivered-dialogue claims still need a traceable control under the exact binding. That balance should remain unchanged.

## Inspection and evidence limits

All inspected content was pinned to **`8e298881e4165128c5a680a0b02c1789c894d8ff`**.

**Documents:** `docs/plans/natural-history-recall.md`, `docs/product-contract.md`, `docs/adr/README.md`, ADRs 0035/0036, and—after the independent code assessment—`docs/findings/natural-memory-consultation/history-recall-review-assessment.md`.

**Requested runtime files**, under `services/ade-api/src/ade_api/features/agent_runtime/`: `turn_memory_snapshot.py`, `natural_context.py`, relevant execution sections of `turn_execution.py` and `executor.py`, `embeddings.py`, `natural_memory_binding.py`, `natural_memory_review.py`, `natural_memory_policy.py`, `natural_memory_reviewer.py`, the success-finalization path in `worker_finalization.py`, relevant table definitions in `persistence/metadata.py`, and `persistence/memory_source_read.py`.

**Additional paths:** `natural_memory_commit.py`; relevant sections of `memory_removals.py`, `worker_control.py` and `worker.py`; and `workflows/evals/character_memory_dev/natural_live_results.py`.

**Tests inspected:** selected relevant sections of `test_natural_context.py`, `test_natural_memory_policy.py` and `test_executor.py`; `test_natural_memory_reviewer.py`; and `persistence/test_postgres_natural_worker_fencing.py`.

The prior assessment’s claimed corrections are reflected in Revision 2, but that agreement is documentary closure, not experimental evidence. 

Whether ranking retrieves sufficient Mandarin evidence, annotations improve interpretation, `H` increases false vetoes, or recall adds worthwhile continuity remains execution-dependent. **My recommendation is to proceed with the bounded design, close the finalization deadline handoff before H3, and resist adding mechanisms to pre-solve those empirical questions. Release qualification and the stale policy-fingerprint gate remain untouched.**