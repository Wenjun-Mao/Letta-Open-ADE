# Verdict: implementation planning is justified, with one read-contract correction and one policy choice still to settle

**Revision 3 has a coherent core.** It resolves the earlier watermark error, replaces specialized mutation-dependency rules with a comprehensible concurrency boundary, and gives clarification, endorsement, inactive records, and operator removal explicit contracts. I would preserve those decisions rather than reopen framework selection or introduce another memory subsystem.

The main remaining concern is **over-conservatism moving from a safety measure into a restriction on ordinary conversation**. Requiring the entire lifecycle snapshot before supplying even the immediately preceding exchange creates a predictable continuity failure at a capacity threshold. Separately, the active-fact-only fallback lacks a specified way to retrieve useful ended or invalidated state, despite that state now being represented correctly.

My recommendation is **proceed toward a bounded implementation plan, not freeze revision 3 unchanged as the production context policy**. Resolve the selective read scope, and explicitly treat the full-snapshot admission rule as a conservative candidate whose usefulness must be tested. Neither requires another broad architecture cycle.

## Revisions inspected and access limits

| Material                                                                                                                                         | Exact revision                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Revision-3 brief, complete design, all 22 expanded scenarios, source map, round-two assessment, both preserved round-two reports, ADRs 0022/0026 | `c01f45a045eb0fdd0fc6b3e18add82f2dbb57024` |
| Previous design’s evidence, processing, context and historical-boundary sections, used for comparison                                            | `d80afb422b3deefa09f13ac5e7017c5e3e8524ef` |
| Implementation and relevant test sections                                                                                                        | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |

Source inspection covered turn admission, execution, context assembly, compaction, review schemas and policy, memory commits, successful finalization, retry handling, current-fact search, and relevant persistence metadata. I also read relevant context, reviewer, memory-policy, finalization and PostgreSQL lifecycle tests.

**All required public review documents were accessible.** I used pinned commits, not `main` or the moving discovery-branch head. I did not execute tests, access services or databases, make model-provider calls, or inspect credentials and ignored captures. Earlier synthetic reproductions remain maintainer-reported evidence, not experiments independently repeated here. The round-two reports likewise describe source inspection rather than executed runtime validation.

Below, **source-proven** refers to the unchanged implementation. Counterexamples involving revision-3 behavior are **design reasoning**, not claimed deployed failures.

# Prioritized findings

## 1. P1 — Ended and invalidated state needs a selective recall route, not only a place in the complete guard packet

**Classification: remaining read-contract gap.**

Section 4 now gives inactive records a useful derived representation: identifying assertion, scope, status, reason and provenance. That resolves the problem of targeting null-valued records. However, section 8 describes the fallback without prior narrative as **budgeted active-fact selection**. The existing `MemoryRepository.search_active_facts()` also explicitly filters to active records and current embeddings. No selective inactive-state lookup is specified for that fallback.

### Counterexample

The user previously reported a relationship with Xiaowang, then explicitly reported a breakup. The record is correctly inactive/ended.

Later, the complete lifecycle snapshot cannot fit the response allocation, although the reviewer’s packet can fit its separate allocation. The current user asks:

> “我后来是不是跟你说过，我和小王分手了？”

The identifying ending descriptor is short and relevant. Yet an active-only selection or search cannot return it. The post-response reviewer may see the inactive record, but that is too late to make the already-generated reply useful.

This is not a requirement for arbitrary retrospective history search. **The ending is part of the system’s latest understanding of that relationship.**

### Smallest sufficient correction

Use the same **current lifecycle view** for selective memory recall as for targeting and guards. Relevant ended or invalidated descriptors should be eligible alongside active assertions, while forgotten chains remain excluded.

That means returning something like:

> “The latest recorded update says this particular relationship ended.”

It does **not** mean returning arbitrary prior revisions, asserting that the user has no partner, or treating a withdrawn claim as true.

This is the clearest remaining contract correction. It strengthens the proposal’s existing “one lifecycle view” principle rather than adding a new subsystem.

## 2. P1 — The complete-snapshot prerequisite creates a discontinuous loss of ordinary conversational context

**Classification: deliberate tradeoff with a logically demonstrable capacity consequence; frequency and user impact are unmeasured.**

The new rule is unambiguous: before admitting a clarification bundle, older dialogue, a summary or an experimental source window, supply **all eligible active and inactive lifecycle views**. If that snapshot does not fit, withhold the prior narrative. This does close the “fresh summary incorrectly considered current” counterexample without a summary-dependency engine.

But it also couples very local conversation to the size of the entire saved-memory collection.

### Counterexample

The immediately preceding exchange is:

> User: “明天面试，有点紧张。”
> Assistant: “最担心哪一部分？”
> User: “自我介绍。”

