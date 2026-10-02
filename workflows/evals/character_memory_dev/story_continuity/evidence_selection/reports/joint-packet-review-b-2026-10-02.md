# Recommendation: revise narrowly, then proceed with offline preparation

**Proceed with deliverables 1–2, after a small protocol amendment. Do not yet adopt whole-packet failure as a native availability policy, or treat the proposed comparison as justification for an extra model request.**

The consequential findings are:

1. **The whole selected set is a defensible preservation boundary, but not necessarily the smallest sufficient evidence set.** With only an ordered list of source IDs, admission cannot safely infer which sources are dispensable. Atomic admission therefore makes sense for this offline comparison. It nevertheless creates avoidable failures when an optional source overflows or disappears; those failures must count against the method, not merely demonstrate successful enforcement.

2. **The main semantic risk occurs before admission: a selector can omit a genuine correction or competing antecedent and leave both consumers with the same misleading picture.** Identical generation/reviewer history prevents an evidence mismatch; it does not prevent shared blindness. Source-only output limits authority and fabrication, but selection still makes a consequential semantic judgment.

3. **The ten-case campaign can identify a useful packet-selection witness or reject a weak recipe. It cannot establish that the extra request improves conversational continuity or pays for itself.** In particular, the methods differ in cardinality, presentation order and abstention policy—not just reference understanding.

These are reasons to sharpen the experiment, not add a graph, episode store, second reviewer or broader benchmark.

**Inspection anchor:** I retrieved commit metadata for **`48db1ca339cbcc7c7f47a3f7af89b654f14aaebc`**, whose message is “Plan four-window joint evidence recovery,” and inspected the source files at that exact revision. The assignment brief was read separately at **`6777e074aa0a795c98c0d548a745cf452555bded`**. All source observations below refer to the former commit.  

## 1. What the evidence establishes—and what it does not

**Observed in the published evidence:** D04’s literal packet contains E07’s withdrawal of the teahouse account, but not E01’s old-bookstore location. The visible response appropriately refuses to invent the missing location. Replacing E04 with E01, while retaining the other three sources and their positions, produces a supported named answer in one witness. The whole-pool witness also names the supported location. The published `behavioral/results.json` agrees with that account. This is evidence that supplying the missing passage *can* improve the response—not evidence that an implemented selector reliably supplies it.  

The capacity result is also consequential: all eight exchanges fit, with **1,476 estimated tokens of reviewer headroom even after the full candidate-reply reserve**. Four is therefore a retained study policy, not a capacity necessity demonstrated by this fixture. I respect that choice for this review; I would not silently replace the four-window experiment with an eight-window method. 

**Code observation:** `history_admission.py::admit_history` constructs successively larger proposals and skips individual capacity failures. `history_attempt.py::HistoryAttempt.omit_before_exposure` removes missing sources and calls admission again; `execute_generation_with_history` can then retry construction before first generation exposure. These are real ways a jointly selected set could be changed. They were **not observed causes of D04**.  

I also would not use the literal reviewer’s disputed ownership conflict to argue for or against retrieval architecture. Its quoted source binding is visible; whether the tentative aside warranted rejection remains unresolved, and no native delivery was exercised. 

## 2. Whole-packet preservation: defensible conservatism, not semantic necessity

### Minimal counterexamples

The following are **constructed counterexamples**, not reported ADE failures.

| Situation | Smallest example | Consequence of the proposed rule |
|---|---|---|
| Optional-source overflow | A alone directly and correctly answers the question. X is an unrelated exchange. A alone produces an 80-token request; A+X produces 110 against a 100-token limit. | Rejects the entire proposal although A was useful and admissible. |
| Optional-source loss | A and X both initially fit. Before final-history exposure, X genuinely disappears; A remains valid and sufficient. | Invalidates useful A solely because the selector also included X. |
| Material-correction loss | A states an obsolete value. C genuinely corrects it. C disappears before exposure, leaving A. | Here, retaining A alone could create false clarity. Automatic salvage is not defensible. |

