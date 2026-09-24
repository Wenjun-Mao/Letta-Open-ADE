# Verdict: substantially improved, but two contract decisions still block implementation planning

**Revision 2 resolves most of the first-round design problems. I would keep its revised fact model, lifecycle, provenance boundaries, and synchronous finalization. I would not yet freeze the summary-watermark or mutation-dependency rules.**

The remaining problems are narrower than before:

**First, a summary’s memory watermark does not establish that the summary incorporates—or is consistent with—the state represented by that watermark.**

**Second, checking selected absence assumptions does not cover every dependency that can make a proposed memory write stale.** The new operator-removal path makes that distinction especially important.

Neither problem calls for a different memory framework. Both call for fewer, clearer correctness obligations.

## Inspected revisions and evidence boundary

| Material                                                                                                                   | Exact revision                             |
| -------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Revision 2 documentation, all 22 scenarios, assessment, source map, both preserved first-round reports, and ADRs 0022/0026 | `d80afb422b3deefa09f13ac5e7017c5e3e8524ef` |
| Unchanged implementation and relevant tests                                                                                | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |
| Previous design used for comparison                                                                                        | `243d8d0b4e850aca304eea2699e58ec24d45479b` |

I inspected the revised packet directly, including complete `reports/pro-a.md` and `reports/pro-b.md`, and followed the pinned runtime evidence. The relevant paths include the reviewer and memory-policy contracts, fact commits, context assembly, compaction, turn execution, finalization, persistence metadata, and the memory/source repositories. I also inspected the relevant test specifications; **I did not execute tests, access a database, or make provider calls**.

All required repository documents were accessible. The assessment’s six synthetic reproductions are **maintainer-reported executions with published reproduction code**, not executions I independently performed. Local captures, deployment state, and the missing Stage A response/wire contents remain unavailable. I did not substitute `main`.

Below, **source-proven** describes the unchanged implementation. A **design gap** describes a contract that revision 2 has not sufficiently determined. Counterexamples involving proposed behavior are logical scenarios, not claimed experimental results.

# Prioritized remaining findings

## 1. P1 — The watermark can label an already-stale summary as up to date

**Classification: design gap with a source-grounded counterexample. This is a planning blocker.**

Section 8 proposes attaching a subject-memory watermark to a summary and supplying intervening changes when the summary predates memory updates. Capturing and rechecking the watermark with the source snapshot correctly addresses one race: stamping a concurrent, newer commit onto an older generation. It does **not** address changes that happened before summary generation but were absent from the summary’s inputs.

Consider this sequence:

> Conversation A contains “小王 is my partner.”
> Conversation B records the breakup. The relationship becomes inactive.
> Later, A is compacted for the first time from its old conversation messages.
> The new summary receives the current subject-memory watermark.

There is no concurrent write in this example. Nevertheless, the summary can still say that 小王 is the current partner. Its watermark is current because it was sampled recently—not because the breakup was incorporated.

This is directly relevant to the baseline: `compaction_model_input()` supplies the previous summary and incremental conversation messages, not a reconciled subject-state snapshot. `RunFinalizer.commit_success()` subsequently commits that generated summary. Recompacting an old summary plus unrelated new dialogue can reproduce the same problem.

**The distinction that needs fixing is:**

> “Generated while memory was at revision N” is not the same as “safe to use without the changes recorded through revision N.”

Even supplying current facts to a summarizer would not make its output a mechanically verified reconciliation. That remains model-dependent.

### Smallest sufficient correction

**Keep current-state guards outside the summary and do not let re-summarization automatically clear their applicability.** An older narrative needs the relevant current replacement, ending, or invalidation regardless of when that narrative was last compressed.

My preference is to **defer the delta-watermark optimization**. Begin with the simpler contract already implicit elsewhere in the proposal: admit historical evidence with sufficient current-state context, or withhold it. A watermark may identify a snapshot or invalidate a cache; it must not certify narrative correctness.

Retaining the watermark optimization instead requires an explicit account of inherited dependencies: what information the summary actually depends on, what remains unresolved, and why re-compaction may advance the boundary. That is substantially more than adding a counter column.

The decisive counterexample should therefore be **“old dialogue compacted after the correction,” not just “correction races with compaction.”**

