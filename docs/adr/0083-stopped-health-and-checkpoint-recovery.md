# ADR 0083: Stopped Health And Checkpoint Recovery

Status: Accepted, 2026-10-19. Guard and stopped-store controller regression checks
are implemented; both actual paired archives and unchanged-parent closeout are
verified. Logical restore/product recovery qualification remains outside Stage 1.

## Root Cause

The product6 checkpoint stopped product writers and produced a readable ADE
archive. Its supervisor then saw the exited fault proxy's cached `unhealthy`
Docker health value, closed the lease and stopped both databases before native
`pg_dump` could begin. The native dump is zero bytes. Closed/stopping receipts,
the writer-free snapshot and database shutdown timestamps identify a guard-state
model error, not a native SQL/schema or semantic failure. All six baseline
services stayed unchanged. Preserve the failed checkpoint and partial archives.

## Decision

Health status only describes a live (`running`, `restarting`, `paused`) container.
An exited container's cached health is not current liveness. Continue rejecting
any recorded OOM, active unhealthy container, changed source/baseline, expired
lease or resource-reserve breach. This is the general Docker observation contract,
not a backup-specific health bypass. Record dump diagnostics privately instead
of discarding stderr when a finite dump fails.

A closed activation stays closed. Recover its coordinated writer-free point
only through a newly admitted finite owner: verify both parent stores are stopped,
copy only their registered volumes read-only into new owned volumes, verify the
copies before startup, then use exact-image database-only helpers to make both
logical archives. Do not restart the parent, mutate retained original volumes,
replay history, run providers or point a product runtime at the copies.

The `stopped_checkpoint` host controller binds the parent's closed lease,
writer-free/closeout records, exact database images and labelled local volumes.
Only its newly owned read-only copy helpers may access those stopped originals;
foreign active dependents, changed parent identities and unsafe filesystem links
fail admission. Each copy records matching content, owner, mode and modification
time manifests before any database starts. Helpers use no network, no ports or
credentials, finite resource limits and the existing supervisor/expiry fences.
Only new copies start, serially, at the parent database image. Retain partial
archives and close the new owner on every failure; never reopen the parent.

## Verification Boundary

Require baseline/resource fencing, exact source/target manifests, retained
in-flight identities, both archive hashes/readable TOCs and owned shutdown.
Database-copy startup and dump readability are not Stage-3 paired logical restore
or product recovery qualification. The actual dual-store checkpoint remains a
required gate until these receipts exist; the first ADE archive alone is not it.

`20261019-checkpoint7` at controller `13a37a241ed02d07525f6988b4291d9264227b2d`
captured both archives through new networkless copies of closed product6.
The 1,441-entry ADE and 1,585-entry Hindsight source/target manifests match;
both TOCs and archive hashes verify independently after export. The parent stayed
closed/stopped, all four copy helpers exited and six baseline services stayed
unchanged. Preserve the failed earlier dump and export-quoting receipt as well.
