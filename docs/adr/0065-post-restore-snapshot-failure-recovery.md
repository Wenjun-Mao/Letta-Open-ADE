# ADR 0065: Bounded P4 Post-Restore Snapshot Failure Recovery

Status: Accepted for the revision-4 P4 recovery source repair, 2026-10-11.
The path preserves and retires one failed attempt; it does not qualify a restore.

## Problem

The revision-4 disposable restore completed `pg_restore`, then failed while
capturing the final snapshot. Its `restore_process_identity_changed` reason
identified the registered host-readback process as the failure point. The
retained registration showed an empty `/proc/<pid>/cmdline`; that alone did not
establish whether the registered `Popen` child had exited or changed identity.
The source runner treated any exact-command mismatch as fatal before collecting
the child's terminal status. Separately, cleanup correctly retained the failed
container and volume, but offered no bounded way to preserve the snapshot state
and release those exact disposable resources. (PC-08/09/13)

## Decision

Bind a registered child to its exact expected argv, owner marker, UID, PID and
start ticks before publishing its job receipt; repeat that identity check after
publication and before opening the child gate. During command monitoring, accept
an empty command line only as a brief teardown transition for the same-birth,
same-UID registered `Popen`, and only when bounded `wait`/`poll` confirms its
exit. Linux may expose both `cmdline` and `environ` as readable empty files
during `exit_mm`; nonempty environment without the owner marker, changed
identity/command, and a still-live child after the bounded wait remain fatal.

For the exact failed snapshot receipt and cleanup outcome, issue a separate
immutable authority (maximum ten minutes, capped by `WORK_CUTOFF`) bound to the
sealed operation, failure and cleanup hashes, exact create-result container and
volume, recovery source SHA, and a fixed scope. It does not alter the original
operation or cleanup deadlines. The recovery rechecks the original successful
create/restore receipts and the exact observed ordered eight-table query prefix
with its final child-result/no-wrapper semantics, stopped main epoch,
baseline, source seals, controller/process absence, and the exact exited restore
container and volume. It starts only that container, registers an independent
finite host-local expiry stopper before start, performs two read-only database
captures, requires matching table hashes, records the frozen P4 comparison and
scope readback, and stops the same container with exact `StartedAt` readback.

Before any resource removal, archive original receipts byte-for-byte, including
missing-result semantics, recovery captures, comparison, authority and intents;
hash and seal the archive. Bound original readbacks by the immutable failure and
cleanup timestamps, accept every fully proven allowed readback without relying
on scheduler-poll counts, and bind later recovery readbacks to their authority.
The closure manifest records every post-archive scoped readback and removal
registration plus child and wrapper receipts before any active receipt is
retired. Then remove only the exact container and its exact
unconsumed volume, verify absence and the unchanged main/baseline state, seal a
closure receipt, and retire active source controls. A fresh finite authority
can continue a sealed partial retirement after interruption. Any unsealed,
changed, symlinked, incomplete or unarchived source blocks retirement and the
next attempt. The result remains `failed_post_restore_retired`; no original
snapshot/compare/success receipt is synthesized, and the capture is not
reported as a successful restore. (PC-08/09/13)

## Alternatives And Consequences

- Treating every cmdline mismatch as identity change was rejected because
  `/proc` teardown can precede `Popen` wait-status publication.
- Accepting an empty argv or environment as success was rejected; only the
  registered child's bounded terminal transition is accepted.
- Retrying the old restore, rewriting its deadlines/results, or deleting its
  resources without a sealed capture was rejected because it would blur the
  failed attempt and its evidence.
- The independent expiry child adds one registered process and immutable
  receipts, but keeps the exact database stop bounded if the recovery controller
  is interrupted after restart.

The operator contract and commands are in the
[P4 restart and recovery runbook](../../workflows/evals/hindsight_memory_probe/p4-runbook.md).
Offline synthetic tests cover terminal process identity, the 194-job historical
inventory and exact query prefix, exact authority, archive seals, successful
capture/retirement orchestration, retry after a stopped partial capture, and
continuation after interruption between container and volume removal. OCI execution,
restore qualification, semantic acceptance, deployment and native adoption
remain outside this decision.
