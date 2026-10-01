# Matched Correction-Dependency Readout

Date: 2026-09-30. **Completed non-blind author-labeled synthetic measurement**
under ADR 0056. No provider/API call, external semantic review, database access,
native turn, model reply or persistence operation was executed. The production
runtime is unchanged; the novelty candidate remains unadopted.

## Decision

The predeclared dependency-specific signal occurs in **all three episode pairs
for the literal baseline and two for the novelty candidate**. Both meet the
two-pair investment trigger. This supports proposing one bounded dependency-recovery
design, not implementing it here, adopting a selector or claiming reliability.
Retain the baseline and close this measurement with the recorded outcomes.

Every selected-arm packet contains the correction. Each selector chooses the
same four source IDs in both members of every matched pair. All self-contained
corrections supply a named answer; the baseline loses that answer in every
referential case, while the candidate resolves only the weekday case. The
location and snack cases retain a correction without the passage naming its
referent. These are available-source selection gaps, not capacity drops or
demonstrated failures by a generator/reviewer.

### Why This Layer

The original exists in every complete eligible synthetic corpus but is outside
the selected four in the failing packets. The source-owned builders admit all
selected windows. Fitting evaluator references supply the missing named value
and correction explanation. Current-only independent-window lexical relevance,
with or without the unchanged novelty penalty, does not guarantee recovery of a
question-critical referent. The observation supports investigating linked
evidence selection in the existing ranking/admission path, not adding a store,
increasing capacity or patching a downstream answer to invent the missing value.

## Provenance And Scope

