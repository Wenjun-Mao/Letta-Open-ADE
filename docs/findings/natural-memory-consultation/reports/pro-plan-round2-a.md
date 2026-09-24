# Verdict: GO for bounded implementation, with four focused checkpoint requirements

**The revised plan closes the previous authorization blockers. I recommend authorizing checkpoints 1–5 without another architecture round or a competing plan.** The remaining findings are implementation requirements within those checkpoints—not reasons to introduce another memory system, concurrency mechanism, or evaluation framework.

The most important additional finding is a **source-visible lock-order mismatch** in the unchanged runtime. The other three concern interactions that the new implementation must handle correctly: removing staged effects after claim deferral, reporting uncertain commit outcomes, and avoiding duplicate results when supporting multiple index versions.

Neither context candidate is selected by this verdict. Live calls, product-policy acceptance, populated deployment, and release qualification remain separate decisions.

## Inspected revisions and access

| Scope                                                                                                                               | Exact revision                             |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Revised plan, design, all 22 scenarios, source map, plan-review assessment, both preserved plan reviews, required M3 plans and ADRs | `f786007f7d03b375ed0d9b36bf3c2ae0f9e947b6` |
| Runtime implementation and selected test sections                                                                                   | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |
| Previous-plan comparison anchor and target of the preserved reviews                                                                 | `1a3181c133b7404d6159dbb55468c0a53bb857bd` |

I followed the pinned implementation through admission, review preparation, memory commits, worker finalization, retrieval/schema, source readers, evaluation cleanup, UI, authentication, and request budgeting. Test inspection included finalization and PostgreSQL lifecycle specifications. GitHub’s comparisons showed documentation changes, not runtime implementation changes.

**All required public packet documents were accessible. Tests were read, not executed.** Local services, database state, credentials, ignored captures, and missing historical provider-request/response evidence remain unavailable. The assessment and preserved reports are evidence of their authors’ reviews, not substitutes for runtime results.

Below, **source fact** means directly visible in the pinned code. **Implementation risk** means a concrete way the proposed change could go wrong, not a reproduced failure of code that has not yet been written. P1 items must be resolved before their affected checkpoint closes; they do not require postponing the start of implementation.

# Prioritized material findings

## 1. P1 — Use one consistent lock order across admission and finalization

**Classification:** source-visible lock-order inconsistency; a possible deadlock follows from the code, but was not reproduced here.
**Affected checkpoints:** 2 and 3.

`RunService.accept_turn()` acquires the conversation row and then the memory-subject row. In contrast, `worker_finalization.py:_lock_conversation_and_subject()` chooses the order by comparing their IDs: when the subject ID sorts first, it locks the subject before the conversation. These are not a consistent global ordering.

### Counterexample

Choose a conversation ID that sorts after its subject ID.

A new admission transaction holds the conversation lock and waits for the subject. Concurrent finalization holds the subject lock and waits for the conversation. The admission path’s active-run check does not prevent this cycle: it runs **after** those locks are acquired.

The new memory-generation fence prevents stale mutations; it does not prevent this locking problem.

### Smallest sufficient correction

Establish one lock-order rule across the touched admission, finalization, operator-action, and cleanup paths. Do not sort IDs inside one helper while other callers use a different fixed ordering. Removing an unnecessary lock is also possible, but only while preserving the specified coherent acceptance and ownership checks.

Add a controlled two-connection regression with the problematic ID ordering and admission overlapping finalization. It should not require provider calls. Keep SQL locks away from provider computation and do not conceal a deadlock through an extra model attempt.

The inspected finalization tests cover lease fencing and safe failure reporting, but those mocked transactions do not establish freedom from this lock cycle.

**This is an implementation correction to the existing transaction boundary, not a reason to replace the single generation counter.**

## 2. P1 — Claim deferral must remove all dependent staged effects, not merely fact operations

**Classification:** new integration risk created by per-claim dispositions; not an existing demonstrated deferral bug.
**Affected checkpoints:** 2 and 3.

The revised contract appropriately allows one claim to be deferred or excluded while unrelated writes remain eligible. However, the baseline prepares new entities separately from fact operations:

`prepare_memory_review()` stages identity entities from the proposal collection, and `commit_memory_review()` inserts every `review.new_entities` entry before processing `review.operations`. That structure needs particular care when adding per-claim filtering.

### Counterexample

