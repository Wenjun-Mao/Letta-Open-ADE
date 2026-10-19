# ADR 0085: Revision-Bound Historical Architecture

Status: Accepted, 2026-10-19.

## Root Cause

The moving native-Memory figure validated old reviewer/fact-store claims against
current source. Hindsight replaced those runtime anchors. Updating anchor strings
alone would falsely present an obsolete architecture as current. Its header also
retained the October 6 baseline although subsequent refactors maintained its
anchors through `d94913dd22e4208e0f6092d0144cc5acbcb49606` on October 8.
All 26 referenced source files and anchors match that last owning commit.

## Decision

Archive the native inventory/tour visibly in the generated HTML/SVG/Markdown and
entrypoints. Preserve its original baseline, graph, teaching examples, capability
statuses and historical current/experimental distinctions. Record the separate
last source-anchor revision explicitly; validate against immutable local Git
objects there, not today's implementation. Reject changed revision bindings,
missing objects, bad anchors, unsafe paths and misleading animation as before.
No fallback to current source and no historical qualification/hash rebind.

Keep a separate current Hindsight source guide for PC-02/03/05/08/09/14's accepted
input, independent delivery, required recall/Retry and dual-store authority.
The Character assessment guide remains current PC-12 vocabulary; do not archive
it merely because it is colocated with the older runtime maps.

## Consequences

Regenerating/reviewing the historical moving figure needs the bound local Git
history; a source archive without those objects fails explicitly. The generated
presentation itself stays self-contained and offline. This documentation repair
does not qualify behavior, revive a native reviewer or authorize deployment.
