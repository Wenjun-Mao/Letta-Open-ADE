# Verdict: GO — revision 5 is ready for bounded implementation

**The amended plan now permits a small, coherent implementation. I found no remaining product-semantic decision that requires another planning cycle.** The preceding execution findings are addressed as explicit contracts and checkpoint obligations, rather than left to an implementer’s interpretation.

In particular, revision 5 clearly distinguishes optional request observations from mandatory persistence; binds semantic decisions once while retaining transactional revalidation; defines counters as observed ADE dispatch attempts; and requires complete memory-delta checks. It also closes the earlier authority ambiguities around inherited restrictions, factual assent versus removal permission, and conflicts grounded in existing facts without an invented write.

**The remaining risks are implementation risks in existing code—not reasons to revise the architecture again.** I rank those below as mandatory execution gates. They should be demonstrated in the implementation diff and tests, not treated as findings that revision 5 failed to address.

## Inspected revision and evidence boundary

**Exact commit inspected: `a38d3e4e778899fab2763853c04cfd52bdb0ca2c`.**

I read the full revision-5 plan, the compact-plan assessment and relevant portions of both linked reports. I inspected the pinned tracing, worker events/finalization, timeout controller, budget implementation/settings, worker compatibility, reviewer schema/binder, provenance reader, diagnostic transport/result checks, and relevant tracing tests.

The requested public reference was accessible. **I did not execute tests, access private captures or databases, call providers, or substitute `main`.** Published diagnostic outcomes remain maintainer-reported evidence. The inspected code still contains the old implementation paths; the plan’s proposed changes are not runtime results.

Runtime paths below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.

# Ranked mandatory execution findings

## 1. Preserve authoritative transactions while making observation genuinely optional

**Priority: P1. Checkpoints 2 and 4. Contract addressed; implementation still required.**

The current code has the precise hazards revision 5 now names:

* `TracedRouterTransport._invoke()` invokes observation hooks around the underlying call without protecting its outcome from those hooks.
* `NaturalLiveTransport._send()` performs capture writes in `finally`, where an error can replace a successful return or the original exception.
* `RunFinalizer.commit_success()` calls `append_success_events()` inside the transaction that commits memory, the assistant message and terminal success. Failure/cancellation finalization can similarly persist request traces inside its transaction.

Revision 5 correctly requires optional writes to be outside or isolated from that authoritative transaction. **Catching an exception around the entire finalizer would not implement this requirement.** Neither would treating all event persistence as optional merely because request observations use events.

### Decisive counterexample

A valid reviewed turn reaches finalization.

If its optional request-observation insert fails, the product outcome must not be changed merely to preserve a count. If its required source or revision insert fails, the turn must not claim a successful commit.

The two failures may both be database errors, but they have different authority.

### Observable exit criterion

Fault injection must establish both directions:

**Optional observation failure:** the original transport result or exception survives; no retry is triggered by capture failure; a successful authoritative commit remains successful; counts/evidence are marked incomplete where necessary.

**Required persistence failure:** no partial assistant/memory success is reported; transaction errors are not swallowed; an uncertain commit acknowledgment remains unconfirmed until authoritative readback resolves it.

Also preserve domain-event causation without requiring an optional transport event to exist. A missing request observation must not make a required tool, revision or run-outcome event impossible to persist.

This needs a small separation of paths, not an observability service or a new durable queue.

## 2. Canonicalize dispatch observation end to end—not merely the event names

**Priority: P1. Checkpoint 2. Contract addressed; implementation still required.**

The current success path reconstructs `model.request.started` and `model.response.completed` events through `_append_model_rounds()` and `_append_conversation_trace()`. Those do not share the UUID-bearing path in `AttemptTrace`. Its successful-run summary also counts generation requests, not all embedding requests. Failure handling uses the actual attempt trace.

Revision 5 explicitly replaces this inconsistency. The important implementation distinction is:

> **One producer can have several readers or retained copies. Several producers cannot independently invent identities for the same dispatch.**

### Decisive counterexample

A run performs a query embedding, conversation generation, review and write-embedding batch. Its trace is retained in an artifact and represented in API-visible events.

That is **four dispatches**, not eight. A provider response ID is not an adequate deduplication key, especially for failures. A replay of the terminal run result is also not another dispatch.

### Observable exit criterion

Use a fake transport with a known invocation sequence and verify:

* Every actual model dispatch receives one canonical local ID.
* Event/artifact copies retain that ID.
* Setup, retrieval embeddings, write embeddings, compaction, tool continuations and explicit retry attempts are included.
* Catalog discovery remains separate.
* A pre-dispatch rejection, such as a route-validation failure, is not counted as a completed outbound attempt.
* Existing summary fields are either derived from the canonical observations or clearly retain their narrower historical meaning; they are not added again to the same totals.

