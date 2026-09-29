# Trial Woodworking Recall: Source-Bound Ranking Diagnosis

Status: 2026-09-29 development diagnostic; candidate v2 is not deployed to the
running trial. Relevant agreements: PC-01/02/03/05/09/10. The trial database
and original user conversations were read only.

Provenance: isolated Compose project `ade-history-trial`, database `ade`/schema
`ade`, source revision `97555ba91a22cb94ddf04ad4f4694b4510de20a4`, and the
running trial's v1 ranker. Both turns bind subject
`c9243a16-9c95-5faa-89c4-6205f9f1ef40` and definition root
`0d2afde2-8a6b-559b-8b22-138f05c09e99`. Target user-message times are
`2026-09-29 19:37:53.263507+00` and `19:39:54.169246+00`. Replay used
`Qwen/Qwen3-Embedding-0.6B` revision
`97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3`, trial deployment fingerprint
`c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086`,
and `history-query-json-v1`/`history-exchange-roles-v1`. The old serialized
query SHA-256 values were `6905321b2294ed539b344a0d171c59215cb2b808ac9edd169441d69bca8c81e3`
for success and `d7391138edeaf4f661879dedb1fd452bd1dfe6a0eb7780a14f566e4a47421690`
for the miss with its actual local suffix.

## Observed turns and as-of source

The original woodworking account is run `a7d9da51-576b-49bf-834f-ede54fe9708c`.
The separate-chat success is `c21b52fe-3842-4f45-bf32-5d81d128fe14`; its
retained outcome admitted the original account and answered with the intended
small stool. The later miss is `315ec99c-4ed2-46bf-a25b-3494baa5ad4e`; its
outcome admitted four city/music exchanges and denied knowing the woodworking
result. A saved-fact search cannot find this one-off event because it searches
profile facts, not transcripts. The miss had no woodworking profile fact.

Reconstructing the exact subject, definition root, purpose, succeeded-pair and
target-time filters gives four eligible prior exchanges for the success and
nine for the miss. The original account was second-newest and seventh-newest,
respectively; the prior correct answer was fifth-newest at the miss. Both were
inside the 128-exchange reader bound. The miss's local suffix was the two
completed exchanges in its own chat about city and live music. No future turn
was included. All relevant source rows had complete pairs and were unarchived;
archive eligibility is not implicated. The retained admission list and source
counts exclude a capacity omission of either woodworking exchange: neither
reached the top-four selector.

## Diagnostic replay, distinct from retained outcome

The running trial did not retain original Qwen scores. A fresh read-only replay
used the pinned Qwen artifact, exact as-of eligible user/assistant documents,
and the old `query_text` serialization. The successful question's source scored
approximately 0.754 and ranked first. The miss with its actual local suffix
ranked the original and prior answer seventh and eighth (approximately 0.345
and 0.343); its top four matched the retained admitted IDs. With the miss's
current question alone, those two ranked first and second (approximately 0.753
and 0.717). Score decimals varied slightly across repeated diagnostic calls;
the ranking and admission conclusion did not.

The proposed v2 `0.7/0.3` score put the original and prior answer first and
second in the same nine-exchange corpus (approximately 0.631 and 0.605).
A separate synthetic anaphoric question over the existing 12-exchange concern
fixture retained both required exchanges in v2's top four (positions 1 and 3);
current-only missed them. These are limited ranking controls, not native reply
evidence. Existing scope and archive reader tests remain the authority for
those structural boundaries.

## Disposition

The root cause is the old single embedding query treating a long, unrelated
local suffix as coequal retrieval intent. The fix belongs in the history
ranker query/score recipe; the reader returned the evidence and generation
could not answer from history it was never supplied. [ADR 0046](../../adr/0046-current-turn-weighted-history-trial-ranking.md)
records the explicit v2 candidate. Original adverse outcomes and H2 captures
remain unchanged. Before any adoption, review the isolated native confirmation
and broader recall tradeoff; no production or release claim follows.
