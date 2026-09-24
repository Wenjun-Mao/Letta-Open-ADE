# ADR 0030: Pending Conversation Leases Use the Database Clock

- Status: Accepted
- Date: 2026-09-24
- Extends: [ADR 0009](0009-ade-owned-agent-runtime.md)

## Problem

Turn acceptance inserted a pending conversation lease with an expiration from
the API process clock. The worker reclaimed it only when PostgreSQL's transaction
clock reached that timestamp. In an immediate isolated worker replay, the first
claim returned handled while the run stayed pending with no attempt or
`run.started` event. A subsequent pass succeeded after the clock advanced.
This is a clock-domain mismatch at the lease handoff, not a packet-builder issue.

## Decision

The pending lease is a serialization placeholder that must be reclaimable as soon
as the acceptance transaction commits. Its `expires_at` is PostgreSQL `now()`
from the same transaction as the lease's `acquired_at`. The worker still replaces
the placeholder atomically with a live lease using the existing conflict and
expiration condition. Live lease deadlines and heartbeats retain their existing
contract.

## Alternatives and Consequences

Adding a client-side grace period or retry loop would hide the clock mismatch and
make claim latency depend on process timing. Waiting in tests would miss the
production race. The packet test now asserts the pending timestamps are equal and
claims a run immediately after acceptance. The SQL migration shape is unchanged.
