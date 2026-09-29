# Trial Woodworking Recall: Source-Bound Ranking Diagnosis

Status: 2026-09-29 development diagnostic, one disposable native confirmation,
and reviewed v2 adoption in the isolated trial at 20:36 UTC. No production or
release adoption. Relevant agreements: PC-01/02/03/05/09/10. The trial
database and original user conversations were read only during diagnosis.

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

## Root cause and candidate

The root cause is the old single embedding query treating a long, unrelated
local suffix as coequal retrieval intent. The fix belongs in the history
ranker query/score recipe; the reader returned the evidence and generation
could not answer from history it was never supplied. [ADR 0046](../../adr/0046-current-turn-weighted-history-trial-ranking.md)
records the explicit v2 candidate. Original adverse outcomes and H2 captures
remain unchanged. The single native confirmation below supports the narrow
fix for this miss. Broader recall quality remains unqualified. The later
trial-only rebuild is recorded at the end; no production decision follows.

## Retained replay inputs and request counts

Ignored local source export:
`workflows/evals/character_memory_dev/.trial/diagnostic/asof-source.json`,
SHA-256 `d0eb7f6a3a6432d1e3195a991f713455a7acd86e6f74b9a9956d88dee5b71b07`.
The adjacent `source_export.py` applies the as-of scope, completed-pair and time
filters and checks each message hash. The export holds nine source exchanges,
the four local suffix messages at same-chat sequences 1–4, and the exact failed
question. No later message entered the export. Documents use
`User: …\nAssistant: …`; the old serialized query hash is the `d739…` value above.

| As-of run ID | Document SHA-256 |
| --- | --- |
| `b2534128-555e-414b-9329-e355c0116c17` | `5ab303153e2187f9a4678c88aa1efd21150ba3d56237436a45b9ad0e04514c97` |
| `ef2d932e-3a8b-4ada-ba40-280798d1f0bb` | `d44a27aff9c6c305694e9b59bb651a7e0d05873077ad8c59b8b1fa0c85ad7d33` |
| `b67b76a8-9ef2-4da9-b75d-23d5e834fd86` | `219d5f77ba223437dc9657b324bc7652afadca6cc53b91981af24d53fd8ee4b4` |
| `e2852412-3cb7-42f0-8c17-f5341d3a8f22` | `4b1748c0b66c561f20e65546ed0d366038033f1404aae5bb4757ca4041e1f55f` |
| `c21b52fe-3842-4f45-bf32-5d81d128fe14` | `de7a04dea957424e6a5db410e355a758e3a25b1d973f418029586754ca77cf45` |
| `8489927e-0380-49c3-8137-5b608d3106a7` | `16a63a78f3d9b0c18847ee7e6601865a5b6360ddf81b36f7a0fcfcee0e4e1f72` |
| `a7d9da51-576b-49bf-834f-ede54fe9708c` | `a5f94eb6b5c903317ca2f57d0d3c8351021eb7d62bb11b3e139c30afdb7d5b84` |
| `9e6ec63f-3e3d-4a37-82c8-dfcc6ba34786` | `c35f89d181f7c5e9880c5417d9dec89be03e4429e134148a43b6cf751a1a255a` |
| `a05938f8-c51a-4cc6-8b2d-8c60ceabfe26` | `0e3f0df52142e8bb1e1ca7f4ebe19eb03de5f8b2ef5148fa441eee50f7d4ade2` |

The local suffix content SHA-256 values, in sequence order, are
`2e9dcd1e23a03a6996bbdaf21660f5609714fd6472d5a04e068c7ac1fdb618dc`,
`df80cb9ccae9ee6c4f83c17e44c682f1fbb9baed9dd7110f3fe2a026ddf6e88a`,
`34d66f32f69da3dd8d23a5ae7759f93d90bb3451c15b47cf1f00a56aafaeee3d`,
and `035c1e7eb75127d074d086203a884fe27b4f65256155daef1a5d7636cdfe7641`.

