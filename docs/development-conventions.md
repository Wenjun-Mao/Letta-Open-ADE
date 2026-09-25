# Development Conventions

ADE favors direct ownership over flexibility for its own sake. Start with the
[reading guide](reading-guide.md), then use the [codebase map](codebase-map.md)
to find the feature, service, or workflow that owns the change.

## Keep One Owner

- `apps/ade-web` owns browser routes, UI, and same-origin proxying.
- `services/ade-api` owns product HTTP contracts and feature orchestration.
- `services/model-router` owns provider discovery, profiles, and one-attempt
  upstream forwarding.
- `content/` holds reviewed prompts, personas, schemas, and reports.
- `workflows/` holds self-contained evals, qualification, probes, and smoke checks.

Put behavior with the owning feature. A feature may use `platform/` and external
integrations, but must not import another feature's internals. Create a shared
package only when two services need one stable, versioned contract.

## Prefer The Smallest Durable Change

- Solve the requested problem without speculative configuration or extension points.
- Do not add an abstraction for one caller or one use.
- Remove replaced code instead of keeping an alias or fallback.
- Make retries, timeout, persistence, and provider ownership explicit at the
  feature/runtime boundary.
- Add only the error handling that represents a real contract or reachable failure.

## Workflow Locality

Put workflow runner, configuration, fixtures, tests, README, and ignored outputs
together under `workflows/`. A workflow uses public ADE API or Model Router
contracts; it does not reach into feature internals. Repository-wide utilities
without workflow-specific inputs and outputs belong in `scripts/`.

## Decisions And Verification

[The product contract](product-contract.md) owns current product intent. Cite
relevant PC IDs in product-affecting plans and reviews; distinguish agreement,
implementation and evidence. Update it when direction changes and explicitly
supersede old requirements. [ADR 0037](adr/0037-current-product-contract.md)
defines document ownership; do not create parallel agreement summaries.

Record durable API, runtime, data-authority, or deployment changes in a concise
ADR. Run the smallest relevant checks first, then the broader repository checks
proportional to risk. Update the owning README when an endpoint, storage
authority, external integration, or operator workflow changes.