The revised definitions are honest: transport completion is not semantic acceptance, a timeout may have reached the provider, missing terminal observations produce unresolved starts, and missing starts make the total incomplete. **Do not strengthen this into a claim about provider receipt or billing.** Revision 5 already states these limits adequately.

## 3. Carry trusted bindings through finalization and migrate every authority consumer

**Priority: P1. Checkpoints 1 and 3. Contract addressed; implementation still required.**

The new contract is coherent: the model selects a request-local handle; ADE resolves it against the held snapshot; finalization checks the resulting trusted record rather than interpreting the handle again.

The current finalizer instead invokes `prepare_natural_memory_review()` using freshly read facts/entities and compares the resulting proposals. That is a concrete path to replace—not retain beneath a new compact parser.

### Decisive counterexample

The reviewer selected `F1` from its original snapshot. Before finalization, the database changes or a fresh list has a different ordering.

The system must reject a stale snapshot where required. It must **never reinterpret `F1` as whichever record now occupies the corresponding position**, or allocate different new-entity identities when preparing the decision again.

### Observable exit criterion

Preparation produces one trusted operation set, including the exact current authority anchor and supporting sources. Finalization retains generation/version, ownership, source-integrity, cancellation and lease checks, but does not rebuild semantic meaning.

The migration must also reach all readback and diagnostic consumers. Currently, `memory_source_read.py` and `verify_attempt_safety()` recognize only `user_assertion` and `user_endorsement` as user authority. The existing binder also cannot represent an earlier user antecedent as support-only evidence.

Required contrasts are now sufficiently specified:

| Case                                                     | Required distinction                                                         |
| -------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Earlier-user assertion plus current resolution           | The current answer is authority; the antecedent supplies bounded support.    |
| Uncertain or no-save antecedent followed by a name       | Resolution does not erase the restriction.                                   |
| “Yes” to factual ending versus “Yes” to proposed removal | Only the specific authorized operation is eligible.                          |
| Sources in a different order                             | Authority cannot change.                                                     |
| Existing fact contradicts the candidate reply            | Conflict can be reported without a fabricated write.                         |
| Historical revision predating the new contract           | Remains readable as recorded, without retroactive endorsement certification. |

These are ordinary typed combinations and validation functions. They do not require a persistent handle registry, another semantic judge or a general provenance framework. The plan explicitly recognizes that binding guarantees are narrower than semantic accuracy.

## 4. Replace the diagnostic’s old success assumptions, not just its input schema

**Priority: P2. Checkpoints 1, 4 and 5. Contract addressed; implementation still required.**

The existing diagnostic has two relevant assumptions:

`capture_scope()` expects every locally reserved request to have a **completed** capture. That does not represent failed or cancelled dispatches as legitimate observations.

`mutation_state_matches()` often looks for the expected record rather than establishing that the complete write set is permitted. The coffee case, for example, can establish the expected scoped addition without excluding every unrelated mutation.

Revision 5 now explicitly requires complete permitted deltas and separates unsuccessful product outcomes from missing observations. That closes the planning gap.

### Decisive counterexample

The reviewer saves the correct morning-coffee preference and an unrelated erroneous fact. Finding the coffee record must not pass the case.

Likewise, a rejected write followed by no committed changes can be a correct negative-test result—but not a successful positive-update result.

### Observable exit criterion

Check the permitted new revisions, fact/entity identity changes, unchanged scopes, tombstones and generation changes—not just final expected values. A net-zero final projection must not hide extra revisions.

Keep semantic-equivalent wording pending explicit review where required. Preserve rejected and unrun cases separately. A structurally valid empty decision is not evidence that a required update succeeded.

The live diagnostic can legitimately establish improved reconciliation before testing broader recall. Revision 5 correctly makes later-recall probes optional while prohibiting write-only evidence from being called continuity qualification.

# Concrete deletions

**Delete the spending subsystem and its active dependencies; do not replace them with disabled aliases or “expected usage” checks that still block sends.**

