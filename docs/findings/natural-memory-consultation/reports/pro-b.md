# Verdict: targeted revision, not an architectural replacement

**Keep ADE’s foundation, but revise the proposal before implementing its new memory contracts.** The strongest reasons are not the already-acknowledged regex gate or absence of episode storage. They are that:

* **A composed preference string is the wrong unit for independent correction, change, and removal.**
* **The proposed lifecycle does not fully cover retraction without replacement or removal of inactive information.**
* **Current-message-only evidence cannot support some ordinary clarification exchanges.**
* **Existing context assembly can omit relevant facts, truncate mandatory policy, and misreport which retrieved evidence reached the model.**

I would address those before adding continuity tables. The existing code already provides substantial infrastructure worth preserving: subject-bound facts, revision lineage, current-revision search, optimistic mutation checks, and transactional finalization of the assistant reply with memory changes. Those are real implementation properties, not merely aspirations in the proposal.

## Revisions and evidence boundary

| Material                                                                                                                                   | Exact revision inspected                   |
| ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Review brief, proposed design, all twelve worked conversations, source map, consultation assessment, and selected imported-report sections | `243d8d0b4e850aca304eea2699e58ec24d45479b` |
| Runtime implementation, persistence metadata/repositories, relevant tests, selected M1/M2 fixtures, and Stage A offline diagnosis          | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |

I used pinned revisions, not `main` or the moving discovery-branch head. I inspected the seven test entry points named in the source map, using targeted portions of the larger executor test file, alongside the relevant write, retrieval, context, compaction, and finalization implementations.

**This was source inspection, not a test execution or deployment audit.** I did not inspect databases, services, credentials, ignored captures, or provider requests. The committed Stage A diagnosis is maintainer-reported evidence; its missing response text and wire request cannot establish what the model actually saw or why it omitted the tool call.

