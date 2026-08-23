# ADR 0006: Comprehension-First Service And Feature Architecture

## Status

Accepted. Implementation proceeds in tested vertical slices.

## Context

Letta Open ADE has grown through useful feature work, but its structure still
answers "what technical layer is this?" more readily than "which product
capability owns this?". A maintainer following one workflow can cross routers,
models, services, registries, options, clients, frontend barrels, and external
integrations before finding the complete behavior.

The current project names are also inconsistent: source directories,
Compose services, images, environment variables, and OpenAPI artifacts use
different names for the web application and API. The result is safe to change
in small areas, but difficult to understand as one system.

## Decision

- Adopt a service-first monorepo with three named applications:
  `apps/ade-web`, `services/ade-api`, and `services/model-router`.
- Organize ADE API and web code by product feature. A feature owns its route,
  contracts, application service, storage adapter, UI/API client, tests, and a
  short local README.
- Reserve `platform/` for application composition, settings, auth, lifecycle,
  and dependency injection. Reserve `integrations/` for external protocol
  adapters. Neither contains feature policy.
- Centralize reviewed editable assets under `content/` and executable eval,
  probe, and smoke workflows under `workflows/`.
- Make Model Router the only owner of provider configuration, model discovery,
  profile interpretation, and provider-facing transport. ADE features consume
  resolved model capabilities through its integration.
- Replace the ADE API's `/api/v1` surface with feature-aligned `/api/v2`
  endpoints. Do not keep old imports, route aliases, service names, environment
  variables, or image aliases after the migration.
- Expose only ADE Web on port `3000` and ADE API on port `8000`. Model Router,
  Letta, PostgreSQL, and Redis remain internal Compose services.
- Keep the root `compose.yaml` as the operator entrypoint. Keep Model Router's
  OpenAI-compatible `/v1` protocol unchanged.

## Consequences

The migration is deliberately breaking for repository consumers and operators.
It will rename packages, services, configuration, images, documentation, and
the ADE API contract in one target direction rather than prolonging a dual
vocabulary.

The work must proceed as tested vertical slices. Each slice keeps the stack
runnable and includes feature-local tests, one integration path, documentation,
and removal of its replaced legacy code. During the migration, temporary
internal wiring may exist only to complete a slice; it must be deleted before
the final architecture is accepted as implemented.

This ADR supersedes ADR 0005 where the two conflict. ADR 0005 remains useful
for its feature-locality principle, but its incremental, compatibility-preserving
scope does not govern this intentional redesign.

## Rejected Alternatives

- Keep the current layer-oriented layout and improve only the codebase map.
  This describes complexity without giving it an owner.
- Split every technical layer into a shared framework. This would introduce a
  second abstraction problem and obscure feature ownership further.
- Preserve `/api/v1`, old package imports, and old environment variables as
  long-term aliases. This makes migration easier briefly but leaves two mental
  models permanently active.
