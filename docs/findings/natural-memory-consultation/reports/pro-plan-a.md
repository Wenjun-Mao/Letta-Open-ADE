# Verdict: revise a few execution and evaluation contracts, then authorize bounded implementation

**The plan is a credible implementation proposal, not another architecture sketch. Its core can be implemented without inventing a new memory model. I would not authorize it unchanged, chiefly because the A/A0/B comparison and policy-selection gate remain insufficiently precise.**

The principal corrections are to **define what each comparison holds constant, apply the same positive continuity requirements to every selectable policy, and ensure failed attempts remain inspectable enough to evaluate the reviewer**. There are also two narrower engineering closures around dependency-safe cleanup and old-policy UI behavior.

I would preserve the PostgreSQL foundation, independently editable preferences, derived lifecycle view, acceptance-time memory generation, shared clarification bundle, and synchronous atomic finalization. Neither A nor B has earned selection.

## Inspected revisions and access

| Material                                                                                                                                                | Exact revision inspected                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Implementation plan, revision-4 design, scenarios, source map, third-round assessment and both preserved third-round reports, referenced plans and ADRs | `1a3181c133b7404d6159dbb55468c0a53bb857bd` |
| Runtime, persistence, migrations, API/UI and selected tests                                                                                             | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |
| Previous design’s evidence, processing and context sections, for comparison                                                                             | `c01f45a045eb0fdd0fc6b3e18add82f2dbb57024` |

I read the brief’s required documents and followed the pinned implementation. GitHub’s commit comparison showed documentation changes, not runtime changes, between the implementation baseline and the plan commit.

**This was static public-GitHub review.** I did not execute tests, inspect databases or services, make model-provider calls, or access credentials or ignored captures. All required public review documents were accessible. Missing local and Stage A wire/response evidence remains unavailable; neither the assessment nor preserved reviews substitutes for that evidence. I did not substitute `main`. The brief and assessment explicitly distinguish proposed contracts and static review from runtime validation.

In the findings below, **source-proven** describes the unchanged code; **contract gap** describes something the plan must determine; and **empirical unknown** describes an outcome that the planned experiments—not this review—must establish.

# Prioritized findings

## 1. P1 — A/A0/B separates the right questions, but does not yet guarantee that the experiments isolate them

**Classification:** experimental-contract gap.
**Affected checkpoints:** 1, 4 and 6.

Adding A0 is the right response to the third-round criticism. Removing summaries is not the same treatment as removing the full-lifecycle prerequisite for immediate dialogue. However, the current recipes leave other variables free to change:

* A0 inherits A’s prior-dialogue admission but removes the summary.
* B explicitly excludes summaries **and older raw windows**.
* The precise raw-message pool, replacement use of freed summary space, and selective fallback behavior are not fully fixed across the relevant pairs.

That is consequential in this repository. In `turn_execution.py`, the summary’s `through_sequence` determines which messages enter the recent raw-message pool. Removing a summary without retaining an explicitly controlled boundary can therefore change **both summary availability and raw-history availability**. It is not automatically a one-variable ablation.

### Concrete counterexamples

**A versus A0:** A supplies a summary plus messages after its boundary. A0 drops the summary and instead admits additional earlier raw messages. A0 answers better because the original wording is now present. That result does not isolate the effect of supplying a summary while holding the other evidence constant.

**A0 versus B:** The relevant dialogue lies outside the shared local suffix. A0 admits an older raw window under its inherited A policy; B cannot admit it. Their difference now includes historical coverage, not merely the prerequisite imposed on local dialogue.

These are **possible implementations allowed by incomplete recipe details**, not demonstrated experimental failures. The chosen short fixtures might avoid them—but the plan should establish that explicitly.

### Smallest sufficient correction

Freeze the **eligible evidence pool and allocation behavior** for each pair:

| Comparison               | Required control                                                                                                                                                                                                                                          |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A/A0**                 | Use the same raw-message boundary, lifecycle input and other settings. State whether freed summary space remains unused or is reallocated. Reallocation is a legitimate policy experiment, but must not be described as a pure summary-presence ablation. |
| **A0/B**                 | Use the same eligible local raw-message pool, excluding older windows from both for this comparison. Specify a common selective fallback where applicable; the intended treatment is full-snapshot admission versus recent-first admission.               |
| **Actual summarization** | Distinguish supplied-summary interpretation from the behavior of the summarizer that produces it.                                                                                                                                                         |

