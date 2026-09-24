# Verdict: ready for bounded implementation, with narrow execution clarifications

**The plan removes real complexity rather than merely relocating it.** Subject identity, target versions and source metadata become deterministic application work; parallel proposal/disposition arrays disappear; and deferral no longer requires an invented mutation. Those are meaningful reductions in independent failure opportunities.

**Remove request-budget enforcement completely, as requested.** The remaining accounting should be a projection of observed dispatch events—not another reservation mechanism, shared counter service or readiness dependency.

I would proceed with the existing plan after recording the execution clarifications below in its checkpoint tests. **I do not see a need for another architecture or planning cycle.** The main risks are carrying forward two incompatible event paths, allowing observation failures to affect execution, and adapting provenance consumers incompletely.

## Inspection boundary

I inspected the plan, assessment and relevant implementation at:

**`236024fc7dd40058e262cea4d0c6d74c44e6b2d0`**

Source inspection covered reviewer construction/schema, evidence validation, preparation/finalization, persistence source constraints/readback, tracing, transport, worker timeout ownership, budget settings/readiness, budget tests, and the natural-memory diagnostic’s transport, contract and result checking.

The cited public files were accessible through GitHub. Private captures, databases and local services were unavailable. **No tests or provider calls were executed.** Published diagnostic outcomes and the assessment’s offline reproductions remain maintainer-reported evidence, not independently repeated measurements.

# Does the new interface actually simplify the system?

**Yes—provided the implementation stays literal.**

A request-local handle map is justified because the model must still identify *which* existing assertion or related entity it means. It does not need to reproduce persistence metadata. A small immutable dictionary translating `F1` into the already-held fact/version is simpler than asking the model for a UUID and version and repeatedly checking that it copied both correctly.

The three evidence modes also represent real distinctions:

| Mode              | Necessary distinction                                                   |
| ----------------- | ----------------------------------------------------------------------- |
| Direct            | The current utterance supplies the assertion or instruction.            |
| Resolve-user      | The current answer completes an earlier user assertion.                 |
| Endorse-assistant | Current assent authorizes a particular assistant-presented proposition. |

These should be **three typed input combinations handled by ordinary functions**, not three extraction pipelines. The plan explicitly rejects model-based support preselection and a general compiler, which is the right boundary.

Two implementation constraints will keep this small: assign support handles to already-admitted messages rather than attempting a preliminary semantic extraction, and serialize each message once rather than repeating its full text in both “context” and “eligible support.” The model selects an exact span within the supplied message; ADE resolves and verifies it.

# Prioritized findings

## 1. P1 — Existing request events are reusable, but not yet one consistent accounting source

**Classification:** source-proven integration hazard.
**Affected checkpoint:** **2**.

`provider_tracing.py` already creates a local request UUID and records operation, stage, model and local outcomes. But successful finalization does not simply persist that same trace. `worker_events.py` reconstructs generation-request events through `_append_model_rounds()` and `_append_conversation_trace()`, without the same request UUIDs. Its `run.completed.model_request_count` includes conversation, reviewer and compaction requests, but not embeddings. Failure handling uses `append_attempt_trace()` and the real trace events.

### Counterexample

A turn performs one query embedding, one conversation request, one review and one write-embedding batch.

Using the successful run’s generation summary as the total misses the embedding calls. Adding the real trace alongside the reconstructed success events risks counting generation twice. Deduplicating by provider response ID cannot solve this reliably: failed dispatches may have no provider ID.

### Smallest sufficient correction

Choose **one producer of canonical request events**, using the existing local request UUID. Persist/project those events consistently for successful and unsuccessful attempts. Remove the reconstructed request-start/completion events from the success path; keep its domain events for committed messages, memory, summaries and tool outcomes.

The accounting definition can be small:

* **Attempted:** one unique local dispatch-start ID.
* **Completed:** the local transport returned its supported response envelope.
* **Failed/cancelled:** that invocation ended in a local exception or cancellation.
* **Unresolved:** a known start has no retained terminal observation.

An invalid reviewer decision can therefore be **a completed transport request and a failed product turn**. Those are not contradictory statuses.

Exclude catalog discovery from generation/embedding totals. Give workflow setup/indexing the same event shape and an iteration/case association, without inventing a conversation run.

**These are ADE dispatch attempts, not confirmed provider receipt or billing.** If starts themselves were lost, the total is incomplete—not merely a complete total with several “unresolved” requests. The plan already allows this limitation; retain it instead of rebuilding durable pre-request reservations.