A review initially stages a new pet entity and associated facts, alongside an independent Toronto residence update. The pet claim is then deferred or excluded by the new claim-consistency/no-save outcome.

If implementation filters the fact-operation list but retains the original staged entity list, it can commit the pet’s identity metadata even though no pet assertion was authorized for saving.

The all-deferred variant is worse: there are zero surviving fact operations, but an entity is still inserted. Treating that result as a no-op would also violate the proposed “no-op does not advance generation” contract.

### Smallest sufficient correction

Construct the **final effective write set** after valid claim dispositions have been applied. Include entity creation in that write set, retain only staged entities justified by surviving operations, and generate/alignment-check embeddings against the finalized operations.

An empty effective write set must mean no new facts, entities, indexes, or generation advance. Do not “fix” an unwanted entity insertion merely by incrementing generation.

This does not authorize silently dropping malformed or invalid proposals. The distinction remains:

* An expressly permitted deferral/exclusion produces the specified no-write outcome.
* Invalid proposals and detected contradictions retain their declared failure behavior.

A mixed-case test and an all-deferred test are sufficient additions. They implement the plan’s existing semantics without adding a pending-claim store or another reviewer. The revised plan already requires staging, assertion-level no-save precedence, and observable per-claim outcomes; this closes their interaction with the existing commit structure.

## 3. P2 — Failure evidence must distinguish confirmed rollback from an unconfirmed outcome

**Classification:** failure-observation refinement; not a claim that the baseline corrupts successful runs.
**Affected checkpoints:** 2, 3 and 5, with evaluation consequences in 6.

The new failed-attempt capture requirement is substantially better. It now specifies selected inputs, candidate visible text, typed reviewer outcomes, absent stages, and rejected-candidate labeling without inserting rejected text into conversation or memory storage.

One distinction should be explicit in the tests: **an exception observed by a caller does not, by itself, prove that the transaction rolled back.**

### Counterexample

Inject a failure after the database commit succeeds but before its success reaches the caller—or fail the diagnostic-artifact write after successful database finalization.

The durable run, assistant message, memory revisions and generation may already be committed. An artifact writer that labels every caught finalization exception “uncommitted/undelivered” would report false evidence. An operator UI that automatically replaces the request with a fresh key could also turn outcome recovery into a new action.

The baseline already contains a useful protection: the worker routes finalization exceptions into `commit_failure()`, which rereads the run and returns without overwriting an already-terminal outcome. Preserve that behavior when adding diagnostic capture.

### Smallest sufficient correction

Make diagnostic and UI outcomes follow the authoritative run or action receipt, not merely the exception path.

When the outcome cannot yet be established, report it as **unconfirmed**, rather than asserting zero effects. Use readback or the original idempotency key to recover the outcome; do not refresh the generation, retarget records, or create a replacement request automatically.

Test failures before commit, immediately after commit, and during artifact retention. A confirmed rejection must still have zero assistant/memory effects. A committed result must not be relabeled as rejected. An unresolved outcome makes the evaluation cell unscorable and subject to the existing infrastructure-stop rules.

This needs no distributed transaction between files and PostgreSQL, and no new memory lifecycle state. It is a truthful observation rule around the existing atomic transaction and receipt mechanisms.

## 4. P2 — Compatible multi-version indexes need deduplication before the result limit

**Classification:** conditional integration risk in one permitted compatibility implementation.
**Affected checkpoints:** 2 and 4.

The revised populated-index requirement genuinely closes the earlier gap: it separates embedding-space identity from index/read-policy compatibility, requires old active records to remain selectable or be explicitly reindexed, and prohibits provider calls inside SQL migration.

There is one useful additional boundary test **if the reader supports multiple compatible index versions simultaneously**.

The baseline uniqueness constraint includes `retrieval_policy_version`, so the same fact/current revision can have an embedding row for each policy version. The current query limits joined embedding rows, not distinct facts. That is fine for its single-policy filter, but a naïve change to accept several versions can introduce duplicates before the limit.

### Counterexample

F1 has both an old and a new compatible index row for its current revision. F2 has one.

With a result limit of two, both F1 rows rank first. Deduplicating later in the context assembler produces only F1; F2 was already excluded. The resulting missed evidence could be incorrectly attributed to selective-context quality.

### Smallest sufficient correction

Choose one eligible representation per fact/current revision before applying the fact-result limit, or otherwise ensure the limit counts distinct eligible facts. A compatibility design that uses mutually exclusive format predicates may avoid the problem directly.

