# Verdict: implementation planning is justified—with two narrow contract clarifications

**Revision 3 closes the previous architectural blockers.** Independent lifecycle guards no longer treat a newly generated summary as reconciled truth; the single memory generation covers identity-dependent writes and add–forget races; inactive records have an identifiable derived representation; and clarification evidence, endorsement, and operator removal now have substantially clearer contracts. These are meaningful changes, not renamed versions of the previous proposals.

**I would proceed to implementation planning rather than commission another broad architecture review.** Before freezing the affected write contracts, clarify two interactions: **same-turn removal must override saving the same assertion**, and **an explicitly contradictory reply and memory interpretation must not be committed together**.

My strongest remaining architectural concern is a deliberate tradeoff, not an undiscovered correctness guarantee: **requiring every active and inactive record before using any preceding dialogue can make ADE lose immediate conversational continuity as its memory grows.** That needs a bounded operating envelope and a meaningful comparison—not another memory framework.

## Revisions and inspection boundary

| Material                                                                                                                                         | Exact revision inspected                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Revision 3 brief, complete design, all 22 expanded scenarios, source map, round-two assessment, both preserved round-two reports, ADRs 0022/0026 | `c01f45a045eb0fdd0fc6b3e18add82f2dbb57024` |
| Runtime implementation and relevant test sections                                                                                                | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |
| Previous design’s evidence, concurrency, context, and watermark sections used for comparison                                                     | `d80afb422b3deefa09f13ac5e7017c5e3e8524ef` |

I used immutable commit references, not `main` or the moving discovery-branch head. Source inspection covered admission, turn construction, reviewer input and validation, evidence binding, commits/finalization, context and compaction, persistence schema, and source readers. Test inspection included relevant memory-policy, reviewer, context, finalization, and repository-contract tests.

**This was static public-GitHub inspection.** I did not run tests, inspect databases or services, access credentials or ignored captures, or make provider calls. All required review documents were accessible through GitHub. The six earlier synthetic reproductions remain maintainer-reported results, not executions performed in this review; missing Stage A response/wire evidence remains unavailable. The preserved round-two reports likewise distinguish their static findings from executed behavior.

Below, **source-proven** refers to the unchanged implementation; **design gap** refers to an insufficiently explicit proposed contract; **tradeoff** means the behavior is already deliberately chosen; and **hypothesis** means its practical frequency or quality impact is unmeasured.

# Prioritized findings

## 1. P1 — Preserve same-turn removal precedence when preference identity changes

**Classification: narrow write-contract gap, supported by an existing protection that must survive the redesign.**

Revision 3 allows mixed operations, independent preference IDs, user endorsement, and fresh restatement after forgetting. Those choices are individually sensible, but their interaction needs an explicit rule. Sections 4–5 do not clearly state whether a same-turn affirmation can become a fresh assertion while that same information is being removed.

Consider:

> “我确实还喜欢早上喝咖啡，但把保存的这条偏好删掉。”

The user confirms the preference’s truth **and** requests its removal from saved memory. The correct result is removal—not forgetting one ID and adding a new coffee-preference ID from the affirmative clause.

The corresponding endorsement case is:

> Assistant: “Roxy 是哈士奇吗？”
> User: “对，但这件事别保存。”

The answer establishes the breed for this conversation. It does not authorize a durable breed write, even when no existing fact is available to forget.

The baseline contains a concrete protection here: `prepare_memory_review()` tracks forgotten keys and rejects forgetting and recreating the same key within one review. `test_forget_then_add_same_key_is_rejected_instead_of_becoming_correction()` expressly protects that behavior. Once independently identified preferences can occupy the same category, retaining only a database-key check is insufficient to preserve the intent-level rule.

This is **not proof that the proposed reviewer would make the mistake**. “Add only when no matching eligible record exists” helps, but the precedence should not depend on an unstated interpretation of matching and operation order.