## 2. P1 — Make the observation path incapable of changing the call’s outcome

**Classification:** source-proven behavior that conflicts with the intended counter-only contract.
**Affected checkpoints:** **2 and 4**.

Several existing observation hooks can affect execution:

`TracedRouterTransport._invoke()` calls trace-start before its protected invocation and trace-completion before returning. The natural reviewer invokes its observation callbacks directly. More concretely, `NaturalLiveTransport._send()` writes captures in `finally` and can raise after the underlying request succeeded, or replace the original exception with a capture error.

### Counterexample

A reviewer returns a valid result, but the capture filesystem is full. The capture writer raises, so the caller never receives the valid result and the turn fails.

That is not observational accounting. It makes artifact availability part of conversational availability.

### Smallest sufficient correction

Best-effort observation must preserve the original return value or exception. A failed count/capture write marks evidence incomplete and can make the **evaluation** unscorable; it must not masquerade as a provider failure, trigger a retry, or rewrite a committed outcome.

The worker already follows this principle for late natural-evidence retention: its final cleanup logs artifact failure without rewriting the authoritative run outcome. Extend that principle to the earlier callbacks and transport capture path.

**Do not apply this exception handling to required persistence.** Failure to store a memory source, revision or required atomic outcome must still prevent successful finalization. Optional request telemetry and required provenance are different obligations. If optional telemetry is written into the same transaction, it needs isolation from the authoritative commit path—not blanket swallowing of database errors.

No new observability service is needed. A small non-vetoing observation helper and existing event/artifact destinations are sufficient.

## 3. P1 — The provenance change must remove the old “first non-assistant source is authority” assumption

**Classification:** source-backed migration/validation hazard; already within the plan’s intended scope.
**Affected checkpoint:** **3**.

The plan correctly separates `user_resolution` from support-only `user_antecedent`. However, current `_validate_claim()` and `_claim_sentence_has_no_save()` find the current authority by selecting the **first source that is not `assistant_referent`**. That shortcut stops being valid once an earlier user source is permitted.

### Counterexample

The source list contains, chronologically:

> Earlier user: “One of my dogs is a Husky.”
> Current user: “Roxy, but don’t save that.”

Reusing the old helper unchanged selects the earlier assertion as “current” and applies its offsets to the current message. That can misapply uncertainty/no-save checks even though all quoted spans are individually exact.

### Smallest sufficient correction

The bound representation should expose **the current authority anchor explicitly**, separately from supporting spans. Pass that anchor to current-utterance checks. Do not recover authority from tuple ordering or “not assistant.”

Update the complete consumer chain in the same checkpoint:

* The database source-role constraint currently admits only the three old roles.
* `memory_source_read.py` recognizes only `user_assertion` and `user_endorsement` as user authority.
* The diagnostic’s `verify_attempt_safety()` uses the same old authority set.

With the proposed persisted roles, a forward constraint migration is necessary—not optional in practice. It remains a small migration: no new table family or historical reinterpretation is needed. Test that `user_antecedent` alone never satisfies authority, and that old revisions/receipts remain readable unchanged.

There is another useful deletion here. `execute_natural_review()` currently prepares once through `validate_decision=prepare`, prepares again on return, and finalization prepares again. The new interface should **bind once to trusted operation records, then revalidate their ownership, source integrity and original versions at commit**—not rebuild handle meanings from fresh rows.

This implements the plan’s “held map” rule while removing redundant preparation. It does not remove transactional revalidation.

## 4. P2 — Name timeout ownership before deleting the budget wrapper

**Classification:** execution-contract clarification, not a reason to preserve spending enforcement.
**Affected checkpoints:** **1 and 2**.

The plan correctly notices that `BudgetedTransport` also contains `min(timeout, 180.0)`. Current timeout behavior has distinct layers:

| Layer                                 | Inspected behavior                                                           |
| ------------------------------------- | ---------------------------------------------------------------------------- |
| `BudgetedTransport._send()`           | Clamps an individual transport invocation to 180 seconds.                    |
| `AttemptController.execute_attempt()` | Creates and enforces one deadline for the execution attempt.                 |
| `RouterTransport._request()`          | Passes its supplied timeout to the HTTP client.                              |
| Retry coordination                    | Invokes another execution attempt when an explicitly permitted retry occurs. |

These are visible in the current code.

### Counterexample

