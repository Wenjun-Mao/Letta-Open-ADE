# Chart Readability Contract

Agreed presentation refinement, 2026-10-07. Applies to the guided message journey,
its detailed/focused tours, the connected capability map and static overview.
This is documentation presentation, not a runtime, ownership or product-policy
change. ADR 0061 and PC-08/09/12 remain the authority for responsibility boundaries.

## Positive Identity

Headings identify what a group **is**, not only what it is excluded from:

- Runtime Coordination: the existing turn orchestration and worker, SUP-01.
- Model Access: the existing Model Router, SUP-03.
- Persisted records: original dialogue, facts/revisions, definitions, summaries,
  search representations and run/attempt/event metadata, with their REC IDs.
- Transient outputs: candidate reply artifacts, distinct from persisted records.
- Platform support: the cross-cutting supporting register, with each piece's
  registered responsibility shown. Independent labs remain adjacent features.

L1/L2/L3 still describes product capability ownership. Support and record headers
do not receive invented depth numbers. IDs, statuses, source bindings and material
qualifications remain visible. The guide derives support headers from the detailed
layout; the review gate binds those names to the canonical inventory's subsystems.

## Connection Placement

The original independent detours put bypass transfers above and below an unrelated
worker card, suggesting that card participated in both transfers. The two HTML
renderers also had different routing rules. The connected map now embeds the
journey's existing `flow-model.js`, including its upstream MIT notice.

Horizontal transfers that skip an intervening card prefer the lower side. Direct
neighbor links remain direct. Explicit `around: "above"` or `"below"` hints remain
available for authoring, including intentional return loops. The acceptance pair
and local-context bypass use the lower side; the retry loop keeps its upper hint.
Obstacle avoidance protects unrelated cards and headings after port assignment.
Stacked/wrapped layouts use their measured geometry rather than forcing a wide
horizontal lane onto every connection. Color is current/completed flow emphasis,
not a different routing rule.

No edges are redirected to or through an unrelated module. Node identities,
edge endpoints/direction, flow membership, transaction grouping and beat order
remain unchanged. The static overview already uses authored outer lanes; its
paths are retained and its support/record labels are clarified.

## Guardrails And Limits

Offline checks cover positive identities in all six chapters, seven detailed and
focused tours, three connected-map flows and the static overview. They check
inventory alignment, shared route use, direct/bypass/explicit-return distinctions,
unobstructed geometry, playback and regenerated outputs. Native SVG raster reviews
cover chapter starts/results, detailed tours and the overview. These are not
browser screenshots; actual Safari layout and assistive technology are not
qualified by the synthetic geometry or source-backed drawing checks.

Rejected alternatives: a new L1 platform domain, renumbered modules, a visual
editing framework, per-tour special routing and moving every gray line regardless
of its endpoints. These would change meaning or add unnecessary machinery.
