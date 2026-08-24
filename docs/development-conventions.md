# Development Conventions

This repo favors boring, discoverable structure over clever scattering. If a
change makes you ask "where is the rest of this?", put the related behavior in
the owning service, feature, or workflow.

Start with the [reading guide](reading-guide.md), then use the
[codebase map](codebase-map.md) to find the owner.

## Config Boundaries

- Root `config/` is reserved for application/runtime source-of-truth config.
- Workflow-specific config belongs beside the workflow runner.
- Current root config should stay limited to project-wide runtime inputs such as `config/model-router/sources.json` and `config/model-router/model-profiles.json`.

Reviewed product material belongs in `content/`, not `config/` or service source:
prompts, personas, label schemas, custom-tool records, and reviewed model
catalog reports each have a named `content/` subdirectory.

## Service And Feature Boundaries

- `apps/ade-web/` owns browser routes, product UI, and same-origin API proxying.
- `services/ade-api/` owns product HTTP contracts and feature orchestration.
- `services/model-router/` owns provider source discovery, model profiles, and
  one-attempt upstream forwarding.
- `packages/model-catalog-contracts/` may contain only stable, typed contracts
  shared by more than one service. Do not create a generic shared package.
- Put feature behavior under the matching `features/<feature>/` home. A feature
  may use `platform/` and `integrations/`, but must not import another feature's
  internal modules.

## Workflow And Eval Folders

Use `workflows/evals/<workflow_name>/` for evaluation, probe, benchmark, or
research workflows that have their own runner/config/input/output lifecycle.
Use `workflows/smoke/` for named live stack checks.

Each workflow should include:

- `README.md` with purpose, smoke/full commands, config fields, outputs, and troubleshooting.
- `run.py` or another obvious entrypoint.
- `config.toml` if the workflow is configurable.
- `inputs/` for checked-in sample input when useful.
- `outputs/` for generated artifacts, ignored by git.

Avoid compatibility shims for newly introduced workflow paths unless explicitly requested.

## Scripts Folder

Keep `scripts/` for repo-wide utilities without workflow-specific config/output bundles, such as diagnostics, OpenAPI export, reset helpers, seed helpers, or small maintenance commands.

If a script grows a config file, sample input, and generated outputs, promote it
into `workflows/evals/` or another named workflow folder.

## Documentation Expectations

When adding a workflow, update:

- The workflow-local `README.md`.
- `docs/codebase-map.md` when it changes where humans should look.
- Root README or MANUAL only when the workflow is part of normal development or operations.

## Architecture Decisions

Use `docs/adr/NNNN-short-title.md` for durable decisions that change a public or
operational contract, runtime boundary, data authority, or long-lived module
shape. Each record should state:

- Context and the decision.
- Consequences and rejected alternatives when they matter.
- Implementation status, including whether the decision is still pending.

An ADR records direction; it must not imply that code or deployment work has
already landed. Update its status when implementation and verification complete.

## Verification Boundaries

- CI runs deterministic checks: locked dependency installation, unit/API tests,
  generated artifact drift, frontend build, Compose rendering, and local image builds.
- Provider probes, browser smoke tests, and evaluations that need live services or
  credentials are explicit operator workflows, not default pull-request checks.
- Keep commands in shared documentation shell-neutral where practical. If a
  platform-specific script is required, label the platform rather than presenting
  it as the universal command.

## Feature Locality

When modifying a feature, keep a complete vertical slice together: thin route
entrypoint, feature API contract/client, state or service, tests, local README,
and operational notes. Delete replaced behavior instead of leaving aliases or
duplicate source trees. The staged modularization direction is recorded in
[ADR 0005](adr/0005-incremental-feature-modularization.md).
