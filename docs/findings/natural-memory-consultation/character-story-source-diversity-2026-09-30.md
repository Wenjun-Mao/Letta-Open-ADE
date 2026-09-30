# PC-11 Source Diversity: Evidence Gains, Relevance Tradeoff

Date: 2026-09-30. Status: completed offline comparison; **candidate not adopted**.
Agent-authored/labeled synthetic cases, not independent human evaluation.
PC-03/05/09/10/11 and ADR 0049 apply. No product-policy or runtime change.

## Experiment

The [pressure diagnostic](character-story-retrieval-pressure-2026-09-30.md)
showed that repeated wrong retellings can hide an origin or correction. This
follow-up tests a small content-diversity selector without oracle source IDs.

The [workflow-local experiment](../../../workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/README.md)
froze its recipe and eight Mandarin cases before its first comparison. Both arms
use the existing runtime literal scorer with a current-only serialized query.
The baseline is the existing top-four selection; the candidate greedily selects
`relevance * (1 - maximum overlap with selected documents)`. Overlap is character
bigram Jaccard similarity. There are no fitted coefficients or per-case rules.
All complete exchanges are already eligible; scope filtering is not reimplemented.

Only text, scalar relevance, timestamps and opaque IDs reach the candidate.
Expected evidence groups, case names and rationales remain scorer-side. Tests
mutate those labels and rename IDs without changing selection, reverse corpus
input order, and check nonmutation, finite scores and deterministic tie behavior.
Both selections pass through actual generation/reviewer history packet builders,
with unchanged four-window admission and ample test token capacity. No source
merging, new store, fact writes, models, HTTP or databases are involved.

This uses **computed lexical scores, not Qwen embeddings**. It compares selection
mechanics, not the native baseline's quality. The cases deliberately stress echo
duplication and are neither a random sample nor an independent held-out set.

## Observed Results

Evidence coverage counts pre-labeled source groups; alternatives within a group
are interchangeable. Faithful paraphrases do not require the original. Conflict
and correction cases require evidence exposing the distinction, not proof that
a model resolves it. No-match is not counted as a successful positive case.

| Case | Baseline groups | Candidate groups | Irrelevant admissions, baseline / candidate |
| --- | --- | --- | --- |
| Faithful paraphrases | 1/1 | 1/1 | 0 / 0 |
| Repeated wrong echoes | 1/2 | 2/2 | 0 / 2 |
| Supported error correction | 0/2 | 2/2 | 0 / 1 |
| Unsupported rewrite | 1/2 | 2/2 | 0 / 1 |
| Distinct similar episodes | 1/1 | 1/1 | 3 / 2 |
| Compatible new detail | 1/2 | 2/2 | 0 / 1 |
| Anaphoric correction | 0/2 | 2/2 | 0 / 1 |
| Unrelated topic | Not applicable | Not applicable | 4 / 4 |

Complete labeled evidence improves from **2/7 to 7/7** positive cases, while
irrelevant admissions increase from **3 to 8 of 28 slots**. The baseline's three
are sources about the other episode; the candidate admits one other-episode
source and seven unrelated-topic sources. (Corrected after external review;
the original two/six split was a reporting error, not a change to the scorecard.)
Neither arm abstains on the no-match
case. These are fixture counts, not accuracy percentages or model failure rates.
All selected exchanges reached both packets without capacity drops.

[`observed.json`](../../../workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/observed.json)
records exact source orders, aggregate counts and SHA-256 bindings for the
pre-observation fixture, recipe and implemented selector. Those snapshots were
recorded after observation as regression evidence, not predeclared desired
answers. Tests reproduce the outcomes including the disadvantages. The recipe
and fixtures were not tuned after seeing results.

## Root Cause And Disposition

Novelty is not relevance or authority. Once one exact echo is chosen, another
copy receives zero utility. A different, weakly relevant source can outrank it,
even after the useful origin/correction has been recovered. The same mechanism
that finds missing evidence therefore fills spare slots with unrelated material.

For the wrong-echo case, literal relevance is 0.552632 for each echo, 0.184211
for the original, and 0.131579 for each unrelated source. In one unrelated source,
the five overlapping bigrams are `er`, `nt`, `se`, `us` and `什么`. Four are
serialization/role-label overlap, not semantic evidence. This is a limitation of
using the existing lexical scorer for this experiment; it does not establish the
same score behavior for Qwen. We do not patch that scorer or alter the query here.

The candidate recovers sources without hardcoded origins in these fixtures.
That does not distinguish general diversity from exact-copy handling; see the
review addendum below. It does **not** justify production integration: it admits
more unrelated text, does not identify correction authority, and has no measured
native retrieval or generation benefit. Keep it evaluation-only and unadopted;
do not describe passing characterization tests as a retrieval fix. No new ADR
is needed for an unadopted experiment under the existing evidence convention.

## Next Decision

Do not stack keyword exceptions, silently tune a threshold against these cases,
or promote an "oldest wins" rule. A next candidate needs to recover related
sources while allowing unused capacity when evidence is irrelevant. Pure novelty
and mandatory slot filling are not enough. A relevance gate also risks excluding
short/anaphoric corrections, so any proposal must address that tradeoff rather
than merely drop low lexical scores.

Before selecting runtime semantics, use a new frozen comparison and independently
reviewed source labels. Native embedding measurements can distinguish lexical
formatting artifacts from a retrieval problem; they require separate approval
and a fresh bound experiment. Generation/reviewer behavior would still need its
own test. The previous native sequence remains closed at turn 7; no gate is
weakened, turns 8-10 remain unrun, and the retained trial is untouched.

## Verification

Focused comparison: 18 tests passed, including eight paired selections/packets.
Run the command in the experiment README with `-s` for the complete scorecard.
No PostgreSQL checks are required for these evaluation-only source changes;
no persistence or eligibility improvement is claimed.

Broad portable verification:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity/tests workflows/evals/character_memory_dev/tests/test_history_ranking.py --ignore=services/ade-api/tests/agent_runtime/persistence -q -rs
```

455 passed, three explicit absent-historical-evidence skips (one H2, two H4),
and one existing Starlette/httpx deprecation warning. Ruff check, format check
and `git diff --check` passed. No push, deployment or provider requests.

## External Review Addendum (2026-09-30)

The [source-checked review assessment](character-story-retrieval-review-assessment-2026-09-30.md)
qualifies the interpretation above without changing any frozen fixture, recipe,
selected IDs or aggregate score. In all five newly covered cases, seven windows
contain exactly four distinct complete user/assistant text pairs. One
representative per distinct pair makes every declared evidence group available.
The experiment therefore does not distinguish a general novelty benefit from
freeing slots occupied by exact copies. This is not a runtime deduplication
recommendation: repeated text can carry distinct times, attribution and authority.

Coverage groups also mix answer support, conflict visibility, rejected-request
provenance and optional detail. Their necessity for the exact query was not
independently established. Preserve 2/7 versus 7/7 as diagnostic coverage, not
answer accuracy or native retrieval benefit. The native selected windows were
different elaboration/refusal/retelling/denial exchanges, not exact duplicate text.

The earlier suggestion to proceed directly toward relevance-gated recovery is
superseded by the assessment's narrower recommendation: first establish which
missing evidence changes justified answers. Runtime remains unchanged. A fresh
packet-sufficiency audit is conditional, not launched by receipt of the reviews.