The first two show unnecessary loss of availability. The third shows why “just omit the failed source” is not a general repair.

There is an additional asymmetry in referential corrections: losing an antecedent may leave a useful correction that supports *uncertainty*, whereas losing a correction may leave an apparently self-contained but obsolete assertion. Neither the number of surviving sources nor their original order establishes which situation applies. This is consistent with the plan’s distinction between sufficient subsets, partial evidence and conditional antecedent needs. 

### Is the whole selected set the right unit?

**My judgment: yes as the current proposal-preservation unit; no as a claim about the true dependency unit.**

The response schema does not distinguish essential sources from optional ones. An admission layer receiving only IDs has no justified basis for silently making that distinction. The proposed ADR correctly avoids pretending otherwise. Its mistake would be rhetorical or evaluative: treating every rejected packet as a safety success without also recording the useful evidence unnecessarily lost. The ADR already acknowledges the optional-source trade-off; make it consequential in the readout. 

The **smallest defensible alternative** is to select a smaller sufficient packet *before admission*, then preserve that packet. This requires no new schema, dependency edges or reviewer, and is already compatible with the semantic prompt’s preference for the smallest sufficient set. It does not solve the fixed-fill deterministic arms’ problem—which is part of their comparative performance, not something to conceal. 

If later evidence shows unacceptable rejection rates, the next alternative is a **new, explicitly identified proposal on the current eligible pool**, not mutation of the old proposal. That could require another selection request and a different failure policy. Neither is warranted now.

A seemingly simpler prefilter—discarding every individually oversized source before selection—is not semantically neutral either. It could hide the only correction and leave an admissible obsolete original. Capacity exclusion would then need to remain an explicit evidence-availability limitation.

### Smallest resolving test

Use the already-planned scripted mechanical examples to cover:

- Optional-source overflow against generation and reviewer separately.
- Optional-source disappearance.
- Material-correction disappearance.

The implementation should reject the whole proposal in each case under the proposed contract. The accompanying interpretation should distinguish **unnecessary rejection of a useful subset** from **prevention of misleading salvage**. These are not extra semantic campaign cases.

Retain the in-budget byte-parity check against `story_packet_builder.py::build_history_packet`, which currently delegates to greedy admission. The new builder should construct the complete selection directly, not accept a trimmed result and relabel it atomic. 

## 3. What the three-arm comparison can actually identify

### Cardinality and uncertainty are policy differences

Literal and neighborhood selection fill available slots; the semantic method can return zero through four. Thus a semantic “win” could arise from recovering missing evidence, omitting unnecessary evidence, avoiding capacity failure through a smaller packet, or merely following the no-history instruction.

Those are potentially useful benefits, but they are not interchangeable evidence of reference recovery. The protocol already correctly treats empty N03 selection as conformance rather than superiority over always-fill methods. Apply that same attribution discipline to nonempty cases. 

**Minimum additional diagnostic:** predeclare a no-call comparison against each deterministic arm’s prefix of the same length as the semantic result. Assess those reference packets using the same source-relative rubric.

This is **not a fourth deployed method** and not evidence that a deterministic stopping rule exists. It simply tests whether an apparent gain requires different source choices or can be reproduced by a shorter prefix of an existing order. Do not force the semantic method to fill four merely to manufacture symmetry.

Empty selection must also remain distinct from uncertainty-preserving evidence. In M01, returning nothing, retaining E07’s rejection of Wednesday, and returning only an obsolete Wednesday assertion are materially different outcomes—even though none supplies the missing Monday passage.

### The literal arm is unchanged in selection, not in its complete pipeline

Under overflow or source loss, literal-top-four plus atomic admission differs from the historical greedy pipeline. That is acceptable: the experiment compares selection methods under a common proposed contract. But its label should be understood as **“unchanged literal selection under proposed joint admission,”** not unchanged runtime behavior. In-budget byte parity resolves this distinction where no source is lost.  

Do not exclude invalid or unadmittable cases when describing comparative usefulness. Otherwise the method’s most consequential failures disappear from the comparison.

