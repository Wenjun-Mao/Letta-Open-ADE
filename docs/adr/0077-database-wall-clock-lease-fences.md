# ADR 0077: Database Wall-Clock Lease Fences

Status: Accepted, 2026-10-19. Root-cause repair within M3/M6; not live recovery proof.

## Problem And Evidence

PostgreSQL `now()` is fixed at transaction start. Three application-role SQL
regressions proved that a conversation owner, delivery heartbeat and bank
initializer could still act after their lease expired inside an open transaction.
A fourth reproduced an assistant reply committed after finalization waited on a
subject lock past expiry, even with a fresh initial ownership check.

The defect belongs to SQL ownership/finalization, not provider timeouts, workflow
fault rules or retry budgets. Earlier controlled stale-token tests did not cover
transaction-age and post-check lock waits. The first full-stack image candidate
was closed without product startup/inference after this diagnosis; its build
receipts remain retained rather than relabeled as proof of the repaired source.

## Decision

Expiry predicates and new lease deadlines use PostgreSQL `clock_timestamp()`.
Conversation acquisition/heartbeat accept a duration, not an application-computed
absolute expiry, removing client clock skew and pre-lock deadline calculation.
The pending reservation, abandoned-run selector, native-delivery claim/heartbeat
and bank initialization use the same database wall-clock boundary. Ordinary audit
timestamps may retain transaction time; they are not ownership authority.

Finalization still locks conversation then run and validates ownership before
product work. Before committing success/failure/cancellation/pause, it locks the
claimed lease row and conditionally releases using a fresh wall-clock predicate
after any lock wait. Failure rolls back the complete product transaction, including
assistant message, outbox intent, summary and events. This is a fencing check,
not a renewal or permission to resurrect an expired owner. Recovery remains an
explicit atomic takeover under the existing token and attempt contracts.

## Rejected Alternatives And Guardrails

Larger leases, application-time comparisons and evaluator sleeps would conceal
the defect. A timestamp constant computed at transaction entry has the same
problem. No migration, Memory semantic rule, provider default or weaker fallback
is introduced. Tests retain transaction-expiry and blocked-finalization cases
alongside takeover, cancellation and unrelated-progress checks. Actual owned-stack
restart/takeover/cancellation still require M6 receipts; passing SQL mechanics
alone does not close that gate or establish Memory/Character quality.
