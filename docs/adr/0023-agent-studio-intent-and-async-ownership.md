# ADR 0023: Agent Studio Intent And Async Ownership

Status: Accepted for the M3 profile-memory slice on 2026-09-22.

## Context

The correction composer emitted “Please correct this saved fact: … The correct
information is: …”, but the reviewer intent detector did not recognize that
prefix. A correction could therefore be proposed as an add. Separately, a
same-conversation evidence read incremented the epoch used by run monitoring,
silently invalidating terminal callbacks. Refreshes could also overwrite a
newly selected definition or a newer transcript page.

## Decision

Treat the editable correction/removal draft and reviewer intent as one narrow
cross-language contract. `config/agent-studio/memory-action-contract.json`
records exact composer examples exercised by both web and reviewer tests. The
reviewer recognizes the generated correction prefix as an explicit correction;
the operator still edits and sends the request, and memory changes still need
review plus a persisted revision. Do not infer a manual fact mutation API from
the draft.

Give conversation selection, read refresh, and run monitoring separate
identities. A read refresh may replace another read, but cannot end a monitor.
Selection changes invalidate callbacks, errors, turn acceptance, pagination,
and monitoring for the old conversation. A same-conversation refresh preserves
an operator's later definition choice. Historical citation paging is a
temporary transcript view with an explicit return to latest messages, not a
conversation restore or a replacement for the current transcript.

Template previews refresh on focus or request. Before creating an immutable
definition version, the UI re-reads active prompt/persona text and stops if it
differs from the reviewed preview. The backend remains authoritative for
version creation and deployment restrictions.

## Alternatives And Consequences

Do not broadly classify any mention of “correct” as correction; that risks
turning ordinary dialogue into memory mutations. Do not stop a run monitor on
every read refresh or silently preserve a historical page as the latest chat.
The preview recheck is not atomic with a concurrent Prompt Center edit; strict
preview-to-snapshot identity would require an expected template revision/hash
on the definition creation API. That remains a follow-up if this race becomes
an acceptance requirement. Tests cover the exact draft-to-reviewer route,
async callback races, paginated citation return, and preview invalidation.
