# ADR 0006: Comprehension-First Service And Feature Architecture

## Status

Accepted and implemented.

## Context

Letta Open ADE has grown through useful feature work, but its structure still
answers "what technical layer is this?" more readily than "which product
capability owns this?". A maintainer following one workflow can cross routers,
models, services, registries, options, clients, frontend barrels, and external
integrations before finding the complete behavior.

The former project structure used different names and locations for the web
application, API, configuration, and API artifacts. That made a small change
safe in isolation but made the system difficult to understand as a whole.

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
- Expose feature-aligned ADE API version 2 endpoints. Do not keep replaced
  imports, route aliases, service names, environment variables, or image
  aliases.
- Expose only ADE Web on port `3000` and ADE API on port `8000`. Model Router,
  Letta, PostgreSQL, and Redis remain internal Compose services.
- Keep the root `compose.yaml` as the operator entrypoint. Keep Model Router's
  OpenAI-compatible `/v1` protocol unchanged.

## Consequences

The redesign was deliberately breaking for repository consumers and operators.
It renamed packages, services, configuration, images, documentation, and the
ADE API contract in one direction rather than prolonging a dual vocabulary.

Ongoing changes proceed as tested vertical slices. Each slice keeps the stack
runnable and includes feature-local tests, one integration path, documentation,
and removal of replaced code.

This ADR supersedes ADR 0005 where the two conflict. ADR 0005 remains useful
for its feature-locality principle, but its incremental, compatibility-preserving
scope does not govern this intentional redesign.

## Rejected Alternatives

- Keep the current layer-oriented layout and improve only the codebase map.
  This describes complexity without giving it an owner.
- Split every technical layer into a shared framework. This would introduce a
  second abstraction problem and obscure feature ownership further.
- Preserve replaced API routes, package imports, and environment variables as
  long-term aliases. This makes a transition easier briefly but leaves two
  mental models permanently active.

## Historical Migration Record

The redesign replaced the previous `agent_platform_api` package,
`frontend-ade` application path, `AGENT_PLATFORM_*` and `ADE_FRONTEND_*`
environment namespaces, `/api/v1` routes, and `agent-platform-openapi`
artifacts. These names are retained in this ADR only to document the completed
breaking change; they are not supported interfaces.