## 2. P1 — Absence checks need a complete mutation-dependency rule

**Classification: incomplete concurrency contract; future failures are untested. This is the other planning blocker.**

Revision 2 correctly distinguishes stale mutations from permitted stale no-op replies. It also identifies absence-dependent new-entity and preference-add proposals. However, the proposed checks are narrower than the dependencies that can invalidate a write.

### Counterexample A: the target version is unchanged, but target resolution is stale

Two pets have identity facts naming them Rocky and Roxy. Conversation A uses those names to select an entity and proposes changing its existing breed fact. Before A commits, conversation B corrects the mistaken name-to-entity assignments. The breed fact’s version has not changed.

A target-version check can pass even though the identity information used to choose that target has changed. This is not a new-entity proposal or a preference add, so the specifically described absence checks do not clearly apply.

Depending on the correction’s meaning, the old interpretation might remain legitimate or might now refer to the wrong animal. The system should not silently decide that question merely because the breed row’s version stayed unchanged.

The baseline finalizer re-prepares the proposed operations against current facts and entities, but `_validate_existing_fact()` checks the targeted fact’s ownership, active status, and version—not every identity fact used to resolve that target.

### Counterexample B: absence changes and then looks absent again

Suppose A prepares a preference add while a category has no eligible records. B adds the preference, and the operator then removes it. A’s final comparison again sees no eligible nonforgotten records.

**Comparing only the final eligible ID/version set would miss that intervening history.** A pre-removal proposal could then recreate information after removal without a new post-removal user statement. Checks that deliberately retain tombstone information or track intervening mutations can catch this; the current wording does not determine which contract applies.

This matters because scenario 15 distinguishes a *later explicit restatement after forgetting* from restoring an excluded chain, while scenario 21 intends stale absence-dependent proposals to conflict.

### Smallest sufficient correction

Choose one rule covering **all nonempty mutation proposals**, including their supporting identity/state dependencies and intervening operator actions.

Given the design’s explicit willingness to reject harmless concurrency, **one subject-memory mutation generation checked against the reviewer’s snapshot is simpler than several specialized read-set families**. It should change for operator removals as well as reviewer writes. An unchanged target version would no longer disguise a changed interpretation environment.

That is not a proposal to serialize provider calls, hold locks during generation, or reject every stale no-op reply. The documented weaker dialogue guarantee can remain.

Fine-grained read sets are also defensible, but then their membership, tombstone handling, supporting-fact dependencies, and snapshot consistency must be specified. They should earn their complexity through a need to avoid excessive conservative conflicts—not be assumed simpler because each set sounds narrow.

## 3. P2 — Historical repair is legitimately deferred, but historical-context claims must remain equally narrow

**Classification: explicit capability deferral with a residual read-side risk. This is part of the first blocker, not a demand for a new history engine.**

Deferring arbitrary retrospective revision repair is reasonable. The revised contract correctly prevents an old-history correction from replacing today’s residence and removes the proposed generic historical-fact tool. That is a real simplification.

However, **removing historical-fact search does not remove historical assertions from summaries or raw dialogue**.

For example:

> A contains “I lived in Beijing before Toronto.”
> B later contains “Beijing was my sister’s city; I lived in Ottawa.”
> The latter is an explicitly deferred retrospective repair, so it changes no durable current fact.
> A later supplies its old narrative.

A subject-*memory* watermark need not change at all. The proposed stale-memory mechanism therefore cannot be treated as covering this correction.

The same limitation appears in the source-window experiment when a later update belongs to an archived conversation or another character root. Excluding that source is an intentional boundary; it does not make the latest **eligible** evidence the latest information the application has ever received. Section 8 correctly acknowledges evidence gaps, but that qualification needs to govern the answers and evaluations consistently.

### Smallest sufficient correction

Keep the deferral, but make the first target explicit:

**Historical dialogue establishes what was reported or discussed. It does not establish that no later correction exists.**

Current-state answers about supported facts should use the current ledger and relevant terminal state. Historical answers may use a sufficiently complete supplied sequence; otherwise they must qualify the report or abstain. Do not silently widen source access to obtain a missing correction.

