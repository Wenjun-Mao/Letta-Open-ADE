# Joint Evidence Packets: External Review Assessment

Date: 2026-10-02. **Both reports reviewed against source; narrow amendments
integrated into proposal v2.1. Implementation remains unstarted.** The
[recovery plan](../../../../../docs/plans/character-evidence-recovery.md) owns the
next offline slice. Relevant [product agreements](../../../../../docs/product-contract.md):
PC-03/04/05/06/07/09/10/11. Product intent and the retained four-window choice stand.

## Judgment

Proceed next with the proposed offline preparation. The reviews improve its
acceptance criteria without establishing that another model request is worthwhile.
Their most useful common point is that atomic admission preserves a selection,
including its mistakes: it cannot detect a material correction already omitted
by the selector. Two consumers sharing that subset may share the same false clarity.

The concrete amendments are material-omission reference packets and an explicit
M01 qualification gate; reporting the cost of rejecting a useful smaller subset;
and B's no-call prefix diagnostic to explain cardinality effects. Native snapshot
validity remains an open integration question. No additional campaign cases,
model calls or architecture are needed for these amendments.

## Report Receipt

The reports respond to the [joint-packet brief](JOINT_PACKET_REVIEW.md). Originals
are preserved byte-for-byte, including trailing whitespace and absent final
newlines; interpretations and decisions appear here rather than in those files.

| Report | SHA-256 |
| --- | --- |
| [A](reports/joint-packet-review-a-2026-10-02.md) | `346e7f451ba02e9ecc0b2d0d19e2fd5c78362d6efba79d4043b040d94e39d7fa` |
| [B](reports/joint-packet-review-b-2026-10-02.md) | `e5479bc60c507f6a181991c92c3daa8c68243b28a90ae1a0d6b889c7386c6611` |

Both report inspecting 20 source files at
`48db1ca339cbcc7c7f47a3f7af89b654f14aaebc` and the brief at
`6777e074aa0a795c98c0d548a745cf452555bded`. A additionally inspected the native
ranker; B inspected the historical assessment. Both disclose prior high-level ADE
context, read earlier assessments and performed no execution or private-receipt
audit. B reports successful connector reads and a failed public raw-web fetch.
These access statements are self-reported. Reviewer identities, modes and mutual
independence are not established by the attachments; agreement is no replication.

The relevant design, runtime and frozen fixtures had no diff between the review
anchor and pre-integration HEAD `6777e07`. This assessment is by the Codex manager,
an AI, using local source and targeted offline checks, not a human/blind evaluation.

## Findings And Integration

### Material Omissions Need Explicit Acceptance Consequences

Both reviews support judging the full eligible ledger and the actual serialized H.
The [binding](../../../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py)
preserves source handles, roles, text, hashes and timestamps, with exchange identity
and lifecycle annotations. Original message IDs and sequence stay outside the H
message fields. Neither valid binding nor richer evaluator receipts supplies
meaning missing from the final request.

B identifies a concrete precision gap: v2's continuation passage names N01/N02/N03
but describes M01 mainly as absent named evidence. In the unchanged D02 ledger,
E02 says Wednesday; E07 explicitly rejects Wednesday and refers to the unavailable
original day. After E01 is withheld, empty H, E02-only and E07-only all lack named-
answer support under the historical metric. Their semantic value is different:
E07 preserves a useful withdrawal; E02 alone hides it. This was verified from the
[complete source](../correction_dependencies/cases.json) and the frozen loader's
expanded D02. No new M01 fixture or model outcome was created.

**Root cause and owning layer:** the prospective continuation rule needs to make
material negative evidence consequential even when every packet lacks a named
answer. Historical `assess_packet` correctly computes its narrower inclusion
metric. The amendment belongs in the proposed selector instruction, reference
judgments and continuation rule, with those historical fields unchanged.

