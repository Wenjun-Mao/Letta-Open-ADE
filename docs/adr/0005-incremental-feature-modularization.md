# ADR 0005: Incremental Feature Modularization

## Status

Accepted. Its incremental, behavior-first extraction rule remains in force;
[ADR 0006](0006-comprehension-first-service-and-feature-architecture.md)
supersedes its previous repository-layout rollout plan.

## Context

Large route pages, broad API client files, and import-time service facades make
feature ownership difficult to discover and make state-race regressions easier to
introduce.

## Decision

- Keep route entrypoints thin and organize stable code by feature domain.
- Extract feature API clients, state/hooks, and UI components only when they have
  a clear ownership boundary and focused tests.
- Move backend initialization toward explicit application dependencies rather than
  expanding global facades.
- Move one complete feature slice at a time and delete the replaced source once
  the replacement is verified.

## Consequences

The service-first redesign keeps these tactics but gives every feature one
discoverable ADE Web and ADE API home. Focused request-identity, selection,
payload, response, seed-transaction, descriptor, proxy, and UI tests protect
those seams.

Large feature modules may still be split when a cohesive boundary emerges. Avoid
line-count-only extraction, repository-wide moves, or generic abstractions that
make ownership harder to discover.
