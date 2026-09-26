# ADR 0038: Bounded Historical Source Contract

Status: Accepted for the isolated H1–H5 probe on 2026-09-26. No production
retrieval policy, default, deployment or release evidence is selected.

## Problem

PC-03 and PC-10 require same-character continuity across persona versions and
archived chats, while PC-05/07 distinguish transcript testimony from saved-fact
state. Current local messages and subject facts cannot recover distant dialogue.
Adding transcript text without source and lifecycle boundaries could present a
removed fact as current, let another character claim participation, or let a
saved-fact repair masquerade as a user retraction.

## Decision

The H1 fixture freezes a finite automatic-history versus empty-history probe.
The reader uses the accepted turn's existing repeatable-read transaction, with
the same connection as local messages and subject memory. It joins conversation,
immutable definition version/root, subject, workspace and purpose. Archived
conversations qualify; only succeeded runs with a complete user/assistant pair
qualify. Local sequence orders only its own chat. Source times select a bounded
corpus and do not assert global commit order. The current run is excluded.

The optional corpus has whole-exchange and source-envelope limits. A linked
claim names its precise message span and source authority role; a deduplicated
set of revision records and predecessor edges connects that origin to the
current fact projection. Source-less operator removal remains on the path.
Intermediate revision status is unknown because existing revisions do not store
it; the current projection supplies the only held status. Earlier revision
values are not exposed. Lifecycle operations and reasons describe saved
representation changes, never prove what the user originally meant or retracted.
An oversized required envelope omits its entire exchange. H3 will admit only
complete windows through one shared generator/reviewer packet and keep `H`
read-only, separate from writable local sources.

## Alternatives And Consequences

Rejected a new transcript schema/service, global timestamp ordering, latest
status alone, enumerated lineage paths, semantic keyword links and a model tool.
This read is deliberately bounded for a probe; coverage misses and unknown
intermediate status are visible limitations. H3 must revalidate admitted source
integrity before every source-bearing outbound request and before commit, with
the successful attempt deadline on the new finalization check. The known
policy-freshness release gate remains unwaived.

Guardrails: H1's frozen fixture, disposable PostgreSQL snapshot/provenance tests,
paired actual-packet comparison, and atomic no-write/purge tests in H3. Live
ranking and dialogue evidence remain separate from this structural checkpoint.
