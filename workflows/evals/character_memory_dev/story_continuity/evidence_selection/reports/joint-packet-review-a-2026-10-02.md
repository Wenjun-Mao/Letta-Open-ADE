# Decision: proceed with offline preparation, with two narrow acceptance clarifications

**The proposed offline slice is worth doing. It does not yet justify the extra semantic-model request or adoption of the native all-or-nothing failure policy.** I would retain the three methods and ten-case ceiling, implement the small service-test builder, and sharpen two acceptance points before freezing outcomes: distinguish failures caused by packet policy from semantic selection failures, and require concrete harmful-omission reference packets for N01/N02.

The consequential findings are:

1. **Whole-selection atomicity is a defensible experiment-preservation rule, not evidence that every selected source is semantically indispensable.** It prevents silent alteration of the proposal, but can reject useful evidence because of an independent optional source.
2. **This is a comparison of three complete selection policies—not a clean test of semantic reasoning alone.** Cardinality, ordering, admission exposure and request cost differ. A favorable result can justify a bounded answer-quality experiment, not the extra request as a production investment.
3. **Source-only output and identical final H do not protect against false clarity caused by omission.** Both consumers can faithfully interpret the same misleading subset. The proposed full-ledger/actual-payload assessment is therefore essential, rather than supplementary.

## Evidence anchor

I inspected source at **`48db1ca339cbcc7c7f47a3f7af89b654f14aaebc`**, whose commit metadata identifies “Plan four-window joint evidence recovery.” I read the detailed brief separately at **`6777e074aa0a795c98c0d548a745cf452555bded`**. I did not substitute current `main`.  

Below, `H` means the actual serialized read-only history delivered to generation and review. All source paths and symbols refer to the source anchor above unless explicitly identified as the later brief.

# 1. Preserve the proposal; do not confuse that with preserving a proven dependency group

### What the code establishes

In `services/ade-api/src/ade_api/features/agent_runtime/history_admission.py`, `admit_history` considers the first four ranked exchanges individually. A candidate that fails capacity is appended to `omitted` and skipped, while later candidates can still be admitted. In `history_attempt.py`, `HistoryAttempt.omit_before_exposure` removes missing ranked exchanges and calls `_admit()` again; `execute_generation_with_history` permits that rebuilding before generation exposure. These operations do not preserve an intentionally joint selection.  

**That is a real prospective hazard, not D04’s observed cause.** The published D04 literal selection already lacked E01. Its generated answer acknowledged the missing original location; repaired-four supplied E01 and named the location. Admission did not remove an originally selected E01 in that observation. 

### Minimal counterexamples to whole-set necessity

The following are **constructed counterexamples**, not repository observations.

Let **A** be one complete exchange that supplies a self-contained, warranted answer. Let **Z** be an independent optional exchange. Both are valid same-scope sources, and the selector proposes `[A, Z]`.

| Event | What remains useful | Consequence of the proposed rule |
|---|---|---|
| Reviewer input with A fits; adding Z exceeds its limit. Generation fits either way. | A alone still supports the answer. | The entire proposal is unadmittable. |
| Z genuinely disappears after selection but before generation exposure; A remains unchanged and authorized. | A still supports the answer. | Later native adoption would invalidate the entire proposal. |

Two windows suffice to demonstrate the tradeoff. No dependency graph, long chain or four-window saturation is needed.

But the converse counterexample matters equally: let A contain an obsolete original answer and C contain its genuine correction. Dropping C can turn authentic historical text into a falsely settled answer. **A generic “keep whatever survives” rule cannot distinguish C from optional Z using membership, hashes or capacity checks.**

### My judgment

With a flat list of IDs, no dependency annotations and no authorized reselection, **whole-proposal rejection is the smallest conservative rule that preserves what the method actually proposed**. I would keep it for this experiment.

I would not describe it as establishing the correct semantic preservation unit. A selector can return an unnecessarily large set, an incomplete set or a misleading set; atomicity faithfully preserves all three. ADR 0060 appropriately acknowledges that structural checks do not establish dependency completeness. 

