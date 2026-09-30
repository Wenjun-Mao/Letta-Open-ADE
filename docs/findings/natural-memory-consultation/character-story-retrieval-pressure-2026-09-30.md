# PC-11 Offline Retrieval Pressure: Evidence Loss, Not A Qualified Fix

Date: 2026-09-30. Status: completed offline diagnostic, agent-reviewed.
Relevant agreements: PC-03/04/05/09/10/11. No product/runtime/prompt change,
native requests, database access, historical requalification or deployment.

## Question And Method

The [native probe](character-story-native-2026-09-30.md) stopped because its
original episode ranked fifth while four later exchanges were selected. Its
answers were consistent. Does that omission only matter to its strict gate?

The runtime-owned
[`test_story_retrieval_pressure.py`](../../../services/ade-api/tests/agent_runtime/test_story_retrieval_pressure.py)
constructs portable, explicitly synthetic English transcripts and 1024-dimensional
unit vectors. Their cosine scores reproduce the **rounded score shape**, not the
texts or embeddings, of native turn 7. Changed documents receive fresh synthetic
vectors and document/recipe hashes. This is a controlled information-availability
experiment, not Qwen retrieval-quality evidence or a replay of private captures.

Both existing Qwen recipes execute through `rank_native_history`, with fake
in-process embeddings and both source-authorization callbacks. V2's two query
vectors are deliberately identical to isolate selection from query mixing.
Selected windows pass through real `admit_history` and `natural_review_request`.
Tests compare complete generation messages and reviewer requests, verify equal
history in both paths, and confirm zero packet-capacity omissions. No model
generates an answer or reviewer decision. No evaluator labels enter model input.
The archive flag is varied in the paired-origin control; database eligibility,
scope isolation and actual version transitions are not re-tested here.

## Observations

| Control | Deterministic result | What it establishes |
| --- | --- | --- |
| Faithful rain/solo/tailor-shop echoes | Original omitted; all four echoes preserve the core. | Original admission is not necessary for every faithful recall. It remains mandatory in the closed native probe. |
| Same sunny/solo/flower-shop echoes, different originals | One original agrees; the other says rain/tailor-shop. Both produce identical generation and reviewer input. | The selected evidence cannot distinguish faithful echoes from repeated errors. This is a potential continuity problem, not just a provenance label. |
| Oracle origin plus three echoes | Both conflicting accounts become visible to generation and review. | Source recovery restores evidence; it does not prove conflict resolution or natural replies. |
| Original retained, low-ranked explicit day correction omitted | Histories with and without "Friday, not Saturday" produce identical packets, even with oracle origin reservation. | Keeping the earliest source alone cannot guarantee correction visibility. Whether the correction is valid still needs semantic assessment. |
| Oracle origin plus correction plus two echoes | Original and correction both visible. | Positive evidence-availability control only, not approval of every claimed correction. |

Under the controlled scores, selection is always `s5, s6, s4, s3`; `s1` and `s2`
are `selector_not_selected`. Paired corpora have different private document and
recipe hashes, but the omitted source text never reaches either model. More
careful model reasoning cannot reconstruct which of these two histories occurred
from identical input. This prevents reliable selection of the differing
weather/location details, not every faithful answer to the broad query: a
common-core retelling could fit both histories. Abstention is not the only
alternative. This wording was qualified after [external review](character-story-retrieval-review-assessment-2026-09-30.md);
the synthetic inputs and outcomes are unchanged, and model behavior is unmeasured.

## Root Cause And Disposition

**Failure represented:** repeated retellings can crowd out evidence needed to
check their accuracy, and an omitted correction can remain invisible even when
the original is supplied.

**Why and where:** `history_ranking.rank_windows` truncates independently scored
exchanges to four. It represents relevance, chronology and stable identity, not
relationships between establishing claims, echoes and corrections. Admission
preserves those four complete windows correctly; the reviewer receives the same
limited history. This localizes the demonstrated information loss before model
interpretation, not in archive visibility, persistence or packet capacity.

**Decision for this iteration:** retain the baseline and frozen gate. These tests
document a limitation; they do not fix or qualify retrieval. Existing ADR 0049
governs synthetic-versus-native evidence. No new production contract is selected.

Do not promote an unconditional "oldest wins" rule: origin reservation restores
one missing source but can still miss a correction, and the model must distinguish
correction from attempted rewriting. Do not raise only `TOP_K`: admission also
has a four-window bound, and a larger finite list remains vulnerable to more
echoes. Neither limit is changed here. Do not introduce an episode store or fact
type from this diagnostic (PC-09).

## Next Bounded Work

Historical recommendation below: the subsequent diversity experiment and
[review assessment](character-story-retrieval-review-assessment-2026-09-30.md)
now favor auditing query-relative packet sufficiency before another selector.
This does not revise this experiment's frozen inputs or results.

Evaluate a source-diversity/related-source recovery candidate offline before
choosing runtime semantics. Its central question is how to recover relevant
establishing and correction exchanges **without evaluator episode IDs, expected
quotes or an oracle-selected origin**. This is a research direction, not an
accepted algorithm. First compare evidence availability on independently labeled
cases: faithful paraphrases, repeated wrong retellings, explicit supported error
correction, unsupported rewrite requests, distinct similar episodes, and
unrelated-topic controls. Preserve scope, source guards and paired capacity.

A candidate must improve those cases without suppressing compatible details or
mistaking every old claim for authority. Record a concise ADR only once the
selection/correction contract is chosen. These synthetic scores do not establish
error frequency, Mandarin retrieval quality, model resolution or reliability.
Those require separately approved native measurements on a fresh baseline;
the previous seven-turn sequence remains closed, with turns 8-10 unrun.

## Verification

Focused offline command:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_retrieval_pressure.py -q
```

Nine controls passed. Broad verification:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity/tests workflows/evals/character_memory_dev/tests/test_history_ranking.py --ignore=services/ade-api/tests/agent_runtime/persistence -q -rs
```

437 passed, three explicit absent-historical-evidence skips (one H2, two H4),
and one existing Starlette/httpx deprecation warning. Ruff check, format check
and `git diff --check` passed. PostgreSQL was not exercised because only portable
tests and documentation changed; no persistence/runtime fix is claimed.
