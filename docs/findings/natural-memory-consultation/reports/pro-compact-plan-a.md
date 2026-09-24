# Verdict: TARGETED REVISION — the compact interface is sound, but two authority decisions need to be settled

**The plan removes real sources of fragility without replacing ADE’s architecture. I would retain its compact decisions, server-owned binding, genuine deferral, explicit completion handling, and atomic reply/memory finalization.**

I would make two narrow amendments before freezing the implementation contract:

1. **Clarification must not silently discard uncertainty, no-save restrictions, or other qualifications attached to the antecedent it completes.**
2. **Clarifying or endorsing a lifecycle request—especially removal—must be distinguished from endorsing a factual proposition.**

There is also a smaller gap in how a **conflict without a write** can use existing saved facts as evidence.

The three evidence modes are **more than renamed source roles**: properly implemented, they can enforce which sources are eligible to contribute to a write. They cannot, by themselves, prove that a sentence is an assertion, that “yes” endorses the intended proposition, or that the selected dog is the right dog. The plan recognizes this distinction, but its acceptance contract needs to make the consequences more concrete.

## Inspection and evidence limits

I inspected the plan, assessment, both preserved reviewer-interface reports, and relevant implementation at:

**`236024fc7dd40058e262cea4d0c6d74c44e6b2d0`**

The GitHub comparison against `aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5` showed documentation/report changes, not implementation of the compact interface. The code at the review commit still has the old parallel proposal/disposition contract and existing binder.

The relevant public documents and source files were accessible. **I did not execute tests, inspect databases or raw captures, or make provider calls.** The published live outcomes and director’s offline reproduction remain maintainer-reported observations. Source inspection independently confirms the one-way endorsement check and permissive empty-object schema, but does not establish their frequency or any production incident.

Runtime paths below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.

# Ranked findings

## 1. P1 — Resolve-user needs an explicit rule for inherited restrictions, not just inherited factual content

**Classification:** a remaining semantic-contract decision, with a source-backed implementation hazard.
**Affected checkpoints:** 1 and 3.

The proposed `Resolve-user` mode allows a current answer to complete an earlier user assertion. That is the right mechanism for:

> **User:** One of my dogs is a Husky.
> **Assistant:** Rocky or Roxy?
> **User:** Roxy.

The current answer supplies the missing identity; the earlier user supplies the breed assertion. Neither message alone supplies the complete report.

However, completing an assertion should not automatically strengthen it or remove restrictions attached to it. The plan says the antecedent must be a real assertion and the current answer must resolve that claim, but it does not explicitly settle these combinations.

### Counterexample A: uncertainty disappears during resolution

> **User:** I think one of my dogs might be a Husky.
> **Assistant:** Which dog?
> **User:** Roxy.

“Roxy” resolves the dog, **not the uncertainty about breed**. Saving “Roxy is a Husky” would be an unsupported strengthening.

The existing `_validate_claim()` checks uncertainty around a current-user source. If implementation merely adds an earlier-user source role while preserving that validation arrangement, it can miss uncertainty that exists only in the antecedent. The current value-support check also pools source text, which cannot establish whether a qualifier was preserved.

### Counterexample B: a clarification becomes an unintended save authorization

> **User:** One of my dogs is a Husky, but don’t save that information.
> **Assistant:** Which dog?
> **User:** Roxy.

The last answer should not silently convert the same restricted assertion into a saveable one. That is different from a later, self-contained statement such as:

> “Roxy is a Husky. Please save that.”

The latter is fresh explicit authorization. The former only completes an unresolved part of the earlier exchange.

### A concrete current-code limitation also needs correction

The instruction to retain the “independent native no-save check” is not sufficient if it means retaining its present scope. `_claim_sentence_has_no_save()` examines the current evidence sentence, not the whole current message or a relied-on antecedent. For example:

> “I prefer coffee in the morning. Don’t save that. I now live in Toronto.”

A coffee write anchored to the first sentence does not encounter the second sentence in that helper. Its Chinese marker set also does not cover the plan’s natural “别保存” wording. These are source-visible limitations of the existing check, not experiments I ran.

### Exact minimal amendment

Add this rule to **Evidence Modes / Dispositions**:

> **Resolution completes only the identified unresolved part of the antecedent. It does not remove uncertainty, non-autobiographical framing, or a no-save restriction attached to that assertion. Evaluate eligibility against the admitted surrounding exchange, including intervening corrections and restrictions. A fresh, self-contained current assertion or explicit change of saving intent is evaluated separately.**

