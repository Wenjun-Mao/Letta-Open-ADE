# ADR 0035: Compact Natural Review And Observational Dispatch

- Status: Accepted for offline checkpoints 1–4 on 2026-09-24; no live or release authority
- Supersedes model-facing and accounting portions of ADRs 0029, 0032 and 0034.
  Those records remain historical. ADRs 0031 and 0033 describe earlier capacity
  experiments and do not qualify this envelope.

## Problem

The former reviewer makes the model select persistent IDs, versions, source roles,
and paired proposal/disposition IDs. Its binder pools quoted user and assistant
text, allowing an assistant's question plus a bare user name to produce a new
fact. An empty object also passes as no change. The request ledger blocks normal
work by monetary caps and can make capture failure change a provider result.

## Decision

The reviewer returns one required `decisions` list of at most 20 discriminated
items. Write items contain semantic type/value/scope, a local target or related
identity handle where needed, and one exact current-user quote. Defer and conflict
items are independent no-write outcomes. ADE owns persistent IDs, target versions,
source roles, offsets and hashes. A request-local immutable map exposes eligible
user/assistant messages, nonforgotten targets, and eligible identities under local
handles. Direct, resolve-user and endorse-assistant modes have separate support
and operation-specific authority checks. The bound current anchor is explicit;
antecedents cannot authorize a revision by source ordering. Bind once, then
transactionally revalidate the accepted generation, target version and sources.

Add `user_resolution` as current authority and `user_antecedent` as support-only
source roles. Preserve historical roles and records as written. New sends require
the new policy binding; old-policy conversations remain readable and terminal
replay stays idempotent.

Count outbound provider attempts at one dispatch boundary with local request IDs
and one start plus terminal event. Aggregate retained copies by request ID and
label missing evidence incomplete. Trace and capture are best effort; source,
revision and run-outcome persistence remain required. Keep existing attempt
deadline, per-request ceiling, cancellation, retries and finite loops. Remove
spending caps, reservations, budget settings and scheduling gates.

## Rejected Alternatives

- Prompt-only changes leave invalid wire combinations and source pooling intact.
- An old/new dual parser hides policy drift and widens accepted malformed output.
- A second semantic judge adds a call without proving entailment.
- Durable request reservations recreate a spending gate and cannot certify billing.

## Consequences And Guardrails

Structural binding limits provenance and stale-reference errors; semantic scope
and entailment still need complete-delta fixtures and later live measurement.
No-save, uncertainty and withdrawal restrictions apply to the identified claim
across all write evidence modes; changing from user resolution to assistant
endorsement or a direct value fragment cannot discard them. A fresh current
assertion can replace uncertainty or withdrawal, while an inherited no-save
restriction requires explicit, claim-bound permission in the cited current span.
Unrelated writes remain valid. A grounded conflict cites a held fact or identity,
the current query/context and an exact candidate span without inventing a write.
An answer that plainly states the cited value is not a validated conflict; broader
contradiction remains reviewer judgment. Tests cover the named contrasts,
PostgreSQL readback/migration, faults and dispatch observation. Checkpoint 5
remains separately authorized.
