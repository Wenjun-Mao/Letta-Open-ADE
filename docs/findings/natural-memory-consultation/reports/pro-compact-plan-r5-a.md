# GO — revision 5 closes the identified authority-contract gaps

**I found no remaining implementation-blocking authority decision in revision 5.** The amendments distinguish clarification from stronger consent, factual confirmation from removal authorization, and conflict evidence from write authority. They also address the dangerous integration shortcuts: recovering authority from source order and treating all quoted material as interchangeable factual support.

**No further mandatory plan amendment is needed before bounded implementation.** The existing implementation still requires the changes and regression evidence specified below; this verdict does not validate that code or authorize live calls, deployment, or release.

## Inspected revision and evidence boundary

I inspected:

**`a38d3e4e778899fab2763853c04cfd52bdb0ca2c`**

The inspection covered the complete plan, compact-plan assessment, relevant sections of both linked reports, current proposal schema/binder, policy preparation, persistence constraints and source readback, snapshot loading, finalization, and relevant policy tests. The comparison with `236024fc7dd40058e262cea4d0c6d74c44e6b2d0` showed documentation/report changes rather than implementation of revision 5.

The required public evidence was accessible. **I did not execute tests or inspect private captures, databases, credentials, or local task history.** Published reproductions and diagnostic outcomes remain maintainer-reported observations. The assessment itself distinguishes source inspection from execution.

# 1. Closure of the preceding findings

| Previous concern                                                                   | Assessment of revision 5                                                                                                                                                             |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Clarification could discard uncertainty, no-save restrictions, or framing          | **Closed as a contract.** Resolution completes only the missing part, retains qualifications, and considers the admitted surrounding exchange—including corrections and withdrawals. |
| Factual assent could authorize forgetting                                          | **Closed as a contract.** Authorization is operation-specific. Completing an explicit removal request differs from confirming that a preference ended or identifying a record.       |
| Conflict without a write lacked grounding                                          | **Closed as a contract.** Conflict may cite read-only snapshot facts or identities alongside the current query and candidate span, without fabricating an assertion or mutation.     |
| Earlier-user support could accidentally satisfy current authority                  | **Closed as a contract.** The current anchor is explicit and must bind to the originating run’s user message. Antecedents remain support-only regardless of ordering.                |
| Commit-time preparation could reinterpret handles or allocate different identities | **Closed as a contract.** Bind once; transactionally recheck ownership, source integrity and original versions without reconstructing semantic meaning.                              |

These are substantive changes in **Evidence Modes**, **Dispositions and Atomicity**, and checkpoint 3—not merely stronger wording around the old generic source list.

Two aspects are particularly important.

First, allowing earlier-user support does **not** grant permission to extract old facts independently: the current response must complete the particular antecedent. Second, allowing an assistant’s proposed action to be endorsed does **not** make the assistant authoritative: the current user’s affirmative response authorizes that specific action.

The resulting boundary is coherent without another classifier call or an `authorized: true` field.

# 2. Ranked implementation hazards—not new planning blockers

The following remain mandatory implementation gates. They are already required by revision 5; I would not request another revision merely to repeat them.

## Priority 1 — Replace pooled-source validation, rather than adding modes around it

**Current source fact:** `bind_natural_sources()` requires an assistant referent when `user_endorsement` is present, but does not enforce the converse. `_validate_claim()` then concatenates source quotes for value support. That combination is the structural route underlying the reported bare-name/Husky counterexample.

**Required implementation:** each mode must determine which sources may contribute factual content:

* **Direct:** the current assertion supplies new factual content; assistant text cannot supply a missing breed or other property.
* **Resolve-user:** the earlier user’s assertion/request supplies the antecedent; the current answer completes it. Assistant clarification text cannot introduce additional facts.
* **Endorse-assistant:** the selected assistant proposition/action request supplies what is being considered; current affirmative assent supplies authority.

The plan now explicitly prohibits interchangeable pooling and requires testing the bare-name attempted write under every mode. That closes the design gap.

**Smallest correction to the code:** replace the generic source-support path with mode-specific binding and eligibility checks. Do not retain pooled validation underneath new field names.

