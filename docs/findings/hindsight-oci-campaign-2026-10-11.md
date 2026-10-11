# Revision-4 Self-Hosted Hindsight OCI Campaign (Interim)

Updated 2026-10-11. Interim evidence for the isolated campaign authorized under
[PC-13](../product-contract.md#hindsight-hosting), with PC-02/03/04/07/09/10/11/12
governing scope and response interpretation. The campaign remains active while a
restore-admission failure is diagnosed. This is not adoption, release qualification,
or the original measured M2 comparison.

## Runtime and infrastructure evidence

The OCI candidate used immutable source
`537e93c993406c41050424ddee161a875f421077`; this documentation/test iteration is
not a deployed or newly qualified runtime SHA. The candidate used pinned ARM64
Hindsight 0.10.3, PostgreSQL 17, pgvector 0.8.6, PGroonga 4.0.8, and CPU BGE.
Pinned-image/provider checks and Chinese term/vector smoke passed. Captured wire
settings showed Memory thinking disabled with JSON-object schema-in-prompt;
Character remained high/high with a 2048-token cap. Qwen used 1024 dimensions
and one query-prefix newline.

Missing/wrong API credentials returned 401 and the correct key returned 200;
MCP was 404. Control-plane missing/wrong access was rejected; login and session
cookie succeeded. Authenticated public-API readback after restart matched the
frozen selection without re-ingestion: four banks, 24 sources, 45 valid facts,
two invalidated facts, and six scopes, including source/fact/entity/context/
curation/scope projections. This is bounded same-volume persistence evidence,
not crash-recovery or Studio archive UI proof.

Ordered P4 finalization was independently qualified. It drained 62 completed
operations with no pending, processing, or deferred work; produced a 514,967-byte
candidate-only dump, SHA-256
`c22688bacbf7b6a0afda7f0787ac75e5f09c8c464614675d31d127626d49d715`; and
captured the canonical ten-table snapshot. The snapshot included seven banks,
27 documents/chunks, 89 units, two invalidated facts, zero observation-history
rows, 80 entities, 173 unit/entity links, 174 entity co-occurrences, and 280
memory links. Zero-row tables were zero-byte JSONL. Other partial/readiness banks
remain in the database; this is not a four-bank-only database claim. All three
main candidate containers stopped with exit 0, no OOM/restart. Six baseline OCI
identities, start times, images, and health were unchanged; the main guard and
jobs are gone.

## Semantic observations

Candidate04 q01 returned superseded jasmine/hot/half-sugar. Readback showed the
corrected fact existed but lacked the optional profile label required by the
other character's strict scope. Candidate05 changed only the fresh-bank Memory
mission/label description and returned oolong/cold/no-sugar, but gave October 1
instead of the September 30 source date. One repaired-context q01 response was
empty at the exact 2048-token cap and remains incomplete.

q02/q03 met their core distinctions. q04 correctly recalled blue cotton,
thread-root, and user absence, but added unsupported prior-sewing detail; “workbench
bag short stems” is present in source s05 and is not itself hallucination. q06
returned September 30 after consolidation but included an invented old
windowsill-letter statement; the initial answer also had an unsupported
iced-lemon detail. q07 initially recalled an unsupported nickname suggestion;
after consolidation it missed the available bike fact. The post-consolidation
result also includes source-projection repair, so it cannot isolate consolidation
as the cause. q08's invalidation/same-source retry included an unsupported
“maybe never mentioned” hedge (absence-to-negative overreach, not categorical
denial) and an unsupported “never forget” promise. A distinct s12 source correctly
recognized the historical October 1 red quote and asked for the current value
without reactivating the removed fact.

Removal checks covered unrelated ingestion, a retry with the same original UUID
and body, then a distinct new source. The same-source retry made no new retain
provider call and did not reactivate the old fact; new s12 facts had distinct
IDs. This supports only the tested explicit invalidation/retry contract, not
general natural-language removal or reliable historical recall. Archive fixture
eligibility is not archive UI/runtime evidence. No winner over native ADE is
established.

## Restore failure and open evidence

The separately admitted disposable PostgreSQL restore failed before creating a
container or volume. `restore.py:_verify_host` selected a tokenless
`job-*.result.json` as a job registration because it used a broad `job-*.json`
glob; the canonical registered-job selector is `supervisor.jobs`. No restore
success is claimed. Main services remain stopped. Provider response count at
the pre-restore boundary was 314; the final aggregate of provider usage and
resource observations is pending a successful diagnosed retry and its receipts.

The private receipt namespace is under
`workflows/evals/hindsight_memory_probe/outputs/candidate05/`; the qualified
ordered-finalization receipt is
`p4-ordered-finalization-independent-qualified-537e93c.json`. The private dump,
wire bodies, credentials, and private reasoning are not copied into this finding.
The durable source contracts are in [ADR 0063](../adr/0063-hindsight-character-evaluation-boundary.md)
and [ADR 0064](../adr/0064-isolated-hindsight-infrastructure.md). This campaign
does not revive Hindsight Cloud, add a generic Memory interface, restore the
removed privacy policy, or authorize adoption/cutover.

## Subsequent restore attempt and source-only repair

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

The source repair requires exact argv, owner, UID, PID and start-tick identity
before a registered child's job receipt is published and rechecks identity
before releasing its gate. A bounded terminal-transition check separately
handles Linux `/proc` teardown after a registered child exits. The repair also
adds a short-lived exact-resource recovery authority that captures and seals
the failed database state before retiring the disposable container and volume.
It does not modify this attempt's private evidence or old deadlines. The repair
has only offline synthetic verification here: it has not
been deployed to OCI, and its recovery path has not been executed against this
candidate. Restore acceptance, final provider usage/resource totals, and the
exact-source live retry remain open. See [ADR 0065](../adr/0065-post-restore-snapshot-failure-recovery.md)
and the [P4 recovery runbook](../../workflows/evals/hindsight_memory_probe/p4-runbook.md).
