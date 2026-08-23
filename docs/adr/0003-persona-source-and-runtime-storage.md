# ADR 0003: JSONL Persona Source And Runtime SQLite

## Status

Accepted and implemented.

## Context

Tracking a mutable SQLite database beside a JSONL seed creates two authorities.
Edits made through the UI can dirty Git, while later seed changes do not reach an
already populated database.

## Decision

- `agent_platform_api/seed_data/personas.jsonl` is the reviewed, versioned persona
  source.
- SQLite is a runtime search/CRUD projection under ignored `data/runtime/`.
- The registry records the reviewed seed's SHA-256 digest and managed key set. When
  the seed changes, startup upserts current seed records and removes only keys that
  belonged to the previous seed but no longer exist in the new version.
- Runtime-only persona keys are preserved during seed synchronization. A runtime
  edit to a seed-managed key is preserved while the seed digest is unchanged, but
  a later reviewed seed version replaces that managed record.
- Promoting runtime edits into reviewed source data remains an explicit export and
  review action. Moving legacy runtime files is also explicit and conflict-safe.

## Consequences

Changes intended for review are made to JSONL. Runtime UI changes need an explicit
export/promote path before becoming source data. Developers must not use a
seed-managed key for an independent runtime persona because a future seed update is
authoritative for that key.

`scripts/migrate_runtime_data.py` moves known legacy files only when the destination
is absent or byte-identical; conflicts stop without overwriting either copy. Tests
cover seed updates, removed seed records, preservation of runtime-only records, and
migration conflicts.