### Ordering remains an uncontrolled component of later behavior

The protocol preserves literal ranking order, anchor-first neighborhood order, and the semantic model’s returned order. `build_natural_binding_map` assigns H handles in that supplied order. Therefore the comparison does not isolate source-set identity from presentation policy.  

For this source-selection-only campaign, retaining those orders is reasonable. Before a downstream behavioral experiment, explicitly choose whether to compare complete policies or hold presentation order constant. Do not infer an ordering benefit from this campaign, which makes no generation calls.

### The simple comparator is narrow

**Static inference, not a new execution:** D04’s highest-ranked source is E07. The declared topology places all eight exchanges in one chat in E01–E08 order. Applying the prescribed neighbor recipe therefore gives **E07, E06, E08, E02**: the original remains absent, and unrelated E08 consumes a slot. This follows from the source topology and proposed recipe, without a model call.   

A semantic win here would beat this particular one-anchor recipe. It would not establish that inexpensive recovery methods in general have been exhausted. I would nevertheless keep the recipe frozen rather than search for a better one on these exposed cases.

### Cost cannot be reduced to final H size

The relevant accounting is:

**Extra selector cost + changes in generation cost + changes in reviewer cost.**

The selector reads the broader pool, has its own output/reasoning usage and failure modes, and precedes downstream processing. The proposed campaign can measure selector usage and elapsed time, and estimate downstream input-size differences. It cannot measure resulting generation/reviewer completion costs or conversational latency because those calls are prohibited. 

Consequently, even a perfect ten-case packet result supports only **a reason to investigate the extra request further**. It does not justify routinely paying for it. Conversely, a smaller final packet is not automatically cheaper end to end.

## 4. The necessary semantic checks are about omitted evidence

The design’s strongest existing feature is its distinction between the **full eligible ledger** and the **actual final H**. Preserve that distinction rigorously.

The ledger establishes which qualifications are materially relevant. Final H establishes what the downstream consumers can actually know. Evaluator knowledge cannot supply a missing answer to H; conversely, H cannot earn settled-answer credit by hiding a correction visible in the eligible ledger.

This is why the historical `correction_dependencies/assessment.py::assess_packet` is insufficient as the new decision oracle: `named_answer_supported` uses subset inclusion, while `unresolved` copies the existing judgment. Those fields have legitimate historical meanings, but do not adjudicate the sufficiency of a newly selected packet. Leave them unchanged. 

### Make the selector instruction match that assessment

The current prompt addresses references, qualifications and conflicting accounts, but can be sharpened with one sentence:

> Do not omit an available correction or alternative that would materially change the answer or uncertainty warranted by your selected packet.

This is a proposed instruction, not a keyword rule. “Materially” matters: it still permits E01 alone in the restoration cases when the omitted correction restores that same answer and the question does not require explaining the correction. The frozen author judgments explicitly allow that route. It does **not** permit the obsolete original alone in N02. 

### Concrete acceptance checks for the planned controls

| Control | Necessary pre-outcome reference contrast | What it detects |
|---|---|---|
| **N01: ambiguous antecedent** | A packet exposing both plausible antecedents and the reference, versus an otherwise plausible packet exposing only one. | False clarity created through omission, not merely failure to select an expected ID. |
| **N02: genuine correction** | Obsolete-original-only, sufficient corrected-answer evidence, and both together. | Whether the assessment rejects an authentic but superseded answer and permits a self-contained correction without unnecessary original-plus-correction requirements. |
| **M01: antecedent withheld** | Correction-bearing partial evidence, empty history, and obsolete-retelling-only. | Whether missing positive evidence is distinguished from concealing available negative evidence. |
| **N03: no history needed** | Empty history versus irrelevant admissions. | Instruction conformance and unnecessary context, not comparative retrieval superiority. |

These contrasts fit the existing plan’s reference-packet and deletion-challenge work; they do not require more selector calls. N01 should be declared unassessable before scoring if its uncertainty-bearing evidence cannot be annotated clearly or represented within four windows. The protocol already requires this. 

