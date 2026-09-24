# Second Pro Review: Targeted Amendment Assessment

Status: assessment of revision 2, preserved as rationale for the later
[revision-3 proposal](../../architecture/natural-memory-design.md), not acceptance
or an implementation plan. Recommendations below describe the assessment checkpoint.
Reviewed design: `d80afb422b3deefa09f13ac5e7017c5e3e8524ef`.
Unchanged implementation: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.

## Preserved Reports

- [Round 2 A](reports/pro-round2-a.md), attachment
  `efcc72e1-535a-41dc-b6ab-bbf568e506a2`.
  SHA-256: `787b9e9ab7fe267169301745d135c03b6139b2063133eb801f49c25f0ecb965a`.
- [Round 2 B](reports/pro-round2-b.md), attachment
  `cafa0f2c-2dfa-4200-a5d9-3c043dc91e87`.
  SHA-256: `2c0fdc0513ecdf840dddd344fdffefd27f50a6f9fe9d35ded54d1578dd971631`.

Both independently report reading the same pinned documents/source; neither ran
tests or inspected services. Copies are unchanged. This assessment checks the
consequential claims against local source and design, not live behavior. No new
provider calls, database tests, or runtime changes were made.

## Verdict

The revised architecture is substantially stronger. Retain separate preference
records, explicit current-fact lifecycle, bounded user evidence, protected context,
source attribution, and synchronous atomic finalization. Neither report calls for
framework replacement or revival of the continuity schema.

One short design amendment is still needed. The proposed summary watermark and
specialized mutation read sets add obligations without yet closing their intended
contracts. The reviewers differ in how they count blockers, not in the need for
another broad research cycle. Combine the remaining work into narrative admission,
mutation consistency, and lifecycle/evidence views, plus a fixture correction.

## Checks And Recommended Dispositions

`Use` means recommend for an amendment, not accept or implement silently.

| Finding | Verification and limit | Disposition |
| --- | --- | --- |
| Summary snapshot age is not reconciliation coverage | `compaction_model_input()` contains only previous summary and incremental messages. Finalization commits memory before the summary. A new summary can therefore derive from old dialogue even without a race. Proposed watermark behavior is not implemented and was not executed. | Use: remove delta-watermark guard elision from the initial design. |
| Writes depend on more than target versions or final absence sets | Finalization re-prepares operations but checks target versions, not all identity-resolution dependencies. An add-then-forget can restore the same eligible set while intervening state changed. These are logical counterexamples to proposed read-set wording, not reproduced database races. | Use: one monotonic subject-memory generation for nonempty reviewer decisions, retaining target versions. |
| Existing subject metadata version is not a memory generation | Repository subject-name updates increment `memory_subjects.version`; fact commit does not maintain it as a fact-state generation. | Use: define a separate memory-state meaning explicitly; do not relabel the existing field without changing its contract. |
| Inactive null-valued assertions need semantic identity | New preference records are distinguished by statement/scope; null values plus opaque IDs cannot identify morning coffee versus evening tea for a later removal. Existing reviewer packet supplies value but no terminal descriptor. | Use: one derived lifecycle-aware record view, with last identifying assertion, status, and source/revision references. |
| Reviewer and conversation clarification windows can diverge | Current turn construction and reviewer input are assembled separately. Revision 2 permits optional older-history withholding while permitting multi-user-span writes. | Use: shared bounded clarification bundle, protected in both stages or ineligible for that turn's mutation. |
| Affirmative endorsement differs from bare reference selection | A bare dog name selects an entity; a clear yes to one unambiguous proposition can be user confirmation. Neither endorses unrelated clauses or removes uncertainty. | Use: explicit endorsement rule and positive/negative examples, not unrestricted assistant authority. |
| Scenario 13 mandates an unsupported preference inference | The exact positive text says the user drinks soy milk/red tea, while expected writes change preferences. This conflicts with scenario 4's order-versus-preference distinction. | Use: make preference language explicit and preserve consumption wording as a negative/control case. |
| Current-state priority needs matching attribute, scope, and time | Toronto residence and a temporary Paris visit can both be true. Persistence alone does not decide what is nearby during the visit. | Use: qualify precedence; extend downstream reply checks, not just storage checks. |
| Direct removal remains sound but has bounded recovery | Existing revision/run and message-source requirements need a real operator-causation alternative. Removing facts may not solve large persona/dialogue/entity input. | Use: shared validation/commit, all-or-nothing target set, atomic action result; describe availability of removal, not universal capacity recovery. |
| Retrospective corrections and hidden updates remain outside ledger coverage | Deferred historical corrections can change raw dialogue without a fact mutation. Root/archive restrictions can hide later information. | Use: historical evidence proves what was reported, not completeness or universal currentness. |
| Withholding can artificially improve safety scores | A model denied useful evidence may abstain safely but fail continuity. No quality experiment was run. | Test: score unnecessary withholding and answerability against independent expected evidence and a no-summary baseline. |

