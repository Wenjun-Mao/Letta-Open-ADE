# ADR 0039: Read-Only History Packet And Commit Fence

Status: Proposed for director verification of the isolated H3 offline checkpoint
on 2026-09-26. Live H2
ranker feasibility and H4/H5 dialogue scoring remain unobserved. No production
default, public route, tool allowlist or release binding changes.

## Problem

A historical exchange can help answer a distant-dialogue question, but it must
not become current write authority. A transcript can also be purged after the
accepted repeatable-read snapshot. Sending or committing with an unverifiable
held source would cross the source integrity contract even on a no-write turn.

## Decision

The evaluation-only `natural-user-assertions-v4-b-history-probe` policy uses
the existing B local/fact context and one H-capable reviewer shape for both
`empty_history` and `automatic_history` arms. An internal frozen selector must
provide at most four ranked run IDs from the bounded H2 corpus; until H2 selects
a recipe, the automatic arm cannot start. This offline seam is synchronous and
performs no corpus embedding or provider dispatch. Existing natural bindings
retain their original reviewer wire schema.

Admission tries complete annotated exchanges against the actual serialized
initial generation request, including tool schema, and the projected reviewer
request with candidate reserve. It preserves the base packet and records whole
windows omitted for capacity. The same H packet is serialized into the
generation system data section and reviewer user packet. Each annotation link
uses the corresponding H message handle, so repeated text and multiple claims
remain joined to their exact source; raw source IDs remain in the guard's held
records. H handles live in a separate request-local map; writes still accept
only current/local U/A evidence and F/E targets. A conflict may cite one exact H quote plus one exact candidate
span. ADE checks H identity, role, hash and unique quote binding; the reviewer
owns semantic contradiction judgment. Historical instructions remain data.
Both model instructions state that saved-fact transitions do not rewrite original
testimony or imply unknown intermediate states, values or causes; removal does
not erase retained dialogue or authorize revival. Ordinary reviewer requests
retain their original field set; only H-capable requests include `history`,
including the empty arm.

Before each outbound generation or continuation request and before review, an
awaited guard reads the held sources afresh and checks workspace, subject,
purpose, definition root/version, run status, complete pair, role, sequence,
content hash and source-relative annotations. A genuine purge before first
exposure removes whole windows and rebuilds both packets. After exposure,
purge or inability to verify is fatal. Scope, hash, stale generation and deadline
failures are always fatal. The finalizer checks admitted sources even when the
reviewer returns `decisions: []`, inside the success transaction and bounded by
the successful attempt's absolute deadline. The check remains outside provider
retry logic; existing lease, cancellation and postcommit acknowledgment rules
continue to own their boundaries. Optional corpus-reader SQL failure retains
the already read mandatory repeatable-read state and yields an explicit
unavailable probe status.

## Alternatives And Consequences

Rejected treating H as U/A support, a new history model tool, a writable
history target, a second finalization path, clipping oversized windows and
silently removing history after exposure. This is a bounded authorization
check, not a lock that prevents a purge after a request is authorized.

Guardrails are exact-packet unit tests, including annotation joins with repeated
text and multiple linked claims, and native fake-router/disposable
PostgreSQL cases for purges at generation, continuation, review and commit;
hash, scope, optional unavailability, conflict plus valid sibling write, and
deadline rejection. The successful provider outcome records probe status and
admitted run IDs. Reader and worker PostgreSQL suites require separate freshly
migrated test databases because reader fixtures leave pending runs in their
database. On this follow-up, 61 focused context/packet/executor tests, 11
evidence/finalization tests, six PostgreSQL reader/lineage/guard tests, and 15
independent PostgreSQL worker tests passed.
No live model result or release evidence is claimed here.
