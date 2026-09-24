# Verdict: revise the reviewer interface, not the memory architecture

**Yes: ADE is asking the model to supply several choices that the server already owns. The next change should remove those choices from the model-facing contract—not add another instruction explaining how to reproduce them.**

My recommendation is to **retain one post-response reviewer call and atomic finalization initially**, but replace the current transaction-shaped output with a smaller semantic decision contract. ADE should bind subject identity, target versions, message identity, source roles, offsets and hashes deterministically.

This will not eliminate genuine semantic errors: deciding which dog the user means, whether a statement changes a preference, and whether an answer endorses a proposition still require interpretation. But those decisions should not be mixed with unnecessary database and provenance bookkeeping.

I also found a **source-backed validation gap around assistant references** that should be corrected before further live testing. The current checks reject some legitimate contextual citations while permitting a particular non-endorsement path to use assistant text as value support.

## Inspection and evidence limits

| Material                                                                                                                                         | Revision inspected                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------ |
| Published consultation brief                                                                                                                     | `aea2719c1e2310d0c5c1a10b9fe75c0d0e3c14e5` |
| Reviewer builder, proposal schema, source binder, native validator, capacity binding, execution/finalization, snapshot reader and relevant tests | `92809c4c1cdae7d7aa3dd5f09e42b2b3bf310e75` |

The required source files were accessible through GitHub. I read the relevant tests but did not execute them. Raw captures, databases and ledgers were unavailable. **The reported successes, truncation and rejections are maintainer-reported observations**, not independently reproduced results. I did not substitute `main` or aggregate separately versioned diagnostics into one campaign.

Runtime paths below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.

# Root-cause analysis

## 1. The public schema permits a choice that the native validator forbids

**Classification: source-backed interface mismatch; a credible contributor to the reported failures, not a measured causal attribution.**

`NaturalAdd` exposes `entity_ref` as an arbitrary string or null for **every** fact type. Only its Python `_fact_contract()` validator rejects a nonempty reference for subject-kind facts. Meanwhile, `natural_review_request()` supplies entity IDs—including the subject entity—and instructs the model to return null for subject additions. The test suite explicitly confirms that the generated schema presents `entity_ref` as `string | null`.

That creates an avoidable task:

> Here is an entity ID identifying the user. For a fact about that user, do not select it; emit null instead.

The model choosing that ID is invalid under ADE’s contract, but it is not a mysterious semantic mistake. **The interface displays a plausible choice that the application does not need the model to make.**

The DeepSeek request also uses `response_format: {"type": "json_object"}`. Its detailed schema is embedded in the instruction text, not supplied through the strict-schema branch used by the other adapter. Consequently, strengthening a Python validator does not itself constrain what this model emits.

**Smallest correction:** subject-kind additions should have **no entity-selection field**. Related-entity additions should be a separate variant whose entity references are limited to the supplied related entities or explicit proposal-local new-entity references.

ADE then binds the subject itself. This is a new, deterministic interface—not silently changing an invalid subject UUID to null after receiving it. Unknown or forbidden fields should still be rejected.

The same principle applies to target versions: the model needs to choose **which offered fact to revise**, but ADE can bind that choice to the fact ID and expected version from the accepted snapshot. It must not look up and substitute a newer version.

## 2. Source authority is both overexposed to the model and incompletely enforced

**Classification: source-backed contract problems. The counterexamples below are static analysis, not executed probes.**

The reviewer emits `message_id`, exact quote and an authority-role label for every source, plus a separate `evidence_quote`. Yet ADE already knows the current message’s identity, each message’s author, bundle membership and chronology. The generic `source_messages` packet combines current and historical messages even though historical user messages cannot occupy any of the allowed source roles.

For the reported Rocky→Roxy correction, the extra historical citation was invalid and unnecessary: the current correction supplies authority, while the targeted fact and its revision lineage identify the old report. The corresponding test demonstrates that removing the historical authority citation makes the hand-authored proposal valid. That is a mechanical test, not proof the prompt reliably produces it.