Ignored local `rank-manifest.json` has SHA-256
`7e10893ac91bfdfcb6e9e8a7ce6d28bc8b996a6c6dbf9011044abbbb7fa09e7e`.
The adjacent `rank_manifest.py` loaded the committed candidate module into a
separate process and ranked that exported source under v1 and v2. V1's top four
exactly matched the retained miss; v2 selected the original account and earlier
answer first and second. This fresh replay made **four** Qwen embedding
requests, two per recipe. They are diagnostic requests, never original-run
receipts. Original scores were not persisted and cannot be recreated exactly.

Retained `model.request.started` events, with matching completed events, show:

| Run | Conversation | Reviewer | History ranking | Retrieval query | Tool retrieval | `search_memory` tools | Catalog |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original success | 1 | 1 | 2 | 1 | 0 | 0 | 1 |
| Original miss | 2 | 1 | 2 | 1 | 2 | 2 | 1 |

All six success and nine miss model requests completed. These counts are
observational; the original trial retained no full ranking-score record.

## One isolated native confirmation

A new subject and definition were created in disposable evaluation database
`ade_m2_memory_test_01a0eec6b`, never in the user's trial database. The ignored
`native_confirmation.py` seeded the seven nonlocal prior exchanges as complete
runs and the two target-chat city/music exchanges at sequences 1–4. It submitted
the exact failed question once through the existing H4 worker/capture path with
the candidate prompt, pinned DeepSeek/Qwen identities, v2 recipe, 180-second
timeout, zero retries and the existing two-request conversation ceiling.
The disposable definition's prompt SHA-256
`bbf7994507491171983300a3cfdfcd823692168d3035bbf6a6b36461dc6010a7`
and persona SHA-256
`d78cf538395a685f960866a4ab3e9f375aeefb5aa94de8f6fcbae03ab152085b`
match the original user's immutable trial definition version.

Ignored local captures:
`workflows/evals/character_memory_dev/.trial/diagnostic/native-confirmation-20260929/`.
The `manifest.json` SHA-256 is
`e8ef56a6f3d11818aa19c0c53c9ecab413260c6d8883318d3b075a7ab079a378`;
the attempt SHA-256 is
`91dbb8715d40de60266f451a7a95b0a64abe227638f5047d0b1a5c4bec2ead7c`.
The native rank saw nine source exchanges and admitted four without capacity
omission. The original account and prior answer were ranks 1–2; every mapped
source document hash matched the export. Native v2 recipe identity was
`a8f45af01d58e26550300d102bbf649422ef39852a7d8ba296792fd995a5ae6f`;
query SHA-256 was
`a1f76e1388b574d90d22766df4dd47d281912ddef4d5c349ab3bc44ac26507ce`.
The query hash matches the external v2 replay; the recipe/corpus identity
differs because disposable runs have new IDs.

The turn committed one assistant reply identifying the small stool and the
shortened board. The persisted message content hash
`2eab68fb5a1bac409cd63751643d27f998824ff3ff939841f14746608ffc4a6d`
matched the captured reply. Its other assertions were supported by the two
admitted woodworking exchanges; it made no unsupported city, music or profile
claim. Reviewer decision was empty. Independent before/after reads found zero
facts, revisions, entity additions and memory-generation advance. There were
no tool calls. Complete attempt receipts record one conversation, one reviewer, two
history-ranking embeddings and one retrieval-query embedding: two DeepSeek and
three Qwen dispatches, all completed. No native reroll followed.

For local reproduction, `source_export.py` is copied into
`ade-history-trial-ade-api-1` and run there, then its output is copied to the
ignored diagnostic directory. Copy the committed candidate
`history_native_rank.py` to `/tmp/history_native_rank_candidate.py` in that
container and run `rank_manifest.py` there. The native confirmation uses the
ignored `native_confirmation.py` with the source export hash, a freshly migrated
passwordless loopback database, the existing `.env`, and the configured API
container for Qwen embedding. Its invocation and raw receipts remain in ignored
local storage. The separate database container `ade-wood-check-01a0eec6`
remains available for manager readback. These artifacts contain user dialogue
and must not be published.

The exact local diagnostic invocations were:

```sh
docker cp workflows/evals/character_memory_dev/.trial/diagnostic/source_export.py ade-history-trial-ade-api-1:/tmp/source_export.py
docker exec ade-history-trial-ade-api-1 python /tmp/source_export.py
docker cp ade-history-trial-ade-api-1:/tmp/woodworking-asof-source.json workflows/evals/character_memory_dev/.trial/diagnostic/asof-source.json
docker cp services/ade-api/src/ade_api/features/agent_runtime/history_native_rank.py ade-history-trial-ade-api-1:/tmp/history_native_rank_candidate.py
docker cp workflows/evals/character_memory_dev/.trial/diagnostic/rank_manifest.py ade-history-trial-ade-api-1:/tmp/rank_manifest.py
docker exec ade-history-trial-ade-api-1 python /tmp/rank_manifest.py
docker cp ade-history-trial-ade-api-1:/tmp/woodworking-rank-manifest.json workflows/evals/character_memory_dev/.trial/diagnostic/rank-manifest.json
PYTHONPATH=. uv run --locked python workflows/evals/character_memory_dev/.trial/diagnostic/native_confirmation.py --database-url postgresql+psycopg://ade_owner@127.0.0.1:32768/ade_m2_memory_test_01a0eec6b --source workflows/evals/character_memory_dev/.trial/diagnostic/asof-source.json --source-sha256 d0eb7f6a3a6432d1e3195a991f713455a7acd86e6f74b9a9956d88dee5b71b07 --env-file /Users/wjmao/projects/HU/Letta-Open-ADE/.env --qwen-container ade-history-trial-ade-api-1 --output workflows/evals/character_memory_dev/.trial/diagnostic/native-confirmation-20260929 --router-port 8147
```

The final command ran once after disposable database setup. Earlier startup
checks rejected an unsupported database name, a vector extension in the wrong
schema, and a container without the API router credential before any native
target turn or DeepSeek dispatch. Their fixes were confined to the disposable
setup; the completed target received no retry.

## Isolated hands-on trial adoption

Manager review approved v2 for the isolated hands-on trial only. At
`2026-09-29 20:36:09 UTC`, the existing `ade-history-trial` API and worker were
recreated from clean commit `6dacaafefe1dfb21c1b2ad32bb9feaf4bb73307f`,
source fingerprint
`f6ebd4e87dcd0a6ab852e3bdfe710c82655cd2d3974884556735771a480922de`.
Only those two services were rebuilt/recreated; PostgreSQL, the model router
and the web container stayed up. The served worker names
`probe_local_qwen_cosine_v2`; both rebuilt containers' native-rank source SHA-256
is `1ec115d92511b1e53e77535bb67075080e0085bb36731d10a678c2a3dc91ec7a`.
The API image is
`sha256:42cde9d0bf8f44149972090b31f355b550434a17854292e2296002b2b8a8d8fd`
and the worker image is
`sha256:631b9e647a46db86a28b8e9071f53bfcbf40363f4c94ce557689861daa75921b`.

Immediately before restart, there were zero pending or running runs. A private
custom-format database backup is retained at
`workflows/evals/character_memory_dev/.trial/diagnostic/trial-before-v2-20260929.dump`
with SHA-256
`9c85c6e0fe289a5a30ab0e4b46d5bb023c823641be883b4901cc97bec145e63d`.
`pg_restore -l` listed the conversation, message, fact, revision and run table
data. The ignored `trial_invariants.py` captured canonical row hashes before
build, immediately before restart, and after the read-only checks. The before
and after files are `trial-before-20260929.json` and
`trial-after-20260929.json` in the same ignored directory. All global and
user-subject counts and SHA-256 row hashes matched, including eight total
conversations, 37 messages, four facts, six revisions, 19 runs and 19 attempts;
for this user, four conversations, 26 messages, three facts and five revisions.
No run was pending or running after restart. The original failed and successful
turns, immutable definitions and source evidence remain intact.

`/api/v2/health` returned 200, `/api/v3/worker-health` returned 200 with
`worker_ready=true`, `database_ready=true` and the served source identity above.
The existing web route `http://127.0.0.1:13001/agent-studio` returned 200.
Via its same-origin proxy, read-only trial options, eight sessions, four
subjects, the user's conversation state and four activity entries returned 200.
No browser tab or draft was touched, and no new turn, model generation or
embedding request was submitted during adoption.

This is an isolated development trial switch. It does not establish general
ranking quality, select a production default, qualify release evidence or
waive the stale-policy gate. The earlier v1 user outcomes and their adverse
assessment remain historical evidence.