Runtime paths below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`. **P1** means resolve before implementing the affected contract; **P2** means a material design decision, test requirement, or bounded tradeoff.

# Prioritized findings

## 1. P1 — Composite preferences are a lifecycle problem, not just a rewriting-quality risk

**Classification: demonstrated representation mismatch.**

The proposal preserves one `person.preference` value per category, composing compatible clauses into it. The existing `fact_registry.py:fact_key` identifies a preference by type, entity, and category. `memory_policy.py:prepare_memory_review` permits only one mutation per fact per review, while the proposed revision reason applies to the whole revision.

Consider this sequence:

> “早上我喜欢咖啡。”
> “晚上我喜欢花茶。”
> “只移除保存的咖啡偏好，花茶那条保留。”

Once both preferences occupy one value, neither available approach matches the intended operation cleanly. Forgetting the record removes both preferences. Revising it to contain only flower tea preserves coffee in that record’s historical chain—but the proposed historical-search contract excludes forgotten **fact chains**, not selectively forgotten clauses.

The same problem affects change-versus-error semantics:

> “早上现在改喝豆浆。晚上那条之前说错了，我一直喝的是红茶。”

One clause is superseded; another was erroneous. A single whole-record reason cannot faithfully describe both predecessors. This remains a problem even with a perfect language model.

**Smallest sufficient correction:** relax cardinality **only for preferences**. Store independently mutable scoped preferences as separate records using the existing fact/revision/source machinery. Keep the category, add stable application-owned assertion identity, and preserve scope in a bounded representation. Mutations target record ID and version; the UI may compose several preferences for display.

Do not introduce a universal assertion graph or pretend natural-language scopes have an easy canonical taxonomy. The necessary property is narrower: **independently removable information needs an independently addressable lifecycle.**

Existing composite values should remain explicitly legacy unless a supported edit establishes how to separate them. Do not infer a clean historical decomposition through bulk rewriting.

## 2. P1 — The proposed transition set is not closed over ordinary correction and removal

**Classification: design gap, with an existing active-only restriction that must change.**

The proposal distinguishes changed circumstances from erroneous facts, but its operation table lacks a clear way to represent:

> “我以前说住在北京是说错了。我不想说实际住在哪里。”

There is no replacement value. Ordinary `end` would preserve Beijing as formerly true; `forget` would invent removal intent; leaving the fact active is incorrect. The proposal specifies correction as an active next version and ending as historical cessation, so neither expresses this case adequately.

There is a second closure problem:

> “我和小王分手了。”
> Later: “把保存的那段关系信息移除。”

The first turn makes the relationship inactive under the proposal. But the current reviewer receives active facts, and `_validate_existing_fact` requires an active target for correction or forgetting. Adding an inactive state without revising target discovery and validation would make ended information harder to remove than active information.

**Smallest sufficient correction:**

Allow erroneous information to be invalidated without a replacement—for example, a nullable correction that produces an inactive current projection and a disputed predecessor. Also allow explicit removal to target any eligible nonforgotten record, including inactive records. Supply relevant inactive targets to reconciliation without enabling unrestricted transcript search.

Write a small transition table covering active, inactive, and forgotten records, including reassertion after ending. Do not leave these cases to prompt interpretation.

For historical answers, derive the old revision’s interpretation from the revision chain: an old `add` followed by a correction is not automatically a once-true fact. Preserving legacy `correct` semantics as unknown rather than retrospectively classifying them is the right proposal choice.

## 3. P1 — The evidence rule prevents some natural clarification-based learning

**Classification: demonstrated validation limitation; proposed contract remains underspecified.**

The reviewer receives recent **user** messages, not the intervening assistant questions. Earlier user messages are reference-only; `prepare_memory_review` binds new evidence exclusively to the current message. For an add, value support comes from that current evidence—not an earlier unresolved user assertion.

A supported-type counterexample:

> User: “我的两只狗里有一只是哈士奇。”
> Assistant: “是 Rocky 还是 Roxy？”
> User: “Roxy。”

Assume neither dog has a saved breed. The last message resolves the earlier ambiguity, but it does not itself contain “哈士奇.” The current policy cannot validate the resulting breed addition from that message alone. Requiring the user to repeat the entire proposition defeats the natural-conversation goal.

**Smallest sufficient correction:** require a **current user authorization anchor**, while permitting bounded supporting spans from earlier user messages supplied by ADE. Include the immediately relevant assistant exchange for reference resolution, but never treat assistant-generated claims as factual evidence.

This is not background catch-up extraction. It is a narrow rule: the current user turn resolves or confirms a specific earlier user assertion, and the resulting write cites both.

The persistence API already accepts multiple source records per revision; the narrower constraint is in proposal binding and preparation. Existing predecessor links preserve old evidence, but the current commit path writes only the latest operation’s evidence into the new revision’s direct source list. That distinction matters when retained content depends on earlier sources.

Finally, `_value_supported` is lexical support checking, not entailment: its term-set comparison cannot establish ownership, negation, or preservation of scope. The proposal correctly acknowledges this. Keep mechanical checks, but evaluate semantic errors rather than describing lexical acceptance as proof.

## 4. P1 — Fix context packing before evaluating a better selection policy

**Classification: demonstrated source-level defects; not dependent on model behavior.**

`context.py:build_context` contains three particularly consequential problems.

**Mandatory policy can be truncated.** The implementation concatenates the system prompt, persona, and memory rules, then truncates that whole string to `prompt_tokens`. A sufficiently long prompt/persona can remove the memory rules at the end, even when the overall model context has room. `validate_current_user_message` uses the same truncated construction.

**Deduplication happens before actual inclusion is known.** The profile is rendered and truncated as a string. However, `active_ids` contains every supplied profile fact, including facts whose text was cut off. Retrieval then removes matching IDs. A relevant fact can therefore disappear from the profile and also be excluded from retrieval.

**Retrieval telemetry can overstate supplied evidence.** `retrieved_fact_ids` is derived from the pre-truncation retrieval list, not the records whose complete text survived serialization.

A simple counterexample is a long preference placed ahead of a relevant location fact. The location is among the twelve profile candidates but outside the rendered profile budget. Even if vector retrieval finds it, ID-based deduplication suppresses it.

These issues would contaminate a recency-versus-relevance comparison: a retrieval failure might actually be a serialization failure.

**Smallest sufficient correction:** select and budget **whole records**, then serialize them. Deduplicate against records actually included, using revision identity where necessary. Record the exact included IDs, versions, and source references.

Mandatory policy must have a separately protected budget and fail explicitly when it cannot fit; it must not be silently shortened. Measure the complete provider request, including tool policy, schemas, and tool-result continuations—not merely the initial context object. The executor adds material after `build_context`, so initial-request accounting alone is insufficient.

There is also an **untested injection risk**: stored values and narrative summaries are directly interpolated into the system message. Separate normative instructions from clearly marked untrusted memory data. That reduces an avoidable trust-boundary problem; it does not prove immunity to prompt injection.

The proposal already says not to truncate mandatory policy. Make this an early prerequisite, not something deferred behind ranking experiments.

## 5. P1 — Ending a fact can leave stale summaries as the only positive account

**Classification: demonstrated stale-context path; the resulting bad reply is a hypothesis to test.**

The proposal says current information should outrank stale summaries. That is necessary but insufficient when a change has **no replacement active value**.

Counterexample:

> Conversation A’s summary says Xiaowang is the user’s partner.
> In conversation B, the user reports a breakup; the relationship becomes inactive.
> The user returns to A and asks for weekend suggestions.

A no-longer-active relationship disappears from active-fact selection. A’s existing summary remains available. There may therefore be no current negative state in context to override “Xiaowang is your partner.”

The implementation loads a conversation’s latest summary independently of subject fact changes. Compaction preserves narrative preferences, commitments, unresolved questions, and relevant assistant responses; it does not reconcile the summary against current subject facts.

**Smallest sufficient correction:** make relevant endings and retractions available as current-state information, rather than treating them solely as material for historical questions. Give summaries an explicit temporal boundary and, preferably, a lightweight memory-state marker so the application can recognize that they predate subject changes.

For current-state claims, an old summary must not substitute for an absent current projection. Use an up-to-date state guard, qualify the statement as historical, or abstain. This does not require rebuilding every summary after every write.

Also amend the existing “committed facts only” instruction so it unambiguously permits responding to a clear **current user update before persistence**. The proposal intends that precedence, but the baseline instruction can be read more narrowly.

**This is separate from forgetting.** Under Option A, old messages and summaries may still contain removed information. That retention is intentional, not an erasure bug. Do not silently implement global suppression while fixing current-state accuracy.

## 6. P2 — Ownership is mostly sensible, but provenance must survive into model context

**Classification: sound proposed scope with attribution and derived-state gaps.**

Using subject scope for shared profile facts and subject-plus-definition-root scope for character continuity is coherent. Existing definition roots and immutable versions support that distinction. A persona version should be provenance, not a new memory owner; a genuinely different character should receive a different root.

However:

> Character B may legitimately know that the user lives in Toronto.
> That does not authorize B to say, “You told me last Tuesday when we discussed your move.”

`turn_execution.py:_context_fact` strips a fact down to ID, key, value, and version. `_tool_fact` adds type, qualifier, and distance, but not source message, time, or originating character context. Shared knowledge and remembered interaction are therefore not distinguishable from those records alone.

**Smallest sufficient correction:** attach a compact provenance envelope to selected evidence: revision identity, user attribution, observation time, and whether the evidence belongs to this character’s conversation history or only to the shared subject profile. Do not expose another root’s full transcript merely to provide provenance for an intentionally shared fact.

There is a related concrete derived-state issue: entity labels are created separately from identity facts. Correcting `pet.name` does not update the corresponding `memory_entities.label`, while all entity labels are supplied to the reviewer. A Rocky→Roxy correction can therefore leave an unqualified Rocky label alongside the current Roxy fact. The stale label is demonstrated; resulting entity confusion is not.

Derive current display identity from eligible identity facts, and distinguish historical aliases explicitly. This is not a demand to erase old names.

For retrieval, exact entity matches should also expand to that entity’s eligible facts within budget. `_fact_document` contains type, qualifier, and value, but no entity name; retrieving a dog’s name does not itself guarantee retrieval of its breed. That is a more directly grounded improvement to test than adding elaborate ranking machinery.

## 7. P2 — Continuity entries have not yet earned their lifecycle complexity

**Classification: architectural hypothesis, not demonstrated inferiority of entries.**

The question is not whether three tables are excessive. Three tables can be reasonable for independently versioned, source-linked records. The larger cost is introducing another extraction, matching, updating, forgetting, scope, and selection contract.

The proposal’s twelve scenarios already expose a useful comparison:

* Surgery/interview exchanges can often remain coherent from recent dialogue or a bounded source window.
* The museum-discussion scenario specifically needs conversation evidence.
* The proposed entries deliberately defer dialogue events, so entries alone do not solve that museum case.

That does **not** prove transcript retrieval will select the right evidence reliably. It proves that there is a credible smaller representation to compare before introducing another durable semantic store.

**My recommendation: defer production continuity tables and compare bounded history first.**

Use eligible, same-subject/same-root source windows carrying speaker, time, conversation, and message identifiers. Include both the originating episode and relevant later updates. First establish representation adequacy with fixed evidence; then test actual selection under the same budget. This is not authorization for broad production transcript retrieval.

If entries remain necessary, narrow their first contract. The current `plan | concern | event` and `open | resolved | recorded` taxonomy does not fully determine whether an interview produces one evolving topic or several overlapping records. Those alternatives have different duplication and resolution costs.

Also distinguish **truth status from selection relevance**. An unresolved entry should not remain emotionally urgent forever. An old statement containing “tomorrow” must be rendered relative to its source date, not as an evergreen upcoming event. Passage of time need not resolve it, but neither should `open` imply “bring this up.”

Do not replace three explicit tables with an opaque narrative blob merely to reduce table count. Reduce the number of behaviors requiring independent correctness.

## 8. P2 — Atomicity protects proposed mutations, not all reconciliation decisions

**Classification: demonstrated concurrency boundary; stronger isolation is a product tradeoff.**

The finalizer rechecks cancellation, lease ownership, conversation version, and proposed memory mutations inside a transaction. This is a strong foundation. It does not compare a subject-memory snapshot version or revalidate a reviewer’s empty decision.

Consider:

> A reads Beijing. Its current user message repeats “I live in Beijing,” so its reviewer proposes nothing.
> B changes the subject’s residence to Toronto and commits.
> A finalizes successfully with its empty decision.

There is no stale target version to reject. The latest successful conversation can therefore contain a current-state assertion that never participates in reconciliation against the intervening change.

This is compatible with the proposal’s weak concurrent-dialogue guarantee. It is **not** equivalent to saying all conflicting reconciliation decisions fail. The guarantee should be stated as protection against stale **proposed mutations**, with no-op staleness treated separately.

For the initial slice, retaining that narrower guarantee is defensible. Test it explicitly. If stronger reconciliation ordering becomes necessary, a subject-memory generation check is a much smaller correction than holding locks during generation or adding a scheduler. It will reject some harmless concurrent work, so that cost should be explicit.

The synchronous failure boundary is also defensible initially: a failed reviewer or required embedding prevents the assistant reply from committing. Do not call this a storage defect, but include it in product availability and latency measurements—not just memory accuracy.

One recovery issue needs specification: **a full reviewer input budget must not make removal impossible.** The proposed capacity failure and the existing UI’s reviewer-mediated removal path can collide. Ensure a bounded, explicitly targeted removal/recovery operation can still execute at capacity; general candidate-only extraction is not required to provide that escape hatch.

## 9. P2 — Evaluation separation is right in the proposal, but the fixtures and telemetry need tightening

**Classification: existing evidence limitations plus concrete specification improvements.**

The proposal already correctly separates write correctness, selected evidence, and conversational quality. I would preserve that rather than criticize it for a conflation it explicitly rejects.

The existing tests establish narrower things:

| Evidence inspected                 | What it can establish                                                                   | What it cannot establish                |
| ---------------------------------- | --------------------------------------------------------------------------------------- | --------------------------------------- |
| Reviewer tests with fake transport | Packet/schema construction, validation and repair behavior                              | Natural-language extraction reliability |
| Memory-policy tests                | Mechanical acceptance/rejection of supplied proposals                                   | General semantic entailment             |
| PostgreSQL lifecycle test          | Revision/source lifecycle and current-revision/subject filtering with synthetic vectors | Semantic retrieval quality              |
| Context tests                      | Selected prompt instructions and budgeting behavior in their cases                      | Actual reply compliance                 |
| Executor tests                     | Tool protocol and argument boundaries                                                   | Whether recall was useful or needed     |

These distinctions are visible directly in the test implementations. None of these tests was executed in this review.

Two fixture details deserve attention.

First, M1’s `repetitive_callback.json` supplies only one user message and memories saying the user repeatedly mentioned early rising. That can test restraint in one response, but not repeated **assistant** callbacks across a conversation. A repetition test needs the actual prior assistant replies.

Second, M2’s comparison fixture contains assistant exemplars asserting future memory behavior and nonmention, including a response to “forget this and never mention it again.” Those are historical fixture contents, not acceptable exemplars under the later Option A reply boundary. Mark them as such when reused; otherwise a chronology fixture can quietly teach the behavior the new policy prohibits.

The Stage A tool failure should remain a conformance finding, not evidence that memory storage needs replacement. Its missing context capture prevents stronger causal conclusions.

**Smallest sufficient correction:** score the evidence actually serialized after packing, annotate supported versus currently unsupported capabilities, preserve abstentions and failed turns, and evaluate attribution rather than keyword presence. Suggesting jasmine tea is not the same error as claiming the user previously preferred it.

# Recommended simplified design

The first milestone should have **one durable fact system, ordinary conversation evidence, and one bounded context assembler**—not two competing semantic memory systems.

| Component                                                                                | Recommendation                                                                                                                                            |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| PostgreSQL, immutable messages, subjects, revisions, source evidence, embedding identity | **Keep.**                                                                                                                                                 |
| Reviewer execution                                                                       | **Keep one synchronous post-response call.** Replace mutually exclusive add/correct/forget modes with mixed, evidence-bound reconciliation.               |
| Fact representation                                                                      | **Keep existing types**, but make independently mutable preferences independently addressable.                                                            |
| Lifecycle                                                                                | Add change-versus-error semantics, invalidation without replacement, and removal of eligible inactive records. Preserve legacy uncertainty.               |
| Evidence binding                                                                         | Current user authorization plus narrowly bounded supporting user spans; assistant text is reference context, not factual authority.                       |
| Context assembly                                                                         | Protect mandatory policy; select whole records; carry revision/provenance; include relevant terminal state; measure the actual request.                   |
| Continuity storage                                                                       | **Defer.** Compare bounded history against entries before accepting another durable lifecycle.                                                            |
| Broader machinery                                                                        | Defer graphs, background extraction, reflection agents, mention scores, temporal interval engines, framework replacement, and global suppression/erasure. |

The resulting path remains familiar:

**Accept user message → assemble bounded evidence → generate → reconcile once → validate → embed changed facts → revalidate and atomically finalize.**

The principal simplification is to make the **unit of meaning match the unit of mutation**, while keeping source conversation available as evidence. It is not to hide several independent assertions inside one value and ask the reviewer to preserve their separate histories.

I would also avoid choosing a universal name/location pinning rule yet. Repair packing first, then compare minimal identity context against relevance-based selection. Define whether `person.current_location` means residence or temporary whereabouts before treating it as a stable default: “I’m in Paris for the weekend” must not silently become a residential move.

# Short validation sequence

**1. Freeze a transition-and-evidence specification.**
Convert the twelve arcs into chronological state checkpoints, then add the counterexamples above: partial preference removal, mixed error/change, retraction without replacement, removal after ending, clarification-based breed assignment, stale cross-conversation summary, and concurrent no-op reconciliation. Annotate permitted sources and forbidden claims before running a model.

**2. Test deterministic infrastructure first.**
Cover long-persona policy retention, whole-record packing, post-truncation evidence IDs, entity labels, current/history/forgotten filtering, source ownership, fresh and populated migrations, rollback expectations, cancellation, and finalization races. These should not require provider calls.

**3. Test reconciliation independently.**
Under an explicitly approved bounded provider budget, compare the current reviewer with the candidate using the same evidence. Score missed updates, false writes, wrong transition reasons, wrong entities, and unsupported evidence separately. Do not reroll failures into successes.

**4. Test retrieval with a correct seeded store.**
Hold write state constant. Compare the repaired baseline against exact-entity expansion and the proposed selection policy at equal token budgets. Inspect the final serialized evidence, not merely search results. Separately compare bounded source windows with continuity entries; do not attribute extraction errors to retrieval.

**5. Test conversation quality, then a small integrated replay.**
Use identical supplied evidence for blinded comparisons of relevance, warmth, restraint, attribution, and multi-turn repetition. Then run chronological end-to-end cases, including failures and immediate new-conversation follow-ups. Require zero observed boundary violations in that defined suite, without presenting that as proof of universal reliability.

**Bottom line:** ADE does not presently need a new memory framework. It does need a more precise fact lifecycle and a trustworthy context boundary. Continuity entries should remain an experiment until they demonstrate an advantage over bounded conversation evidence; composite preferences should not remain the default merely because they avoid a small, targeted cardinality change.