Moving “180 seconds” into each individual model call without preserving the attempt deadline would allow a tool continuation and reviewer to receive fresh full windows. Conversely, deleting the wrapper without replacing its documented per-request constraint changes longer configured attempts.

### Smallest sufficient correction

Record which existing layer owns each deadline. Preserve the shared attempt deadline across conversation, tools and review; retain the documented per-request diagnostic bound at a non-accounting transport layer. Explicit retries must remain explicit attempts, not hidden extensions of a request.

The current controller enforces **attempt execution**, not one wall-clock deadline spanning every retry and finalization. Do not silently broaden or narrow that contract as part of accounting removal.

Move the timeout regression out of `test_request_budget.py` before deleting the budget-specific tests. No new timeout framework or mandatory configuration family is needed.

## 5. P2 — Strengthen the diagnostic’s state checks; keep recall claims proportional to what it tests

**Classification:** acceptance weakness in the reusable scorer, plus an optional useful-recall probe.
**Affected checkpoints:** **1, 4 and 5**.

The proposed diagnostic is substantially better than a parseability test: it covers scoped assertions, correction, ownership, endorsement, no-save, deferral and removal. But the existing `mutation_state_matches()` often establishes that an expected record exists, rather than that the **complete mutation set is correct**. The coffee case, for example, requires a scoped coffee addition and excludes jasmine; it does not reject every other unintended write.

### Counterexample

The reviewer saves the correct morning-coffee preference and also an erroneous extra fact. A presence-oriented scorer can accept the expected addition while missing the unrelated change.

### Mandatory correction

For each new diagnostic case, freeze the complete permitted **before/after memory delta**: expected additions/revisions/removals, unchanged identities and scopes, and forbidden extra mutations.

Keep semantic wording flexible. Correctness should not require identical JSON strings, but neither should the runner treat keyword presence as semantic acceptance. A mechanically matching result should remain pending semantic review where meaning matters.

### Optional improvement

Add one or two later-recall probes to the existing successful sequences—for example, a new same-subject conversation asking about morning versus evening drinks without restating the preferences. This distinguishes persistent useful recall from echoing the current utterance.

This is **not mandatory for establishing that the reviewer interface improved**. Without such a probe, label the result reconciliation/write evidence and leave retrieval/continuity to the later comparison. The plan already correctly prevents this diagnostic from selecting A or B.

# Concrete keep/delete/defer recommendations

## Delete—not disable—the spending machinery

| Inspected location                                      | Remove                                                                                                                                                                                                             | Preserve                                                                                                      |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `request_budget.py`                                     | `RequestLedger`, `BudgetedTransport`, reservations, limit/source bindings and budget identity                                                                                                                      | Ordinary transport construction and credential resolution, moved to an existing transport/construction module |
| `platform/settings.py`                                  | `agent_runtime_budget_ledger_path`, `agent_runtime_budget_stage`, `agent_runtime_budget_generation_limit`, `agent_runtime_budget_embedding_limit`, `_validate_runtime_budget()` and associated validator arguments | Context, timeout, retry, authentication and worker settings                                                   |
| `worker_health.py`                                      | Budget argument/payload in compatibility fingerprinting and `budget_identity` dependency                                                                                                                           | Migration, runtime-mode, source/build and worker-health checks                                                |
| `natural_live_transport.py`                             | `RequestScope` spending limits, `reserve_local()`, ledger snapshots and schedule-exhaustion exceptions                                                                                                             | Approved-route checks, case association, redaction and safe artifact paths                                    |
| `natural_live_campaign.py` / `natural_live_contract.py` | Ledger setup, 96/160 enforcement, reserved-allocation assertions and active dependence on historical spending schedules                                                                                            | Finite case list, source identity, explicit retry/timeout rules, semantic and infrastructure stops            |
| `test_request_budget.py`                                | Reservation races, spent-slot persistence, cap exhaustion and budget-configuration tests                                                                                                                           | Relocated timeout, dispatch observation, retry and transport-construction coverage                            |

These are concrete deletion targets in the pinned code. The four settings use the `ADE_API_` environment prefix; remove their documented environment/Compose wiring as the plan requires.

Also replace `capture_scope()`’s assumption that every locally reserved request must have a **completed** capture. Observational reporting must represent failed/cancelled/unresolved dispatches, not reject their existence as an invalid count. Missing evaluation evidence can still make a case unscorable.

