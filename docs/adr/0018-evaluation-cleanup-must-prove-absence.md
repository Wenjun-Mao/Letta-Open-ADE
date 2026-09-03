# ADR 0018: Evaluation Cleanup Must Prove Resource Absence

Status: Accepted

## Context

The Agent Runtime parity workflow exercises the real Agent Studio API. That API
correctly owns created definitions, subjects, and conversations as
`agent_studio`, while the original cleanup query selected only `development` and
`evaluation`. The deletes therefore affected zero rows, but successful SQL
execution was incorrectly recorded as completed cleanup.

## Decision

Cleanup scopes declare the exact resource purposes they may delete. The parity
workflow authorizes only `agent_studio` and remains constrained to generated keys
prefixed by its high-entropy run ID in the default workspace. Other workflows
retain the narrower `development` and `evaluation` default.

A cleanup transaction is complete only after a purpose-independent postcondition
query proves that no exact scoped definition, definition version, or memory subject
remains. A purpose mismatch or remaining resource fails and rolls back the
transaction. Row counts alone are diagnostic and never establish completion. The
recovery-manifest schema advances to version 2 for these required fields.

## Consequences

- Product Agent Studio resources outside the exact run-bound scope remain
  ineligible for deletion.
- Parity artifacts cannot claim cleanup success when public API ownership and
  cleanup ownership diverge.
- Cleanup code is part of the production schema-policy fingerprint, so changing
  this evidence contract invalidates prior qualification.
- PostgreSQL integration tests cover both default-purpose and explicitly
  authorized Agent Studio cleanup and remove all fixtures they create.
