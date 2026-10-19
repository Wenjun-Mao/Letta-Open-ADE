# ADR 0070: Immutable Hindsight Message Delivery

Status: Selected for Stage 1 implementation, 2026-10-18. Native feasibility and
product integration verification remain pending. User authority is M0-M6/A1-A6
in the [implementation plan](../plans/hindsight-integration.md).

## Problem

The incumbent commits native fact-review changes with a reply. PC-14 instead
separates ADE product records from asynchronous Hindsight processing. A lost
HTTP acknowledgement must not duplicate extraction, and a failed operation must
not be called completed merely because its identifier already exists. Repeated
whole-conversation replacement would also reprocess earlier sources unnecessarily.

## Decision

An accepted user message or committed assistant reply creates one immutable
delivery in the same ADE transaction as its source. A candidate reply is never
a source. Persist the exact payload bytes/hash, operation UUID, original source
ID/time/speaker, relationship, conversation and sequence before dispatch.
Preserve the source conversation's immutable definition-version ID as metadata;
an ordinary persona update does not create another bank or rebind prior sources.
Never rebuild an outstanding payload from a newer conversation or configuration.

Use one Hindsight bank for `(workspace, subject, character root)`. The bank key
is deterministically derived from all three identities and persisted/authorized
by ADE. Persona version and chat ID do not split that relationship. All learned
facts and observations stay inside it; no shared-profile labels or pool.

Use a separate document per message, with native `update_mode=replace` and one
item per async operation. The operation UUID is stable for that relationship and
source ID. Preserve the original message in the current source body; place whole,
ordered earlier messages in a separately marked antecedent context. The initial
antecedent budget is 8,000 serialized characters, selecting recent whole messages
from the same conversation. This retention context budget does not define the
Character's recent-dialogue policy. Source text itself is never truncated.

ADE's persisted payload hash and unique source binding prevent same-ID/different-
payload submission. On lost acknowledgement, poll the original operation. A
confirmed missing operation allows resubmission of the same bytes and UUID.
A failed/cancelled operation uses native `POST .../operations/{id}/retry`, then
polls that same operation; it does not mint a fresh retain operation. Partial
failure recovery must be demonstrated against the pinned implementation before
dependent rollout. Keep native operation records indefinitely for this scope.

Serialize delivery per relationship and fence worker leases. An uncertain or
exhausted item blocks later delivery in that relationship until reconciliation;
other relationships and healthy reply execution continue. Delivery acknowledgement,
retention completion, consolidation completion and semantic correctness are
different observations. Hindsight owns interpretation and consolidation.
Native `batch_retain` parents remain pending while their child operation processes;
inspect child status when reporting running work instead of treating parent pending
as proof that extraction has not started. Preserve both raw statuses for diagnosis.

The concrete integration client performs one HTTP attempt. Public source
envelopes and bank configuration live in `ade_api.integrations`.
Native feasibility can exercise that contract without importing runtime internals;
the product service still owns authorization and persisted bank selection.
The client preserves malformed responses and wrong bank/operation acknowledgements
as failures. Successful
empty recall is a valid result; a failed lookup pauses the reply under PC-14.

## Alternatives And Consequences

Whole-chat replacement and a second ADE reviewer were rejected by PC-09/14.
Appending every turn to a shared document would require additional native
concurrency/recovery proof without providing source isolation. Per-message
documents make attribution and replay identity inspectable, at the cost of a
bounded antecedent window and an explicit outbox. That outbox is operational
bookkeeping, not another fact store.

The pinned API supports a caller-supplied async UUID and native failed-operation
retry. See source `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`:
[request contract](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/api/http.py#L1269),
[replay and submission](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L22245),
and [retry transition](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L21377).
The source-backed contract and offline tests do not replace M1's native checks.

## Guardrails

Test scope isolation, candidate rejection, original timestamps, unchanged replay
bytes, lost acknowledgement, failed/partial operation recovery, ordered delivery
and stale-worker fencing. Inspect retained sources/facts/observations/recall for
reference resolution and correction versus change. Keep failed evidence and
update this record if the native gate disproves the chosen source/recovery shape.
Do not add a semantic workaround or relabel a counterexample as a pass.
