# Evidence Selection: External Review Assessment

Date: 2026-10-02. **Reports received and source-checked; proposed protocol changes
await a decision.** No selector implementation, eight-source diagnostic, provider
call, runtime change or native requalification occurred. PC-03/04/05/06/09/10/11
remain in force. The [continuity plan](../../../../../docs/plans/character-story-continuity.md#model-assisted-evidence-selection)
is the delivery entrypoint; [protocol v1](PROTOCOL.md) is preserved, not superseded
by consultant recommendations.

## Recommendation

Keep semantic selection as a hypothesis, but do not build its model runner next.
First propose a small offline slice that challenges the need for compression and
makes whole-packet qualifications govern the comparison. The strongest verified
critique is not that historical scores are wrong: **having a named answer present
does not establish that the complete packet supports choosing it confidently.**

An eight-source capacity diagnostic would also be useful, but explicitly departs
from ADR 0057's four-window experimental boundary. Obtain approval and record that
evaluation-only amendment before implementation. Do not change runtime constants,
silently bypass the existing builder, or treat receiving these reports as approval.
Neither report establishes that all eight sources fit or that larger packets
produce better answers. Retain the baseline and native turn-7 stop.

## Report Receipt

The user supplied these two reports against the [published brief](EXTERNAL_REVIEW.md).
They are preserved byte-for-byte, including original whitespace and absent final
newlines. Our interpretation and recommendations appear only in this assessment.

| Report | SHA-256 |
| --- | --- |
| [A](reports/review-a-2026-10-02.md) | `a6fd0504b686734c51c137ebdd163edf61f21a27350b2c1947361ec06fa7bc5a` |
| [B](reports/review-b-2026-10-02.md) | `08fb9dc650f4f73415462ad0342341f2ad100269898647b55cf84cc875229245` |

Both report inspecting source `1a5336acbd34bc3bf0adde544ff2502b8875a07a` and the
brief at `3ecc4b0755e0a40cc55ed6f6163a326a8e1c53ad`, without executing tests,
providers or database checks. Both disclose prior high-level ADE context; neither
is blind. Actual reviewer identities, consultation modes and independence are not
established by the attachments. Agreement is not independent replication.
Their inspection claims are self-reports, not separately audited access receipts.

Both list the nine priority source paths and additional admission, binding and
assessment code. A also lists the correction-study README/context and comparison
lines 1-180; B lists comparison lines 1-170. Neither claims full reproduction of
the 63 packets. The relevant source and frozen correction-study directory had no
diff between the source anchor and pre-integration HEAD `3ecc4b0`.

## Verified Findings

### 1. Answer Availability Is Not Whole-Packet Sufficiency

The historical [assessment](../correction_dependencies/assessment.py) deliberately
uses answer-route set inclusion for `named_answer_supported`; it reports mistaken
retellings and correction admission separately. Additional conflicting sources
cannot revoke that availability signal. Its `unresolved` field copies the
full-ledger annotation, not a new judgment of uncertainty in the selected packet.

Using the unchanged [packet builder](../../../../../services/ade-api/tests/agent_runtime/story_packet_builder.py)
through the correction study's `build_packet`, we constructed these D02 packets
locally. Both sources were admitted in each, with zero capacity omissions:

| D02 sources | Actual historical content | Old named-answer signal | Generation / reviewer estimates |
| --- | --- | --- | --- |
| E01, E02 | E01 names Monday; E02 names Wednesday for the same bookmark episode. No correction is present. | True | 1,267 / 8,793 |
| E01, E07 | E01 names Monday; E07 rejects Wednesday and restores the original account. | True | 1,288 / 8,814 |

The reviewer estimates include the full synthetic reply reserve, against the
unchanged 11,469 limit; generation uses 11,213. These are request estimates, not
provider token observations. Full source text remains in the frozen
[cases](../correction_dependencies/cases.json); no source was rewritten.

The first packet permits recognizing a conflict, not settling it from chronology
or repetition. The second supplies the restoration. This confirms the reports'
counterexample without a new fixture, model judge or change to historical labels.
E01 alone remains a legitimate bare-answer route under those labels; requiring
every correction in every answer would repeat the earlier overconstraint.

**Root cause and owning layer:** the risk is reusing a monotonic availability
field as a prospective settled-answer decision. It is not incorrect historical
arithmetic or a broken identity validator. The remedy belongs in the proposed
packet-assessment and continuation rules, not a keyword rule, hidden score change
or runtime truth-selection patch. That revision is recommended, not implemented.

### 2. Four Is A Policy Constraint, Not A Measured Capacity Necessity

The [ranker](../../../../../services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py)
uses `TOP_K = 4`. The [admission layer](../../../../../services/ade-api/src/ade_api/features/agent_runtime/history_admission.py)
also fixes four and slices candidates before testing capacity; the shared builder
asserts that ceiling. Simply supplying eight IDs cannot measure an eight-source
request. Existing small-packet headroom motivates a diagnostic but proves no
whole-pool fit. No such diagnostic was executed in this review integration.

Any future exception must be explicitly evaluation-only, retain complete source
exchanges and both consumers' existing budgets/reserves, and verify that all eight
actually reach both final payloads. A fit would challenge the compression premise
for that fixture, not establish larger-history feasibility or behavioral benefit.
Compare eventual end-to-end cost, not just selected-packet size: selection adds
a request before generation and review.

### 3. The Simple Arm And Controls Need Narrow Claims

We recomputed the reports' three neighborhood predictions in memory from the
unchanged baseline and source order, using exactly the proposed one-anchor recipe:

| Case | Recomputed neighborhood IDs | Historical availability interpretation |
| --- | --- | --- |
| D02 | E02, E01, E03, E04 | Named answer present; conflicting weekdays; correction absent. |
| D04 | E07, E06, E08, E02 | Correction present, named antecedent missing, unrelated E08 selected. |
| D06 | E02, E01, E03, E07 | Named answer and its restoring correction present. |

These verify the static deductions, not a frozen three-arm result or downstream
model behavior. The comparison is one-step, single-anchor expansion under four
slots, not all retrieval-only methods. Do not tune neighbor recipes on these cases.

All six old cases share the E01/original and E07/restoration structure. The already
planned N01/N02 should break that pattern without changing meaningful chronology
or adding cases. B additionally proposes requiring a useful gain over both simple
arms on at least one new, structurally different case. That stricter continuation
gate is a recommendation awaiting decision, not an agreed requirement.

N03 compares different admission policies: deterministic arms fill four when
available; the semantic arm may abstain. Treat an empty response as conformance
and report unnecessary admissions, not matched abstention superiority. Do not
invent a lexical threshold or force the semantic arm to fill slots for symmetry.

### 4. Source Integrity Does Not Guarantee Preserved Meaning

The [binding code](../../../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py)
and actual D02 payloads expose message handle, role, content, content hash and
timestamp, but not original message ID or within-chat sequence. Conversation and
version identity remain at exchange level. Richer source-order receipts cannot
establish what the final model sees. No failure caused by this distinction was
demonstrated in the existing timestamp-ordered fixtures; defer wire changes until
a concrete example needs them.

Prospective assessment needs two views: the full eligible ledger to identify
material omitted qualifications, and the actual final H payload to judge what
survives serialization. Neither evaluator knowledge nor selector-only metadata
may supply a fact missing from that payload. Authentic sources can still create
false clarity by excluding a competing antecedent or genuine correction. Fresh
shared H prevents a generator/reviewer evidence mismatch, not shared blindness
to an omission. PC-05 supplies the structural-versus-semantic distinction; no
second reviewer or new story store follows.

The [reader](../../../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py)
takes the newest 128 scoped completed exchanges before content and annotation
exclusions. This source check is not a new database test. A bounded selector cannot
recover sources outside its pool; M01 tests an absent antecedent, not safe detection
of an absent correction. Keep that limitation, without adding a new benchmark.

## Insight Disposition

| Disposition | Insight | Action or boundary |
| --- | --- | --- |
| Use | Whole-packet qualifications and answer presence differ. | Preserve old metrics; propose explicit qualification handling for future decisions using D02 as the concrete witness. |
| Use | Final-wire meaning, source integrity and candidate availability are distinct. | Assess both omitted qualifications and the actual delivered evidence; do not infer meaning from richer receipts. |
| Use | Fixed neighborhoods, repeated fixture topology and asymmetric abstention limit conclusions. | Narrow claims; retain N03 as conformance and make planned N01/N02 structurally different. |
| Test | The available eight-source pool fits both existing downstream budgets. | Propose one offline D04 capacity diagnostic with a separately approved four-count exception. Not executed. |
| Test | A new-case gain is needed to justify further selector investment. | Consider B's stricter continuation rule during protocol revision; no new gate adopted here. |
| Park | Model runner, behavioral evidence-restoration test and broader candidate retrieval. | Decide the cheap capacity/rubric questions first. Behavioral calls and runtime integration require separate approval. |
| Park | Additional original sequence metadata in H. | Require a concrete wire-level ambiguity before changing the contract. |
| Discard | Report agreement, a fitted larger packet, or more gold IDs proves continuity improvement. | None measures generated answers, reviewer behavior, persistence or reliability. |

## Proposed Next Slice

Recommend approval for an **offline-only capacity and rubric slice**, not the
selector harness. Record a narrow ADR 0057/protocol amendment permitting a D04
eight-source measurement; leave runtime four-source policy and all historical
artifacts untouched. Measure complete paired requests with the existing budgets,
reply reserve and empty-context controls. State explicitly if an eight-source
packet cannot be represented without a further contract change.

Alongside that measurement, specify prospective whole-packet qualification rules
using the verified D02 counterexample and preserve alternative sufficient sets.
Resolve the N01/N02 structural requirements and proposed new-case gate before
authoring/finalizing controls. Do not enlarge the ten-case ceiling or implement
provider-attempt orchestration as part of this smaller slice.

If preserving the bounded pool removes the demonstrated evidence gap, defer the
selector runner unless compactness has a separately important benefit. If a
material selection need remains, propose the revised ten-case investigation.
Neither path establishes better actual answers; A's larger-packet comparison and
B's fixed-count evidence-restoration test are later alternatives, not cumulative
commitments or authorized provider work.

## Verification

Both archived report hashes match the original attachments. Local verification
loaded the existing frozen inputs/judgments through their hash-checking loaders,
recomputed the three neighborhood ID lists and constructed the two D02 packets
above through runtime-owned admission. No eight-window bypass or source mutation
was used. These targeted assertions verify the claims relied on here; they do
not constitute new model outcomes or a rerun of native evidence.

The existing correction and prior packet-comparison regression suites also pass
unchanged: `uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_correction_comparison.py services/ade-api/tests/agent_runtime/test_story_packet_comparison.py -q`
reports **20 passed**. Local Markdown links/anchors and authored-doc whitespace
are checked separately; no full runtime, database or provider suite was needed.

Only this assessment, report archives and documentation status links changed.
No new fixtures, labels, prompts, harness, runtime tests or database run were added.
Protocol v1's operative requirements and ADR 0057 remain unchanged pending a user
decision. Original report whitespace is intentionally excluded from authored-doc
whitespace checks so that the received evidence stays byte-identical.