A smaller defensible packet is possible **when selection proposes it in the first place**—A rather than `[A, Z]`, or a sufficient two-source combination rather than four. The existing zero-to-four schema already permits that. There is no generally safe proper-subset salvage operation encoded by the current response contract.

For later native failure handling, another defensible alternative is **a separately identified new proposal**, potentially produced by the deterministic method from the freshly authorized pool. That would be a new selection decision, not preservation or successful admission of the original proposal. It would require explicit fallback authorization and assessment; I would **not** add it to this slice.

### Smallest resolving test and minimum change

Use the already-planned scripted mechanical examples to demonstrate both sides:

- A sufficient A plus optional Z, with reviewer-only overflow and then source loss.
- An original A plus material correction C, demonstrating why indiscriminate removal cannot be called meaning-preserving.

For the first example, retain evidence that A alone fits and is sufficient **as an evaluator reference**, without dispatching it or substituting it for the attempted packet.

**Acceptance clarification 1:** report this as a *packet-policy rejection despite a useful admissible alternative*, not a semantic misunderstanding or an absence of useful history. The plan already separates failure layers and permits reference packets; this makes that distinction concrete without another campaign arm. 

The current proposal’s service-test ownership is appropriate. `story_packet_builder.py::build_history_packet` delegates to greedy `admit_history`; validating its trimmed result afterward would not implement whole-selection construction. Reusing the real binders and serializers in a separate small builder is justified. 

# 2. The comparison can justify further testing—not yet the extra request

## D04 is a useful diagnostic, but a predictable challenge for this neighborhood recipe

The source ledger places E01–E08 in one archived conversation in that order. Given D04’s literal anchor E07, the frozen neighborhood recipe selects **E07, E06, E08, E02**: anchor, predecessor, successor, then literal fill. E01 remains absent. This follows directly from the supplied topology and recipe; I did not execute the ranker.  

That makes D04 a legitimate test of a distant-reference weakness. It does **not** make this one neighborhood method representative of all inexpensive retrieval approaches. A semantic win there would establish an advantage over the two frozen comparators on that case—not that another model request is generally necessary.

Do not tune the neighborhood rule after inspecting results. Equally, do not turn its deliberately limited scope into an argument against retrieval-only recovery as a class.

## The asymmetries are acceptable for policy comparison, provided they remain visible

| Dimension | What the comparison actually measures | Required interpretation |
|---|---|---|
| **Cardinality** | Deterministic methods generally fill four available slots; the semantic method prefers a smaller set and may return none. | N03 emptiness is conformance, not matched superiority. Fewer sources are not independently evidence of better recall. |
| **Uncertainty** | Methods select evidence that may expose or conceal uncertainty. They do not produce answers. | A valid empty list does not demonstrate calibrated uncertainty. Useful partial evidence and absence of evidence must remain separate. |
| **Ordering** | Literal order, anchor-first order and model-chosen order differ. | Reordering the same sources is not antecedent recovery. A later behavioral comparison must either control order or acknowledge a combined selection-and-ordering effect. |
| **Admission** | All three new arms use joint admission, unlike the legacy greedy path. | The literal arm is an unchanged **selector under a new admission contract**, not an unchanged end-to-end runtime baseline whenever overflow occurs. |
| **Cost** | One method adds a serialized model request before downstream work. | Smaller final H cannot by itself establish lower total cost, lower latency or greater value. |

These distinctions are largely already present in `evidence_selection/PROTOCOL.md`, especially “Three Frozen Arms,” “Final Packet Isolation” and “Assessment And Decision.” They should survive implementation and reporting rather than become secondary caveats.  

I would **not** force the semantic arm to select four, invent a lexical abstention threshold, or add another live arm merely for symmetry. You are comparing useful policies, not isolating a single algorithmic ingredient.

