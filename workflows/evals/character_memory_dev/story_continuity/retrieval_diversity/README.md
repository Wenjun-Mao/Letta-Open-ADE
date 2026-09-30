# Offline Source-Diversity Candidate

Status: experiment only; no runtime integration or native calls. PC-03/05/09/10/11
and ADR 0049 apply. The parent story fixture and closed native gate are unchanged.

## Pre-Observation Recipe

Freeze this recipe and the agent-authored cases before running the comparison.
No independent human annotation or held-out generalization is claimed.

Input is an already eligible corpus of complete exchanges, their text, source
timestamps, opaque IDs and externally computed relevance scores. The candidate
has no episode IDs, expected answers, correction flags or origin annotations.
The limit stays four. Start with maximum relevance; subsequently maximize
`relevance * (1 - maximum_selected_document_Jaccard_overlap)`. Overlap uses
casefolded alphanumeric character bigram sets of complete user/assistant text.
Tie-break by newer timestamp then ascending ID, matching the baseline convention.
Select four or all available sources, even at zero score, as the current selector
does. There is no relevance cutoff, origin reservation, keyword rule or coefficient
tuning. This is a deliberately small novelty-penalized candidate, not a claim of
semantic episode linking, correction interpretation or a production design.

Compare against the existing runtime top-four selector using the existing
`literal_token_match` scorer and current-only query serialization for **both**
arms. These are actual computed lexical scores, not Qwen measurements. Integration
checks own imports of runtime internals; the candidate imports only standard
library code. Tests verify full source packets in generation and review and keep
the existing admission bounds. Corpus eligibility is assumed at this seam, not
re-proven through a database.

## Scoring And Limits

Each fixture's `evidence_groups` are scorer-only alternative source IDs: at least
one per group must be selected for evidence coverage. Faithful echoes may suffice
without the original; ambiguous/conflicting cases require the sources that expose
the distinction, not an automatically declared true answer. `irrelevant_ids`
measure unrelated/cross-episode evidence admission. Empty groups mean no positive
evidence requirement, not automatic useful recall; no-match cases are separately
assessed for irrelevant admissions.

All cases are explicit synthetic Mandarin dialogue, all same-scope eligible.
No field claims independently verified semantic ground truth. Cases include
faithful paraphrases, wrong echoes, supported correction, rejected rewriting,
similar episodes, compatible details, unrelated topics and anaphoric correction.
Do not tune the formula or fixture after seeing output; record failure instead.
Test success is mechanical validity, not candidate acceptance.

Run from repository root, without providers or a database:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_diversity_candidate.py -q -s
```