### A concrete validation gap: the endorsement check is one-way

`bind_natural_sources()` requires:

> A `user_endorsement` must have an `assistant_referent`.

It does **not** require the converse. A proposal may contain a current `user_assertion` plus an `assistant_referent`, and `_validate_claim()` combines **all** bound quotes when checking support for the value.

Consider two known dogs and no saved breed:

> Assistant: “Is Roxy a Husky?”
> User: “Roxy.”

A proposal can cite “Roxy” as `user_assertion`, the assistant question as `assistant_referent`, and propose Roxy’s breed as Husky. The inspected checks provide a path through validation: the current source supplies an allowed role, and the assistant quote supplies the word “Husky.”

**A bare name is not the required endorsement.** This is precisely the distinction the brief says must be preserved. The existing test named `test_assistant_referent_requires_current_user_endorsement` covers a valid endorsement and an unavailable message, but does not test this reverse condition.

### The opposite problem: legitimate reference resolution has no adequate source role

Consider:

> User: “One of my dogs is a Husky.”
> Assistant: “Rocky or Roxy?”
> User: “Roxy.”

The current message authorizes resolving the earlier assertion. It does not contain the breed, and the assistant question does not contain it either. With no existing breed fact, current-span-only value support cannot establish the proposed value, while citing the earlier user assertion is forbidden by the binder.

**Current authorization and supporting provenance are different concepts.** Requiring a current anchor need not prohibit recording the earlier user span whose meaning the anchor resolves.

**Smallest correction:** distinguish three evidence shapes: direct current assertion, resolution of an earlier user assertion, and endorsement of an assistant proposition. ADE should derive message roles from those shapes and its supplied reference map—not accept a free-form authority-role choice.

Earlier user support must never authorize a write alone. Assistant text must never become factual support merely because it appears among selected quotes. These are explicit contract changes, not reasons to weaken provenance checking.

## 3. Deferral currently requires inventing the mutation that cannot yet be justified

**Classification: source-backed structural limitation.**

`NaturalReviewDecision` requires a one-to-one correspondence between `proposals` and `claim_dispositions`. A deferred claim therefore needs a complete add/revise/end/reassert/forget proposal. `prepare_natural_memory_review()` then validates evidence, uncertainty, targets, entity resolution and collisions **before** filtering out deferred operations.

For:

> “One of my dogs is a Husky.”

the unresolved issue is which entity owns the breed. A structured deferral should not require the reviewer to choose a dog or invent a new identity first.

Likewise, a hypothetical-location proposal marked deferred can fail the uncertainty validator before reaching the deferral outcome. The existing “all deferred” test uses the clear assertion “I live in Toronto,” so it does not exercise this difficulty.

**Smallest correction:** make write, defer and conflict separate decision variants. A defer needs an identifying current span and reason, not a complete mutation target/value. A conflict needs grounded evidence and the conflicting candidate-reply span, not a fabricated write.

This also removes the parallel-array reconciliation task and much of the repeated `claim_id`/`supported` bookkeeping. Keep a small local reference only where it genuinely connects multiple claims about a newly introduced entity.

## 4. Output exhaustion is a separate failure class

The published observations support the conclusion that **1,024 output tokens were insufficient for at least one reported high-thinking request**. They do not establish that 4,096 solves source selection, entity selection or semantic reliability. The diagnostic capacity binding deliberately preserves the input ceiling while separately increasing the reviewer request allowance.

The current reviewer repeats quotes across fields and duplicates each claim across two arrays. Shrinking that contract is warranted independently of the token issue.

I would also classify an output-limit stop separately from invalid JSON, schema mismatch, authority rejection and semantic disagreement. `NaturalMemoryReviewer.review()` currently parses content and wraps most failures as `natural_review_validation`; it does not itself give a `length` stop a distinct outcome.