One additional interpretation point: the proposed selector is not given the complete downstream capacity calculation. A semantically useful selection that overflows is an unsuccessful policy outcome, but not necessarily evidence that the model misunderstood the episode. The whole-request estimates should identify the binding consumer.

## Four remains a policy choice with an unproven benefit here

The completed capacity readout reports that D04’s eight-source packet fits both consumers with full reserves. Relative to literal-four, it adds **755 estimated generation-input tokens and 793 estimated full-reserve reviewer-input tokens**. These are serialized-byte estimates, not provider-token measurements. 

Under the retained four-window policy, investigating better selection is reasonable. But the experiment cannot establish that paying another model to compress these short histories is better than retaining more original evidence. That alternative is excluded by the chosen policy, not defeated by evidence.

The eventual cost comparison must include:

> selector work + generation work + reviewer work + unsuccessful attempts,

not just final packet size. The proposed campaign can measure selector usage and elapsed receipt intervals and estimate downstream request sizes. It cannot measure downstream completion cost or conversational benefit because it makes no generation/reviewer calls. 

**Smallest resolving test:** after a genuine packet gain, compare actual replies from the **method-produced packets** on the cases where methods meaningfully disagree. Another evaluator-repaired packet would not establish that the proposed method produces useful inputs reliably.

# 3. The cases can expose false clarity, but cannot establish general reliability

## The essential safeguard is the two-view judgment

A packet needs assessment against both:

**The full eligible ledger:** what material corrections, alternatives or qualifications exist?

**The actual final H:** what can generation and review genuinely see and interpret?

This is especially important because a source-only selector still makes a semantic filtering decision. It cannot invent a new source ID successfully, but it can omit the one source that makes an apparently clear answer wrong. Identical H gives both consumers the same evidence; it does not give the reviewer access to missing qualifications.

The repository already recognizes this distinction in `REVIEW_ASSESSMENT.md` and the revised protocol. I regard it as a sound correction to the earlier answer-presence framing, not a new defect in the current design.  

## Freeze a few concrete negative reference packets

**Acceptance clarification 2:** before outcomes, make the intended harmful omissions explicit in the new controls’ reference packets and deletion judgments.

| Control | Required contrast |
|---|---|
| **N01: ambiguity** | A packet exposing the material alternatives supports uncertainty. A packet retaining only one plausible referent must not receive settled-answer credit merely because that place is named. |
| **N02: corrected original** | The obsolete-original-only packet must fail settled-answer sufficiency. A packet containing a genuinely sufficient corrected route can pass without mechanically including every historical account. |
| **M01: withheld antecedent** | The remaining correction can support rejection of the mistaken weekday and useful partial evidence. A packet containing only the mistaken retellings must not gain credit by concealing that correction. |
| **N03: no history needed** | Empty is appropriate selection behavior. Four irrelevant sources are unnecessary admissions, not an observed generation failure. |

This does not require new campaign cases, another factual reviewer or an automatic truth-scoring engine. It concretizes the protocol’s existing requirement for source-quoted alternatives, qualifications and deletion challenges. 

Preserve the important counterbalance: **D02’s E01-only route is not automatically bad.** The full ledger restores that same original value. It can support the bare answer while omitting an explanation of the correction. Conversely, E01 plus a conflicting retelling without the restoration warrants qualification. The existing readout explicitly distinguishes these packets; do not regress to “every answer requires original plus correction.” 

## Make “structurally different” substantive, not cosmetic

The six exposed D cases are three paired families with the same E01-original/E07-restoration structure. Their labels explicitly say that E07 restores E01. Different weekdays, locations and snacks are not independent demonstrations of correction reasoning.  

The plan already requires N01/N02 to break that structure. During preparation, ensure that decisive evidence is not discoverable by the same source-position shortcut and that the relation itself differs: unresolved alternatives in N01 and an actually superseded original in N02. Do not alter the exposed D fixtures or select a favorable new topology after seeing outcomes.

I would not require every safety control to demonstrate superiority over both simpler methods. Controls should first prevent harmful behavior. A gain confined to D04 can justify a **targeted restoration follow-up**, but not broad confidence in a general selector. A new-case gain broadens the evidence somewhat; it still does not create a reliability estimate.