Scenario 2’s old-name question, for example, is supportable when the relevant rename/correction dialogue is supplied. It must not implicitly require a generic historical lookup after those details disappear from context. Scenario 16 should remain visibly unsupported for durable retrospective repair rather than being scored as solved through a convenient recent window.

This is an acceptable first product boundary. It is not complete historical continuity.

## 4. P2 — Clarification is substantially improved; distinguish entity selection from affirmative endorsement

**Classification: the original counterexample is resolved in the design; adjacent semantics remain unspecified.**

The revised “one dog is a Husky → Rocky or Roxy? → Roxy” contract is appropriate. It supplies the missing earlier user assertion, preserves the current clarification anchor, and treats the assistant’s question as reference context rather than factual authority. The eight-message boundary is a deliberate limitation, not an architectural defect.

The next distinction to settle is between these exchanges:

> Assistant: “Which dog?”
> User: “Roxy.”

and:

> Assistant: “Is Roxy a Husky?”
> User: “Yes, she is.”

A bare name does not endorse an assistant-invented breed claim. An unambiguous affirmative answer can be a new user assertion, even though the assistant supplied the proposition’s wording.

Revision 2 explicitly settles the first case when only the assistant introduced the breed. It does not clearly settle the second. Developers could implement “assistant text is never evidence” too broadly and preserve the original inability to learn from ordinary confirmation.

The baseline lexical check reinforces that risk: current evidence binding and value support do not naturally support a value whose wording appears only in the question being confirmed. This is a source limitation, not proof that the revised policy would make the wrong decision.

### Smallest sufficient correction

Specify one **endorsement rule**, not another evidence subsystem: a current answer may resolve only what it actually answers.

“Roxy” resolves the owner of an already user-reported claim. “Yes, she is” can affirm an unambiguous proposition. Neither should remove uncertainty from “might be a Husky,” endorse unrelated clauses, or convert a quoted or fictional proposition into biography.

Also treat eight messages as a maximum eligible window, not a guarantee that eight arbitrarily long messages fit. A source window shortened for budget reasons must not hide a negation or intervening correction while presenting the remaining excerpt as complete.

These are bounded semantic cases to settle and evaluate. They do not justify another reviewer model or unrestricted historical extraction.

## 5. P2 — Direct operator removal is coherent; its recovery promise should be narrower

**Classification: sound design change with explicit storage and availability consequences.**

I do **not** regard the new operator path as inherently an unsafe bypass. It describes an explicitly confirmed action, exact targets and versions, server-bound ownership, durable action provenance, and idempotency. It also avoids pretending that the action is an ordinary user-message quotation. Those are the right distinctions.

There is a real implementation contract to change: existing revisions require a `run_id`, and existing revision-source rows require message IDs and spans. An operator action cannot honestly be represented as the existing conversational evidence shape without extending that contract. The design acknowledges a durable action record, so this is not an undiscovered requirement—but it must remain one explicit causal alternative, not a fake conversation or a parallel unaudited mutation path.

The current accepted ADR routes operator-prepared removal through the conversation/reviewer path. Direct removal is therefore an intentional amendment to that product contract, not merely an optimization beneath unchanged semantics.

### The narrower capacity counterexample

A reviewer packet can overflow because of a large factual set, but also because of long supporting dialogue or accumulated entity metadata. Deleting one preference does not necessarily restore ordinary chat in those latter cases. The baseline reviewer supplies the recent user-message window and non-subject entity list as well as facts.

### Smallest sufficient correction

Describe this as **“removal remains available when ordinary review is unavailable,”** not as a universal guarantee that deleting facts restores conversation.

Distinguish the cause of capacity rejection and avoid supplying unneeded orphan-entity metadata. Keep one mutation-validation/commit boundary with two legitimate causal origins: conversational review and explicit operator action. Both must participate in the concurrency rule from finding 2.

Retaining fail-closed normal turns at capacity is a defensible bounded-slice tradeoff. It should remain visible as a product limitation, not be disguised as natural conversational memory. I would not add background extraction merely to avoid acknowledging that boundary.

The stated local-only access assumption is appropriately narrow. I did not verify deployed network isolation or authentication, and an `origin=local-operator` audit field must not itself be mistaken for authorization.