| Location                                             | Concrete removal                                                                                                                           | What must survive                                                                        |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| `request_budget.py`                                  | `RequestLedger`, `BudgetedTransport`, reservations, caps, `budget_identity()`, ledger bindings and `exhausted()`                           | Ordinary transport construction, credential resolution and applicable timeout behavior   |
| `platform/settings.py`                               | The four `agent_runtime_budget_*` fields, `_validate_runtime_budget()`, associated validator arguments and environment wiring              | Authentication, runtime, timeout, retry and context settings                             |
| `worker_health.py`                                   | Budget contribution to `worker_compatibility_fingerprint()` and `budget_identity` dependency                                               | Worker freshness, migration, runtime-mode and source/build compatibility                 |
| `worker_events.py`                                   | Reconstructed transport-event loops in `_append_model_rounds()` and the transport portion of `_append_conversation_trace()`                | Required message, revision, summary, tool and terminal domain events                     |
| `natural_live_transport.py`                          | `RequestScope` spending limits, `reserve_local()`, ledger snapshots and schedule-exhaustion gates                                          | Route validation, case attribution, redaction and safe capture paths                     |
| `natural_live_contract.py` and active campaign setup | Active 96/160/reservation assertions and ledger-dependent scheduling                                                                       | Fixed semantic cases, source identity, explicit retry/timeout rules and behavioral stops |
| Old reviewer wire contract                           | Parallel proposal/disposition arrays, joining IDs, model-emitted subject selectors, versions, source-role enums and redundant quote fields | Typed lifecycle meanings and historical data readback                                    |

These targets are present in the pinned code.

Remove reservation, cap-exhaustion and budget-readiness tests with those features. Preserve or relocate tests for transport construction, timeout behavior, explicit retries, route validation and dispatch observation.

**Do not mechanically delete everything named “budget.”** Context/output allowances and finite execution loops remain required controls. Likewise, removing ledger-specific source bindings is not permission to remove independent evidence fingerprints or deployment compatibility checks.

Historical ledgers and frozen files can remain byte-identical without remaining executable authorities for the new diagnostic.

# Timeout ownership is now explicit enough

I do not see a remaining timeout-design blocker.

The inspected code places the 180-second request clamp in `BudgetedTransport`, while `AttemptController.execute_attempt()` creates and enforces the execution-attempt deadline. Revision 5 explicitly preserves these distinct meanings and says not to redefine the deadline across all retries and finalization.

The migration test should demonstrate that tool continuations and review do not receive fresh full attempt windows. Explicit retries remain separate authorized attempts. Removing the spending wrapper must neither remove the applicable request ceiling nor silently impose it on unrelated callers that previously used different timeout behavior.

This is an execution regression test, not another timeout abstraction.

# Observable checkpoint completion

| Checkpoint                               | Evidence sufficient to exit                                                                                                                                                                                                                               |
| ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1 — Contract freeze**                  | Concrete positive/negative decisions cover inherited restrictions, action-specific assent, read-only conflicts, strict completion and complete permitted deltas. Each field has a clear model or server owner.                                            |
| **2 — Counter-only operation**           | Calls beyond former spending limits still dispatch; one canonical ID covers each dispatch; setup/embeddings/retries are counted; observation failure preserves returns, exceptions and cancellation; required persistence failure still prevents success. |
| **3 — Compact interface and provenance** | Bind-once records survive to finalization unchanged in meaning; stale generations/versions reject; source-order permutations cannot change authority; new roles persist/read correctly; old records and terminal replay remain intact.                    |
| **4 — Integration**                      | Real isolated API/worker/PostgreSQL tests with fake providers demonstrate atomic success, correct deferral, failure, lost acknowledgment and cancellation. Domain events remain available when optional observations are absent.                          |
| **5 — Separate live diagnostic**         | One fixed interface/envelope and predeclared case list; complete deltas and useful replies reviewed; failed/unrun outcomes retained; dispatch totals explicitly observational; no inferred A/B winner or release qualification.                           |

The existing tracing tests provide useful stage, identity and redaction coverage to extend, but they are not evidence that the revised non-vetoing behavior already exists. I read them without running them.

# Optional refinements—not authorization blockers

**Prefer one ordinary aggregation function.** It can consume canonical observations from run events and setup artifacts, deduplicate retained copies by local dispatch ID, and return counts plus completeness. It does not need a metering service, shared mutable counter, durable reservation or reconciliation engine.

**Prefer the simplest observation-persistence arrangement that preserves the boundary.** Best-effort append outside the authoritative transaction is easier to reason about than intricate savepoint behavior. Either can satisfy the plan, but do not introduce machinery merely to promise exact counts through process death—the plan correctly declines that promise.

**Keep the later-recall probe optional.** It would provide useful product evidence, but its absence should narrow the diagnostic’s claim, not block a reviewer-interface repair.

# Conclusion

**Revision 5 is implementation-ready within its stated scope. No further planning amendment is required by this review.** Its added specificity resolves the previous contradictions without introducing another memory store, model stage, persistent registry or accounting subsystem.

The next meaningful review should examine the implementation diff and checkpoint evidence: whether old paths were actually removed, whether optional observation cannot affect authoritative outcomes, and whether the compact reviewer produces correct—not merely parseable—decisions.

**Keep the semantic reviewer and atomic boundary. Delete spending enforcement. Count observed ADE dispatches honestly. Proceed to implementation verification rather than another prose-review cycle.**
