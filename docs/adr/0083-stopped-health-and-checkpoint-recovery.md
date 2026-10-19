# ADR 0083: Stopped Health And Checkpoint Recovery

Status: Accepted, 2026-10-19. Guard regression checks are implemented; the new
stopped-store checkpoint controller and actual paired archives remain pending.

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

## Verification Boundary

Require baseline/resource fencing, exact source/target manifests, retained
in-flight identities, both archive hashes/readable TOCs and owned shutdown.
Database-copy startup and dump readability are not Stage-3 paired logical restore
or product recovery qualification. The actual dual-store checkpoint remains a
required gate until these receipts exist; the first ADE archive alone is not it.
