# ADR 0005: Incremental Feature Modularization

## Status

Accepted and implemented through the August 2026 maintenance cleanup. This
remains an ongoing structure rule.

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
- Preserve public routes and contracts while moving one feature at a time.

## Consequences

The rollout split the frontend API client by feature, reduced Agent Studio and
Test Center route controllers to composition owners, separated persona SQL from
seed policy and mapping, extracted generation request/response mapping, and moved
router forwarding into a one-attempt transport. Focused request-identity,
selection, payload, response, seed-transaction, descriptor, proxy, and UI tests
protect those seams.

Large feature modules may still be split when a cohesive boundary emerges. Avoid
line-count-only extraction, repository-wide moves, or generic abstractions that
make ownership harder to discover.