Suppose unrelated saved preferences and inactive descriptors make the complete lifecycle snapshot exceed the generation allocation. The recent exchange itself is tiny.

Under the proposed rule, the antecedent is withheld, and the current phrase becomes harder to interpret. The character can ask the user to restate something it was just discussing, even though the problem is unrelated memory pressure—not missing historical evidence.

There is a second consequence: **ending or invalidating records does not necessarily reduce this pressure**, because their descriptors remain eligible. Eventually, restoring space may require saved-record removal rather than ordinary lifecycle updates. That is an acceptable bounded-capacity limitation only if it is made explicit; it is not an unlimited natural-continuity design.

### The proposed comparator needs a sharper definition

A “no-summary baseline” will not isolate this tradeoff if it retains the same full-snapshot prerequisite for raw recent dialogue. In the short interview example there may already be no summary; both variants would lose the same exchange.

The useful comparison must distinguish **removing summaries** from **removing the global prerequisite for immediate dialogue**. Scenario 19 correctly calls for counting lost answerability, but the alternative policy needs to be independently specified.

### Smallest sufficient correction

Do not silently weaken the guard rule or introduce a semantic dependency graph. Instead:

**Treat full-snapshot admission as a conservative bounded baseline, not an already-accepted production necessity.** Compare it with a small recent-dialogue-first candidate using selected current-state and terminal-state evidence under the same total budget.

That alternative may have worse stale-state behavior; it has not earned adoption. Conversely, full-snapshot admission has not earned adoption merely because it avoids selecting guards. The comparison must include both the breakup counterexample and unrelated-memory-pressure cases.

For a first small-memory slice, retaining the complete packet may be reasonable. The supported operating range and the cost of unnecessary withholding must then be explicit. This is the most important remaining product-policy choice.

## 3. P2 — The acceptance-time generation fence is defensible, but its recovery semantics must be explicit

**Classification: sound concurrency design with a broader availability cost than “reject stale writes” alone suggests.**

The generation rule now covers the important cases that specialized read sets left unclear: changed identity dependencies, add-then-forget races, operator mutations, and rollback. Capturing the generation at acceptance also prevents an old pending turn from being silently interpreted as a fresh post-removal statement. I would not casually move that capture later.

However, a generation mismatch **before packet construction** rejects a turn before the reviewer can determine that it would make no writes.

### Counterexample without simultaneous provider execution

Two different conversations share one subject and have pending turns accepted at generation G. The first processed turn changes a preference and commits G+1. The second pending turn merely says:

> “晚安。”

The second turn conflicts when constructing its initial snapshot—even though it would probably produce an empty review.

This follows from the proposed contract. It does not contradict the narrower allowance for an already-running no-op reply whose snapshot was established earlier.

The baseline permits pending runs in different conversations, rejects another pending/running turn only within the same conversation, and its worker loop processes one claimed run at a time per worker. Thus the queued-turn case deserves testing independently of simultaneous model calls.

### Retry is not the same as resubmission

Once G is stale, another attempt bound to G cannot make it current again. The baseline retries selected transport/timeout failures, reuses the claimed run, and calls successful finalization outside the retry wrapper. Idempotent admission also returns the original accepted run rather than creating a fresh user message.

**Smallest sufficient correction:** explicitly classify a memory-generation conflict as terminal for that accepted run. Same-key replay returns that outcome; it must not silently refresh the snapshot. A fresh attempt against current state requires a deliberately new submission.

That distinction matters after removal. Automatically cloning an old failed request with a new idempotency key would defeat the user-intent boundary the acceptance fence was meant to preserve.

Keep the single counter rather than rebuilding fine-grained dependencies now. Measure queued rejection, in-flight write conflict and permitted stale no-op completion separately. They are different outcomes, not one “concurrency failure rate.”

## 4. P2 — Full-snapshot prompting makes ordinary fact retrieval redundant, while the baseline still depends on it

**Classification: source-grounded simplification opportunity.**

When prior dialogue is admitted, revision 3 supplies every eligible active assertion as part of the lifecycle snapshot. Under an unchanged generation, active-fact search cannot discover an omitted active fact: none was omitted.

Yet `TurnExecution.execute()` currently performs a query embedding and automatic search before generation, regardless of whether the available profile already supplies everything needed. Optional `search_memory` searches the same active-fact store.

### Counterexample

A short goodnight reply has a complete lifecycle packet and its recent dialogue available. The automatic query-embedding request fails. If the baseline execution order is retained unchanged, that otherwise answerable turn can fail before conversation generation.

This is an existing dependency in the baseline, not an observed revision-3 failure. The new full-packet rule makes its redundancy particularly clear.

