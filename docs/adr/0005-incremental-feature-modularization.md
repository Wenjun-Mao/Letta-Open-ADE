# ADR 0005: Incremental Feature Modularization

## Status

Accepted. The first incremental rollout is implemented; this remains an ongoing
structure rule.

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

The first rollout split the frontend API client by feature, extracted stable Agent
Studio panels and memory-diff logic, separated generation-lab copy/presenters, and
replaced backend catch-all facades with focused dependencies and modules. Request
identity, selection, proxy, memory diff, and parsing tests protect the extracted
seams.

Large route controllers may still be split when a cohesive boundary emerges. Avoid
line-count-only extraction, repository-wide renames, or generic abstractions that
make ownership harder to discover.