[Inputs, context and labels](README.md#frozen-inputs-and-ownership) were committed
and pushed at `2447917ddd979a8459d23e1998c421aa22f196bf` before any new-case scoring
or selection. [The manifest](freeze.json) is pinned by `inputs.py` with digest
`902c6c72ceb2e15e52737e5550bbee054ee7be76cdee25cfddd6d9ce9edb062b`.
No transcript, query, judgment, coefficient, tie-break, slot limit or frozen
source was changed after the outcomes. Deterministic replays verify regeneration,
not additional attempts or variant search.

[Judgments](judgments.json) are source-quoted non-blind author-agent annotations.
The author knew prior results and both selectors; old Pro reports informed the
query-relative rubric but did not annotate these six cases. Internal read-only
Relay reviews checked implementation mechanics, not label truth or independence.
No blind, independent, external or human-validation claim is made.

Three new Mandarin families concern a weekday, a location and a carried snack.
Each has seven distinct plausible episode windows plus one unrelated window.
Only the correction's assistant text differs within each pair. The restored value
appears solely in the original and the self-contained correction, not the query,
user turns, compatible detail, saved facts, suffix or persona biography.

All eight exchanges of a case belong to one archived synthetic conversation,
with sixteen ordered messages and a fresh current chat. Same-subject/character
eligibility and ordinary-version lineage are controlled assumptions, not actual
reader or database observations. Source timestamps order utterances; they do not
date the fictional event. Selected-window order is not dialogue adjacency.
The semantic story contract is an evaluation criterion, not a claim that its full
normative wording or the full native persona was supplied verbatim to a model.
Actual runtime-owned instructions and requests are inspectable in the artifacts.

## Case Results

IDs are complete exchanges; order below is selector/admission order. "Named"
means a frozen answer route is present, not that a model generated that answer.

| Case | Correction | Baseline admitted | Baseline evidence | Candidate admitted | Candidate evidence |
| --- | --- | --- | --- | --- | --- |
| D01 / weekday | Self-contained | 02,04,07,05 | Named Monday via E07; correction explained. | 02,07,04,01 | Named Monday via E01 or E07; correction explained. |
| D02 / weekday | Referential | 02,04,07,05 | E07 present, E01 missing; no named weekday. | 02,07,04,01 | Named Monday; E07's dependency resolved. |
| D03 / location | Self-contained | 07,02,05,04 | Named old-bookshop doorway via E07. | 07,02,05,04 | Same named place via E07. |
| D04 / location | Referential | 07,02,05,04 | E07 present, E01 missing; no named place. | 07,02,05,04 | Same dangling reference and missing named place. |
| D05 / snack | Self-contained | 02,07,05,04 | Named sesame flatbread via E07. | 02,07,05,04 | Same named snack via E07. |
| D06 / snack | Referential | 02,07,05,04 | E07 present, E01 missing; no named snack. | 02,07,05,04 | Same dangling reference and missing named snack. |

`text_lengths` reports Unicode code points for the current text, serialized scoring
query, both source roles and complete scored documents. E07 assistant lengths
are **37/41** for the weekday pair, **40/43** for location and **36/41** for snack,
self-contained/referential. No wording was padded or shortened to equalize them.
Literal scores are recorded beside these lengths; provider token estimates are
a separate dimension.

Every selected arm also contains an actual mistaken retelling. None admits the
unrelated E08 or an other-episode source. E06's optional detail is absent in all
selected arms; that does not make a bare answer insufficient. Zero unrelated
admissions here does not undo the older candidate's unrelated admissions or
establish specificity on other corpora. Do not combine historical denominators.

Named-answer support, correction admission, dependency resolution, correction
explanation, mistake visibility and optional/unrelated admissions remain separate.
An original-only reference names the answer without reproducing the correction
rationale. Self-contained E07 alone names the restored value and acknowledges
the error. Referential E07 alone withdraws the mistaken value but cannot name its
replacement; E01+E07 supplies that explanation. No rule makes earliest, newest
or most repeated automatically authoritative. The complete ledger's explicit
restoration, not origin reservation, grounds the author's reading. No unresolved
interpretation was recorded in these six labels; that is not independent proof.

## Packets And Omissions

The artifacts contain **63 exact paired request records**: twelve selected-arm,
six empty-history and 45 distinct-per-case reference packets. All labeled answer,
correction, mistake and optional-detail alternatives are represented. Every
reference supports its declared use after admission; each empty packet lacks a
named answer. This verifies availability under the labels, not their correctness.

All 63 fit with zero capacity omissions. Generation estimates are **877-1,659**
against **11,213**; reviewer estimates with the full **4,096-token reply reserve**
are **8,394-9,204** against **11,469**. The suffix ceiling remains **640**, with
an empty suffix. These are source-owned estimates, not provider token measurements.
Selection omissions, capacity omissions and intentional evaluator exclusions
are recorded separately. Capacity failures and ambiguous labels cannot trigger
the investment signal; a missing correction is not a resolved or dangling one.

Generation/reviewer H packets match exactly, with complete pairs, roles, hashes,
timestamps and packet-local handles. `source_order` receipts retain original
message identities and conversation-wide sequence numbers, which the H wire
format itself does not expose. A narrow runtime-owned request helper is shared
with the old audit; its 68 packets and comparison still regenerate byte-for-byte.
All old reports, freezes, labels and outcomes retain their original digests.
DeepSeek names in requests identify the existing serialization profile only;
no API-mode substitute for Pro consultation was made.

## Inspect And Reproduce

[comparison.json](comparison.json) binds each request digest, case/pair assessment,
full omission reasons, source-order receipts, execution-source hashes and the
[packets.jsonl](packets.jsonl) digest
`5eadb2b5cf8ad52c4f46691d92b0bae8365b29f7cb7859bf01f0e8ab63e1aa27`.
The reviewer candidate is an explicit synthetic placeholder, not model output.
The JSON/JSONL are generated evidence artifacts, not manually edited source.

From the repository root, without providers or a database:

```sh
PYTHONPATH=. uv run --locked python services/ade-api/tests/agent_runtime/story_correction_comparison.py
uv run --locked python -m pytest workflows/evals/character_memory_dev/story_continuity/correction_dependencies/tests services/ade-api/tests/agent_runtime/test_story_correction_comparison.py -q
uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity workflows/evals/character_memory_dev/tests/test_attribution_contract.py -q
```

Final verification: the new suite passed **23 tests**; the combined packet,
admission/capacity and attribution command passed **90**, with **one existing
private-evidence skip**. Broader runtime/story-workflow/attribution checks passed
**551**, with **76 PostgreSQL/private-evidence skips** and one existing
Starlette/httpx deprecation warning. Ruff lint/format, scoped whitespace and
33 local-document link/anchor checks passed. Both standalone generators and
exact in-memory reproduction preserve historical bytes and new packet digests.
Database, provider and native verification remain unperformed.

## Next Investment And Stop

Proposed next deliverable, not started: one bounded design for question-critical
linked-evidence recovery inside the existing history ranking/admission owner,
preserving four complete source windows, scoped archived access and the same
evidence supplied to generator and reviewer. Explain how a referent is found
without oracle labels, automatic origin priority or phrase-specific correction
rules before choosing a mechanism. No extra reviewer, episode graph/store,
runtime prompt, model setting, prototype or native sequence is selected here.

The measurement is complete even without a retrieval fix. These are small
constructed corpora, one acknowledgment/restoration template across three
dimensions and exposed author labels, not independent natural-language
replication or statistical generalization. Wording also changes lexical features,
although the selected IDs did not change within these pairs. Qwen/embedding
retrieval, native interpretation, naturalness, persistence and production quality
remain unmeasured. Keep the baseline, preserve the earlier native turn-7 stop,
and stop before the proposed design or another live run.