### Smallest sufficient correction

Where the complete snapshot is supplied, **reuse it rather than retrieving the same records through another provider call**. Keep the vector foundation and the selective retrieval path for cases where they actually select evidence. Required-tool conformance remains a separate contract.

Similarly, decide whether old narrative is admissible before undertaking optional compaction solely to supply it. The current implementation plans and executes compaction before building the final context; revision 3 should not inherit a failure dependency on a summary that its own policy will withhold.

This is a genuine reduction in independent failure points. It does not require asynchronous review, looser write validation or replacement storage.

It also clarifies evaluation: under full-snapshot admission, ranking can affect ordering and presentation, but generally not which active facts reach the model. Do not describe that comparison as a test of selective retrieval coverage.

## 5. P2 — Shared clarification evidence closes the original gap, but introduces a budget dependency and a fallible reply-based veto

**Classification: resolved evidence contract with adjacent implementation and behavioral risks.**

The endorsement distinction is now appropriate. A bare name resolves a reference; an unambiguous affirmative answer can endorse a proposition. Persisting role-labeled references avoids pretending that the user literally authored words supplied by the assistant’s question. The candidate reply is reference-only, and the same selected bundle reaches generation and review. These are substantive improvements.

Two interactions remain worth making precise.

### The reviewer must have room for the reply that does not yet exist

The bundle is selected before generation, but the reviewer now receives the candidate reply as additional input.

A packet can fit with lifecycle views, instructions and the chosen bundle, then overflow when a long generated reply is appended. Shrinking the reviewer’s bundle afterward would break the shared-evidence contract; discarding the reply would preserve correctness but create an avoidable chat failure.

**Minimal correction:** reserve space for the bounded candidate reply when choosing the shared bundle. Final-request validation remains necessary, but it should be a backstop rather than the first point where this predictable input is counted.

This matters because the baseline reviewer has no candidate-reply argument; it is a real new input dependency, not something already covered by its current packet.

### A clarification question should veto only the dependent mutation

Consider:

> User: “Roxy。另外，我们已经搬到多伦多了。”

The proposed reply asks which dog the user meant. Deferring the unresolved breed assignment is reasonable. The self-contained residence update should remain eligible.

Revision 3’s wording already supports this narrow interpretation. Preserve it. Do not implement “reply contains a question” as a whole-turn no-write rule.

Likewise:

> “Roxy 是那只哈士奇——她今年多大了？”

The question asks about age; it does not necessarily express uncertainty about breed. Whether the reviewer incorrectly vetoes the breed write is an empirical question.

**Minimal correction:** keep the veto claim-specific and score false vetoes as missed writes. “Defer” should mean no dependent write on this turn with an observable reason—not an implied pending job that a future “thanks” will silently complete.

No additional judge or persistent clarification engine is justified.

## 6. P2 — Forgetting is internally coherent, but two user-visible outcomes need explicit coverage

**Classification: consequences of the accepted limited-removal contract, not erasure bugs.**

The operator command now has the right structure: exact targets, versions and displayed generation; server-bound ownership; all-or-nothing effects; atomic action outcome; distinct causal provenance; and idempotent outcome replay. The baseline’s required `run_id` and message-source fields genuinely need an alternative causal origin, which revision 3 explicitly acknowledges rather than disguising as a dummy chat.

The remaining concern is presentation, not another mutation mechanism.

**First, removal can increase historical exposure under the new admission rule.** A lifecycle packet is too large, so an old summary is withheld. Removing enough records makes the packet fit, allowing that retained summary back into context. It may contain the removed information.

Option A permits this. The surprising interaction should nevertheless be tested and reflected in operator wording: removing saved records does not promise reduced exposure from every retained-history source.

**Second, replayed success is historical action success, not a fresh assertion about current memory.** Suppose action A removes record F; the user later explicitly states the information again, producing F2; replaying action A returns its original success. That must not be presented as proof that the information is currently absent.

The smallest correction is to distinguish the recorded action outcome from a current-state readback. No sticky suppression rule is needed. ADR 0022’s limited removal promise and ADR 0026’s prohibition on premature or excessive claims should remain intact.

# Disposition of the round-two findings

“A” and “B” refer to the preserved round-two reports. **Resolved means resolved in the proposed contract, not implemented or validated.**