Also make clear that the native no-save check must be adapted to this evidence contract rather than reused unchanged.

This is **not a persistent topic-suppression system**. It governs the assertion being completed within the already bounded exchange.

### Decisive tests

Use hand-constructed decisions, not just model-generated happy paths. The definite Husky example must permit resolution; the uncertain version must not become a definite breed fact; the no-save version must not write that assertion; the later explicit save statement may be eligible.

For the mixed coffee/Toronto message, a legitimate coffee deferral may coexist with the residence write. An invalid coffee write must not be silently discarded to salvage its siblings.

---

## 2. P1 — Evidence modes must distinguish confirmation of a fact from authorization of an operation

**Classification:** under-specified product semantics, not a request for another model stage.
**Affected checkpoints:** 1 and 3.

The output supports `revise/end/reassert/forget`, but the contextual evidence modes are described primarily in terms of **earlier assertions** and **assistant propositions**.

A removal request is not simply a factual assertion. The plan needs to say whether, and how, a current short answer can complete or approve that request. Otherwise implementations can either reject legitimate clarification or treat ordinary factual assent as permission to delete.

### Positive case: resolving an earlier removal request

> **User:** Please remove one of those saved drink preferences.
> **Assistant:** The morning-coffee preference or the evening-tea preference?
> **User:** The morning-coffee one.

The current answer identifies the target of an earlier explicit removal request. Requiring the last message to repeat “remove” would reintroduce memory-command ceremony.

The current implementation does require explicit removal wording in the current source quote: `_validate_claim()` passes that quote to `is_explicit_forgetting_request()`. Therefore, adopting the new modes without changing operation-aware authorization would still reject this natural exchange.

### Positive case: approving a specific proposed action

> **Assistant:** Shall I remove the saved morning-coffee preference?
> **User:** Yes, please.

This can be a specific current authorization to remove that record.

### Negative case: endorsing factual change is not authorizing removal

> **Assistant:** Is morning coffee no longer your preference?
> **User:** Yes.

That can support an ending or change of the reported preference. **It does not, by itself, authorize forgetting the saved record and its active recall eligibility.**

Likewise, “Yes, that is the old preference” identifies a record; it does not necessarily authorize any mutation.

### Exact minimal amendment

Add:

> **Contextual resolution and endorsement may apply to a factual report or to a specific lifecycle request. The current answer must complete or affirm the particular proposition or action being proposed. Factual assent, target identification, ending, correction, and permission to remove are not interchangeable. Forget requires a current direct request or a current answer completing or affirming an explicit, target-specific removal request.**

The existing mode, operation and evidence fields should be sufficient. Do not add another permission classifier call or a model-supplied “authorized” flag that merely asserts the conclusion.

If contextual action authorization is intentionally excluded from this slice, state that explicitly and label these removal-clarification cases unsupported. My recommendation is to support them: they fit the proposed bounded evidence mechanism and the product’s natural-interaction goal.

### Decisive tests

Run the same current response—“Yes”—against different prior questions. It must not have the same mutation meaning in all cases.

For the positive removal-resolution case, persist the current answer as `user_resolution` and the earlier request as support-only `user_antecedent`. For assistant-proposed removal, preserve current endorsement and the exact assistant action request. Neither historical text nor assistant text authorizes the action alone.

---

## 3. P2 — A conflict without a write needs a read-only grounding route

**Classification:** a narrow ambiguity in the proposed conflict shape.
**Affected checkpoints:** 1 and 3.

Separating conflict from executable mutation is an important improvement. But the plan’s evidence descriptions still emphasize current assertions and contextual assertion support. It should explicitly cover conflict with **an existing supplied fact**, where the current user asks a question rather than making an assertion.

### Counterexample

The held snapshot contains:

> F1: the user’s dog is named Roxy.

The exchange is:

> **User:** What is my dog’s name?
> **Candidate:** Your dog is named Rocky.

There should be no need to invent a new name write—or falsely label the user’s question as an assertion—to report the conflict.

The plan does not expressly prohibit this case, but “grounded interpretation/evidence” is insufficiently specific to ensure that implementations handle it consistently.

### Exact minimal amendment

Add:

> **A conflict may cite relevant read-only fact or identity handles from the held snapshot, together with the current query/context and the exact conflicting candidate span. Conflict evidence does not confer mutation authority and does not require a new assertion or executable write.**

This reuses the existing map. It adds no retrieval, source expansion, or fourth write-evidence mode.