[Protocol v2.1](PROTOCOL.md#ten-case-ceiling) now requires pre-outcome contrasts for
concealed ambiguity, an obsolete original, a correction-bearing partial packet,
empty history and withdrawn-retelling-only evidence. Its prompt explicitly
addresses materially omitted corrections/alternatives; M01's harmful omission
blocks a positive continuation claim. Meaning is assessed in actual H. N01/N02
must break both the exposed source-position shortcut and restoration relation.
These require source-quoted semantic judgments; code cannot replace that review.
An original-only route can still suffice when the omitted correction confirms it.

### Preserve The Proposal And Measure Its Rejection Cost

The current `admit_history` greedily skips individual capacity failures, and
`HistoryAttempt.omit_before_exposure` can remove individual sources and readmit.
Both reports correctly identify prospective hazards for a joint selection. D04
already lacked E01 when selected, so those paths did not cause its observed miss.

Their constructed examples are sound: a useful A plus optional Z can fail solely
because Z overflows or disappears; dropping a material correction C can instead
leave an obsolete A falsely settled. IDs and capacity checks do not distinguish
these meanings. These are logical examples for future tests, not observed failures.

Keep whole-proposal admission for this comparison. [ADR 0060](../../../../../docs/adr/0060-joint-history-packet-admission.md)
now states that it preserves the proposed set rather than proving minimum semantic
necessity. Scripted tests will cover optional-source overflow/loss and material-
correction loss, with separate source-quoted reference judgments. If a reference
subset is sufficient and admissible, report the larger proposal's rejection as a
policy cost. Retain the failed method outcome; do not silently replace its packet.

### Explain Which Policy Difference Produced A Gain

The comparison changes source choice, cardinality and presentation order together.
The literal arm retains its selection algorithm under a new admission rule; its
overflow behavior is not the historical end-to-end baseline. We recomputed D04's
literal IDs as E07/E02/E05/E04 and its proposed neighborhood as E07/E06/E08/E02.
This verifies the reports' static deductions about one fixed recipe, not a result
against inexpensive retrieval methods as a class.

Use B's [matched-length prefix diagnostic](PROTOCOL.md#no-call-cardinality-diagnostic),
with a refinement: predeclare all length-zero-through-four prefixes, freeze case
texts and semantic judgments before computing deterministic orders, then freeze
the prefix packets/assessments before selector dispatch. Select the comparison
length from the valid semantic result. This prevents choosing a favorable prefix
or retuning the cases after results. It adds no live arm or call.
Invalid/uncertain/unrun results have no comparison length;
valid but unadmittable results keep their failure. The diagnostic explains gains
and does not impose another continuation gate.

If a shorter existing prefix matches the useful evidence, no source-choice
advantage has been shown. The semantic result supplied its length, so this also
does not establish a deployable deterministic stopping rule. N03 emptiness remains
conformance; order changes alone establish no recovery. A later behavioral test
must use method-produced packets and declare how presentation order is handled.
Cost must eventually include selection, generation, review and unsuccessful
attempts. This selector-only campaign cannot measure downstream response value,
completion cost or conversational latency.

### Defer Native Snapshot Policy To Its Owning Integration

Both reports identify a useful open question: an unselected candidate can affect
selection, then change or disappear while or after the model sees the pool.
`HistoryAttempt` separates ranking exposure from final H exposure; its request
guard validates admitted sources. The native embedding ranker guards its broader
pool around embedding calls. The dispatch guard checks accepted memory generation,
but this review does not audit every mutation path or establish a future semantic
selector's snapshot lifetime.

ADR 0060 now names that question and the needed race test, including empty results
and an unselected material qualification. Trace existing fence coverage before
adding machinery. Also distinguish proposal failure from user-turn failure and
identify any future fallback as a new proposal. Immutable offline fixtures can
proceed without deciding native fallback or adding a persistent graph.

M01 covers an absent antecedent whose absence is signaled by a surviving reference.
It cannot qualify detection of an omitted correction outside the candidate pool.
The reader's newest-128 boundary remains relevant to later candidate-recovery work.

## Insight Disposition

| Disposition | Insight | Integration or boundary |
| --- | --- | --- |
| Use | An authentic subset can conceal a material qualification. | Explicit prompt wording, harmful-omission references and M01 continuation condition. |
| Use | Atomicity preserves proposals and can lose useful evidence. | ADR/readout distinction and separately assessed sufficient-subset references. |
| Use | Matched-length deterministic prefixes help attribute gains. | Predeclared no-call references; no fourth arm, stopping policy or additional gate. |
| Use | Final H, complete policy differences and total cost govern claims. | Wire-level reference inspection, precise baseline label and method-produced downstream packets. |
| Test | N01/N02 break source-position shortcuts and represent their intended meaning. | Author/review concrete controls and deletion contrasts before the runner; controls do not yet exist. |
| Test | Optional-source and correction-source failures have different semantic costs. | Scripted mechanical examples plus source-quoted judgments in the next offline slice. |
| Park | Whole-pool drift, native user-turn failure and any new-proposal fallback. | Explicit ADR open question and mutation/race evidence before native adoption. |
| Park | Wider retrieval, changed wire metadata or a different source-count policy. | Require a concrete need and scoped decision; no new benchmark now. |
| Discard | Atomic validity, smaller H, reviewer agreement or report consensus proves useful recovery. | None establishes answer quality, reliability, end-to-end cost or persistence. |

## Verification And Next Step

Both archived report hashes match the supplied attachments. The existing frozen
input/judgment loaders passed their source and artifact hash checks. Targeted
offline assertions reproduced the D04 rankings and the three D02 missing-answer
observations above; the quoted source text establishes their differing meanings.
The linked code was inspected at an unchanged source revision. No fixture,
runtime, builder or historical output was modified by this review integration.

Authored-document whitespace and 83 local links/anchors pass, checked separately
from the unmodified reports. This is a documentation and archival change; runtime
test suites, databases, providers and private captures were not rerun or accessed.
The proposed offline preparation still owns its actual control and mechanical tests.

**Follow-up recommendation: none.** Direct offline control authoring and packet
construction are the next useful work. Another Pro or Deep Research round has no
specific additional contribution now. Reopen Pro for a concrete semantic-reference
or native-snapshot dispute that local evidence cannot resolve; use Deep Research
if measured candidate-availability failures create a specific retrieval-method or
scale question. The revised proposal remains the deliverable of this consultation;
implementation and any model campaign are separate work.
