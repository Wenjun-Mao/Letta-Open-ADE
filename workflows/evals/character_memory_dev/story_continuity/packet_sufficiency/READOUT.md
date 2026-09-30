# Packet-Sufficiency Diagnostic Readout

Date: 2026-09-30. **Completed as an explicitly non-blind synthetic diagnostic
under ADR 0055, not as the originally planned blind audit.** No provider, API
review, database, native turn or model response was executed. The novelty
candidate remains **unadopted**; the runtime and original native stop are unchanged.

## Decision

Retain the existing selector. The novelty candidate recovers useful opposed
evidence in one new nonidentical-retelling control, so its observed benefit is
not restricted to exact duplicate padding. But both selectors fail the new
antecedent-dependent weekday question, and novelty selection removes a correction
that the baseline did recover. This is evidence of a remaining dependency-recovery
problem, not a reason to tune this fixture or qualify the candidate.

The old complete-source-group gains also overstated some answer needs: C02's bag
contents and C07's solo participation are supported by both arms. Added wet-corner
or rejected-rewrite context improves detail/visibility, not the minimum answer
under the reports' accepted readings. Preserve the old scorecard rather than
retroactively changing its meaning or denominator.

## Evidence And Procedure

The [two original reports](reports/assessment-2026-09-30.md) disclosed inherited
ADE context. The user accepted using them after a replacement preflight failed,
and declined API substitution. They are neither certified blind annotations nor
verified independent endorsements. All conclusions below remain conditional on
their source-checked interpretations and the author's fixture construction.

[Judgments](judgments.json) were transcribed and hash-bound in commit
`bed18094eaaeabe66c5d754cb098fcccf29ec952` **before** new-control selection.
The original eight cases, two new controls, exact queries, chronology, context,
old outcomes and source-owned selectors still pass the original input freeze.
No scorer, selection coefficient, source role, capacity limit or fixture changed.

Both selectors receive only complete user/assistant text, opaque source IDs,
synthetic ordering timestamps and the same current-only literal-bigram scores.
All eight historical arm selections reproduce their frozen results after the
one-to-one neutral-ID translation. Report judgments and reference sets are
evaluated only after selection; none enter either selector.

Reader assumptions are the frozen controlled context: independent cases, eligible
same-user/same-character archived history, separate synthetic chats per exchange,
empty current local suffix and saved facts, and no authored persona fact resolving
these events. These are not native chat-adjacency receipts. The external rubric's
story contract is an evaluation criterion, not a claim that the full native prompt
or all normative text was supplied verbatim to a model. Actual runtime-owned
instructions and request shapes are inspectable in the saved packets.

## Case Results

IDs below are complete neutral exchanges; their displayed order is selection
order. "Supported" means an annotated answer route is present after admission,
not that a model generated, interpreted or preferred that answer.

| Case | Baseline admitted | Candidate admitted | Post-admission interpretation |
| --- | --- | --- | --- |
| C01 | 02,05,04,07 | 02,05,07,06 | Neither supports named Friday. Baseline includes E04's correction without E01's antecedent; candidate includes neither. |
| C02 | 06,05,04,03 | 06,02,01,07 | Both support bag contents. Candidate also exposes wet-corner disclosure and its explicit bag anchor, with one unrelated admission. |
| C03 | 06,03,05,04 | 06,03,02,01 | Empty history is sufficient for a new present piano choice. Both selectors unnecessarily admit four unrelated windows. |
| C04 | 05,04,03,02 | 05,01,07,06 | Baseline shows only one account. Candidate supports a qualified place/weather conflict, but includes two unrelated windows. |
| C05 | 05,04,02,01 | 05,02,04,01 | Both support a bounded next-day outcome and explicit search. Neither establishes eventual fate. |
| C06 | 04,05,02,06 | 04,05,02,01 | Candidate recovers the sole opposing account among seven distinct text pairs; baseline hides it. No unrelated windows in either arm. |
| C07 | 06,05,03,02 | 06,04,01,07 | Both support solo rather than shared participation. Candidate adds rewrite/refusal visibility, with one unrelated window. |
| C08 | 06,04,03,02 | 06,01,05,07 | Candidate supports named-day conflict and restoration-then-opposition visibility; baseline shows Saturday alone. Correction authority remains unresolved. |
| C09 | 03,06,05,04 | 03,06,07,01 | Both support first-encounter snow. Baseline adds three other-episode windows; candidate adds one other-episode and one unrelated window. |
| C10 | 06,04,03,02 | 06,01,05,07 | Candidate supplies first-bowl/later-cup mapping; baseline's generic cup accounts do not. The current occasion remains unspecified. |

