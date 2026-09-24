# Natural factual-continuity diagnostic: infrastructure stop

Status: stopped at the first native turn. The user authorized this small live
diagnostic after the reviewer/ADE responsibility amendment. Its eleven-turn
schedule and complete-delta expectations were frozen in
`workflows/evals/character_memory_dev/fixtures/natural_memory/factual_live_diagnostic.json`
before dispatch. This is no semantic pass/fail result or policy selection.

## Exact binding and observed requests

The attempted source was `b22fad9b8a6411f904eb5bc3a8418cf039541647`,
fingerprint `cf64fae94761a403855ed11c41f6f951033852838b3c49ea1e5ef02da9047947`.
The schedule SHA-256 was `db71c625fa9d3ba7047fcb5faf9a3e803df591afa6fe4d405d12b4c900b1ec3a`.
The held context was `natural-user-assertions-v4-b`; reviewer input limit 6,759,
output allowance 4,096, no reviewer repair, turn retry count zero. The DeepSeek
Flash route retained its high-thinking profile and catalog fingerprint
`870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`.
The Spark Qwen embedding fingerprint was
`0f16a45a659a9e5708e1705e750a27ce350c93c8caea1edb01b34d39fff3789f`.
The reviewer instruction/schema hashes in the private manifest identify the
exact wire contract. No release-policy fingerprint was rebound or waived.

The first router preflight output (`natural-factual-live-20260924-01a0d5b7`)
stopped before any model dispatch: an IP-form Spark URL did not match the
pinned catalog URL. A local DNS bridge restored the exact `dgx-spark` URL, and
both pinned deployments appeared in the catalog. The second output
(`natural-factual-live-20260924-01a0d5b7-v2`) began the first native turn.
Observed dispatches: **zero DeepSeek generation**, **one Spark embedding
attempt, zero completed, one failed**. The worker event log separately shows
a completed router catalog observation and the failed `retrieval_query`
embedding request. The native run failed with `http_502` after one attempt.

## Root cause and database delta

The isolated router could discover Spark synchronously, while async HTTPX
could not resolve `dgx-spark`. Its resolver supplied the hostname as bytes;
the diagnostic host's local alias bridge matched only a string. The failed
embedding capture, router `upstream_unreachable` path, and a separate async
catalog GET that reproduced the name-resolution error support this diagnosis.
The bridge now handles both forms; a unit test covers them, and an async GET
to the pinned `/models` route returned HTTP 200. This correction is confined
to the local diagnostic host. It preserves the deployment's pinned URL and
does not alter ADE product semantics or provider selection.

Independent PostgreSQL readback of the retained disposable database
`ade_m2_memory_test_01a0d5b7` found one accepted user message, one failed
run/attempt, **zero assistant messages, facts, revisions or embeddings**, and
subject memory generation **1**. The subject's one implicit entity existed at
session setup; the failed turn added no entity. The native attempt artifact marks generation,
candidate reply and reviewer stages absent, and the candidate undelivered.
Thus no source citation or factual lineage was created. The remaining ten
predeclared turns were unrun. There are no useful reply excerpts to assess;
the browser success check could not apply. No semantic result, recall claim,
habit/preference judgment, or failure-rate estimate follows from this stop.

Private, mode-restricted captures are retained under
`workflows/evals/character_memory_dev/outputs/natural-factual-live-20260924-01a0d5b7-v2/`.
The manifest SHA-256 is
`dc2fba6d0e5c9b66fc194c3d823a40b5fb0a67a60cf77f16e7b15db0f8955ad7`;
attempt SHA-256 is
`36428ae1fe1a2d75b2793873cc8075ba1d8c0955c55006b6fbeb1dddf07730f7`;
failed dispatch capture SHA-256 is
`290fbc242a4002891380b241aadc6f523c52999aad210ccb3e1e53c11357532d`.
The router and worker stopped after capture. The database and ignored evidence
were retained for audit.

Next move: review this stopped attempt and authorize a newly bound run if the
factual-continuity question still needs live evidence. Do not resume or reroll
the failed turn under this schedule. The frozen 30-cell campaign and release
gate remain separate.
