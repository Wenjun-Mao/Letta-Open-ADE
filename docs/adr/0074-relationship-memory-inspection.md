# ADR 0074: Relationship Memory Inspection And Independent Product Readback

Date: 2026-10-19. Status: accepted for the approved Stage-1 implementation.
Product authority: PC-02/03/04/07/09/12/14 and the approved
[M4 integration scope](../plans/hindsight-integration.md#m4-complete-agent-studio-and-public-inspection).
This records source contracts, not release, live Memory or Character acceptance.

## Problem

The incumbent UI queried facts by subject alone and awaited remote Memory together
with saved chat. Neither contract fits character-local, separately persisted
Hindsight Memory. A remote outage must not hide already saved input or look like
successful empty recall. Native task/error bodies are not ordinary UI activity.

Browser inspection also exposed a contract mismatch: saved-input Retry returns a
`TurnAcceptedResponse`, while the first client treated it as `RunResponse` and
opened `/runs/undefined`. Its mock returned the same wrong shape, hiding the bug.
Mobile inspection exposed unbroken timestamps/source content determining grid
intrinsic width. These belong at the typed receipt and layout boundaries, not in
server aliases, downstream missing-ID tolerance or page-wide overflow clipping.

## Decision

- Public Memory paths start at
  `/api/v3/memory/subjects/{subject_id}/characters/{character_root_id}`. ADE derives
  the bank from an existing persisted relationship in its active fresh workspace.
  The client cannot choose a bank, create a relationship through inspection, use
  a persona-version ID as a root or cross ownership through a source/operation ID.
- `/deliveries` is ADE-only and remains usable during native outages. It exposes
  independent acknowledgement/retention timestamps, status counts, pending age,
  first unfinished operation and each later item's blocker. Retained is processing
  completion verified by source readback, not semantic correctness or consolidation.
- `/memories`, `/sources/{document_id}` and `/operations` are read-only native
  inspections. Original sources must also belong to a scoped ADE delivery and
  match its immutable payload. Native single-operation reads are bank-scoped and
  request no task payload. Unknown/pruned operations are not invented successes.
- Native progress is allow-listed again on read, including previously persisted
  rows. Raw errors, private reasoning, task payloads and unknown fields stay out
  of ordinary responses. Reported progress is a last snapshot, not a percentage.
- Delivery Retry is operator-only, check-count fenced and uses the original
  outbox intent. Saved-input Retry is a separate command: read its typed
  acceptance receipt, verify the saved run identity, then fetch the actual Run.
  Neither Retry adds a user message. Ambiguous responses preserve the same key.
- The UI loads saved conversation/runs independently, and polls delivery,
  learned Memory and native operations independently. Failed reads do not become
  empty lists. Selection epochs reject late A-to-B-to-A responses and source reads.
  Long inspection values wrap within their component without hiding page overflow.
- New definitions use conversation and compaction roles. Retire subject-only fact
  lineage, manual removal and historical-trial redirection from this maintained UI.
  Original history/data and old deployment artifacts remain untouched.
- Turn activity separates ADE generation/compaction calls from Hindsight calls,
  and automatic/tool-supplied Memory IDs from original-chat context. A summary
  placeholder is not evidence of earlier dialogue. Unknown attempt observations
  remain unavailable/partial rather than being presented as zero or causality.

## Alternatives And Guardrails

A combined chat/Memory request, subject-only inspection, raw native proxy and
compatibility fact adapter were rejected: each weakens authority or truthful UI
state. A new generic Memory abstraction is unnecessary.

Real application-role PostgreSQL/API tests cover scope forgery, source integrity,
outage-independent readback, Retry fencing and progress privacy. UI tests cover
independent loading, selection races, actual receipt shape and paused-input guards.
Loopback browser checks use the normal product path with controlled network
boundaries; they must be labelled mechanical, not live semantic qualification.
M5 actual native/product capture and M6 fault/recovery closeout remain separate.

The unrelated-progress SQL fixture creates its other relationship after the first
has failed. A same-transaction timestamp tie previously made the test assume
unpromised global FIFO; per-relationship order and unrelated progress remain the
assertions, with no scheduler priority change.