**One substantive gate clarification is needed:** explicitly include **M01’s material qualifications** in the no-regression condition. The protocol’s continuation passage specifically names the ambiguity, corrected-original and no-history controls, while M01 is separately described as an availability gap. Merely withholding named-answer credit is too weak: selecting only a withdrawn Wednesday account while omitting available E07 should preclude a favorable semantic-continuation conclusion. Useful partial evidence is allowed; misleading partial evidence is not.  

### Known-template overfitting remains a real limitation

Inspection of `cases.json` shows three episode families, each with two correction variants. All preserve the original-at-E01/restoration-at-E07 structure; M01 is another derivative of that structure. These are not seven independent demonstrations of general recovery. 

The already-planned N01/N02 structural departure is therefore necessary, not decorative. During authoring, ensure that first-position recovery and the known restoration position cannot solve both controls. N02 should place the genuine correction away from the familiar restoration position; N01 must require retaining unresolved alternatives rather than electing a favored account.

I would not add a broad benchmark or another judge. Passing these controls can falsify some simple shortcuts; it cannot establish generalization. Gains confined to exposed restoration cases should retain the plan’s existing **limited-follow-up** status, not become native-integration evidence. 

## 5. What blocks which stage

### Offline preparation: no unresolved native authority issue requires stopping

The proposed source-only schema, separate outcome states, real serializers and isolated request construction are sufficient foundations for this bounded slice. The important acceptance requirements are already largely present:

**Preserve provenance and authority.** Build from original complete exchanges; retain applicable annotations and bindings; keep historical material separate from current write-authorizing support. In the existing binding map, `history_packet` is separate from ordinary `eligible_support`, and the synthetic builder checks that eligible support is empty. This is a useful structural boundary, not proof that a model will interpret history correctly.  

**Fail without producing a substitute packet.** Invalid selection, valid empty selection, unavailable input, unadmittable proposal and uncertain/unrun attempts must remain distinguishable. Full generation and full-reserve reviewer capacity must both be checked. These are implementation acceptance requirements, not reasons to build native machinery first. 

**Assess the final wire representation.** The selector is proposed to see source message IDs and within-chat sequence. Current H serialization carries handles, roles, content, hashes and timestamps, but not those original message IDs or sequence fields. A reference packet must therefore convey its required meaning in actual H—not only in richer evaluator receipts. I found no demonstrated failure requiring a wire-format change now.  

The actual semantic blocker would be discovering that the proposed controls cannot be adjudicated or represented under the four-window contract. Resolve that before implementing a model runner, as the plan already orders the work. 

### Before the separately authorized selector campaign

Freeze concrete transcripts, judgments, requests, route/settings, hashes and attempt behavior. Confirm the actual route and environment then—not from historical D04 receipts. Preserve consumed or uncertain attempts without retries. None of this authorizes generation, review or native calls. 

### Before native adoption

Native adoption has additional unresolved obligations:

**Broader-pool exposure needs its own authorization boundary.** `HistoryAttempt` already distinguishes `ranking_exposed` from final-history `exposed`; `authorize_request` validates admitted exchanges, not an arbitrary larger selector input. A semantic phase must authorize the actual pool before exposure, including when it eventually returns an empty selection. 

**Define source drift during selection, not only after selection.** Specify what happens when a candidate disappears or changes while the selector request is in flight—including a candidate absent from the returned list. Selected-source checks alone do not define whether that returned selection remains valid against a changed pool. This needs an explicit native policy and race test; it does not block immutable offline fixtures.

**Preserve existing integrity and lifecycle enforcement.** `validate_admitted_history` distinguishes genuine absence from altered or cross-scope rows; `validate_history_before_dispatch` checks accepted memory generation; `validate_history_at_commit` rejects missing or unverifiable admitted sources. Native wiring must retain these boundaries and the surrounding persistence fencing. Fact removal must not be confused with historical-source deletion, and retained testimony must not independently reactivate a removed fact.  

