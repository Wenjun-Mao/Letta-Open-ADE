# Historical Maintenance Record

This page preserves the pre-service-first cleanup record for historical context.
It is not a source of current paths or runtime commands. Use the
[architecture overview](architecture/overview.md), [codebase map](codebase-map.md),
and [operational manual](../MANUAL.md) for current guidance.

## Retained Decisions

- Persistent agent behavior stays with Agent Studio and Letta; stateless labs
  use Model Router for provider requests.
- Retry ownership is explicit and request-scoped. Model Router makes one
  upstream attempt per forwarded request.
- Persona source material is reviewed JSONL content, while SQLite is a local
  runtime projection.
- Test Center orchestrates named live checks and exposes their run artifacts.
- Provider probes and model evaluations are operator-run workflows rather than
  default pull-request gates.

## Superseded Layout

The historical cleanup used a layer-oriented backend and older service names.
The comprehension-first redesign supersedes that layout with feature-owned
service code, centralized `content/`, and `workflows/`. Do not restore the
previous paths, names, API version, or host-port topology from old screenshots,
notes, or commits.

## Current Direction

New changes follow [ADR 0006](adr/0006-comprehension-first-service-and-feature-architecture.md):
one complete vertical slice moves UI, API, tests, docs, and operations together.
The move is complete only after the replaced implementation is deleted and the
feature has a discoverable local README.