**Do not require identical final prompts across A0/B.** Different admitted bundles under pressure are the intended effect. The invariant should be identical inputs *available before selection*, with the resulting selection differences recorded.

Checkpoint 6 already correctly says scripted summaries do not establish summarizer quality. Preserve that distinction: scripted A/A0 probes can establish the effect of supplied summaries, but cannot by themselves establish that a summary-producing production configuration behaves adequately. Any summary-enabled finalist needs the actual compaction path covered before product acceptance.

This needs a more precise recipe, not a fourth production strategy or a general experiment framework.

## 2. P1 — The selection gate needs symmetric positive requirements and an explicit definition of what may be selected

**Classification:** acceptance-contract gap.
**Affected checkpoints:** 1 and 6.

The design and scenarios expressly reject success through blanket abstention. That is good. But the concrete selection gate singles out **B** for preserving answerability on short exchanges under unrelated memory pressure. The common conditions emphasize boundary violations, lifecycle outcomes and forbidden claims. It then permits selection when “one passes.”

The general product goal and the executable gate therefore need tighter alignment.

### Concrete counterexample

A0 withholds an otherwise usable interview exchange and answers:

> “I don’t have enough context to know which introduction you mean.”

There is no incorrect write, isolation violation or forbidden factual claim. B uses the exchange appropriately but fails a different stale-state probe.

Without a common positive requirement, an implementer could conclude that A0 is the sole passing policy—even though it failed a predeclared, answerable continuity case. The scenario prose argues against that conclusion; the selection procedure should rule it out directly.

A second ambiguity is **whether A0 is a selectable product policy or only an ablation**. Passing A0’s no-summary probes must not authorize A’s summary-enabled configuration. Conversely, retaining A0 as a possible no-summary finalist is reasonable, but should be deliberate.

### Smallest sufficient correction

Before execution, freeze:

**A common required operating envelope and per-case answerability contract.** Every selectable policy must satisfy the same mandatory short-exchange and stale-state cases within that envelope. Outside-envelope diagnostics remain informative failures or limitations, not opportunities to redefine the required envelope after seeing results.

**The selectable configurations.** State whether the decision is A versus B, A0 versus B, or any fully tested configuration. Evaluate the actual configuration being selected; do not transfer A0’s success to A.

**Candidate failure versus campaign stopping.** Infrastructure, authorization, isolation and budget failures should stop as declared. Ordinary comparison outcomes—such as unnecessary withholding—need a predetermined treatment: disqualify that candidate and complete authorized comparisons, or stop with an explicitly incomplete result. An unrun candidate is not a failed candidate.

**Completeness before selection.** Budget exhaustion cannot leave one policy apparently winning because its difficult cells were never executed.

Positive success need not be an exact response string. For the interview example, it can require correctly understanding what “自我介绍” refers to and giving relevant support without another unnecessary clarification. Warmth can still receive blinded human comparison with ties.

The proposed **96 generation-request / 160 embedding-request ceiling** is properly described as a spend bound, not a guarantee of completion. Keep it; tighten the consequences of incomplete coverage rather than automatically enlarging it.

## 3. P1 — Failed-attempt evidence must be an explicit checkpoint deliverable, not just successful-run manifests

**Classification:** source-proven observability limitation; engineering prerequisite for the proposed semantic evaluation.
**Affected checkpoints:** 3, 4, 5 and 6.

The amendment now gives detected reply/write contradictions a clear outcome: fail the atomic attempt. It also requires measuring missed contradictions and false vetoes. Those are coherent semantics. The unresolved implementation detail is how the diagnostic will inspect the relevant evidence **after that failure**.

The baseline’s safe provider trace deliberately records response **shape**—content present or absent, finish reason, tool-call count and usage—not the candidate reply or reviewer decision. Moreover, `context.built` and `memory.proposed` are emitted through `append_success_events()`, after successful finalization. Reusing those primitives unchanged does not provide the proposed evidence on rejected attempts.

### Concrete counterexample

The candidate reply correctly identifies Roxy. The reviewer incorrectly calls it a contradiction and fails the turn.

A failed run plus “content was present” cannot distinguish that **false veto** from correctly rejecting “Rocky is the Husky.” Nor can it establish whether the reviewer and generator received the same antecedent.