**Do not infer that high thinking is intrinsically unsuitable, or that a larger limit is the durable interface fix.** Both remain hypotheses requiring controlled evidence.

# Recommended design: one semantic reviewer, deterministic ADE binding

Retain the sequence:

**Generate candidate reply → one compact review → deterministic binding and validation → atomic finalization.**

Change who supplies the information:

| Model decides                                                                                  | ADE supplies or derives                                              |
| ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Whether the current utterance states, changes, withdraws, removes or leaves a claim unresolved | Bound workspace, subject and character context                       |
| Which offered related entity or existing assertion is meant                                    | Actual database IDs and expected versions from the accepted snapshot |
| The supported value and scope; change-versus-error meaning                                     | New persistent IDs and lifecycle bookkeeping                         |
| Which current span supports the decision, and which eligible antecedent is needed              | Message identity, speaker, chronology, exact offsets and hashes      |
| Whether the actual candidate reply contradicts the reconciled claim                            | Application of the declared allow/defer/fail outcome                 |

That division preserves the semantic work while removing redundant serialization decisions.

### Keep the wire contract small

Use type-specific subject and related-entity additions. Use short, request-local handles for existing targets rather than requiring the model to reproduce UUID/version pairs. Resolve those handles only against the original server-held snapshot; a handle is not authorization by itself.

Use one decision list. A write carries its operation and required semantic fields; a defer carries its current anchor and reason; a contradiction carries its grounded claim reference and exact candidate-reply quote.

Replace the generic source list with structurally distinct **current authority** and **context dependency** fields. For direct writes, the current message ID is implicit. Where the model must select an antecedent, it selects from ADE’s bounded reference map. Exact quote binding remains native, including rejection of missing or ambiguous spans.

This is not “let the server guess the meaning.” ADE must still reject an unknown entity handle, ambiguous quote, stale snapshot or unsupported endorsement. It must not repair malformed model output by silently dropping inconvenient sources.

### Preserve scoped preferences without another ontology

The reported missing “morning” is a semantic scope error, not an entity-ID error. Prefer retaining the user’s scoped wording for preference assertions rather than gratuitously normalizing it to “coffee.” Continue testing time, frequency and conditions; removing server-owned fields does not prove that scope was preserved.

### Remove derivative identity choices too

`new_entity_label` is another unnecessary free-text output when an accepted identity claim already supplies the name. Derive the label from that claim.

Also build the reviewer’s entity choices from lifecycle-eligible identity facts. The inspected path currently loads raw `list_entities()` rows and passes their labels into the reviewer packet. That allows operational labels to remain a separate source of identity hints instead of deriving them from the current fact view.

None of these changes requires a new table family, framework or general schema compiler.

# One credible alternative: reconcile before generating the reply

A second viable workflow is:

**Review current input → bind and validate provisional memory changes → generate against that provisional understanding → atomically commit both.**

It still normally uses two model calls overall—one reviewer and one conversational generation call. It discovers malformed proposals before spending on the reply and gives the generator a clearer account of the intended factual update.

However, **it is not equivalent to the current safeguard**: the reviewer has not seen the actual reply and cannot veto its explicit contradiction or unnecessary clarification. Restoring that independent post-reply check would require another stage. The alternative therefore needs an explicit response-quality contract change, not merely moving a function call.

I rank it second. The observed failures are principally in the reviewer’s interface; changing call order does not remove them. First test the smaller contract while preserving the existing post-response check.

## Why I would not decouple reply and memory success yet

Atomic finalization currently makes a reviewer failure a conversational availability failure: a useful candidate may never be delivered. The execution and finalization paths support that coupling.

That is a real cost, but silently converting an invalid review into “no memory changes” is not an acceptable simplification. It could expose a reply claiming successful saving/removal or containing the very disagreement the failed review was supposed to detect.

An explicit “reply delivered, memory update failed” product mode could be considered later, but it needs its own outcome semantics and treatment of contradictory or unsupported claims. **These small diagnostics do not yet justify that extra correctness obligation.**