## Judge what survives serialization

`natural_memory_binding.py::build_natural_binding_map` gives final H message handles, roles, content, hashes and timestamps, with conversation/version/archive information at exchange level. Original message IDs and within-chat sequence are not serialized as message fields in H, although the selector input includes them.  

Therefore, a source combination that is intelligible using selector-only sequence metadata must not automatically receive final-packet sufficiency credit.

**Smallest check:** inspect the actual constructed H for each new control’s reference packet before freezing its judgment. If the decisive relation disappears at serialization, repair or narrow that fixture/contract explicitly. Do not add new wire metadata without a concrete need.

## M01 tests one kind of absence, not general awareness of missing history

M01 leaves an explicit reference to an unavailable antecedent. That can expose an answer gap. It does not establish safe behavior when the missing item is a correction and the surviving text looks self-contained.

The reader in `persistence/history.py::read_history_corpus` takes the newest 128 scoped completed exchanges before its content and annotation exclusions. A correction can therefore be outside the eventual candidate pool. 

**Inference:** two larger histories can yield the same visible candidate pool, while only one contains an excluded correction. No selector operating on that identical pool can distinguish them from source text alone.

The minimum change is to keep that limitation explicit—not add another live benchmark now. Passing M01 cannot qualify general “missing recollection remains uncertain” behavior across arbitrary candidate omissions.

# 4. What blocks which stage?

## Offline preparation: no unresolved native policy needs to block it

I found **no reason to require database integration, a new persistence model or resolution of the optional-aside reviewer dispute before authoring controls and building the service-test mechanics**.

The offline acceptance requirements are the ones that make the experiment interpretable: assessable frozen controls; feasible intended four-window reference packets; source-only membership validation; no evaluator leakage; unchanged complete source content and lifecycle metadata; identical H; both full-request capacity checks; distinct invalid/empty/unadmittable states; and byte parity with the historical builder on fitting selections. These are already substantially specified.  

In particular, a short synthetic reviewer placeholder is not the capacity test. The existing builder also calls `preflight_reviewer_bundle` with the full candidate-reply reserve; the new builder needs that same distinction. 

Synthetic scope metadata remains an assumption. It can verify serialization and isolation mechanics, not actual archive/version/database eligibility.

## Before the separately authorized selector campaign

Freeze concrete inputs, judgments, requests, route/settings, hashes and attempt behavior. Verify current routing/configuration at launch rather than inheriting D04’s service qualification.

Retain the proposed maximum of ten one-attempt selector calls, no repairs or rerolls, and zero generation/reviewer calls. Uncertain dispatches must remain consumed attempts rather than becoming convenient missing observations. These are existing protocol requirements, not new work I am proposing. 

## Before native adoption: resolve the broader-pool snapshot boundary

The plan correctly requires authorization before exposing the broader pool and revalidation of selected sources. One boundary deserves a more explicit native contract:

> **What happens when an unselected source that influenced selection disappears or changes after the selector has seen it?**

A selector might legitimately choose an original-only answer route because a separate correction confirms that original. That correction need not appear in final H, yet it influenced the decision that the subset was sufficient.

The current code has separate `ranking_exposed` and generation `exposed` states. `HistoryAttempt.authorize_ranking_sources` validates ranking sources, while `authorize_request` checks admitted exchanges. `history_native_rank.py::rank_native_history` guards its source-bearing embedding dispatches. Those existing paths do not themselves specify the future semantic selector’s complete snapshot policy.  

**This is an unresolved integration requirement, not a demonstrated bug in the unimplemented selector.**

The smallest native resolving test is: change or remove an **unselected material qualification** after selector-pool exposure, leaving selected text unchanged. Verify whether the existing accepted-memory-generation fence invalidates the attempt, or whether a deliberately defined snapshot policy permits it. `persistence/history_guard.py::validate_history_before_dispatch` already checks accepted memory generation; I did not inspect or execute every mutation path to establish its coverage of this scenario. 