**Smallest sufficient correction:** state that an explicit same-turn removal or instruction not to save an assertion excludes saving that assertion from the turn’s other clauses, including endorsements and explanatory repetitions. Unrelated additions remain eligible. A later fresh user assertion can still be saved under Option A.

That is a current-turn eligibility rule, not sticky suppression, global erasure, or a return to whole-message forget-only mode.

## 2. P1 — The reply/reviewer disagreement rule is currently asymmetric

**Classification: narrow consistency gap; the failure scenario is untested.**

The shared bundle closes the previous structural problem in which the reviewer could privately use an antecedent withheld from generation. Supplying the candidate reply to review and withholding a dependent mutation when that reply asks to clarify the same unresolved claim are useful additional protections.

However, an **explicitly wrong interpretation** is not covered as clearly as an expressed uncertainty.

Constructed example:

> User: “One of my dogs is a Husky.”
> Assistant: “Rocky or Roxy?”
> User: “Roxy.”
> Candidate reply: “Got it—Rocky is the Husky.”
> Reviewer proposal: save Roxy’s breed.

Both stages received the same bundle. The reviewer’s write can be correct, yet the transaction would commit an assistant statement contradicting it. The candidate reply is not asking for clarification, so the specifically stated deferral rule does not apply.

The baseline finalizer demonstrates why this must be addressed at the semantic contract rather than attributed to SQL atomicity: it commits the prepared memory operations and `result.assistant_text` together, but does not establish that those two outputs mean the same thing. **Atomic commitment is not semantic agreement.**

The converse also matters: ordinary conversational questions should not suppress supported writes. After a clear breed statement, “How old is she?” is not unresolved uncertainty about the breed. A question mark is not a valid mutation veto.

**Smallest sufficient correction:** extend the existing reviewer’s narrow check to distinguish an unresolved dependent claim from an explicit incompatible interpretation of that claim. An unresolved claim can defer only its dependent mutation; a detected explicit contradiction should fail the atomic attempt rather than silently commit inconsistent outputs. Do not rewrite the answer behind the user’s back or add another model call.

This does not turn the reviewer into a universal truth judge. Detection remains fallible and needs semantic tests. It simply defines the outcome when the contradiction is detected.

## 3. P2 — Full lifecycle admission creates an “all memories or no dialogue” threshold

**Classification: deliberate tradeoff with a logically certain capacity threshold; its practical severity is untested.**

Section 8 now requires the complete eligible active/inactive lifecycle snapshot before admitting **any** prior narrative—including the immediate clarification bundle. If it cannot fit, prior narrative is withheld; the reviewer cannot privately retain the antecedent; dependent writes become ineligible. If the reviewer’s own full packet cannot fit, the entire turn fails. This is internally coherent and explicitly documented.

The consequence is stronger than “long-term recall is bounded”:

> ADE has accumulated many unrelated preferences and inactive records.
> It asks “Rocky or Roxy?”
> The user answers “Roxy.”
> The complete lifecycle snapshot no longer fits alongside the exchange.
> ADE discards the antecedent and asks what “Roxy” means.

The loss is caused by unrelated saved information, not by the length or difficulty of the local exchange. More memory can therefore make the character less capable of following the immediately preceding conversation.

The same effect can discard a recent “let’s leave that topic alone” request, a temporary-location report, or prior assistant replies needed to avoid repetition. These are conversational costs, not merely lower recall scores.

Revision 3 correctly includes an unrelated-memory-pressure control and says unnecessary withholding must count against answerability. Keep that requirement. But a **no-summary baseline that retains the same full-guard prerequisite cannot isolate this problem**: it may discard exactly the same short raw exchange.

**Smallest sufficient correction:** treat full-snapshot admission as a bounded initial baseline, not a permanent definition of trustworthy context. Establish its usable record/token envelope while reserving room for a complete local exchange. Distinguish a summary-removal comparison from a comparison that actually changes the admission rule for local dialogue.

I would not claim that a relevance-selected guard subset is equally safe without evidence; that would reopen the earlier coverage problem. Nor would I add a dependency graph now.