The same issue arises when generation succeeds but review, embedding or commit fails. The absence of a committed assistant message is correct atomic behavior; the absence of diagnostic evidence is not sufficient for scoring that behavior.

### Smallest sufficient correction

Add an explicit diagnostic exit condition:

> For synthetic evaluation attempts, including failed attempts, retain the actual selected input/bundle, tool evidence, user-visible candidate reply, typed review proposals and claim dispositions, and final commit outcome.

Keep that material clearly marked **uncommitted/undelivered** when appropriate. It must not become an assistant transcript message or durable fact merely to make it inspectable. Private provider reasoning is neither needed nor appropriate.

This can use the existing attempt/artifact machinery with a narrow synthetic-evaluation capture path. It does not require a second memory store or general production prompt logging.

A focused fake-provider test should deliberately produce a contradiction failure and verify both properties together: **no assistant or memory commit, but sufficient retained evidence to distinguish correct rejection from false rejection**.

For API/UI purposes, also distinguish safe terminal reasons—generation conflict, detected interpretation conflict, capacity failure and provider failure—from per-claim no-write outcomes. The existing memory-action UI primarily correlates successful run events with persisted revisions and otherwise gives generic “not confirmed changed” wording. That is insufficient as the sole presentation of the new outcomes.

The plan already asks for observability. This finding makes the failure path an enforceable completion criterion rather than assuming successful-run telemetry covers it.

## 4. P2 — Waiting until a case ends is necessary, but does not define dependency-safe cleanup

**Classification:** source-proven cleanup hazard; engineering closure rather than new product semantics.
**Affected checkpoints:** 2 and 6.

Checkpoint 2 correctly warns against purging source evidence needed by surviving revisions. The current cleanup implementation shows why this needs a concrete deletion unit, not just a scheduling instruction.

`EvaluationSessionService.purge()` operates on one conversation. Its deletion path removes source links and predecessor edges associated with that conversation’s messages or run-owned revisions, clears current-revision pointers where necessary, and deletes those revisions. It can leave another conversation sharing the subject alive.

### Concrete counterexample

A single fact has this revision sequence:

> Conversation C1 creates R1.
> C2 creates R2, referring to R1.
> C1 creates R3, referring to R2.

The case finishes. Deleting either conversation first can damage evidence or lineage retained by the other. Merely postponing the first purge until the case finishes does not make either per-conversation deletion safe.

Operator-caused revisions add another dependency: they are not necessarily owned by any conversation run.

### Smallest sufficient correction

Define the cleanup unit as an **exclusively owned evaluation case/subject closure**, and remove it atomically or dispose of its dedicated test database. Retain/refuse individual conversation purges when surviving records depend on their evidence.

The exact helper structure is an engineering choice. The required behavior is not: surviving shared fixtures must retain complete provenance, and cleanup must account for operator actions as well as runs.

Add the alternating-conversation chain above to the named cleanup tests. Check for active work across the deletion scope, not only in the first conversation selected for purge.

The existing explicit Agent Studio reset is a different, purpose-scoped operation with its own receipt and active-run checks. Extend its references for the new schema without turning ordinary saved-memory removal into reset or erasure.

This is not a request for a generic graph-deletion framework. A clearly owned disposable evaluation scope is simpler.

## 5. P2 — Separate old-conversation writability from subject-memory controls

**Classification:** bounded API/UI contract clarification.
**Affected checkpoint:** 5, plus eventual cutover verification.

The proposed cutover is explicit and defensible: preserve old-policy conversations for reading, require a newly bound conversation for new semantics, and retain the subject when requested. It does not silently rewrite historical definitions.

However, **“this conversation cannot accept new turns” and “this subject’s saved information cannot be removed” are different capabilities**.

The baseline UI couples memory actions to the selected conversation: `prepareMemoryAction()` requires an active fact and a nonarchived conversation, and sends the operation through the composer. `sendMessage()` primarily guards archived and active-run state. The new direct subject-removal command needs a different relationship to conversation writability.

### Concrete counterexample

After cutover, all of a user’s existing conversations are old-policy/read-only. The user opens one, inspects the current subject memory, and wants to remove a record.

If the UI disables all memory actions because the conversation cannot execute, the supposedly model-independent removal control becomes dependent on creating a new chat. That is unnecessary and undermines the capacity-recovery purpose of the new endpoint.

