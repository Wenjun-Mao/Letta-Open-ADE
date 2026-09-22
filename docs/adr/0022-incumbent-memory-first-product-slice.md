# ADR 0022: Incumbent Memory First For The Next Product Slice

Status: Proposed. Requires approval of the M2 sequencing change below.

## Context

M2 originally requires a measured ADE/Hindsight comparison before M3. The
[findings](../findings/m2-memory-approach-comparison.md) now establish ADE's
typed-fact storage lifecycle and bounded PostgreSQL-backed Luna conditioning.
They do not establish semantic retrieval, model extraction, long-session
continuity, or comparative quality. Hindsight has not been run here.

More supplied-context probes will not resolve those missing measurements.
The approved development lane is Luna, not Spark; it does not supply native
provider protocol or embedding qualification. Adding a memory service now
would add operational scope without a demonstrated product benefit.

## Proposed Decision

Retain the existing ADE PostgreSQL memory implementation as the incumbent for
one bounded Agent Studio product slice. Defer the external-service comparison
rather than declare it passed. No new service, schema family, retrieval layer,
or provider compatibility bridge is authorized by this decision.

Allow M3's supported-fact workflow to proceed after approval, while native
provider/retrieval acceptance remains pending. Keep concerns, promises, shared
experiences, and long-history relevance as explicit open requirements, not
capabilities implied by successful preference recall.

This is a cost-and-scope decision under uncertainty, not selection of a proven
quality winner. The original measured M2 comparison remains incomplete. If
approved, mark that experiment deferred and record the revised milestone
criterion explicitly in the roadmap and tracker; do not rewrite its history.

## Alternatives

- Wait for the complete comparison: preserves the original sequence but blocks
  provider-independent product improvements on unavailable experiments.
- Adopt Hindsight now: rejected because no case-specific benefit or lifecycle
  equivalence has been demonstrated here.
- Expand ADE into a general temporal-memory system now: rejected because the
  current samples do not justify that representation or complexity.

## Consequences And Reopening

Preserve source evidence, subject ownership, immutable definition versions,
optimistic memory revisions, and forgetting tombstones. Do not change the
meaning of an existing subject to silently create character-private memory.
Do not treat a persona edit as permission to rewrite historical conversations.

Reopen the comparison when a repeatable product case fails because of memory
representation or retrieval, not merely wording, and the smallest ADE change
has a concrete maintenance cost worth comparing with another service. Before
a trial, authorize providers and installation, preserve chronological fixtures,
and compare identical budgets and operator-reviewed outcomes.

No release-gate waiver follows. Governed changes still need fresh native
qualification before merge/deployment. Luna remains development-only.

Next work is bounded by the [M3 plan](../plans/m3-agent-studio-continuity.md).
