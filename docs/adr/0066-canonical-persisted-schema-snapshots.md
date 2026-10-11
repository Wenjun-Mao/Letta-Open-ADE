# ADR 0066: Canonical Persisted Schema Snapshots

Status: Accepted for the isolated Hindsight P4 snapshot workflow,
2026-10-11. This records a source contract; it does not qualify an OCI restore.

## Problem

P4 compares exact candidate and restored PostgreSQL snapshots. Both capture
paths included every `pg_namespace` row, so backend-local `pg_temp_N` and
`pg_toast_temp_N` schemas appeared in the original capture but not after
restore. Their changing names describe transient session state, not lost
application data. Filtering schema differences in the comparator would hide
real durable drift.

## Decision

Define one shared canonical schema query and use it for finalization,
disposable restore capture, and the restore read-only query allowlist. Exclude
only names matching `^pg_(temp|toast_temp)_[0-9]+$`. Retain schema names and
owners, extension names and versions, Alembic rows, and all ten canonical data
tables in strict hash-backed comparison. Owner, extension, migration, or data
drift remains a mismatch.

The capture layer owns this distinction because it defines logical persisted
state. Downstream tolerance would weaken exact comparison and could accept
arbitrary schema drift. (PC-08/09/13; see ADR 0064 for the isolated P4 contract.)

## Guardrails

Offline tests bind both capture callers and the command allowlist to the shared
query, assert the narrow temporary-name predicate and retained durable fields,
and prove owner, extension-version, and Alembic changes still mismatch. No
live database call is part of these tests.
