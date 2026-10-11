# Revision-4 Self-Hosted Hindsight OCI Campaign

Updated 2026-10-11. Closeout evidence for the isolated campaign authorized under
[PC-13](../product-contract.md#hindsight-hosting), with PC-02/03/04/07/09/10/11/12
governing scope and response interpretation. The final source was deployed and
the isolated infrastructure and bounded logical restore qualified. Semantic
findings are mixed and do not qualify native adoption, production-release
qualification, or the original measured M2 comparison.

## Runtime and infrastructure evidence

The final candidate used source `a3e78c5c63b17eadc3d02b05ce7e04eb6042944f`,
manifest SHA-256 `a3cc7ef61d2cc1a4d5289c80afb820fb9990cb8d9d89f585b1653ace212d0de0`,
and an immutable 1,166-file staged bundle with SHA-256
`a640db9c2254487a0773624465f47443fe3270fb11851ebddc2e525cefde96be`. The
Hindsight 0.10.3 ARM64 image digest was
`acf5e76bd9a5b65f9f7c540a3414007c7f874b34346587dac7e4feab7ae80cba` (image ID
`5a0d6fe60340607037bc4ee3dfe1b299990d0ca61f21c06ef4f89f5411fc9926`), with
PostgreSQL 17, pgvector 0.8.6, PGroonga 4.0.8 and CPU BGE. Three cached serial
builds completed. Actual pinned-image fake-provider checks made zero external
inference requests.

Final fresh startup, API/control-plane auth and same-source restart were
qualified. Missing/wrong API keys returned 401, correct returned 200, and MCP
returned 404; control-plane missing/wrong keys returned 401, login returned 200,
and the session cookie could access banks. A prior actual Mac SSH-tunnel/browser
dashboard login against the same Hindsight image/auth is retained at source
`fb3ecb3`, screenshot SHA-256
`c3294f574ef5116cdbd98926ae90288919ab08f96a342e40c02d44f7b9a46f9b`. The final
SHA received HTTP auth qualification, not a newly repeated browser test. Final
Chinese readiness recall used the existing bank with no
retain or Character request: 1 merged/reranked/returned fact, 1024 dimensions,
one query-prefix newline, one embedding call, rerank 1.123 s and recall 3.577 s.
Across 69 Character requests, actual wire settings showed DeepSeek Flash,
thinking enabled/high, max 2048, non-streaming, and no `response_format`.
Memory retain/consolidation used 4096-token ceilings, thinking disabled and
JSON-object schema-in-prompt; startup checks used 512 tokens, thinking disabled,
and no JSON format.

Authenticated public-API before/after readback matched the frozen selection
without rebuild, re-ingestion, or changes to container images/volumes. The three
container IDs and mounts were unchanged; `StartedAt` changed across restart.
Fresh epoch 26 (`ac457c8d77fa6a8de6e2079488f374934e7ccfa328b95c512f1e8bffc3b73b63`)
and same-source restart epoch 27 (`5720ff8f2e77335efb20602ee05bf9f0111c2793b7a03ed1f0bbc629ca5e6a8b`)
were distinct. The frozen selection covered four banks, 24 sources, 45 valid
facts, two invalidated facts, and six scopes. Exact original text, context,
fact/entity, curation, and scope projections matched. This is bounded
same-volume persistence evidence, not crash-recovery or Studio archive UI proof.

Ordered P4 finalization token `bb3ee1bb83ee4bff9985d1cf490975d7` was
independently qualified. It drained 62 completed
operations with no pending, processing, or deferred work; produced a 514,967-byte
candidate-only dump, SHA-256
`904ab67bdb14b12522dbe53d27fafb227f8e3590d2ae4d96d287b41843463403`; and
captured the canonical ten-table snapshot. The snapshot included seven banks,
27 documents/chunks, 89 units, two invalidated facts, zero observation-history
rows, 80 entities, 173 unit/entity links, 174 entity co-occurrences, and 280
memory links. Zero-row observation-history JSONL was exactly zero bytes. Other
partial/readiness banks remain in the database; this is not a four-bank-only
database claim. All three main candidate containers stopped with exit 0, no
OOM/restart. Six baseline OCI identities, start times, images, and health were
unchanged; controller and registered job processes are gone, while receipts and
retained candidate DB/cache volumes remain. No native/trial deployment, Cloud
setup, or recurring automation was created.

## Semantic observations

Candidate04 q01 returned superseded jasmine/hot/half-sugar. Readback showed the
corrected proposition existed but lacked the optional profile label required by
the other character's strict scope. Candidate05 initial and post-consolidation q01
returned hot, unsweetened oolong, but also asserted an October 1 first-chat
origin. q01 is an other-root query: the portable preference may be shared, while
private source origin, first-chat participation and time should be excluded. The
s01 message timestamp is October 1 at 09:00 and says “yesterday” about the event
(September 30); event date and message date are distinct. Do not treat September
30 as the expected cross-root answer. A separate post-projection-repair q01
response was empty at the exact 2048-token cap and remains incomplete, not a
semantic pass.

Candidate04 and candidate05 used fresh banks with changed Memory missions/labels.
Corpus, queries, persona, Character model settings, retrieval-token limits,
reranker and concurrency were held fixed. The Hindsight RAM ceiling was also
retuned from 6 GiB to 4 GiB based on measured headroom; no quality/performance
causal claim is made from this comparison.

q02/q03 met their core distinctions, not general reliability. q04 recalled blue
cotton/thread-root and user absence; “workbench bag short stems” is supported by
s05, while prior sewing/leftover-thread detail was unsupported. q06 returned
September 30 after consolidation but invented a past windowsill-letter statement;
the initial “iced lemon” detail was unsupported because s09 says lemon water.
q07 initially recalled the bicycle correctly and hedged unsupported nickname
absence. New naming suggestions may be compatible current fiction under PC-11;
they are not established recalled memories. The post-consolidation response
missed the available bike fact and also followed source-projection repair, so the
change cannot be attributed to consolidation alone. q08's “maybe never
mentioned” is absence-to-negative overreach, not categorical denial; the
unsupported “never forget” promise is separate. A distinct s12 source recognized
the historical October 1 red quote and asked for the current value without
reactivating the invalidated fact.

The invalidation check covered unrelated ingestion, retrying the same original
UUID/body, then a distinct new source. The retry made zero new retain calls, old
fact IDs remained invalidated, and dependent observation lookup returned 404.
New s12 facts had distinct IDs; no old fact was reactivated. This supports only
the tested explicit invalidation/retry contract, not general natural-language
removal or reliable historical recall. The archive fixture establishes
eligibility only, not Studio archive UI/runtime behavior. The campaign is 32
completed cases (16 per candidate), 68 nonempty arms and 69 captured Character
requests; one q01 output was empty at the token cap. This is not a pass rate or
statistical comparison. No winner over native ADE is established.

## Restore, usage, resources, and sealed evidence

The final disposable restore was independently qualified as **logical persisted
PostgreSQL state restore only** under token
`ad652fafae7c42168618ca0b8d75c451`. Restore project `ade-hindsight-restore-ad652fafae7c4216`
used no network or published ports and a 1 GiB/0.25 CPU limit. All ten canonical
data tables, schema/extensions and Alembic state, and frozen scopes matched; the
exact restore container and volume were removed. This does not establish
restored Hindsight API startup, crash recovery, native product continuity, or
Studio UI behavior. The earlier selector, unpublished inventory, and E459
failures remain sealed historical failures; their recovery evidence is not
misrepresented as a restore pass.

The final archive contains 10,054 files/61,491,200 bytes, SHA-256
`ac09bb1ce1450b4841c1b872ffccffc1f777aa3d0d474b5bf5edd1b8c5bf3464`; its
index SHA-256 is `26e6685880f4021371323f8f6663403957ab638838618623b6d0abc8361d72fc`.
Remote and local archive hashes matched; all 10,054 file/tar/extracted-byte
hashes were verified. Five dump files had valid PGDMP magic. Five provisioned
secret literals were checked and had zero literal matches in the archive; this
is not a claim that no possible secret-like data exists. The 32 cases, 68
nonempty arms, and 69 Character requests are in the local sealed archive, as is
one preserved empty q01 response. No private wire bodies, credentials, database
dumps, or private reasoning are copied into this finding.

The archive's 329 captured responses were all HTTP 200, with no missing response
artifacts. Three early base64 embedding responses had empty dimension
projections because the historical capture handled numeric arrays only; later
capture was repaired and final readiness independently measured 1024 dimensions.
These metadata gaps are not evidence of a transport failure or wrong dimension.
Reported usage (not billing, provider-account totals, or cost estimates) is
353,113 chat tokens (317,449 prompt, 35,664 completion; 158,716 cache-hit and
158,733 cache-miss prompt tokens) and 10,244 embedding prompt/total tokens.

Across 2,759 resource samples, minimum available memory was 7,645,130,752 bytes
and minimum free disk 107,454,246,912 bytes. Identified service peaks were
Hindsight 1,394,483,200 bytes, router 66,891,776 bytes and DB 316,342,272 bytes.
The earlier cold BGE factory peak was 1,816,231,936 bytes, measured separately.
No sampled OOM/restart was observed; sampling is bounded evidence, not a host
performance guarantee. The campaign stayed on the original 2-core/approximately
11.65 GiB host without the planned upgrade. Final allocation was 5.75 GiB/1.5
cores. A separate main-checkout `npm ci --prefix apps/ade-web` reported 26 ADE
web dependency vulnerabilities (7 low, 1 moderate, 15 high, 3 critical). This
was not an audit of the deployed pinned Hindsight image; no dependency updates
were made in this docs-only closeout.

The local independently verified archive is under
`workflows/evals/hindsight_memory_probe/outputs/campaign-closeout/final-a3e78c5-1791733755949290911/`;
the corresponding remote private archive is under the OCI campaign-closeout
directory. Its local verification receipt and archive manifest bind deployed
source SHA `a3e78c5c63b17eadc3d02b05ce7e04eb6042944f`, manifest hash
`a3cc7ef61d2cc1a4d5289c80afb820fb9990cb8d9d89f585b1653ace212d0de0`, and
bundle hash `a640db9c2254487a0773624465f47443fe3270fb11851ebddc2e525cefde96be`.
The campaign closed before the original hard stop without modifying operation
deadlines. The durable source contracts are in [ADR 0063](../adr/0063-hindsight-character-evaluation-boundary.md),
[ADR 0064](../adr/0064-isolated-hindsight-infrastructure.md),
[ADR 0065](../adr/0065-post-restore-snapshot-failure-recovery.md), and
[ADR 0066](../adr/0066-canonical-persisted-schema-snapshots.md). The campaign
does not revive Hindsight Cloud, add a generic Memory interface, restore the
removed privacy policy, or authorize adoption/cutover.

## Preserved failed attempts and source repairs

Earlier failed operations remain separately preserved: attempt 47 failed before
resource creation during job selection; attempt 85 created a restore resource
but did not publish a coherent inventory; E459 failed after import with an
invalid pre-gate empty-command registration. That registration state is
observed, not a proven cause of the original E459 failure. Linux `/proc`
terminal teardown was a possible mechanism, not established as the incident
cause.

A later separately admitted attempt passed exact container creation and
`pg_restore`, then failed during the final snapshot with
`restore_process_identity_changed`; cleanup preserved the failed container and
volume. The retained `restore-identity-list-readback` registration is for the
exact `docker ps -aq --no-trunc` command, has an empty command-line hash, and has
neither child nor wrapper result. The `restore-snapshot-table-unit_entities`
query has a successful child result but no wrapper; the other expected table
query jobs have successful child and wrapper results. The complete inventory
shows 90 identity-list registrations: 59 successful global container-list
reads, 30 successful exact owned-volume-list reads, and the one failed global
list registration. It also shows an ordered prefix of eight canonical table
queries (`banks` through `unit_entities`); the first seven have both successful
receipts, while the final query has a zero-exit child result without a wrapper.
The failed registration was created during that final query's monitoring
interval. The two later table queries were not launched. This separates the
failed identity-list registration from the earlier completed queries, but does
not establish wrapper-level completion of `unit_entities` or successful
restoration.

The 7ec recovery CLI used a new 600-second authority, preserved and independently
byte-checked all 598 original files before exact container/volume retirement, and
did not change earlier operation deadlines. Its table/state/scope comparison was
preservation evidence, not a restore pass: PostgreSQL session temporary
namespaces differed in the schema snapshot. Source21 required exact argv, owner,
UID, PID and start-tick identity before publishing a registered child's job
receipt and rechecked identity before releasing its gate. A bounded
terminal-transition check separately handled Linux `/proc` teardown after a
registered child exits. ADR 0065 added the exact-resource recovery authority;
ADR 0066 canonicalized persistent-schema comparison by excluding only anchored
temporary namespace names from both snapshots. The final source then passed P4
and disposable restore qualification. Earlier attempts remain failures and are
not retroactively called successful.