### Smallest sufficient correction

Expose or derive separate capabilities:

**Conversation continuation** depends on the immutable binding’s compatibility.

**Direct saved-record removal** depends on the active subject scope, operator authorization, displayed generation and target versions—not on having a runnable selected conversation.

**Reviewed correction** still needs an eligible conversation and a deliberate user turn.

Also state clearly that a new conversation retaining the subject retains shared saved facts, **not automatically the old conversation’s recent dialogue or summary**. A short “yes” in that new conversation cannot inherit an absent antecedent merely because the character root and subject match.

The existing API does have real `require_operator`/`require_reader` dependencies; the plan is right to reuse them rather than treating an audit-origin label as authorization. Their deployed configuration was not verified here.

This clarification does not require a new authorization system or manual fact CRUD.

# Areas that are sufficiently specified—and should not be reopened

## Migration and provenance

The plan identifies the correct migration predecessor, `20260902_0006`, and explicitly addresses the meaningful additions: separate memory generation, legacy semantics, independent preference identity, alternative operator causation, role-labelled message sources and current terminal descriptors. The baseline migration tree and `0006` file support that anchor.

The provenance change is real, not cosmetic. Existing message-source rows require a message ID and exact span, while the source reader returns message-derived locators. Operator actions must therefore remain genuine alternative causes, and assistant referents must remain distinguishable from user authority throughout storage, readback and UI. The plan acknowledges these requirements.

I would keep the following as implementation acceptance obligations, not demand a second schema-design exercise: preserve legacy evidence without inventing whether it was direct assertion or endorsement; test cross-subject causal/source references; preserve legacy ambiguous corrections and locations; and demonstrate populated readback through the new clients. The existing repository tests establish narrower source-join and boundary behavior, not the new causation contract.

## Concurrency and retry ownership

The amendment now adequately distinguishes acceptance-time conflicts, finalization conflicts on nonempty decisions, permitted already-running no-op staleness, and deliberate fresh submission. That is a coherent conservative contract.

The baseline admission path already distinguishes idempotent replay from new admission and excludes overlapping active turns within a conversation. Its retry helper retries selected transport/timeout failures rather than all exceptions. Extending those boundaries with a terminal memory-generation conflict is a targeted change, not a reason for another scheduler or fine-grained dependency system.

Keep the counter tied to **every effective writer** and preserve its transactional coupling with effects. Harmless conflicts and queued “goodnight” failures are availability costs to measure, not evidence of broken atomicity.

## Reviewer outcomes and terminal retrieval

Assertion-scoped no-save precedence is materially better than the baseline’s normalized-key guard. The plan explicitly stages operations so order or new IDs cannot bypass the intent rule. Its permit/defer/contradiction distinction also avoids turning every conversational question into a write veto. Those semantics are sufficiently clear for implementation; detection reliability remains empirical.

Likewise, selective recall of an inactive descriptor is now specified as **current lifecycle information**, with a current-revision index—not arbitrary historical search and not reuse of an old active embedding. Preserve that correction. The baseline execution currently embeds non-null operation values, so terminal indexing needs the explicit implementation change already called out by checkpoint 2.

## Budgets and rollback

The shared ledger is an appropriate existing primitive: reservations are committed before sending, concurrency is serialized in SQLite, failed/interrupted requests remain spent, and bindings/limits are checked. The plan correctly requires new diagnostic and setup paths to use that same boundary. **96 generation requests means all counted conversation/reviewer/compaction requests, not 96 conversational turns.**

The rollback section also makes the right distinction: additive SQL does not imply old-binary compatibility or a harmless downgrade. A tested matching restore or compatible forward fix, with an explicitly authorized recovery point/data-loss window, is the appropriate requirement. No rollback success is established by this review.

# Disposition of the third-round findings

**“Addressed” means addressed in the proposed contract and work scope—not implemented or validated.** The mappings below use the preserved third-round reports and assessment.