Across these ten cases, baseline admits **4 unrelated and 3 other-episode**
windows; candidate admits **11 unrelated and 1 other-episode** window. These counts
include the four no-match admissions in C03 for each arm. The historical
positive-case-only combined counts (3 versus 8) remain unchanged. Do not compare
these different scopes as if they were the same metric.

## References, Ambiguity And Omissions

The audit includes **38 distinct-per-case evaluator reference packets**, one for
every unique answer-route or visibility set, plus ten empty packets and twenty
selected-arm packets. Each reference supports its labeled use after admission;
this checks availability, not the correctness of the label. All ten cases and
all alternative sets can be inspected in [comparison.json](comparison.json),
with report attribution and conditions retained in [judgments.json](judgments.json).

- C01's E01 singleton supports the bare named day under the reports' full-ledger
  assessment; E01+E04 supplies the correction rationale. Neither arm contains E01.
  Missing E04 in the candidate is not recorded as a dangling reference, but is
  separately visible as absent correction evidence. Absence is not resolution.
- C02's E02-only wet-corner route remains conditional on cross-chat coreference.
  It is not needed to certify a contents-based answer. The candidate includes an
  explicit anchor anyway; neither reading changes the arm's contents support.
- C08 preserves B's additional conditional `{E02,E05,E06}`, `{E03,E05,E06}` and
  `{E04,E05,E06}` withdrawal/reassertion references. Neither selected arm contains
  one, so this enumeration difference does not change the arm contrast. The
  candidate can name Friday and show restoration, but cannot reconstruct the
  pre-correction Saturday target without a pre-E05 Saturday source. That latter
  dependency is optional for its named-day conflict route and is not a failure
  of every possible answer. No adjudicator or automatic correction-priority rule
  is introduced to resolve the remaining product ambiguity.
- C10's conditional E01-only first-class answer stays conditional. E05, also
  selected by the candidate, supplies an unconditional episode-distinguishing
  route without asserting what occasion the current question intended.

All **68** packets fit without capacity omissions. Generation input estimates
range from **874 to 1,621** against **11,213**; reviewer estimates with the full
**4,096-token candidate-reply reserve** range from **8,390 to 9,165** against
**11,469**. The shared-suffix ceiling remains **640**, with an empty suffix here.
The prior five toy checks separately cover oversized messages/annotations and
nonempty local/H overlap; they do not add semantic cases to this diagnostic.

Generation and reviewer history packets match exactly, with complete source
pairs, attributed roles, source hashes and timestamps. Capacity is not the cause
of the semantic evidence omissions above. These are source-owned estimates,
not actual provider token usage. DeepSeek route names in the serialized runtime
packets identify the existing test profile only; no API call or substitute for
the Pro-mode consultation was made.

## Inspect And Reproduce

[packets.jsonl](packets.jsonl) contains all exact generation/reviewer request
objects, one keyed packet per line. The reviewer candidate text is explicitly a
synthetic placeholder, not a model response. `comparison.json` binds the JSONL
digest and each request's digest and records selected/admitted IDs, omissions,
capacity estimates and separate assessment dimensions. Both files are generated
audit artifacts, not manually edited source.

From the repository root, without providers or a database:

```sh
PYTHONPATH=. uv run --locked python services/ade-api/tests/agent_runtime/story_packet_comparison.py
uv run --locked python -m pytest workflows/evals/character_memory_dev/story_continuity/packet_sufficiency/tests services/ade-api/tests/agent_runtime/test_story_packet_sufficiency.py services/ade-api/tests/agent_runtime/test_story_packet_comparison.py -q
```

The generator owns runtime imports at the service-test layer, while the workflow's
input/judgment loaders remain standard-library-only. Regeneration must reproduce
the committed artifacts; do not refresh labels or selectors to obtain a pass.

Verification: the focused command passed **29 tests**. The broader runtime and
story-workflow run passed **510 tests**, with **76 PostgreSQL/private-evidence
skips** and one existing Starlette/httpx deprecation warning. Ruff lint/format
and scoped whitespace checks passed. No live-service verification was performed.

## Limits And Next Investment

This completes the amended offline diagnostic, not the original blind evidence
objective, a retrieval fix, native model quality, naturalness, persistence or
release qualification. Small authored synthetic cases and exposed-context labels
do not establish general novelty benefit. C06 weakens the exact-copy-only
explanation; C01 independently demonstrates that novelty is not dependency recovery.

If more work is chosen, the next bounded measurement should contrast self-contained
and antecedent-dependent corrections under nonidentical competing retellings,
with more plausible distinct sources than slots and labels frozen before outcomes.
Its question is whether recoverable, question-critical dependencies survive,
not how to make this candidate win. That is a proposal only: no additional corpus,
review, selector or native sequence is launched by this readout.