**Do not delete every setting or test containing “budget.”** Finite tool loops, maximum model steps, context/output limits and explicit retry limits are execution contracts, not spending controls. The source has “attempt budget” wording for retry exhaustion; its meaning, not the word, determines whether it stays.

Historical ledgers and frozen fixtures should remain byte-identical. Their old spending instructions should cease to govern active commands; no compatibility adapter is needed merely to keep obsolete diagnostics executable.

## Keep the small semantic core

Keep one reviewer call, one decision list, three evidence combinations, one held binding map and one atomic mutation boundary. Keep exact quotes, current authorization, eligible identity views, genuine deferral, strict completion classification, and honest no-change/failure outcomes.

Delete the old parallel-array joining logic and model-emitted subject selectors, target versions, source-role enums and redundant quote fields when the new parser replaces them. The old schema visibly requires those clerical fields and defaults both arrays to empty, so replacement—not tolerant parsing—is appropriate.

## Defer additional machinery

Do not add durable handle registries, a compiler intermediate language, semantic support pre-extraction, a second judge, generalized event reconciliation, a billing dashboard, memory-first ordering or degraded reply delivery. None is needed to implement this plan.

The plan’s instruction to stop if evidence modes cannot be “enforced” should not become a demand for deterministic proof of natural-language entailment. **Native checks establish binding and permitted combinations; semantic tests establish observed interpretation quality.** Another layer of metadata cannot turn the latter into a theorem.

# Lean execution sequence

The existing order is sensible; make its checkpoints more concrete rather than writing another plan.

**First, freeze the boundary examples and accounting semantics.** Include the explicit current-anchor representation, completion-status behavior, canonical request ID, observational failure rule and timeout ownership.

**Second, remove spending enforcement and unify observation.** This is independently testable with fake transports. A request count exceeding a former threshold must still dispatch, while an extra reviewer call or unauthorized retry remains a separate execution-contract violation.

**Third, replace the reviewer interface and migrate its provenance consumers together.** Produce trusted bound operations once; preserve finalization checks. Test new evidence through SQL storage, readback and UI—not merely the parser.

**Fourth, run integration and the separately authorized diagnostic.** Keep one fixed source/interface/envelope and a finite predeclared case list. Recompute context capacity after the schema change, rather than preserving an obsolete token number through evidence truncation. The plan already specifies this correctly.

# Observable completion criteria

| Area                           | Evidence that should exist before declaring the checkpoint complete                                                                                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Actual simplification**      | One live reviewer parser; no parallel-array join; no model-owned persistence metadata; no persistent handle store; no duplicated full-message serialization merely for support eligibility.                |
| **Binding/provenance**         | Positive direct/resolution/endorsement cases and negative bare-name, wrong-role, missing-span, stale-handle and cross-subject cases; antecedent-first ordering cannot change authority.                    |
| **Atomic outcomes**            | Genuine defer permits independent valid work; malformed/truncated/conflicting review does not salvage siblings; no-change creates no mutation embeddings/entities or generation advance.                   |
| **Counter-only operation**     | Fake calls beyond former caps still execute; one dispatch has one ID across event/artifact copies; setup, embeddings, continuations and explicit retries are included; catalog is separate.                |
| **Failure independence**       | Broken telemetry preserves the original transport result/exception; mandatory provenance failure still rejects commit; lost evidence produces “incomplete/unscorable,” not fabricated zeroes.              |
| **Compatibility**              | Existing facts, revisions, message sources, receipts and terminal replays remain readable; new roles pass authoritative readback; obsolete fresh-send bindings do not silently acquire new semantics.      |
| **Useful diagnostic evidence** | Complete allowed mutation deltas, scope/identity preservation and semantically reviewed replies; failed and unrun cases retained; no inference of an A/B winner or failure rate from the small diagnostic. |

## Readiness conclusion

**Proceed with bounded implementation on this plan.** Treat findings 1–4 and complete-delta scoring as mandatory checkpoint obligations, not invitations to expand the architecture. The later-recall smoke probe is optional provided acceptance claims remain appropriately narrow.

The empirical questions remain whether the compact interface reduces invalid proposals, whether 4,096 output tokens are adequate for the frozen diagnostic, and whether semantic errors persist after bookkeeping is removed. The available public evidence cannot answer those yet.

The intended end state is appropriately small: **a semantic reviewer, deterministic binding, strict native validation, atomic outcomes, and best-effort dispatch counts—with the spending subsystem gone.**
