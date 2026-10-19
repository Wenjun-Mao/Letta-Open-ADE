# Hindsight Product Flow: Scoped Stage 1 Observations

Status: real six-slot capture, eight representative safety cases and native browser
mechanics observed. M0-M6 is **not complete**; successful paired-backup, final
evidence sealing and maintained-test reconciliation remain pending.
No human Character judgment, general Memory reliability, paired restore,
production deployment or release qualification follows.

Authority: [integration plan](../plans/hindsight-integration.md), PC-02/03/05/08/
09/12/14. The [interface finding](hindsight-interface-mechanics-2026-10-19.md)
remains controlled Interface evidence, not native semantic qualification.

## Source And Capture

Product image/evaluator: `325378bd743e85c404cdd80b4d43c4010f72c69c`.
Governed source fingerprint:
`c3a0d91dd3c003fbd70971d6b69ca1503806856f0dad69e8e8c1cd695d361453`.
OCI activation: `20261019-product6`. Existing approved inference routes and pinned
self-hosted Hindsight were used; provider-reported/configured identities are not
remote weight attestations. No incumbent stores or model defaults were changed.

`stage1-product-02` ran `q01-relevant`, `q02-correction`, `q02-change`, twice each,
with fresh relationships, actual ADE-accepted user seeds and generated committed
assistants. The evaluator waited for original-source retention and automatic
consolidation, then probed a distinct same-version conversation without source
dialogue/summary carryover. This evaluation wait is not a product reply barrier.

All six captures completed with zero mechanical issues. All six observed nonempty
Memory selections in the actual probe input and committed a reply. The original
source documents, ownership, version/time/sequence, native readbacks, complete
Character requests and commit IDs passed the sidecar/reload checks. This satisfies
the bounded successful-cross-conversation demonstration, not broad reliability.
Blank human review templates remain unsubmitted; all six Character reviews are
`UNREVIEWED`, not AI-authored human verdicts or averaged quality scores.

The private export archive hash is
`8055acb79231c551cb749c37dc7054020aabd5636d8bb2929945b540f517f352`.
It matched OCI/Mac bytes; a newly generated local report independently revalidated
all six captures. Raw evidence stays in the workflow's ignored
`outputs/implementation-20261018/verified-export/stage1-product-02/`.

The preceding `stage1-product-01` at
`e4b4ffd449165fee92fff2ca84bb746b6f726be1` remains six failed slots: seed dialogue
committed but processing inspection failed before probing. The source-backed
pagination defect and repair are in [ADR 0080](../adr/0080-native-processing-pagination.md).
Both six-slot runs must remain visible; the repaired run does not overwrite or
erase the first denominator. Correction/change outputs still need contextual
Memory/Character review; no semantic consensus is inferred from mechanical success.

## Four Actual Safety Cases

Controller: `0e64b75e10ce43c18ad45a83d7356328d1f87d12`, mounted read-only in the
recorded product runner image. Product and controller revisions remain distinct.
`proxy-safety-01` preserved each planned case and actual public/Router readbacks.

| Case | Observed mechanism |
| --- | --- |
| Failed generation | Injected pre-send failure produced no assistant; the one accepted user source was retained. |
| Cancellation | A held request was cancelled without reaching Router or committing an assistant; accepted user retention remained eligible. |
| Delayed retention | The reply committed while its user retain was still held. Another fresh relationship committed and retained both sources before release. |
| Lost acknowledgement | Native returned 200 before the injected lost acknowledgement. Both saved sources became retained; the affected immutable operation had one submission attempt. |

All four mechanical cases passed. They do not establish semantic Memory quality,
Character acceptance, billing totals, quiescence or the remaining M6 requirements.
Traffic snapshots are time-bounded observations; native work can continue.

## Owned Host Recovery

`host-safety-01` passed both recall-outage and same-store runtime restart at the
same product image, using controller `d513fd5aa5b9c51ff0e5fe91720fea5721ff75ae`.
The outage paused without Character dispatch or a fabricated empty Memory result;
explicit Retry reused the saved run/user input with an idempotent replay receipt.
The restart stopped/restarted the exact API/worker/native containers and mounted
stores after native acceptance. Reconciliation retained the immutable operation
with one submission attempt; it did not replay history.

`stale-worker-01`, controller `0adfb4acf02f681c5ca414e014284eccdc8d12ac`, remains a
failed controller case. Its actual finalizer waited behind the owned subject lock,
the database clock proved lease expiry, both attempts produced real candidates,
and one reply committed on attempt two. The validator incorrectly expected an
`abandoned` status; the owning repository uses `failed` with
`worker_lease_expired`. The corrected controller additionally reads that reason
from SQL. A new predeclared case remains required; do not relabel this failed one.

The fresh `final-safety-01` stale-worker case passed at controller
`f43e0cb5a996194651630eb2b7330a34dd1b3927`. Its independent SQL receipt confirmed
attempt one `failed`/`worker_lease_expired`, attempt two succeeded and exactly one
committed assistant. Native source readbacks also retained only the one user and
one committed assistant. Both actual candidates remain in private capture.

That run's isolation case remains failed: subject/character forged IDs and role
denials passed, but the temporary API readiness check used native's `/health`
instead of ADE's `/api/v2/health`. The source and repeated HTTP 404s identify a
controller error; the API started and cleanup stopped it with exit 0 and no OOM.
The corrected readiness test is source-backed; fresh controller attempts receive
new API names/workspaces without deleting or reopening the earlier resources.
Actual workspace-boundary qualification still requires the corrected case.

The corrected `isolation-safety-02` case passed at controller
`bba39ee28daed89a70f382a754a2bb3ba5f8b1aa`: separate subject/character scopes,
forged known document/operation/retry IDs, reader/unauthenticated roles, and a
same-image API bound to another workspace, including reverse access denial.
Its extra API was stopped. All eight representative safety cases now have scoped
passing receipts; earlier failed attempts remain separate.

## Native Browser And Checkpoint

The actual native browser journey found an operator/admin deployment mismatch;
[ADR 0082](../adr/0082-candidate-web-authoring-role.md) records the corrected private
web binding. Only that service was recreated at its original image, with
configuration controller `40a28038085d080683002a6c28d59a0436fb2610`; API/worker,
both stores, model identities and sealed environment stayed unchanged.

The Chinese browser conversation completed two replies. A timed native outage
paused the second input; reload preserved it without a fabricated assistant.
After same-container restoration, separate reply and delivery Retry succeeded.
Independent public readback verified exactly two users/two assistants and four
matching retained original documents, with run attempt counts one/two. A fresh
same-relationship chat had no copied dialogue but shared the four deliveries;
another character had empty Memory/delivery state. Original-source inspection and
390-pixel viewport/document width were observed. The dedicated browser and SSH
tunnel were closed. These are Interface/mechanical observations, not human
Character acceptance or general Memory reliability.

The new paired checkpoint reached writer-free stores and created a readable ADE
archive, but failed its native dump when supervision closed on cached health of
the exited fault proxy. The partial native file is zero bytes; all candidate
containers stopped and all six baseline identities/health stayed unchanged.
[ADR 0083](../adr/0083-stopped-health-and-checkpoint-recovery.md) records the root
guard correction and required recovery through new owned copies. Product6 stays
closed; successful paired archives and the final evidence seal are still pending.

The first paired-checkpoint attempt at the previous activation preserved readbacks
and stopped owned resources, but failed before dumps because of a wrong Alembic
table assumption. Its failure is retained; six baseline identities/health were
unchanged. [ADR 0081](../adr/0081-owned-safety-observation-controllers.md) records
the configuration-derived correction. Actual dual archives remain pending.
