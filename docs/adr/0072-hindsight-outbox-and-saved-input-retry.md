# ADR 0072: Hindsight Outbox And Saved-Input Retry

Status: Accepted for the approved Stage 1 implementation, 2026-10-19.
Persistence, worker, API and browser qualification are in progress.

## Problem

PC-14 replaces the incumbent reply-plus-fact transaction with two persistence
authorities. A native operation may already have committed a prefix when a
request fails, while a required recall failure must not become an apology reply
or another accepted user message. One worker loop cannot own both long retention
and reply execution without making unrelated turns wait.

## Decision

ADE's accepted-message and committed-reply transactions also append an immutable
message delivery (ADR 0070). PostgreSQL binds its original source, relationship,
configuration, exact payload/hash, document and operation identities. Separate
delivery scheduling claims only the first unfinished item per relationship;
short leases and completion updates are fenced with their original token.
No network call runs inside an ADE transaction. The reply worker never waits
for retention and never acquires a delivery lease.

A relationship has separately leased initialization and a frozen native bank
configuration. New-bank initialization may reconcile an interrupted creation;
an established missing bank is an error, never an empty successful replacement.
Native pending parents and processing children remain separately observable.
Acknowledged acceptance, completed retention, automatic consolidation and semantic
correctness are not interchangeable states.

Transport uncertainty reconciles the original native operation. A confirmed
missing operation permits the same bytes/UUID to be sent; failed/cancelled native
work uses the native retry endpoint. A failed native operation requires explicit
delivery Retry; five consecutive transport/inspection failures leave an uncertain
item for explicit reconciliation. Healthy nonterminal operations remain scheduled
polls, not new extractions. Backoff and concurrency are operational controls,
not spending limits or model-request quotas. A blocked relationship does not
block unrelated relationships or healthy recall.
Native progress is a last-reported snapshot and can remain stale after retry;
preserve it separately from the authoritative operation state and source readback.

Required automatic/tool recall failure pauses the saved-input run. It commits no
assistant message, releases the worker lease, and retains the conversation's
pending-input guard. Retry uses an idempotent receipt and the observed attempt
number, performs fresh recall, and creates no new user message. Cancel releases
the guard but preserves the accepted source and its delivery eligibility.
Conversation/version/subject incompatibility rejects Retry. Ordinary creation of
a newer persona version does not alter an older conversation's immutable binding.

All run lifecycle writers lock conversation before run, then subject where
needed. Claim, heartbeat, cancellation, retry and finalization preserve lease
fencing; a stale worker cannot finish a newer attempt. A unique run/role message
binding prevents duplicated accepted users or committed replies.

Use an explicitly configured fresh workspace key (no implicit default) with an explicit
Hindsight authority marker. Never silently convert the incumbent workspace or
resume its conversations. Keep historical native rows/tables and migrations,
but remove their maintained execution, reviewer and reset/removal paths.
Hindsight Stage 1 remains development-only; historical native release evidence
cannot qualify it. No existing service is redeployed by source publication.
The concrete reply replacement and its separate model roles are recorded in
[ADR 0073](0073-hindsight-reply-runtime.md).

## Alternatives And Guardrails

Dual writes, fake empty reviewer results, a generic backend abstraction, holding
SQL locks during HTTP, and resending input on Retry were rejected. Tests must use
real disposable PostgreSQL for atomic intent, hash/ownership invariants, ordered
dispatch, crash reconciliation, duplicate Retry and stale-token rejection.
Explicit metadata constraint names must match the frozen reviewed migrations,
not gain another generated name prefix during a module split.
API/UI faults must preserve visible saved chat while remote inspection fails.
Memory semantics and Character review remain separate from these mechanics
(PC-02/03/04/05/07/08/09/11/12/14).