Do not respond by inventing a persistent dependency graph. Define the snapshot and reuse existing fences where sufficient.

Native adoption also needs an explicit distinction between **proposal failure and user-turn failure**, authorization for any new proposal or fallback, selected-source handling before and after exposure, commit-time integrity checks, and lifecycle tests showing that history cannot restore removed facts or become persistence authority. PC-05/07 and the existing source guards provide boundaries, not evidence that this new phase already obeys them.  

# 5. What should change the next action?

| Result | Recommended next action |
|---|---|
| Necessary meaning cannot be represented within four sources, or a control is unassessable | Stop before model execution. Revisit the case or explicitly reopen the four-window policy; do not tune the selector around an impossible target. |
| The simpler method supplies equally useful evidence | Prefer that method for the next bounded investigation. Do not retain the semantic request merely because it also works. |
| Semantic “gains” consist only of fewer sources, N03 emptiness, reordering, or answer-string presence | Do not claim a recovery advantage or justification for another model phase. |
| Semantic selection recovers a genuinely useful route or qualification that both simpler arms miss, without control harm | Consider a separately frozen answer/reviewer comparison using those actual selected packets. D-only gains warrant correspondingly narrow follow-up. |
| Actual replies become better with those packets | Consider native integration only after its authority/failure contract and tests are resolved. Packet improvement and reply improvement still do not establish persistence or cross-chat continuity. |
| Practical misses are predominantly sources absent from the candidate pool | Reframe toward candidate recovery rather than further selector sophistication. This eight-source experiment cannot establish that prevalence. |

The existing D04 outputs should remain described narrowly: literal-four produced appropriate missing-location uncertainty; repaired-four and whole-pool each produced supported naming once. The literal reviewer conflict concerned an optional ownership-ambiguous aside, not an invented restored location. Neither the conflict nor the two no-change decisions establish native acceptance or persistence.  

**Bottom line:** retain the experiment’s strict packet preservation, but use the offline slice to challenge the semantic selector’s incremental value—not to presume a path to deployment. No additional architecture, campaign case or factual reviewer is needed now.

---

## Inspection record, access gaps and prior context

I read **20 source files** at `48db1ca339cbcc7c7f47a3f7af89b654f14aaebc`:

```text
docs/product-contract.md
docs/plans/character-evidence-recovery.md
docs/adr/0060-joint-history-packet-admission.md

workflows/evals/character_memory_dev/story_continuity/evidence_selection/
  PROTOCOL.md
  READOUT.md
  behavioral/READOUT.md
  behavioral/results.json
  REVIEW_ASSESSMENT.md
  RESEARCH_REVIEW.md

workflows/evals/character_memory_dev/story_continuity/correction_dependencies/
  cases.json
  judgments.json
  context.json

services/ade-api/src/ade_api/features/agent_runtime/
  history_ranking.py
  history_admission.py
  history_attempt.py
  history_native_rank.py
  natural_memory_binding.py
  persistence/history.py
  persistence/history_guard.py

services/ade-api/tests/agent_runtime/story_packet_builder.py
```

I also read `workflows/evals/character_memory_dev/story_continuity/evidence_selection/JOINT_PACKET_REVIEW.md` at the separately specified brief commit.

**Access and verification limits:** GitHub reads only. I did not execute tests, reconstruct request artifacts, call providers, inspect private captures/configuration, access a database or operate services. Published outputs were inspected directly, but private receipt correspondence and reported test results were not independently reproduced. I read the repository’s research assessment as historical context; I did not independently recheck its papers or use their reported benchmarks to select an architecture.

**Prior ADE context:** I had high-level background concerning ADE’s typed facts, immutable dialogue, factual reviewer and earlier recovery discussions. I did not retrieve previous conversations or use that background as evidence for this review. Reading the pinned historical assessments also means this review is not blinded; independently reasoning about their claims does not create independent experimental replication.