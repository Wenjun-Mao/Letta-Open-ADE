# ADR 0028: Shared Pre-Request Budget for Native Qualification

- Status: Retired; replaced by observational dispatch counting in
  [ADR 0035](0035-compact-natural-review-and-observational-dispatch.md).

> Pre-request spend reservations, cap enforcement, and cap approval below are
> historical. Runtime timeouts, retry limits, and bounded tool loops remain.
- Date: 2026-09-23

## Problem

The black-box qualification runner submits turns, but the worker can issue
multiple conversation, reviewer, compaction, retrieval, and document-embedding
requests inside each turn. A cap in the runner cannot bound provider spend,
and separate API/worker counters would race or reset on restart.

## Decision

Reuse the M3 SQLite reservation ledger at the common Agent Runtime transport
boundary. When all four budget settings are supplied, the standard API and
worker builders use a ledger under the shared runtime-data directory. Each
generation or embedding request commits a reservation before send; failure,
timeout, cancellation, and an interrupted process all leave that slot spent.
SQLite's immediate write transaction serializes reservations across processes.
The ledger binds immutable limits, stage, source revision/fingerprint, and
runtime mode. Budgeted construction requires a clean exact build identity.
API/worker compatibility includes the budget configuration, and full native
qualification fails preflight without a matching `qualification` budget and
zero requested retries. The canonical acceptance workflow joins governed
source fingerprinting, so its preflight or execution code cannot change after
evidence collection without invalidating release lineage. Release evidence
gates remain separate and unchanged.

## Alternatives and consequences

- Do not count only accepted turns, only the API process, or only successful
  provider responses; those approaches miss internal requests or allow reruns.
- Do not reuse an existing stage ledger with raised limits or a new source;
  create a separately approved stage and retain prior evidence.
- The budget is disabled by default. Static wiring is not authorization for
  the proposed numerical caps or any live call. Direct relocation canaries
  remain outside the canonical runner and must reserve against the approved
  stage ledger before sending. An exhausted cap stops provider sends and
  invalidates the incomplete stage; it does not relax canonical cases.