**Decisive regression:** hold the assistant question constant—“Is Roxy a Husky?”—and alternate current “Yes” with “Roxy.” Then inject the unauthorized breed write under each available mode. Changing the mode must not create a bypass.

## Priority 2 — Make current authority explicit throughout preparation and persistence

**Current source fact:** `_validate_claim()` and `_claim_sentence_has_no_save()` recover authority as the first source that is not `assistant_referent`. The no-save helper also examines the current evidence sentence rather than the complete admitted exchange. Those assumptions are incompatible with support-only earlier-user sources.

**Required implementation:** pass an explicit current authority anchor separately from supporting evidence. Evaluate inherited restrictions and following-sentence restrictions against their correct messages and scope—not by applying an antecedent’s offsets to the current message.

Persistence must follow the same distinction. The current database constraint admits only the three old roles; the source reader recognizes only `user_assertion` and `user_endorsement` as user authority and does not establish the proposed current-run-anchor relationship. Revision 5 expressly requires updating constraints, preparation, readback, UI and diagnostic checks together.

**Smallest correction to the code:** use explicit authority/support role sets and validate the current anchor against the originating run. Do not replace “first non-assistant” with the equally unsafe “any user source.”

**Decisive regressions:** permute source order without changing the result; reject antecedent-only new revisions; reject a purported current anchor from another run; retain restrictions when their sentence is not the selected quote. Operator actions must retain their separate causation rather than acquiring fake user evidence.

Historical records should remain readable under their originating policy and lineage. They must neither be relabeled nor retroactively described as having passed the new endorsement checks. That compatibility rule is now explicit.

## Priority 3 — Preserve the bound decision through finalization

**Current source fact:** finalization calls `prepare_natural_memory_review()` again using freshly read facts and entities. Preparation can allocate new entity/assertion identities. The new compact interface should not carry that reconstruction pattern forward.

**Required implementation:** retain the request-local map and trusted prepared operations. Revalidate their original references and integrity transactionally, without silently changing what F1/E1/U1/A1 denotes or allocating a different identity.

The existing repeatable-read snapshot and accepted-generation check provide a suitable foundation; a new handle registry or concurrency mechanism is unnecessary.

**Smallest correction to the code:** separate one-time semantic binding from commit-time integrity checks, as the plan now directs.

**Decisive regression:** bind a proposed write, change the subject generation before finalization, and verify rejection without remapping, partial writes, or another reviewer call. Separately verify that unchanged-state finalization uses the same prepared identities.

# 3. Concrete authority tests

Assume the named pets/preferences already have unambiguous eligible identities, and no conflicting information exists unless stated.

| Conversation or state                                                                                      | Required result                                                                                                  |
| ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| User: “One of my dogs is a Husky.” Assistant: “Rocky or Roxy?” User: **“Roxy.”**                           | Permit the bounded breed resolution. Persist current `user_resolution` and earlier `user_antecedent` distinctly. |
| Replace the first statement with **“One of my dogs might be a Husky.”**                                    | Do not save a definite breed. The final name resolves identity, not uncertainty.                                 |
| Add **“Don’t save that information”** to the earlier assertion                                             | The final name does not lift that restriction. No breed write.                                                   |
| The user withdraws the earlier claim before answering the name question                                    | Do not revive the withdrawn assertion through resolution.                                                        |
| Assistant alone: “Is Roxy a Husky?” User: **“Yes.”**                                                       | A clear answer to that single factual proposition may authorize the breed write.                                 |
| Same question; user: **“Roxy.”**                                                                           | No breed write. A bare name is not endorsement.                                                                  |
| User: “Remove one saved drink preference.” Assistant: “Coffee or tea?” User: **“The morning-coffee one.”** | Permit forgetting only that target. The earlier request is support; the current resolution is authority.         |
| Assistant: **“Shall I remove the saved morning-coffee preference?”** User: “Yes, please.”                  | Permit the specified removal, not an unrelated mutation.                                                         |
| Assistant: **“Is morning coffee no longer your preference?”** User: “Yes.”                                 | May support ending the preference; must not authorize forgetting it.                                             |
| Snapshot F1 names the dog Roxy. User asks its name. Candidate says **Rocky**                               | Permit a grounded conflict with no proposed write. Veto the attempt without inventing user assertion authority.  |
| Same snapshot/query; candidate says **“Roxy. How old is she?”**                                            | The unrelated follow-up question is not a conflict or a reason to fabricate a write.                             |