Add a populated fixture containing overlapping compatible indexes, a separate relevant fact, a terminal descriptor and a forgotten chain. Assert distinct-result coverage as well as eligibility.

This is not a demand for another ranking system. The simplest compatible read path that passes those tests is preferable. The existing PostgreSQL lifecycle test uses supplied proposals and synthetic vectors; it establishes a useful place to test filtering mechanics, not semantic retrieval quality.

# Closure assessment of the previous findings

**The material previous plan-review findings are addressed in the revised specification.** “Addressed” does not mean implemented, tested, or empirically successful.

The closure below is based on the revised plan itself, not merely the assessment’s recommendation to adopt the reviews.

| Previous finding                                                                                             | Disposition   | Why the correction is substantive                                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------ | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **A1/B1 — A/A0 could change raw-history coverage or reallocate summary space**                               | **Addressed** | The raw cutoff and nonsummary contents/order are fixed; A0 preserves the summary boundary and leaves its allocation unused. Paired-manifest assertions are explicit.                                               |
| **A1/B1 — A0/B was described too strongly as an admission-only contrast**                                    | **Addressed** | Both use the same eligible local pool. The plan now calls it a comparison of full-versus-selective, recent-first packages, including retrieval cost—not one Boolean’s isolated effect.                             |
| **A2/B2 — usefulness criteria and candidate eligibility were asymmetric**                                    | **Addressed** | A and B are selectable; A0 is diagnostic. Both selectable policies face the same useful-answer criteria and frozen envelope. Incomplete required coverage cannot produce a winner.                                 |
| **A2/B2 — supplied summaries could implicitly qualify production summarization**                             | **Addressed** | Actual compaction on both named summary arcs is required before accepting A. A0 evidence cannot qualify A merely because they share a prerequisite.                                                                |
| **A3/B3 — failed reviews lacked sufficient scoring evidence**                                                | **Addressed** | Failed synthetic attempts have explicit capture requirements, absent-stage labels, privacy boundaries and a false-veto test. Finding 3 above adds an outcome-recovery edge case, not a replacement capture design. |
| **B4 — preserved vectors could become invisible under a new read policy**                                    | **Addressed** | Compatibility is now an explicit populated-store requirement, separate from semantic vector-space identity. The precise compatible reader/reindex choice remains engineering work.                                 |
| **A4 — case-end timing did not make individual purges provenance-safe**                                      | **Addressed** | The campaign owns a disposable database; optional case cleanup must own a complete subject closure. Unsafe individual purges are refused, and surviving lineage/current pointers are tested.                       |
| **A5 and B’s integration notes — old-conversation writability was coupled to removal and old outcome types** | **Addressed** | Continuation, direct subject removal and reviewed correction are separate capabilities. Typed outcomes distinguish run mutations, operator receipts, deferrals and failures.                                       |
| **Cutover and replay wording could imply seamless continuation or current absence**                          | **Addressed** | New conversations inherit eligible saved facts, not old unsaved dialogue. Historical action receipts and current readback are explicitly distinct.                                                                 |
| **Generic history repair, broader transcript retrieval and continuity tables**                               | **Deferred**  | Their absence remains visible; the plan does not rely on them to pass its bounded target.                                                                                                                          |

I do not see a reason to reopen the already-settled preference representation, lifecycle reasons, source-role distinction, or operator-removal contract simply to obtain another round of agreement.

# Assessment of the revised comparisons and acceptance gate

## The comparison claims are now appropriately limited

The revised A/A0 recipe tests **supplied-summary presence with the other evidence fixed**. The A0/B recipe tests **different admission and selection packages without summaries**, using the same preselection local pool. It no longer claims to isolate every individual mechanism inside that package. Those are meaningful and executable distinctions.

The plan also makes the actual selectable configurations explicit. Evidence reuse requires identical serialized requests and relevant processing/commit behavior, and actual compaction remains required for summary-enabled acceptance. I would keep reuse opportunistic: when equivalence is not immediately demonstrable, execute the separately budgeted cell or report it unrun. Do not build an equivalence framework to save a few calls.

One consequence should remain clear: a mandatory pressure case can expose a limitation of A **deterministically**, before any model is called. When the rule withholds an essential antecedent, no amount of fluent generation makes the missing evidence present. That can legitimately count against A; it does not establish that B passes. The planned “neither passes” outcome remains important.

## Safe but unhelpful abstention no longer has an acceptance loophole