There is an immediate simplification available without weakening the rule: **when the complete bound lifecycle snapshot is already supplied, automatic retrieval cannot contribute an otherwise absent current fact from that snapshot.** The baseline always embeds the current message and searches before building context. In a full-snapshot mode, that work may be redundant unless deliberately used to improve ordering. Keep vector retrieval for selective-context paths and later experiments rather than paying for it ceremonially on every full-snapshot turn.

## 4. P2 — Budget the candidate reply before selecting the “longest fitting” shared bundle

**Classification: a bounded capacity-contract refinement, not a new architecture requirement.**

Revision 3 chooses the longest clarification suffix fitting both stages, then supplies the generated candidate reply to the reviewer. That reply is not available when the bundle is selected. Sections 5–7 require capacity checks, but the allocation should explicitly reserve the later candidate-reply input.

Counterexample:

> Lifecycle views, instructions, schema, and the shared bundle nearly fill the reviewer’s input budget.
> Generation produces a valid, somewhat longer reply.
> Adding that reply makes review impossible.
> Atomicity discards the otherwise usable answer.

Failing before sending the oversized reviewer request would obey the final-request limit. It would still be an avoidable failure if the reply allowance was predictable.

The unchanged reviewer packet does not include the candidate reply; its interface currently accepts the current message, recent users, active facts, and entities. Revision 3 therefore adds a real input-budget obligation rather than merely changing an existing field’s label.

**Smallest sufficient correction:** reserve a conservative allowance for the permitted candidate reply before selecting the shared bundle. Do not repair overflow afterward by giving the reviewer a different bundle or clipping a reply clause that could contain the relevant contradiction.

The same principle applies to tool continuations: reserve or check their actual additions without silently changing the evidence contract. No additional semantic stage is needed.

## 5. P2 — Acceptance-time generation binding protects writes but also rejects some not-yet-interpreted turns

**Classification: intentional stronger consistency tradeoff; recovery wording needs precision.**

The single generation is simpler than specialized identity/category/absence read sets, and revision 3 correctly specifies atomic advancement, rollback, operator participation, and no advancement for no-op or replay. It also deliberately binds generation at **message acceptance**, not merely when the reviewer snapshot is constructed.

That stronger rule has an important consequence:

> A turn in conversation A is accepted at G but waits for execution.
> Conversation B adds an unrelated preference and commits G+1.
> A attempts to construct its first packet and fails before determining whether its message would produce any write.

Thus “nonempty write decisions are protected” is not the entire availability contract. The acceptance-to-snapshot check can reject a turn that would ultimately have been a no-op.

The baseline does **not** queue multiple active turns within the same conversation: `RunService.accept_turn()` rejects a conversation already holding a pending or running turn. This risk concerns different conversations sharing a subject, worker scheduling, and operator actions—not an invented same-conversation queue. The same service also returns the original run for an idempotent replay.

**Smallest sufficient correction:** retain the conservative rule initially, but give generation conflicts a clear terminal meaning and recovery path. Retrying transport with the same idempotency key must return the original outcome; it must not silently acquire a new generation. Reconsideration against newer memory requires a fresh explicit admission/reconfirmation.

Do not spend retry allowance rerunning a request whose immutable accepted generation can no longer match. Conversely, do not present a conflict as “the character understood and saved your update.”

This is not a reason to add another counter or serialize provider calls. Measure harmless-conflict frequency before replacing the simpler invariant.

## 6. P2 — Ending, forgetting, and historical-context admission need a composed test

**Classification: an accepted Option A limitation with a potentially surprising conversational consequence.**

The derived inactive descriptor solves the previous identification problem: a null-valued morning-coffee record can still be selected for removal without presenting it as a current preference. Forgotten descriptors then disappear from model-facing lifecycle views. That is coherent.

Now compose those rules:

> A’s old dialogue says X is the user’s partner.
> B records the breakup; the inactive relationship descriptor supplies the ending guard.
> The user removes that saved relationship information.
> A’s old dialogue is later supplied again.

After removal, the complete **eligible** lifecycle snapshot no longer includes the ending descriptor. The old narrative remains under Option A. A complete packet can therefore contain less information needed to interpret that narrative than it did before removal.

This is **not an erasure bug** or a justification for secretly retaining the forgotten guard. Retained history is an explicit product contract. It does show why “complete lifecycle snapshot” must never become shorthand for “the supplied narrative is current.” Revision 3 acknowledges that limitation in general; it should be tested in this concrete sequence.

**Smallest sufficient correction:** add an end → forget → resume-old-conversation case. Absence of the saved ending is not evidence that the relationship resumed. Old dialogue remains an attributed report, and the reply must not invent restored current status.

The same qualification covers deferred retrospective corrections and updates unavailable because of root/archive boundaries. Do not solve missing evidence by widening those boundaries or by reintroducing a hidden historical-state system.

## 7. P2 — Endorsement support should not become a universal confirmation requirement

**Classification: useful new capability with an untested boundary, not a reason to prohibit endorsement.**

Allowing an unambiguous “Yes, she is” to establish a user report is the right correction. The assistant question supplies the proposition’s meaning, while the user’s assent supplies its authority. Role-labeled links preserve that distinction. The baseline’s current-user-only quote binding and single direct-evidence payload must change accordingly.

Two boundaries deserve care.

First, **complete messages are not necessarily complete discourse context**. A roleplay frame can fall outside the eight-message suffix while an apparently ordinary question and “yes” remain inside it. The window limit bounds evidence; it cannot prove that missing context would not change the interpretation.

Second, the rule should preserve genuinely explicit partial confirmation:

> “Yes to the first question; no to the second.”

That is different from a generic acknowledgment after several questions. Rejecting every multi-proposition exchange would make natural clarification needlessly repetitive.

**Smallest sufficient correction:** assess endorsement at the proposition level using the supplied framing, including negation and scope. Treat missing framing as an evidentiary limitation when it makes the meaning uncertain; do not assume that a short affirmative always means autobiography.

Also keep ordinary direct assertions independent of endorsement mechanics. The character should not start asking users to confirm every reported fact merely because the new evidence schema can represent confirmations.

The existing design already recognizes that binding is not entailment. These are semantic validation cases, not a request for another judge or a persistent clarification engine.

# Disposition of the round-two findings

Here, **resolved means resolved in the proposed contract**, not repaired in the unchanged runtime or proven by execution.

| Round-two finding                                                                       | Revision 3 disposition                              | Remaining consequence                                                                                                             |
| --------------------------------------------------------------------------------------- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Summary watermark is not reconciliation coverage — A1/B1                                | **Resolved**                                        | No freshness certification or guard retirement through recompaction. Full-guard cost remains untested.                            |
| Writes depend on more than target versions and final absence sets — A2/B5               | **Resolved**                                        | One generation covers identity changes and empty-again races, provided every effective writer participates.                       |
| Existing subject metadata version is not memory generation — assessment                 | **Resolved**                                        | The new meaning is explicitly distinct; implementation must not merely rename the field.                                          |
| Null inactive assertions cannot be identified — B3                                      | **Resolved**                                        | One derived lifecycle view supplies identifying content, status, and references without a second mutable description.             |
| Generation/reviewer clarification windows can diverge — B4                              | **Resolved structurally; partial behaviorally**     | Shared membership closes hidden antecedents. Explicit reply/write contradiction still needs the outcome rule in finding 2.        |
| Assent differs from bare reference selection — A4/B4                                    | **Resolved for the specified cases**                | Scope, partial endorsement, and same-turn no-save instructions remain important combined cases.                                   |
| Scenario 13 incorrectly requires preference writes from consumption — B2                | **Resolved**                                        | Explicit preference wording is positive; consumption-only wording is retained as a control.                                       |
| State precedence must match attribute, scope, and time — A6                             | **Resolved**                                        | Residence and temporary whereabouts are distinguished in both storage and downstream reply scenarios.                             |
| Operator removal needs real causation, atomic results, and bounded recovery — A5/B6     | **Resolved**                                        | Distinct operator provenance, all-or-nothing targets, and outcome replay are explicit. Deployed authorization remains unverified. |
| Historical corrections/unavailable later updates escape the ledger — A3 and B deferrals | **Explicitly deferred/bounded**                     | Historical evidence is not complete world history; removing generic history search does not eliminate narrative uncertainty.      |
| Withholding can artificially improve safety scores — A7/B evaluation                    | **Resolved methodologically; untested empirically** | Answerability is independently annotated. The comparator must actually isolate the admission rule being evaluated.                |
| Continuity tables and broad source retrieval must earn their complexity                 | **Explicitly deferred**                             | Fixed-window adequacy and actual retrieval remain separate experiments.                                                           |

