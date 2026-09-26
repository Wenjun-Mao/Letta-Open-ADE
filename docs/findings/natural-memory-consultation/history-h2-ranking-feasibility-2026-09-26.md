# H2 Historical Ranking Feasibility, 2026-09-26

Status: Completed finite synthetic ranking probe; director review pending.
This is retrieval feasibility, not delivered dialogue or production evidence.

## Frozen authority and execution

The integration was committed as `76c2108206bf94ecb61cc6f054049265d8d68ba2`
before live embeddings. The frozen contract SHA-256 was
`4ac62cf6a3daf1335ff13492007b6ae1b90918920c56a979c41c39a669d98721`;
development fixture SHA-256 was
`110d5dce2f2777dba061640518f81a8152e2ec43cdf6eff78a4845eb4b527c17`;
held-out fixture SHA-256 was
`7a402aa3b0dba6c0672515698248b511c214fa08ed37c94fc0db2b881d7886df`.
The configured route was `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B`,
artifact `Qwen/Qwen3-Embedding-0.6B` revision
`97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, 1024 dimensions, and
deployment fingerprint
`c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086`.
The same identity passed preflight for both phases.

The runner used only frozen synthetic fixture text. It did not seed or read a
native database during these live calls and makes no claim of a fresh source
check for fixture-owned text. Native source-bearing dispatch is separately
implemented behind the accepted repeatable-read snapshot and fresh guard.
No DeepSeek generation or reviewer request was made.

## Development selection

| Case | Recipe | Top four exchange IDs | Evidence outcome |
| --- | --- | --- | --- |
| Mandarin coffee paraphrase | Literal | d8, d2, d5, d12 | Ranking miss: d1 absent. |
| Mandarin coffee paraphrase | Qwen cosine | d1, d2, d8, d11 | Sufficient: d1 present. |
| Concern and distant resolution | Literal | e11, e2, e12, e10 | Topic hit only: e1 absent. |
| Concern and distant resolution | Qwen cosine | e11, e2, e1, e6 | Sufficient: e1 and e2 present. |
| Unrelated weather query | Literal | z7, z10, z9, z8 | Four irrelevant admissions. |
| Unrelated weather query | Qwen cosine | z7, z6, z10, z2 | Four irrelevant admissions. |

Both positive development corpora had 12 candidates, and the unrelated corpus
had 10. The frozen rule requires every positive minimum evidence set in the
top four, then minimizes irrelevant admissions, then prefers literal on a tie.
Literal failed both positives; Qwen satisfied both. Both admitted four
irrelevant windows without a no-match cutoff. **Qwen cosine is the selected H2
recipe for this bounded probe.** The irrelevant-admission risk remains explicit.

## Held-out ranking

The selected Qwen recipe ran once on each of the four frozen held-out cases:

| Case | Eligible corpus | Ranked IDs | Exchange evidence outcome |
| --- | ---: | --- | --- |
| Archived earlier version | 2 | a1, a2 | Sufficient. |
| Correction then original value returns | 3 | c1, c3, c2 | Sufficient. |
| Removed fact acknowledgment | 1 | f1 | Sufficient. |
| Distant concern resolution | 2 | q2, q1 | Sufficient. |

All required exchange IDs were present. These corpora fit entirely within
four windows, so the held-out result primarily confirms coverage and scope;
it does not independently establish rank quality under pressure. The runner's
exchange-level sufficiency does not score whether a model will interpret
correction, removal or resolution metadata correctly after admission.

## Dispatches, artifacts and limits

Fourteen Qwen embedding dispatches occurred: one document batch and one query
request for each of seven cases. The document batches covered 42 synthetic
exchanges in total. All 14 redacted receipts report success, with no failed or
unrun scheduled cell and no reroll. Development Qwen case times were 2.579,
2.484 and 2.586 seconds; held-out times were 2.474, 2.430, 4.694 and 2.606
seconds. These are embedding/ranking case times, not full turn latency.

The ignored [development result](../../../workflows/evals/character_memory_dev/outputs/history-h2-ranking/development.json)
(SHA-256 `8c6bc0ff6c648f05be0edcfd2834f34116f237d619e4531234ac13599142ba32`)
and [held-out result](../../../workflows/evals/character_memory_dev/outputs/history-h2-ranking/heldout.json)
(SHA-256 `b51bcfcfcba8a5345601da1c2a65d03cbc73e3344d4e9314a329bd97d4e7e7dc`)
retain every candidate score, ranked ID, query/document and recipe hash,
scope omission, evidence assessment, latency and redacted input-hash receipt.
The held-out CLI summary printed `selection: null` because that phase did not
copy the development selection into its summary; all four saved cells identify
the Qwen recipe and the runner's summary field was corrected afterward without
reissuing an embedding request.

Offline integration passed 66 focused tests, four disposable PostgreSQL guard
tests and 16 independent worker cases, including a native Qwen fake-router
turn. The first combined worker rerun failed before conversation dispatch
because `history_ranking` was absent from the provider-trace stage allowlist;
that contract was corrected and the 16-case fresh-database rerun passed.
Earlier H3 PostgreSQL reader fixtures had left pending runs, so worker checks
use a separate fresh database. No production/default/release binding changed.

Next gate: director review of H2 evidence. H4 native dialogue and persistence
scoring remain unrun.