**Do not claim long-history recovery from eight-source selection.** `read_history_corpus` limits the newest scoped completed exchanges to 128 before content and annotation exclusions. M01 tests an absent antecedent; it does not establish that the system can recognize a correction omitted upstream. Archive/version eligibility and database behavior need native evidence, not fixture metadata. 

## 6. Minimum changes and decision rules

I recommend only these amendments to the prospective work:

| Location | Minimum change |
|---|---|
| `evidence_selection/PROTOCOL.md`, selector prompt and assessment | Add the material-omission instruction above; explicitly make misleading omission in M01 a continuation-blocking regression. |
| Same protocol, assessment | Predeclare the matched-length deterministic-prefix diagnostic, and distinguish source recovery, useful pruning, cardinality/capacity effects and N03 conformance. |
| `docs/adr/0060-joint-history-packet-admission.md`, consequences/readout expectations | State that atomicity preserves a proposal, not a proven minimum dependency set; report avoidable rejection of sufficient subsets as a cost. |

The N01/N02 structural departures, final-H inspection and mechanical negative tests are already planned. Make them concrete rather than creating additional deliverables. Leave historical artifacts and labels unchanged.

The next action should change according to the evidence:

| Result | Appropriate next action |
|---|---|
| A simpler arm supplies equally useful evidence, with no material qualification loss. | Prefer that simpler method for further investigation; do not advance semantic selection merely because it returned fewer IDs. |
| Semantic selection adds a genuinely useful packet under four, with controls intact. | Consider a separately authorized, bounded generation/reviewer comparison. The packet result is not itself reply-quality evidence. |
| Gains occur only on the familiar restoration pattern. | Permit at most limited follow-up, with the template limitation explicit. Do not infer general recovery. |
| False clarity, omitted corrections, invalid outputs or excessive atomic rejection undermine the gain. | Stop or revise the selector hypothesis; do not reroll or repair outputs into success. |
| Necessary meanings repeatedly cannot fit four, despite adequate token budgets. | Revisit the count policy explicitly. Do not make the selector compensate indefinitely for an unsuitable constraint. |

**Bottom line:** the next offline slice is worth doing as a small test of **question-relative source selection under a retained cap**. It is not yet a test of a reliable character-memory system. Preserve honest uncertainty as successful behavior when evidence is missing, and require downstream reply evidence before claiming that packet gains improve continuity.

## Inspection scope and limitations

I inspected **20 source files** at the review anchor, plus the separately pinned brief. The directory prefixes below expand the shortened references used above.

| Directory | Files inspected |
|---|---|
| `docs/` | `product-contract.md`; `plans/character-evidence-recovery.md`; `adr/0060-joint-history-packet-admission.md` |
| `workflows/evals/character_memory_dev/story_continuity/evidence_selection/` | `PROTOCOL.md`; `READOUT.md`; `behavioral/READOUT.md`; `behavioral/results.json`; `REVIEW_ASSESSMENT.md`; `RESEARCH_REVIEW.md` |
| `workflows/evals/character_memory_dev/story_continuity/correction_dependencies/` | `cases.json`; `judgments.json`; `context.json`; `assessment.py` |
| `services/ade-api/src/ade_api/features/agent_runtime/` | `history_ranking.py`; `history_admission.py`; `history_attempt.py`; `persistence/history.py`; `persistence/history_guard.py`; `natural_memory_binding.py` |
| `services/ade-api/tests/agent_runtime/` | `story_packet_builder.py` |
| Brief revision `6777e074…` | `workflows/evals/character_memory_dev/story_continuity/evidence_selection/JOINT_PACKET_REVIEW.md` |

GitHub connector reads succeeded at the requested revisions. A separate public raw-web fetch failed; it was not used to substitute another revision. I did not run code, tests, services, providers or database queries, and did not inspect local files or private captures. Published test results and private-receipt verification remain repository-reported evidence, not checks I reproduced.

High-level prior ADE context was already present in the session; I did not retrieve conversation history or use it as evidence. This is an independent analysis, **not a blind review**. The two historical review documents were read as prior arguments, not independent validation of this proposal; their linked research and private underlying evidence were not re-audited.