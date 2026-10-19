# ADR 0080: Native Processing Pagination

Status: Accepted, 2026-10-19. Applies to PC-05/08/09/14 inspection, not semantic
Memory or Character qualification.

## Problem And Evidence

The first actual six-slot product run generated and committed its seed dialogue,
then every slot failed native processing inspection. The collector requested 200
operations. ADE accepted that limit and forwarded it, but source-pinned Hindsight
0.10.3's operations endpoint permits only 1-100. Native limit 100 returned 200;
limit 200 returned 422 with the explicit maximum; ADE limit 100 returned 200.
The source at `eb6df499d35300e5b2f3f029b2e6adda04ed90f8` declares the same cap.
The problem belongs to the public inspection parameter contract, not Memory
extraction, Character prompting or an unavailable native service.

## Decision

Expose an operations-specific 1-100 page limit in ADE's API/OpenAPI. Keep the
independent ADE delivery and native memory-list limits unchanged. The existing
Studio client already requests 100. Stage 1's small-case collector requests 100
and still rejects incomplete pages instead of silently asserting completeness.
Future larger assessments must implement complete pagination before expanding
those bounds. Do not clamp an invalid caller value, swallow native 422, invent
an empty operation list or relax processing-completion checks.

The six failed slots, actual sources and provider traffic remain immutable. A
repaired demonstration uses a new source-bound run and reports both runs, not
selected successful replies. The public SQL/API regression must reject 200 at
validation and allow 100; actual native retest remains required.
