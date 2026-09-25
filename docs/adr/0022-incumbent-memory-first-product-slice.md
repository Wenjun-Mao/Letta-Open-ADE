# ADR 0022: Incumbent Memory First For The Next Product Slice

Status: Accepted incumbent-memory direction; execution details partially superseded.

> The external-service comparison remains deferred, not passed. DeepSeek replaces
> the Luna-only lane ([ADR 0025](0025-deepseek-development-lane.md)); the current
> reviewer and explicit operator-removal path follow
> [ADR 0035](0035-compact-natural-review-and-observational-dispatch.md).
> Subject sharing and immutable persona versions remain current.

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

## Decision

Retain the existing ADE PostgreSQL memory implementation as the incumbent for
one bounded Agent Studio product slice. Defer the external-service comparison
rather than declare it passed. The original measured M2 comparison remains
unexecuted and deferred; ADE has not won a head-to-head quality comparison.
No new service, schema family, retrieval layer, or provider compatibility
bridge is authorized by this decision.

Proceed with four usable operator journeys for saved profile facts: choose an
existing conversation, start a new conversation with the same subject, start
an isolated subject, inspect current and historical evidence, prepare a
correction/removal in the composer and explicitly send it through the existing
turn/reviewer/write path, and create a new immutable persona definition version
through Prompt Center. A subject intentionally shares saved facts across its
conversations and persona versions. It does not denote private relationship
history with one character.

Use the wording **Remove saved information** for the supported forget action.
It removes a fact from active-fact and search input through the existing
tombstone path. Historical revisions, evidence, summaries, and old
conversation context remain, so old context may still contain the information.
This is not data erasure, suppression across all contexts, or a promise that
the user cannot state the fact again. The action requires explicit user send;
an acknowledgment or an unsuccessful run cannot be reported as a committed
change.

Keep `/api/v3` and existing resource ownership. Only additive evidence fields
for authoritative source conversation and message position are in scope. Keep
concerns, promises, shared experiences, and long-history relevance as open
requirements, not capabilities implied by preference recall.

This is a cost-and-scope decision under uncertainty. The roadmap and tracker
show M2's original comparison as deferred and M3's narrower profile-memory
slice as in progress without rewriting the M2 evidence history.

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

At the end of this slice, review the operator journeys and remaining capability
gaps **before substantial new memory machinery**. This review is mandatory
even if a plainly required capability is absent without a failed benchmark.
For each gap, record user impact, whether ADE already has an adequate
contract, the smallest source-owned change, and the cost of comparing or
adopting a service. A failed case is useful evidence but is not a prerequisite
for reopening the comparison. Before a Hindsight trial, authorize providers
and installation, preserve chronological fixtures, and compare identical
budgets and operator-reviewed outcomes.

No release-gate waiver follows. Governed changes still need fresh native
qualification before merge/deployment. Luna remains development-only.

Next work is bounded by the [M3 plan](../plans/m3-agent-studio-continuity.md).