Revision 5 supplies the governing rules for all these results.

Two composed cases are especially valuable:

**No-save survives a change of evidence mode.** After “Don’t save that breed information,” an assistant asking the factual question “Is Roxy a Husky?” and receiving “Yes” does not itself establish changed saving intent. By contrast, a later explicit “Roxy is a Husky; please save that now” supplies a separate current authorization. This follows from the plan’s claim-scoped restriction and explicit-change rules; it does not require a persistent suppression feature.

**An unrelated write survives a legitimate deferral.** For:

> “I prefer coffee in the morning. Don’t save that. I now live in Toronto.”

a valid result can defer coffee and write Toronto. But if the reviewer actually proposes the unauthorized coffee write, the application must reject the invalid decision rather than silently discard it and salvage Toronto. The plan now names this distinction explicitly.

For negative conversational inputs, **no write does not automatically mean no reply**: a valid deferral or no-change decision may deliver a checked candidate. An injected unauthorized write, malformed review, or validated conflict must follow the declared atomic rejection path.

# 4. What is structurally guaranteed—and what still depends on interpretation?

| Native checks can establish                                                                   | Semantic judgment remains necessary                                                                  |
| --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| The anchor is an exact span of this run’s current user message.                               | Whether that span asserts, endorses, identifies, withdraws, or merely acknowledges something.        |
| Support belongs to an eligible earlier message of the correct role and chronology.            | Whether the current answer actually completes that antecedent.                                       |
| Direct mode excludes assistant factual support; antecedents cannot satisfy current authority. | Whether uncertainty, scope, fictional framing, or no-save applies to the particular claim.           |
| Handles resolve to the held subject/snapshot and original versions.                           | Whether the model selected the intended dog or preference.                                           |
| A conflict cites a real snapshot record and an exact candidate span.                          | Whether the statements genuinely conflict rather than discuss different times, scopes or attributes. |

**The plan is ready because it specifies the intended distinctions—not because it makes them all mechanically decidable.** Its explicit rejection of mode tags as proof, prohibition on pooled support, and requirement for both positive and negative empirical tests are appropriate.

The existing tests are narrower evidence. For example, the inspected endorsement test uses the relatively self-contained “Yes, Toronto is right”; its all-deferred test uses “I live in Toronto.” Neither establishes the required behavior for bare short assent or genuinely unresolved ownership. Those tests remain useful mechanics tests but cannot substitute for the newly specified contrasts.

# Mandatory versus optional work

**Mandatory contract corrections before implementation: none identified.**

**Mandatory implementation/acceptance work:** implement the three gates above; freeze complete allowed mutation deltas; verify source roles through storage and readback; preserve no-change/deferral versus atomic rejection; and include the restriction/action/conflict contrasts in the separately authorized live diagnostic—not only hand-authored unit tests. These obligations are already in revision 5.

**Optional improvements:** add further paraphrases and combinations of the same contrasts, and later-recall probes when evaluating continuity rather than just reconciliation. They can improve evidence, but should not become a prerequisite for settling this authority contract or justify another model stage.

The counter-only accounting work does not create a new authority loophole in the plan: it explicitly separates optional observation from mandatory source/revision/run-outcome persistence. Removing spending enforcement must not turn provenance persistence into best-effort telemetry.

## Final recommendation

**Proceed to bounded implementation of revision 5.** It closes the preceding blocking decisions without expanding the architecture. The remaining risks are failures to implement the stated contract completely and model interpretation errors that need measured testing.

Do not add another authority flag, semantic judge, persistent handle store, or repair loop. Implement the explicit anchor and mode-specific binding, preserve the held snapshot through commit, and let the decisive positive/negative tests determine whether the resulting reviewer is reliable enough for the next diagnostic.