# What stays unchanged

Keep PostgreSQL, immutable messages and revision evidence, independently editable typed facts, subject isolation, accepted-snapshot/version checks, current-user write authorization, no-save precedence, exact provenance, cancellation/lease protection, explicit retry ownership and truthful committed outcomes.

Keep limited removal: saved-record exclusion is not erasure of historical messages.

The proposed changes are to the **model-facing contract and deterministic binding boundary**. The current validator should become clearer and tighter, not more permissive about invented references or assistant-origin facts.

# Verification before restarting the policy comparison

## Focused offline regressions

Replace prompt-string presence as the main assurance with contract and native-validation tests:

| Area       | Required cases                                                                                                                                                                                   |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Ownership  | Subject additions cannot carry an entity selector; related handles cannot cross subjects; two pets with the same name are not automatically merged                                               |
| Authority  | Valid direct assertion; valid current resolution of earlier user evidence; valid endorsement; assistant-only support and bare-name non-endorsement rejected                                      |
| Deferral   | Missing entity, hypothetical claim and no-save intent can produce a valid no-write decision without invented mutation fields; unrelated supported writes remain eligible                         |
| Provenance | Current-only typo correction; exact antecedent spans when needed; missing/ambiguous quotes rejected; target versions remain bound to the accepted snapshot                                       |
| Outcomes   | Contradiction with no new write can be reported; malformed/truncated output, veto, embedding failure and commit failure preserve the intended no-reply/no-memory outcome and diagnostic evidence |

The authority test should specifically cover the current one-way-check counterexample. The deferral test should use a **genuinely unresolved** dog reference, not a fully specified assertion labelled unresolved.

No model call is needed to establish those mechanical properties.

## A small, separately authorized live diagnostic

Freeze one new interface version and one output envelope. Re-run the chronological coffee, evening-tea and typo-correction cases, then add related-entity creation, actual clarification, positive versus negative endorsement, and no-save/deferral beside an independent valid update.

Include predeclared repetitions of the subject-add case in different surrounding contexts to test recurrence. Those are planned observations—not retries used to erase a failure.

A 4,096-token allowance is a reasonable **diagnostic candidate** given the reported truncation, not an already-qualified production default. Keep thinking settings fixed initially so an interface change is not confounded with a reasoning-mode change. Any subsequent thinking-mode comparison should be separately declared.

Record failures by stage: truncation, parsing/schema, binding/authority, semantic proposal, reply disagreement and finalization. Preserve candidate and typed-decision evidence without private reasoning. Stop as predeclared; do not continue editing prompts within a supposedly frozen campaign.

Only then freeze a new A/B campaign. The changed reviewer shape and output envelope affect capacity, latency and costs for both policies; previous partial positions cannot be carried forward as completed comparison evidence. The brief already correctly treats the existing runs as separate diagnostics.

# Uncertainties and evidence that would change the recommendation

**The interface mismatch is demonstrated; its share of the observed failure rate is not.** I cannot establish how often the model would violate a smaller contract from these observations.

If the compact interface produces structurally valid proposals but still loses scope, chooses the wrong entity or treats acknowledgment as endorsement, the remaining problem is semantic extraction quality. That would justify a controlled reviewer-model or thinking-setting comparison—not more database fields.

If valid reviews remain sufficiently slow or failure-prone to damage ordinary conversation, the memory-first alternative or explicit degraded reply outcome deserves evaluation. If the pinned router offers genuinely schema-constrained output, that could improve formatting reliability, but its availability and behavior must be verified rather than inferred from the non-DeepSeek adapter.

The new source-role shapes, genuine deferral variant and any reordered/degraded workflow require an explicit contract/ADR amendment. Changing the completion allowance requires a new evaluation-envelope binding.

**My recommendation is to remove server-owned choices from the reviewer, close the assistant-reference authority gap, and make deferral representable without a fake write. Retain one reviewer call and atomic finalization until that smaller design has been tested.**