### Decisive tests

The wrong-name candidate should support a grounded conflict with zero writes. The correct-name answer followed by “How old is she?” must not be treated as a conflict merely because it contains a question.

Whether two differently worded statements actually conflict remains a semantic judgment; binding F1 and the candidate span is the structural guarantee.

# Do the evidence modes actually close the original loophole?

**They can close its structural path, but only if the binder controls which evidence contributes to a value—not merely the names assigned to source links.**

The current code permits a current `user_assertion` plus an `assistant_referent`, then pools their quotes for value support. The proposed contract must eliminate that general-purpose pooling path.

The correct division is:

| Mode                  | Native structural guarantee                                                                                                                                                            | Judgment that remains semantic                                                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Direct**            | The authority anchor binds to the current user message. No assistant or arbitrary historical message supplies missing factual content.                                                 | Whether the utterance asserts the fact, preserves scope, or is quotation, fiction, sarcasm, or negation.                                          |
| **Resolve-user**      | The antecedent belongs to an earlier user message in the held suffix; the current answer is separate; assistant clarification context cannot contribute additional factual properties. | Whether the answer completes that antecedent, which entity it identifies, and which qualifications remain applicable.                             |
| **Endorse-assistant** | The proposition comes from a permitted assistant message; a distinct current-user anchor is required; neither source can authorize the write alone.                                    | Whether the user affirmatively endorses that particular proposition rather than acknowledging, rejecting, quoting, or answering another question. |

Consequently, the decisive endorsement pair is:

> **Assistant:** Is Roxy a Husky?
> **User:** **Yes.** → potentially valid endorsement.

versus:

> **Assistant:** Is Roxy a Husky?
> **User:** **Roxy.** → not sufficient endorsement.

Testing only “Yes, Roxy is a Husky” is inadequate: that utterance can already function as a direct assertion. The compact interface must demonstrate that legitimate short assent works without making every short answer affirmative.

Also test an attempted mode-switch escape: supplying the bare-name example under `Direct`, `Resolve-user`, or `Endorse-assistant` must not provide three alternative routes to the same unauthorized breed write.

A valid source handle proves membership and origin. **It does not prove assertion, consent, or correct reference resolution.** The plan’s instruction to supply handles by role/chronology, without a preselection model call, is appropriate precisely because it does not pretend otherwise.

I would make the structural tests mandatory and measure broader interpretation errors separately. I would not introduce an additional semantic judge merely to describe those errors as “validated.”

# Persistence, history and binding: sound direction, specific integration gates

These areas do not require another product-architecture decision.

## Source roles must remain a closed authority/support distinction

Adding `user_resolution` and `user_antecedent` is reasonable. The existing database constraint permits only the three old roles, and the current source reader accepts a run revision when it finds `user_assertion` or `user_endorsement`. The implementation must update more than the enum.

The new read/write checks should use explicit role sets:

* Current authority: `user_assertion`, `user_endorsement`, or `user_resolution`, as allowed by the mode.
* Support only: `user_antecedent` and the appropriately constrained assistant reference.

**Never use “any user source” or “the first non-assistant source” as the authority test.** The existing preparation code uses the latter pattern; it becomes unsafe once earlier-user support is representable. Source ordering must not change which message is authoritative.

Required persistence tests should prove that an antecedent-only revision is rejected, that current authority binds to the originating run’s user message, and that prior support has the correct chronology and scope. Operator-caused removal retains its separate valid origin; it must not need a fabricated user source.

## Preserve historical evidence without retroactive recertification

The plan correctly requires new immutable bindings, unchanged old evidence, readable old conversations, and terminal replay without retaining a second live parser.

Preserving an old row means preserving what was recorded and under which policy—not asserting that the old decision passed the new evidence rules. New role-pairing rules must not silently relabel earlier sources or manufacture endorsement.

Use the existing originating run/conversation/policy lineage where version-sensitive interpretation is needed. No new universal provenance system is necessary.

Test that an old terminal result remains readable/replayable without invoking the new reviewer parser, while a fresh turn cannot silently execute the obsolete contract. The current admission path already distinguishes replay before fresh execution validation; preserve that separation.

## Request-local binding is adequately specified

The held F/E/U/A map, implicit subject ownership, server-held target versions and final generation check are a real simplification. The current snapshot loader already uses a repeatable-read snapshot and checks the accepted generation; the proposed map should be constructed from and retained with that snapshot.