The plan now freezes answerability independently of what an assembler retains, applies positive useful-answer criteria to both candidates, counts failed/vetoed/unrun probes separately, and prohibits selecting a winner from incomplete required coverage. It also distinguishes ordinary response-quality failures from campaign-stopping boundary or infrastructure failures. This directly addresses the previous concern about choosing whichever policy avoids saying anything wrong.

The exact numerical operating envelope and executable request schedule still need to be frozen in checkpoint 1. **That is a legitimate checkpoint deliverable, not an unresolved architecture decision**, provided the values are fixed before observing model replies and cannot be retrospectively narrowed to rescue a candidate.

The proposed request ceilings remain ceilings—not evidence that the complete matrix fits. The existing ledger reserves before sending and retains failed/interrupted reservations, which is the right foundation. Its presence does not establish coverage of every new diagnostic path; the plan correctly requires that coverage before live approval.

# Other implementability conclusions

### Mutation and concurrency contracts are sufficiently determined

The single memory-generation fence now has a coherent meaning: capture at acceptance, build the matching snapshot, reject stale nonempty writes, distinguish already-running no-op behavior, and require deliberate fresh submission rather than secretly refreshing the fence. The cost—some harmless conflicts, including queued turns—is explicit.

The lock-order correction above is necessary precisely because a correct optimistic-concurrency rule and a correct locking discipline are separate obligations. It does not justify bringing back specialized semantic read sets or holding locks during model calls.

### Provenance-safe cleanup is no longer merely a delete-order promise

The revised ownership rule addresses the actual baseline hazard. The existing purge can remove source links and predecessor material associated with one conversation while another conversation keeps the shared subject. Waiting longer before calling it would not solve that. The revised exclusive-database/complete-subject approach, with refusal of unsafe individual purges, is the right level of correction.

Keep exclusive ownership explicit. `purpose=evaluation` alone does not authorize destroying every evaluation resource. There is no need for a generic graph-cleanup framework or a new production erasure operation.

### Operator actions and cutover are now coherent

The plan correctly distinguishes operator causation from a conversation run or user quotation. The baseline schema and source reader are message/run-oriented, so this remains real implementation work, not a renamed endpoint. Its ownership and source-role checks must survive through persistence and readback.

The revised UI capability split is also appropriate: direct removal is subject-level and does not require a runnable conversation; correction still requires a reviewed turn. The repository contains a real role-based authorization dependency to reuse. When authentication is disabled, its source deliberately grants the caller admin status; I did not verify how the deployed system is configured or exposed. An operator-origin label must therefore remain audit information, not authorization.

Requiring a new immutable binding for new semantics is a consequential but explicit cutover choice. The plan now honestly states the loss of unsaved conversational continuity at that transition rather than silently copying history. Saved-memory removal remains limited removal, not erasure of those historical messages.

### Rollback is appropriately separated from implementation correctness

The plan does not assume that additive SQL makes old binaries safe. It requires drained writers, matching application/database compatibility, tested recovery and an explicitly authorized recovery point/data-loss window. That is sufficient as a planning contract; actual restoration remains unverified.

# Authorization recommendation

**I recommend authorizing bounded implementation of checkpoints 1–5, with these four requirements included in their completion criteria:**

| Requirement                                                                                                          | Owning checkpoint |
| -------------------------------------------------------------------------------------------------------------------- | ----------------- |
| Consistent lock ordering and an admission-versus-finalization concurrency regression                                 | **2–3**           |
| Final effective-write-set construction that removes unused staged entities after permitted deferral/exclusion        | **2–3**           |
| Authoritative commit-outcome recovery, including acknowledgment/artifact failures without automatic fresh submission | **2–3, 5**        |
| Duplicate-safe result limiting when multiple compatible index versions are supported                                 | **2, 4**          |

These are small corrections and tests within already affected code. They do not require a new memory architecture, another reviewer, persistent clarification jobs, or another broad plan-review cycle.

**The remaining empirical questions are genuinely empirical:** which context policy delivers useful continuity, natural matching and endorsement accuracy, false-veto rates, terminal-state retrieval quality, actual compactor behavior, conflict frequency, capacity and cost. Static review cannot answer them, and the revised gate now allows them to disqualify either candidate.

The next step should be implementation and its offline checkpoint evidence—not further architectural expansion. Checkpoint 6’s live calls, subsequent policy selection, deployment, rollback execution and release approval remain separately authorized work.