| Third-round finding                                                              | Disposition                            | Remaining consequence                                                                                                                            |
| -------------------------------------------------------------------------------- | -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| **A1 — same-turn removal/no-save must dominate equivalent saving**               | **Addressed**                          | Assertion-level eligibility and operation-order-independent checks are explicit. Semantic matching still needs tests.                            |
| **A2 — explicit reply/write disagreement differs from unresolved clarification** | **Partial**                            | The atomic failure outcome is now explicit. Failed-attempt capture must make false vetoes and detected contradictions independently inspectable. |
| **B1 — selective recall must include terminal lifecycle state**                  | **Addressed**                          | Current descriptor/index semantics are specified; arbitrary history and forgotten chains remain excluded.                                        |
| **A3/B2 — full-snapshot admission can destroy immediate continuity**             | **Partial**                            | It is now a provisional control and B is genuinely different. The controlled comparison and symmetric positive gate need findings 1–2.           |
| **A3/B4 — full-snapshot automatic retrieval can be redundant**                   | **Addressed**                          | The plan skips it when the complete snapshot is supplied while preserving genuine selective/tool paths.                                          |
| **B4 — optional compaction can become a needless failure dependency**            | **Addressed**                          | Narrative eligibility is determined before compaction undertaken solely for that response.                                                       |
| **A4/B5 — reviewer capacity must reserve the future candidate reply**            | **Addressed**                          | The plan explicitly reserves it using the reviewer’s own estimator, checks final requests and prohibits reviewer-only clipping.                  |
| **A5/B3 — acceptance-time generation conflicts need terminal/replay semantics**  | **Addressed**                          | Queued and in-flight cases, same-key historical outcomes, and explicit fresh submission are distinguished.                                       |
| **A6/B6 — end → forget → old-history exposure**                                  | **Addressed as a limitation and test** | No hidden retained guard or erasure promise is introduced. The actual response behavior remains untested.                                        |
| **B6 — replayed removal success is not current absence**                         | **Addressed**                          | Historical receipt and current readback are explicitly separate.                                                                                 |
| **A7/B5 — endorsement, partial assent and unrelated questions**                  | **Addressed in semantics**             | Proposition-level interpretation and false-veto tests are named; empirical reliability is unknown.                                               |
| **Retrospective repair, continuity tables and broad source retrieval**           | **Deferred**                           | The plan correctly does not count their absence as implemented continuity.                                                                       |

The third-round criticisms were not merely renamed. Most now have an explicit operation, outcome or owning checkpoint. The remaining work is chiefly making the evaluation and completion evidence as precise as the write contract.

# Simplification recommendation

**Keep the three variants as evaluation recipes, not three product subsystems.** A small frozen recipe manifest and the existing assembler are enough; final production selection should leave one accepted binding.

**Keep one lifecycle view, one mutation generation and one commit boundary.** Operator and conversational causation require different provenance, not parallel implementations of forgetting or concurrency.

**Use the diagnostic artifact path for rejected synthetic candidates.** Do not create fake assistant messages, another semantic ledger or a second judge just to obtain evaluation evidence.

**Make cleanup follow ownership of the disposable case.** That is simpler than repairing shared provenance after a sequence of destructive per-conversation purges.

**Do not implement deferred history features to make the tests appear answerable.** Missing cross-conversation dialogue and retrospective repair must remain visible limitations.

# Authorization conclusion

**Bounded implementation can be authorized after the plan incorporates the following corrections. No new provider experiment is required to choose these contracts first.**

| Before authorization, make the plan explicit about…                                                                       | Nature of the correction                                   |
| ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| Controlled A/A0 and A0/B evidence pools, allocation behavior and what each comparison can conclude                        | **Blocking evaluation-contract decision**                  |
| Common positive answerability requirements, required envelope, selectable configurations and incomplete-result handling   | **Blocking acceptance-contract decision**                  |
| Inspectable failed-attempt evidence sufficient to score contradiction detection, false vetoes and withheld context        | **Named engineering exit gate for checkpoints 3–4/6**      |
| Dependency-safe evaluation cleanup at the case/subject scope, with refusal of unsafe individual purges                    | **Named engineering exit gate for checkpoint 2**           |
| Separate old-conversation writability from subject-level operator removal and explicit new-conversation continuity limits | **Bounded API/UI contract clarification for checkpoint 5** |

Once those changes are recorded, **checkpoints 1–5 are a reasonable authorized implementation scope**. The unknowns—natural matching quality, false vetoes, selective terminal recall, context-policy usefulness, capacity and latency—belong in the planned validation, with results allowed to reject either policy.

Checkpoint 6 still requires its separate live authority. Policy adoption, populated deployment, rollback execution, fresh qualification and release approval remain separate decisions.