| Round-two finding                                                                           | Revision-3 disposition    | Assessment                                                                                                                                                       |
| ------------------------------------------------------------------------------------------- | ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A1/B1 — watermark recency is not reconciliation coverage**                                | **Resolved**              | Guard applicability no longer depends on summary creation or recompression. The full-packet replacement has a separate usability cost.                           |
| **A2/B5 — selected absence checks miss identity dependencies and intervening changes**      | **Resolved**              | One monotonic generation covers nonempty writes and operator effects. Acceptance-time rejection and recovery need explicit operational treatment.                |
| **B3 — inactive null records cannot be identified semantically**                            | **Resolved**              | The last identifying assertion is derived and labeled as withdrawn. Selective recall of that state is the new gap in finding 1.                                  |
| **A4/B4 — reference selection differs from affirmative endorsement**                        | **Resolved**              | Authority and referent roles are distinguished, with positive and negative scenarios. Semantic reliability remains untested.                                     |
| **B4 — generation and reviewer can receive incompatible clarification windows**             | **Resolved structurally** | One shared bundle prevents reviewer-only antecedents. Reply reserve and false vetoes remain validation obligations.                                              |
| **B2 — consumption wording incorrectly mandates preference writes**                         | **Resolved**              | Scenario 13 now separates an explicit-preference positive case from the consumption-only control.                                                                |
| **A6 — residence must not override temporary whereabouts**                                  | **Resolved**              | Precedence is scoped to the same attribute, scope and time; scenario 22 now tests downstream use of the Paris visit.                                             |
| **A5/B6 — operator removal needs honest provenance, atomicity and bounded recovery claims** | **Resolved**              | The command is explicitly distinct from conversational review and does not promise to cure every capacity problem.                                               |
| **A3/B7 — retrospective repair and unavailable later updates**                              | **Explicitly deferred**   | Historical reports are not promoted into complete or universally current history. That is a legitimate first-target limitation.                                  |
| **A7/B7 — withholding can make safety scores look better while harming continuity**         | **Partially addressed**   | Independent answerability and unnecessary withholding are now scored. The competing admission policy still needs definition; “no summary” alone is insufficient. |
| **Continuity tables and broad source search**                                               | **Explicitly deferred**   | The source-window comparison remains an experiment, not an implied implemented capability.                                                                       |

The amended design and expanded scenarios substantiate these dispositions. I do not see a reason to reopen the already-settled preference representation, lifecycle reasons, source-role distinction or atomic operator command merely to obtain another round of agreement.

# What the safeguards do—and do not—establish

Three distinctions should survive into the implementation handoff.

**A complete lifecycle snapshot is complete only for the eligible ledger, not for the user’s life or all received dialogue.** An unsupported concern, an unpersisted retrospective correction or an update outside the permitted root/archive boundary may still be absent. Revision 3 acknowledges this correctly. Supplying every record does not eliminate semantic interpretation or justify treating all stored material as equally relevant.

**A shared evidence bundle aligns available evidence, not model understanding.** The conversation model can still misread an antecedent while the reviewer interprets it correctly, or vice versa. The narrow clarification veto reduces one visible inconsistency; it does not establish agreement on all response claims.

**Atomic finalization establishes transactional coupling, not conversational truth.** The baseline commits memory and the assistant message together after revalidation. Its tests cover useful mechanical properties: evidence binding and target versions, current-revision filtering, subject isolation, and lease fencing. Those are valuable foundations, but neither the tests nor this review establish extraction accuracy or natural dialogue quality.

The evaluation design is now much better positioned to expose those distinctions. In particular, scenario 2 no longer silently requires the deferred historical tool when the rename evidence is unavailable, and scenario 19 explicitly counts loss of otherwise answerable context. Preserve those qualifications rather than turning all 22 arcs into a single pass/fail “memory works” score.

# Readiness and genuine remaining decisions

**The architecture is ready for bounded implementation planning.** It does not need another storage family, background reviewer, history engine, graph, or framework comparison before that work can be planned.

I would not close the affected read/context contracts until these two items are settled:

| Remaining decision                             | Smallest sufficient resolution                                                                                                                                                                                                                                                                          |
| ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Selective recall of current terminal state** | Make eligible inactive descriptors available through current-memory selection/search, not only through the complete guard packet. Keep arbitrary revision-chain search deferred.                                                                                                                        |
| **Status of the full-snapshot prerequisite**   | Either accept it explicitly for a bounded small-memory operating range, or keep it provisional pending an equal-budget comparison against a genuinely different recent-dialogue-first admission policy. Do not call a no-summary variant a sufficient comparison when it retains the same prerequisite. |

The generation-conflict recovery rule, candidate-reply reserve and historical-action replay wording are narrow clarifications that should be recorded with those decisions. They do not justify another architectural review cycle.

**My overall recommendation is to preserve revision 3’s core and stop expanding the architecture.** Its strongest simplifications are one lifecycle view, one mutation generation and one shared clarification bundle. Its weakest choice is making the entire saved-memory collection a prerequisite for understanding the previous conversational exchange. That choice should earn its place through measured usefulness—not merely through conservative intent.