These dispositions follow the revised design and scenarios, not the assessment’s recommendations alone. In particular, scenario 13’s correction and the expanded scenarios 17–22 directly address the corresponding round-two objections.

# What should stay small

**Keep one fact lifecycle and one derived lifecycle view.** The inactive descriptor is justified because it solves a concrete targeting problem. Do not create separate mutable interpretations for reviewer targeting, generation guards, and operator display.

**Keep one mutation generation.** Its conservative conflicts are easier to explain than several subtly incomplete read-set rules. It is a write-consistency mechanism, not a summary-truth certificate or a guarantee that every reply sees the latest state.

**Keep one mutation boundary with two legitimate causal origins.** Operator removal now has a coherent contract. The existing schema’s required `run_id` and message-span sources demonstrate why typed operator causation needs an explicit alternative rather than dummy runs or fabricated quotations. That extension is necessary; a parallel unaudited removal implementation is not.

**Do not perform redundant retrieval in full-snapshot mode, and do not add machinery merely to avoid admitting the mode’s limits.** Full guards, selective fact retrieval, and optional older narrative should have distinguishable purposes. Ranking experiments are not informative when the full candidate set is supplied regardless.

**Continue deferring generic historical search, retrospective repair, continuity tables, and background review.** None is required to settle the remaining narrow rules. Their absence should remain a capability boundary, not be concealed by more elaborate summary bookkeeping.

# Planning readiness and genuine remaining blockers

**Planning is justified. I do not see a remaining architectural blocker requiring another framework investigation or another broad review cycle.**

Two small normative decisions should be recorded before the affected plan is frozen:

| Required clarification                                | Recommended decision                                                                                                                                                       |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Same-turn assertion versus removal/no-save intent** | Removal or an explicit instruction not to save the same assertion wins for that turn. Repetition used to identify the target is not a fresh-save escape hatch.             |
| **Explicit reply/write interpretation conflict**      | A detected incompatible interpretation cannot commit atomically as success. Distinguish it from an unresolved dependent claim and from unrelated conversational questions. |

No new provider experiment is needed to choose those semantics. The other concerns—full-guard capacity, unnecessary clarification, harmless conflicts, endorsement accuracy, irrelevant callbacks, latency, and useful recall—belong in bounded validation, with results allowed to disprove the chosen baseline.

The inspected tests currently establish narrower properties: memory-policy tests validate supplied proposals, reviewer tests still protect old mode-specific schemas, context tests assert construction and instruction presence, and finalization/repository tests exercise lease or source-boundary behavior. They are not evidence that revision 3’s conversational behavior works.

**Bottom line:** revision 3 is a coherent basis for implementing natural current-fact memory with bounded conversational evidence. Its greatest remaining risk is not insufficient safeguards; it is allowing safeguards to make the character repeatedly forget the conversation immediately in front of it. Preserve the foundation, settle the two narrow write rules, and let the bounded validation determine whether the conservative context policy is useful enough to keep.