## Recommended Amendment, Not A New Architecture

### 1. Historical narrative is never certified current

Drop summary-watermark-based omission of guards for the first target. A generation
counter can identify a snapshot; it cannot certify that a summarizer understood
all changes, including those from other conversations or deferred historical edits.
Recompaction must not retire needed lifecycle information simply because a new
summary was created later.

Supply relevant current replacements/endings/invalidations independently of the
narrative, or withhold optional narrative with an explicit evidence gap. Apply
precedence only to the same attribute/scope/time. Define the conservative admission
rule in the amendment rather than inventing a summary-dependency subsystem.
Guard-or-withhold remains model-behavior risk reduction, not a semantic guarantee.

The minimal decisive example is sequential: old partner dialogue in A, breakup
committed in B, then first compaction of A. A fresh summary can still be stale.
Also retain the case where a raw historical correction causes no fact mutation;
no memory counter can claim to observe that correction.

### 2. One conservative mutation-snapshot contract

Prefer a monotonically advancing subject-memory generation for every committed
memory-relevant mutation, including operator removals. Bind a coherent reviewer
input snapshot to its generation. At finalization, a nonempty decision based on
an older generation conflicts; retain exact target versions and scope validation.
No-op replies may keep the already-declared weaker snapshot behavior. Provider
execution is not serialized under database locks and conflicts cause no hidden
model rerun. Define snapshot capture and atomic generation advancement explicitly.

This deliberately rejects some harmless concurrent writes. That tradeoff is easier
to explain than separate identity/category/absence read-set rules. Specialized
dependency tracking should wait for a measured conflict-rate need. One counter
does not prove source entailment, dialogue linearizability, or narrative freshness.

### 3. One lifecycle view and one local clarification bundle

An inactive-record descriptor should identify the withdrawn assertion from its
revision evidence, with explicit inactive reason and scope. Reuse that derived
meaning for reviewer targeting, context guards, and operator display. It is neither
a current preference nor permission to expose forgotten chains. Do not maintain
an independently mutable duplicate description.

Choose a bounded clarification exchange once. Necessary antecedents must be
available to both generation and review; if they cannot fit, ask for clarification
without a mutation depending on unseen antecedents. Eight user messages is a
maximum eligibility window, not permission to clip out a negation or correction.

Explicit affirmation can supply the user authority for one clearly framed
proposition; the assistant supplies its referent, not its truth. Ambiguous assent,
multiple propositions, uncertainty, quotes, and fiction remain unsupported without
clarification. This does not need another reviewer or persistent dialogue engine.

### 4. Correct the fixture and narrow adjacent promises

Use explicit preference wording for the mixed-operation positive example:
"早上现在更喜欢豆浆了；晚上那条以前说错了，我一直更喜欢红茶。"
Keep the original consumption statement as a contrast where a preference mutation
is not required. A useful response can acknowledge a routine without changing a
preference. This critique is valid even though the faulty example originated in
the first review: reviewer suggestions are not automatically golden expectations.

Make direct multi-target removal all-or-nothing, with action outcome and tombstones
committed together. Share the mutation boundary with conversational review, but do
not let a model select operator authority. Include only entities needed by eligible
records or the bounded exchange. State which input budget failed; removal remains
available but cannot cure every overlarge current message, persona, or source window.

## Readiness And Next Step

Recommend a short revision 3 addressing these named contracts, not another full
memory-framework investigation. No live benchmark is necessary to choose their
semantics. Matching quality, evidence selection, useful recall, false abstention,
latency, and conflict rates remain empirical questions for a later approved plan.

The user's review-before-planning boundary remains in place. This assessment does
not amend revision 2, adopt an ADR, produce an implementation plan, authorize new
calls, or unblock qualification. Raw reports and this local assessment are not
release evidence. No commit, push, merge, or deployment occurred in this review.
