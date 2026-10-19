# Hindsight Native Source And Recovery Boundary

Date: 2026-10-19. Authority: approved Stage 1 M0-M6/A1-A6, with GitHub Actions
excluded. This is native Memory-boundary evidence, not ADE product integration,
Character assessment, human acceptance, a measured baseline or release readiness.

## Tested Identity And Scope

Hindsight 0.10.3 image digest `acf5e76bd9a5b65f9f7c540a3414007c7f874b34346587dac7e4feab7ae80cba`,
source `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`; PostgreSQL 17 with
PGroonga 4.0.8 and pgvector 0.8.6. Existing DeepSeek and Spark Qwen embedding
routes were reused without changing those services. Native initialization reported
1,024 embedding dimensions. The public BGE-v2-m3 snapshot and weight hash in
`model_cache.py` were verified; Chinese populated recall showed complete
cross-encoder scoring, not a passthrough ranker.

Ordinary gates ran at `3b5f35b918981647d70582f75c9bbd35447f14bc`, failed-operation
recovery at `9c895f3be73a0d03f9f7a884df2c7cd26c2e97c5`, and successful partial
recovery at `78c705bf308717af73becd852a77a255f80f51ef`. All used fresh isolated
banks with frozen controlled sources, original speakers/times and immutable
definition bindings. No Character model was called and no authored answer was
injected through an ADE conversation.

## Outcomes

| Gate | Observed result |
| --- | --- |
| `q01-relevant` | One source; real acceptance followed by injected lost acknowledgement; same-operation reconciliation, automatic consolidation and immutable replay passed; two candidates reranked. |
| `reference` | Three attributed messages; antecedent-only tea reference resolved; source readbacks/replay and automatic consolidation passed; six candidates reranked. |
| `q02-correction` | Two sources; readback retained the correction and recalled the corrected preference; three candidates reranked. |
| `q02-change` | Two sources; readback distinguished earlier preference from genuine later change; three candidates reranked. |
| `attribution` | Two sources; readback attributed the fictional solo event to the assistant and preserved the user's absence; four candidates reranked. |
| Failed operation | Owned Router stopped; native operation genuinely failed; retry of the same operation completed with unchanged source and no replacement operation identity. |
| Partial operation | Owned Router interrupted after committed progress; five memory IDs survived the genuine failed operation and retry; final readback contained 48 memories and the unchanged complete source. |

These are bounded source/readback inspections, not general semantic qualification.
Ordinary cases retained historical source assertions alongside later observations;
retrieving a source statement does not itself mark it as currently true. Human
semantic/Character review remains pending and must not be inferred from mechanics.

## Failures And Operational Lessons

The first partial-recovery attempt completed without an interruption and is retained
as a failed recovery proof. Its root cause was the harness checking parent
`processing`: native `batch_retain` parents remain `pending` while children process.
The repaired harness checks actual child processing plus committed memories.
After successful retry, native child progress still retained an earlier 1/15
snapshot although status was completed and readback had advanced. Preserve raw
progress as a last-reported snapshot, not an authoritative completion percentage.

Preparation also exposed unordered Docker mounts, a normally completed auto-removing
cron job, and an inspection timeout during image preparation. ADR 0071 records
the inventory fixes. The timeout remained fail-closed; artifact preparation was
finished before supervision and inference were activated. Closed activations were
never reopened, and all failed captures were preserved.

Across retained activations there are 191 final-send observations: 54 chat and
137 embedding requests, including startup and failed/no-interruption attempts.
All recorded inputs have matching raw-byte hashes and received HTTP 200 outcomes.
This counts observed HTTP attempts, not distinct learned facts, provider billing
or proof of provider acceptance for failed calls that never reached Router.
Embedding vectors use base64; the initial observer's list-only dimension summary
does not measure those responses. Native initialization and reported model identity
are separate evidence, not a cryptographic model-weight attestation.

Private HTTP records, raw sources, lease/check/stop receipts, model snapshots and
database dumps remain under the ignored workflow outputs and OCI activation
directories. All OCI native-gate services and their safety units were stopped after
capture. Existing ADE/trial and unrelated host services were not replaced.

## Next Boundary

ADR 0070's concrete per-message source/recovery contract is feasible against the
pinned native implementation. M2-M6 must still prove ADE acceptance/finalization,
durable scheduling, scoped recall and pause/Retry, real browser behavior and the
six actual-product probe slots. Native feasibility is not a substitute for those
gates or for the later Stage 2/3 qualification work.