## 6. P2 — “Current facts outrank narrative” must compare the same claim and scope

**Classification: an important clarification to the new residence semantics.**

Defining new `person.current_location` writes as reported residence, preserving ambiguous legacy meaning, and dropping universal location pinning are improvements. But the precedence rule must not turn residence into an overriding answer to every whereabouts question.

Consider:

> Saved residence: Toronto.
> Recent dialogue: “I’m in Paris for the weekend.”
> Next turn: “What would be nearby?”

Toronto residence and temporary presence in Paris do not contradict one another. Choosing Toronto merely because it is a committed fact would be wrong. Conversely, the Paris visit should not become a residential move.

### Smallest sufficient correction

State that precedence applies to conflicting claims about **the same subject, attribute, scope, and relevant time**. Persistence is not a universal factual-authority ranking.

Extend scenario 22 from write-state checks to downstream use: after the temporary-visit statement, does the character distinguish home from present surroundings? This needs no new permanent whereabouts table. It is a working-context interpretation test.

The same principle applies to scoped preferences: an explicit exception can guide the present reply without globally replacing an independently stored preference.

## 7. P2 — Guard-or-withhold must be evaluated for the useful context it discards

**Classification: untested product hypothesis, not a reason to reject conservative behavior outright.**

Revision 2 correctly separates proposal accuracy, committed state, supplied evidence, and reply quality. It also correctly counts missed updates and unjustified abstention. Preserve those improvements.

The new withholding policy introduces a specific evaluation hazard:

> Unrelated subject-memory changes make an old narrative expensive to guard.
> The application withholds it.
> The reply safely says it lacks context.

That may be the correct bounded fallback. It is still a continuity failure when the withheld material was both relevant and safely usable under a simpler selection method. It must not become a success merely because the model made no unsupported claim.

### Smallest sufficient correction

Keep the expected evidence and answerability annotations independent of what the system elects to supply. Distinguish **necessary withholding** from **over-conservative loss of usable evidence**, and count the latter against retrieval/context quality.

The proposed no-summary comparison is worthwhile here. On a short, fully supplied interview exchange, recent chronological dialogue can support continuity without any summary watermark or summary-refresh semantics. That establishes a simpler representation’s sufficiency for that case—not an empirical victory on long histories.

The existing tests remain narrower evidence: context tests check instructions and construction behavior; PostgreSQL lifecycle tests use supplied proposals and verify persistence/filtering. They do not establish the conversational usefulness of guard-or-withhold.

# Disposition of the material first-round criticisms

**“Resolved” below means resolved as a design decision—not implemented or empirically validated.** The unchanged runtime must not be counted as repaired.