A valid E1 still does not prove the model chose the right dog. But it can guarantee that E1 is an offered entity of the permitted kind within this subject, rather than a model-selected database identity.

Likewise, the proposed effective-set preparation correctly avoids entities and mutation embeddings surviving a legitimate deferral. There is no need to restore the parallel proposal/disposition arrays or require a guessed mutation to explain why no write is appropriate.

# Completion handling and counter-only accounting

**Both directions are implementable as specified. I do not see a reason to retain spending enforcement against the stated requirement.**

Requiring `{"decisions":[]}` rather than accepting `{}`, rejecting `length` before parsing, separating binding failures from semantic conflicts, and distinguishing committed/rejected/unconfirmed outcomes all address actual weaknesses in the current implementation. The present reviewer parses content and groups many failures under one validation code; the new classification should remain observable without becoming an automatic repair path.

Counter-only accounting also has a coherent boundary: count ADE outbound attempts once, distinguish incomplete observation from zero activity, and do not let ordinary telemetry failure change product outcomes. The plan explicitly preserves finite tool execution, timeouts and retries, so removing request caps does not imply unbounded execution.

Two engineering checks matter:

**Preserve timeout ownership.** The existing budget wrapper applies `min(timeout, 180.0)`; deleting it must not accidentally remove the intended diagnostic timeout. The plan already calls this out.

**Separate observational events from authoritative transaction events.** Making request-count telemetry best-effort must not make memory/run outcome consistency optional. A missing count can be “unknown”; an uncertain commit cannot be reported as either success or rollback by inference.

The proposed 4,096-token allowance remains a diagnostic choice requiring a newly computed envelope. Neither the compact schema nor previous partial successes establish that it is sufficient.

# Decisive regression set before live work

The following should be frozen in checkpoint 1 and exercised through the native binder and isolated persistence path before model trials.

| Group                          | Required positive and negative contrast                                                                                                                                                       |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Original loophole**          | Same assistant Husky question: short affirmative assent may authorize; bare “Roxy” must not. Inject attempted writes through every evidence mode.                                             |
| **Antecedent resolution**      | Definite earlier user assertion resolves correctly; uncertain, quoted/fictional, withdrawn, or no-save antecedents must not become stronger saveable assertions merely through a name answer. |
| **Lifecycle authorization**    | A target answer completes an explicit removal request; assent that a fact is outdated must not be treated as removal permission.                                                              |
| **No-save scope**              | Following-sentence “Don’t save that” and Chinese “别保存” controls; unrelated current updates survive legitimate deferral, but malformed/unauthorized sibling writes are not salvaged.           |
| **Conflict without write**     | Wrong answer against a supplied current fact can be rejected without a fabricated mutation; a correct answer with an unrelated question is not a conflict.                                    |
| **Binding and identity**       | Wrong-kind/unknown handles, stale generations and foreign sources fail; same-name pets stay distinct; deferred new identities leave no rows or mutation embeddings.                           |
| **Provenance compatibility**   | Source order does not change authority; antecedent-only evidence fails; valid new role combinations persist exactly; historical evidence and replay remain unchanged.                         |
| **Completion and observation** | `{}`, missing/null decisions, unsupported or absent completion status, and length-terminated JSON fail correctly; no hidden retry; lost telemetry does not rewrite the authoritative outcome. |

For semantic live tests, retain both the raw conversational context and the bound result. A fixture passing with a hand-authored decision proves the binding mechanism; it does not prove the model will choose that decision.

The proposed separately authorized fixed diagnostic, with predeclared repetitions and no mid-run scorer changes, is appropriate after these amendments. Its outcome must remain capable of showing fewer serialization errors **but continuing semantic failures**.

# Readiness conclusion

The earlier major interface criticisms are genuinely addressed in the plan: subject selection is removed, target versions become server-owned, historical support gets a distinct proposed role, deferral no longer requires a fake mutation, missing output is no longer intentional no-change, and completion failures become explicit.

**The remaining blocking decisions are narrow:** what restrictions a resolved assertion carries forward, and how current answers authorize specific lifecycle operations. Freeze the read-only conflict-grounding case at the same time.

After those amendments, **the plan is ready for bounded implementation**. The persistence checks, role-order tests, timeout preservation, counter aggregation, old-conversation compatibility and fault-injection tests are checkpoint requirements—not grounds for another architecture cycle.

Keep one reviewer and atomic finalization for this repair. Do not add a new framework, a second judge, automatic repair, or degraded reply delivery to compensate for an evidence contract that can be made clearer first.
