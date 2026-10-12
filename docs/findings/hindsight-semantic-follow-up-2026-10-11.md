# Revision-5 Hindsight Semantic Follow-Up

Updated 2026-10-11. The authorized isolated follow-up is closed, with a verified
source/request repair and mixed semantic outcomes. This is not native adoption,
release qualification, or a winner in the original M2 comparison. Scope follows
[PC-13](../product-contract.md#hindsight-hosting) and PC-02/03/04/07/09/10/11/12;
the [revision-5 plan](../plans/hindsight-self-hosted-experiment.md#revision-5-closed-semantic-diagnosis-and-repair)
preserves the approval and clock. The revision-4
[campaign finding](hindsight-oci-campaign-2026-10-11.md) remains historical.

## Tested Sources And Verified Repair

Baseline runtime source was `46599c64e7c219cca7c9ed048908108cc94d40e3`;
the final rebuilt and deployed candidate source was
`d2a27c338d71d90ef2fa8ad7a7085682a7aa4e06`. Later diagnostic-note and closeout
commits are documentation only, not newly deployed runtime identities.
Hindsight remained pinned to 0.10.3 on the existing OCI ARM host. No native
ADE/trial service, persistence, model default, provider account, original corpus,
questions, persona, or candidate04/05 evidence changed.

The demonstrated projection-contract gap was addressed in the evaluation
feature, not by re-ingesting facts or filtering question-specific text. Character
receives `shared_profile_facts` separately from `same_character_history`.
Foreign or ambiguous profile facts retain their text and occurred dates but
lose structured source attribution. Non-profile memories without exactly one valid active
character owner are omitted from Character context; raw recall diagnostics are
preserved. Profile knowledge can answer questions about the subject without
claiming this character heard it or participated in the source conversation.
Instructions distinguish faithful recollection from present interpretation and
compatible new solo history. PC-11 still permits naturally introduced solo past
stories without a fixed fiction label; invented prior telling or shared
participation remains disallowed. [ADR 0063](../adr/0063-hindsight-character-evaluation-boundary.md)
records the contract and regression guards.

The controls were versioned and bound into manifests before observations.
Actual built-runner inputs and serialized post-adapter requests were verified,
including the two context groups for all 39 repaired arms. The same-bank
source manifests differed only in source SHA. Ordered raw-recall projections were identical
across the repair for q01 (14 memories), q06 (4), and q07 (35); retained-bank
inventory was unchanged. This excludes changed raw recall as the explanation
for that pair, but does not establish model attention or uniquely attribute
response changes to the repair. Fresh recall composition varied.

## Bounded Observations

| Runtime and stage | Character arms | Output ceiling |
| --- | ---: | ---: |
| Baseline initial comparisons, two subjects | 21 | 2048 |
| Baseline same-bank capacity ablation | 9 | 4096 |
| Baseline post-consolidation focused cases | 9 | 2048 |
| Repaired same-bank focused cases | 9 | 2048 |
| Repaired fresh initial focused cases | 9 | 2048 |
| Repaired fresh post-consolidation focused cases | 9 | 2048 |
| Repaired remaining original cases q02/q03/q04/q05/q08 | 12 | 2048 |

These are 39 baseline and 39 repaired responses, not 78 independent cases or a
statistical pass rate. Focused stages compare Hindsight, empty, and adequate
arms for q01/q06/q07. Fresh initial and post-consolidation used the same new
workspace `hs_semantic_r5_d2a27c3` and retained banks, with consolidation between
them; post-consolidation did not reinitialize or re-retain the banks. Remaining
original cases ran once, not as focused-case rerolls.

All 78 Character responses were nonempty and ended with `stop`. For all nine
baseline capacity pairs, actual serialized post-adapter request bodies matched
except `max_tokens` changing from 2048 to 4096. The historical empty q01 output
was not reproduced; its cause remains unestablished. This does not qualify
provider capacity generally or justify changing native defaults.

Grounding, conversational judgment, and character fidelity are assessed
separately under PC-12, not averaged into an acceptance score:

| Case | Grounding | Judgment and character fidelity |
| --- | --- | --- |
| q01 | Repaired samples give hot, unsweetened oolong and withhold the source chat/own hearing. Fresh post still calls a profile timestamp the earliest record in response to an origin question. Same-bank answer inconsistently treats a misspeak correction as a preference change, despite explicit raw correction in its request. | Natural and helpful, but the remaining record-time inference does not establish origin or participation. Useful profile dates should not be erased generally. |
| q06 | Lemon water and the mailbox name are correct. Same-bank answer still invents a past shared naming utterance absent from its supplied facts; neither fresh answer repeats it. | Uncertainty about the absent bag story is appropriate; suggestions that the user misremembered are unsupported speculation. Offering a new solo story now is PC-11-compatible, not itself an invented prior shared event. |
| q07 | Repaired same-bank and fresh samples use the bicycle profile, preserve the hypothetical scarf trip, and withhold the other root's bicycle name. Same-bank and fresh initial answers nevertheless turn uncertain red-kite evidence into categorical denial; fresh post is more careful. | Warm and playful; speculation about another chat and memory promises remain judgment limitations. A present naming offer is allowed, not established recollection. |
| q02 | Current order is correct, but Hindsight presents the corrected jasmine misspeak as a real earlier preference; adequate distinguishes correction from later temperature/sugar changes. | Remaining chronology/meaning failure, not evidence for removing profile dates or adding case-specific rules. |
| q03/q05 | Shared rainy-alley history and the imaginary bookstore/name/tagline are correctly recalled; the store stays imaginary. | Bounded positive evidence, not general continuity qualification. The q05 empty arm also speculates that records disappeared without evidence. |
| q04 | Blue cotton thread and the solo repair are supported; Hindsight invents a beige bag color absent from source and supplied context. Adequate leaves color unknown. | The unsupported color is a recollection failure. Remaining blue thread is explicitly source-supported and must not be mislabeled as invented. |
| q08 | Hindsight returns the active source's red notebook cover. | No new curation/invalidation/retry stage was run; historical lifecycle proof is not renewed. |

A distinct Memory-side defect is the consolidated jasmine-as-original-preference
summary in **q07's** supplied context. It is **not in q01's** captured request.
q01 receives explicit raw misspeak correction; its answer inconsistency and
record-time inference are separate observations. The earlier manager
capture-location error is preserved and corrected by an append-only receipt,
not rewritten as causal evidence. These captures do not reveal which memory the
model attended to. Detailed source, control, request, reply, comparison, and
correction pointers are in the reviewed
[diagnostic note](../../workflows/evals/hindsight_memory_probe/semantic-diagnostic-notes.md#revision-5-exact-source-retest-and-regression-outcome-2026-10-11).

## Operations, Usage And Closure

Activation was `2026-10-11T20:12:43Z`; the five-hour target, new-work cutoff,
and six-hour hard stop remained unchanged. New supervision was bound to the
activation-specific registry and receipt namespace, not adopted from revision 4.
[ADR 0067](../adr/0067-hindsight-revision-five-activation-clock.md) records this
contract. Actual OCI disconnect/expiry, controller-loss/resume, single-controller
lease, and typed BuildKit cancellation proofs were renewed before replay.
Clean source export, serial builds, auth and Chinese full-reranking/BGE readiness
were verified. A runner verification timeout before HTTP was diagnosed as CPU
allocation and corrected before semantic work; it is not a semantic outcome.
No new browser/UI acceptance was performed.

The activation-scoped router recorded 278 upstream requests, all with terminal
HTTP 200 responses: startup 4, retain 71, consolidation 95, recall 30, Character
78. Transport success is not semantic acceptance. Character-result receipts
report 161,442 prompt and 35,357 completion tokens; these figures exclude retain,
consolidation and embeddings and are not total campaign usage, billing or spend.
The sealed phase-usage receipt separately retains API-reported fields and their
reporting coverage; missing fields are not zero. The host stayed at two cores
and approximately 11.65 GiB; the planned upgrade was not required or verified.
Final allocation was 5.75 GiB/1.5 CPU. No sampled OOM/restart was observed.

Ordered finalization drained candidate work, captured the canonical ten-table
snapshot and a 910,695-byte candidate dump with a readable table of contents,
then stopped all three candidate containers with exit 0 at
`2026-10-11T23:36:14Z`. Dump SHA-256:
`4501bfd36c12361cc2419d2a29f331315b8c32991e8fecf3da14598484f56577`.
All 55 registered job processes and the controller are gone. Six baseline OCI
container identities/state remained unchanged. Candidate DB/cache volumes and
the retained secrets file remain; only owned temporary sessions/keepawake were
retired. The idle source worker was reviewed, archived and unregistered from
Relay without changing unrelated routes.

**`p4_complete=false`: no fresh public restart readback or disposable restore
was run.** A readable dump is not restore proof. Revision 4's exact-source
logical PostgreSQL restore remains historical only; its archive hashes were
reverified unchanged. No restored Hindsight API, crash recovery, native
continuity, Studio archive UI, or new lifecycle qualification is claimed.

The private archive was sealed at `2026-10-11T23:42:18Z`, before the target and
cutoffs. It contains 3,724 indexed files in a 23,265,280-byte tar:

- Archive SHA-256: `23840a1a178c2a2708f903da66bb8c6e763f756602d39dadcf5f5f226369b86e`.
- Index SHA-256: `779068160a32e6f0de915c1a5bf35be4da53bd9cffd29f0203186c141610e5a0`.
- Registry SHA-256: `81f3781de69576ddf42e246012a6324d8e4274e8c6f69e65312dd84be78ba0ea`.

Remote/local archive and index hashes matched; every indexed tar member and
extracted file was independently byte/hash verified. Local private evidence is
under `workflows/evals/hindsight_memory_probe/outputs/revision5/closeout/final-d2a27c3-1791761774/`;
`archive-seal.json` and `manager-local-archive-verification.json` bind the source,
hashes and qualification limits. The extracted supervisor receipts include
`manager-final-state-verification.json`, `manager-router-usage-by-phase.json`,
`epoch-0005.finalized.json`, and the source-bound request/comparison proofs.
No raw wire bodies, credentials, dumps, vectors or private reasoning are copied
into this tracked report or committed from the ignored evidence directories.

Independent verification on the final runtime code passed the README-prescribed
suite: **540 passed, 1 skipped**, with one existing Starlette deprecation warning.
Focused feature/CLI checks passed (75 tests); Ruff, compileall, dummy static
configuration validation and diff checks passed. The documentation closeout
also reran the prescribed suite (540 passed, 1 skipped), Ruff and dummy validation;
all 172 local link targets across the eight edited documents and diff checks passed.
This is not whole-repository pytest or renewed web/npm,
OpenAPI, dependency-audit, or deployed UI qualification; existing unrelated
frozen-input/default-discovery problems and dependency findings were not repaired.

The decision is to **close this bounded run**, not reroll unchanged failures to
fill the clock. The reusable gain is a verified ownership/request contract and
controls that separate supplied evidence from output defects. General correction
accuracy, faithful recalled detail, uncertainty calibration, Memory consolidation
accuracy, and PC-11 story-admission/continuity remain unresolved. Later native
integration or another experiment needs a separate planning/authority decision;
this report adds no second reviewer, keyword policy, generic Memory framework,
Cloud revival, native deployment, or adoption claim.