| First-round criticism                                                                                              | Revision 2 disposition                  | Consequence                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------ | --------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Composed preferences cannot be independently corrected or removed — A1/B1                                          | **Resolved**                            | Separate application-owned records address the structural mismatch. Legacy decomposition remains explicitly unsupported without new user clarification. |
| A known present does not determine whether the old report was true — A2                                            | **Resolved**                            | `revise(unspecified)` avoids inventing either a move or an original error.                                                                              |
| Invalidation without replacement, inactive removal, and reassertion — A4/B2                                        | **Resolved**                            | The transition contract now covers these cases and preserves gaps rather than inventing continuous truth.                                               |
| Correcting arbitrary older history without replacing the present — A2                                              | **Explicitly deferred**                 | Legitimate scope reduction; read-side historical claims must remain bounded as discussed above.                                                         |
| Current-only evidence blocks ordinary clarification — B3                                                           | **Partially addressed**                 | The Husky example is resolved. Affirmative confirmation and budget-shortened evidence windows need explicit interpretation.                             |
| Mandatory-policy truncation, pre-inclusion deduplication, stale-revision suppression, overstated telemetry — A3/B4 | **Resolved**                            | Whole-record packing, revision resolution, protected policy, and final-input manifests are the appropriate contracts.                                   |
| Unversioned entity labels bypass current fact identity — A5/B6                                                     | **Resolved**                            | Derive current names from eligible identity facts; use neutral references otherwise. Concurrent identity dependencies remain a separate issue.          |
| Ended/invalidated facts leave stale narrative as the only positive account — A4/B5                                 | **Partially addressed**                 | Guards and withholding address the right problem; watermark freshness is not yet a sufficient admission criterion.                                      |
| Shared profile knowledge is not this character’s remembered interaction — A7/B6                                    | **Resolved**                            | Compact provenance and prohibition on expanding another root’s whole message are coherent.                                                              |
| Character-private continuity cannot imply universally current world state — A7                                     | **Explicitly bounded/deferred**         | Dated dialogue replaces the proposed private current-state lifecycle. It cannot promise unseen cross-root updates.                                      |
| Continuity tables must justify their separate lifecycle — A8/B7                                                    | **Explicitly deferred**                 | The source-window comparison now precedes adoption. This resolves the sequencing criticism, not the continuity capability.                              |
| Target checks do not cover no-op staleness and semantic duplicate races — A9/B8                                    | **Partially addressed**                 | No-op staleness is honestly permitted. Mutation dependencies and intervening changes still need one complete rule.                                      |
| Capacity must not make removal impossible — A10/B8                                                                 | **Resolved as an escape-path contract** | Direct removal is available by design; restoration of normal chat is not universally guaranteed.                                                        |
| Old tests and fixtures protect superseded assumptions — A6/B9                                                      | **Resolved in the specification**       | Separate scores, actual prior assistant turns, and rejection of old promise exemplars are appropriate.                                                  |
| Location meaning, universal pins, and entity expansion — B6/recommendation                                         | **Resolved or explicitly experimental** | Residence is defined; ambiguous legacy values remain ambiguous; ranking benefits remain unmeasured.                                                     |

These dispositions follow the revised design and scenarios rather than treating the assessment’s “Use” labels as approval. The preserved reports’ architectural hypotheses remain hypotheses.

# What I would simplify before planning

**Keep the new fact lifecycle.** Separate preferences, unknown historical relationships, invalidation, inactive removal, and reassertion are meaningful distinctions. Removing them to reduce enum values would merely push their differences into exceptions.

**Prefer one conservative mutation-snapshot rule over several bespoke dependency rules.** Under the design’s accepted conflict behavior, checking a subject-memory generation for nonempty proposals is easier to reason about than separately maintaining identity, category, absence, and operator-removal dependency sets. Keep targeted versions too; they serve a different purpose.

**Do not add a second notion of factual validity through summary watermarks.** Summaries are evidence derivatives. Current-state interpretation should remain with the ledger and the supplied dialogue, not with a “fresh summary” designation.

**Keep one removal implementation with two legitimate command origins.** A direct operator action and a reviewer proposal need different provenance, but not different ownership, tombstone, version, or concurrency semantics.

**Continue deferring continuity tables and generic historical search.** Their absence is now an honest scope boundary. Do not recreate the same complexity indirectly through elaborate summary dependency tracking before the simpler source-window comparison shows a need.

This reduces independent obligations rather than merely reducing table count.

# Is revision 2 ready for implementation planning?

**Not quite ready to freeze, but close. I see two blocking design decisions—not a need for another broad architecture exercise.**

| Blocking decision                | What must be settled                                                                                                                                                                                                                                                                                                         |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Historical-context admission** | A watermark must not certify that pre-existing changes were incorporated. Either remove the delta-watermark optimization from the initial target, or specify its inherited dependency/coverage meaning. The rule must handle old dialogue compacted after a correction and acknowledge updates outside the fact ledger.      |
| **Mutation consistency**         | Choose a complete rule for nonempty proposals: preferably a conservative subject-memory generation, or fully specified dependency sets. It must cover identity-based target resolution, operator actions, and changes that disappear from the final eligible record set. Permitted stale no-op replies can remain permitted. |

The confirmation examples, scoped residence use, typed operator causation, capacity limitations, and withholding-quality checks are bounded clarifications or validation obligations. They should be incorporated without expanding the architecture. **Missing live measurements do not themselves block writing the plan**, provided the plan does not assume their outcomes.

Once those two contracts are settled, revision 2 is ready to become an implementation plan for **natural current-fact memory with bounded conversational evidence**. It is not yet a design that promises complete cross-conversation historical continuity—and it is better for making that distinction explicit.
