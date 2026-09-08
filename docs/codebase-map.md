# Codebase Map

Use this page to find the first owner of a change. The current request path is:

```text
Browser -> apps/ade-web -> services/ade-api -> PostgreSQL and Model Router
                                  ^
                         ade-runtime-worker claims Agent Studio runs
```

## Repository Homes

| Concern | Home |
| --- | --- |
| Browser UI, page routes, and feature state | `apps/ade-web/src/features/` |
| Product HTTP contracts and application behavior | `services/ade-api/src/ade_api/features/` |
| App composition, settings, auth, and dependency wiring | `services/ade-api/src/ade_api/platform/` |
| Provider protocol and catalog client | `services/ade-api/src/ade_api/integrations/model_router/` |
| Agent Studio runtime | `services/ade-api/src/ade_api/features/agent_runtime/` |
| Provider discovery, profiles, and forwarding | `services/model-router/` and `config/model-router/` |
| Prompts, personas, schemas, and reviewed reports | `content/` |
| Evals, qualification, probes, and smoke checks | `workflows/` |
| Durable decisions | `docs/adr/` |

## Feature Homes

| Feature | ADE Web | ADE API | Primary dependency |
| --- | --- | --- | --- |
| Agent Studio | `agent-studio/` | `agent_runtime/` | PostgreSQL and Model Router |
| Comment Lab | `comment-lab/` | `comment_lab/` | Model Router |
| Label Lab | `label-lab/` | `label_lab/` | Model Router and schemas |
| Prompt Center | `prompt-center/` | `prompt_center/` | Prompt/persona content |
| Schema Center | `schema-center/` | `schema_center/` | Label-schema content |
| Test Center | `test-center/` | `test_center/` | Workflow orchestration and artifacts |
| Model Catalog | `model-catalog/` | `model_catalog/` | Model Router catalog |

## Common Changes

| Change | Start here |
| --- | --- |
| Add or disable a model source | `config/model-router/sources.json` |
| Tune model capabilities or sampling | `config/model-router/model-profiles.json` |
| Change provider forwarding | `services/model-router/src/model_router/` |
| Change Agent Studio memory or run behavior | `features/agent_runtime/` and its local README |
| Change Comment or Label generation | The owning lab feature |
| Change prompt/persona behavior | Prompt Center and `content/prompts/` or `content/personas/` |
| Change a label schema | Schema Center and `content/label-schemas/` |
| Add a Test Center workflow | Test Center descriptor plus a self-contained workflow |
| Regenerate API artifacts | `uv run python scripts/export_openapi.py` |

Features may depend on `platform/` and external integrations, but not on another
feature's internals. Workflows consume public API contracts and retain their
inputs, config, documentation, tests, and generated outputs together.
