# Codebase Map

Use this page to find the first owner of a change. Read the
[architecture overview](architecture/overview.md) for dependency rules and the
[request flows](architecture/request-flows.md) before crossing a service or
feature boundary.

## Runtime Map

```text
Browser
  -> apps/ade-web
  -> services/ade-api
  -> services/model-router -> configured providers

Agent Studio adds:
services/ade-api -> letta -> services/model-router -> configured providers
```

ADE Web and ADE API are host-facing on `3000` and `8000`. Model Router, Letta,
PostgreSQL, and Redis are Compose-network services. Model Router is the only
provider-facing boundary for normal discovery and generation.

## Repository Homes

| Concern | Home | Start With |
| --- | --- | --- |
| Browser UI, page routes, feature state | `apps/ade-web/` | `src/app/` for thin routes, `src/features/` for product behavior |
| Product HTTP API and feature orchestration | `services/ade-api/` | `src/ade_api/features/<feature>/` |
| API setup, settings, auth, dependency wiring | `services/ade-api/` | `src/ade_api/platform/` |
| Letta and Model Router protocol adapters | `services/ade-api/` | `src/ade_api/integrations/` |
| Provider discovery, profiles, and forwarding | `services/model-router/` | `src/model_router/` and `config/model-router/` |
| Typed catalog/probe exchange formats | `packages/model-catalog-contracts/` | `src/model_catalog_contracts/` |
| Prompts, personas, schemas, tools, reports | `content/` | owning center's adapter and its matching content subdirectory |
| Model source configuration | `config/model-router/` | `sources.json`, local overlay, and `model-profiles.json` |
| Evals and provider probes | `workflows/evals/` | workflow-local `README.md` and `run.py` |
| Live smoke coverage | `workflows/smoke/` | named smoke script or `make smoke` |
| Compose support files | `infra/` | `compose.yaml` and the relevant `infra/` asset |

## Feature Homes

Every product capability has matching ADE Web and ADE API homes. Keep route
entrypoints thin and put behavior, contracts, content/storage adapters, and
tests with the owning feature.

| Feature | ADE Web | ADE API | Primary dependency |
| --- | --- | --- | --- |
| Agent Studio | `src/features/agent-studio/` | `features/agent_studio/` | Letta |
| Comment Lab | `src/features/comment-lab/` | `features/comment_lab/` | Model Router |
| Label Lab | `src/features/label-lab/` | `features/label_lab/` | Model Router and label schemas |
| Prompt Center | `src/features/prompt-center/` | `features/prompt_center/` | prompt and persona content |
| Schema Center | `src/features/schema-center/` | `features/schema_center/` | label-schema content |
| Tool Center | `src/features/tool-center/` | `features/tool_center/` | custom-tool content and Letta |
| Test Center | `src/features/test-center/` | `features/test_center/` | workflow orchestration and typed artifact projections |
| Model Catalog | `src/features/model-catalog/` | `features/model_catalog/` | Model Router catalog |

See the [feature README template](feature-readme-template.md) for the expected
local documentation. A vertical feature change keeps web, API, tests, docs, and
operations together, then deletes replaced implementation rather than leaving an
alias behind.

## Content And Runtime Data

- `content/prompts/system/`: versioned system prompts by scenario.
- `content/personas/`: reviewed persona seed and templates.
- `content/label-schemas/`: reviewed Label Lab schemas.
- `content/custom-tools/`: managed custom-tool registry material.
- `content/model-catalog/`: reviewed probe reports and allowlists.
- `data/runtime/`: ignored runtime projections, SQLite, Test Center runs, and
  other generated state.

Reviewed content has no application imports. Runtime state is never a substitute
for its reviewed source. See [ADR 0003](adr/0003-persona-source-and-runtime-storage.md)
for the persona projection contract.

## Common Changes

| Change | Start Here |
| --- | --- |
| Add or disable a model source | `config/model-router/sources.json` or ignored `sources.local.json` |
| Tune model sampling/capabilities | `config/model-router/model-profiles.json` |
| Change provider discovery/forwarding | `services/model-router/src/model_router/` |
| Change Agent Studio lifecycle or memory flow | Agent Studio feature and [Agent Studio flow](architecture/request-flows.md#agent-studio) |
| Change Comment or Label generation | owning lab feature and its request/response mapping |
| Change prompt/persona behavior | Prompt Center feature and `content/prompts/` or `content/personas/` |
| Change label schemas | Schema Center feature and `content/label-schemas/` |
| Change custom tools | Tool Center feature and `content/custom-tools/` |
| Add a Test Center run type | Test Center feature plus its workflow entrypoint and artifacts |
| Add an eval/probe | a self-contained `workflows/evals/<workflow>/` folder |
| Regenerate API artifacts | `uv run python scripts/export_openapi.py` |
| Diagnose the Compose stack | `scripts/collect_diagnostics.sh .env` |

## Guardrails

- Do not call providers directly from ADE Web, ADE API features, or workflows.
- Do not let one feature import another feature's internal implementation.
- Do not create generic `utils` or a catch-all shared package.
- Keep workflow runner, config, fixtures, outputs, documentation, and tests
  together under its workflow.
- Record durable contract, deployment, or data-authority decisions in `docs/adr/`.
