# Letta Open ADE Manual

This is the operational runbook for the local stack. For code ownership, use
[docs/codebase-map.md](docs/codebase-map.md); for durable architecture choices,
use [docs/adr/](docs/adr/).

## Before Starting

- Install Docker Compose, Python 3.12 with `uv`, and Node.js for frontend-only checks.
- Create `.env` from `.env.example` and replace every placeholder secret. Generate
  `LETTA_ENCRYPTION_KEY` once, keep it persistent, and back it up with the database;
  changing or losing it makes credentials already encrypted by Letta unreadable.
- Review `config/model_router_sources.json`; configured provider endpoints must be
  reachable from the Docker host.
- Treat the default stack as local-only. Its loopback bindings and bearer roles are
  a development baseline, not a substitute for reviewed ingress, TLS, secret
  management, rate limits, monitoring, and a deployment threat review.

## Start, Stop, And Inspect

The canonical Compose project name is `letta-open-ade`. Docker treats a project
name change as a separate stack, even when both stacks use the same checkout and
bind-mounted data. Before the first startup from a checkout that previously ran
under another project name, identify and stop only the old stack from this
repository:

```text
docker compose ls
docker inspect <container-name> --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
docker compose -p <old-project-name> down --remove-orphans
```

Confirm that the inspected working directory is this repository before stopping
the old project. Do not add `-v`: the migration is a container cleanup, not a data
reset. Never run two Compose projects from the same checkout because both can
mount `./data/pgdata` into separate Postgres containers.

Start or rebuild all services:

```text
docker compose up -d --build
```

Inspect health and logs:

```text
docker compose ps
docker compose logs --tail=200 agent_platform_api
docker compose logs --tail=200 model_router
docker compose logs --tail=200 letta_server
```

Stop services without deleting local volumes:

```text
docker compose down
```

The local endpoints are:

- ADE frontend: `http://127.0.0.1:3000`
- Agent Platform API health: `http://127.0.0.1:8284/api/v1/health`
- Letta API: `http://127.0.0.1:8283`
- Model router health: `http://127.0.0.1:8290/v1/health`

There is no supported Letta UI endpoint on `8083` in this Compose stack.

## Rebuild A Service

Rebuild a service after changing its dependencies, container files, or copied
source files:

```text
docker compose build agent_platform_api
docker compose up -d --force-recreate agent_platform_api
```

Replace `agent_platform_api` with `model_router` or `ade_frontend` as needed.

If Letta cannot find local NLTK data, seed it and recreate Letta:

```text
scripts/seed_nltk_data.sh
docker compose up -d --force-recreate letta_server
```

On systems that do not execute shell files directly, invoke the script with a
POSIX-compatible shell.

## Deterministic Checks

Run these from the repository root. They do not intentionally call a provider or
start a Compose stack:

```text
uv sync --frozen --group dev
uv run ruff check agent_platform_api model_router ade_core evals scripts tests
uv run python scripts/check_python_format.py --base origin/main
uv run python -m pytest
uv run python scripts/export_openapi.py --check
uv run python scripts/generate_openapi_zh_manual.py
git diff --exit-code -- docs/openapi/agent-platform-openapi-zh.json frontend-ade/public/openapi/agent-platform-openapi-zh.json docs/openapi/zh_openapi_missing_terms.json
npm ci --prefix frontend-ade
npm --prefix frontend-ade run test
npm --prefix frontend-ade run lint
npm audit --prefix frontend-ade --audit-level=high
npm --prefix frontend-ade run build
docker compose --env-file .env.example config --quiet
```

The Chinese generator intentionally writes its artifacts and missing-term report;
the following `git diff` command verifies that committed copies are current.

## Manual Live Checks

These checks require a configured, healthy stack and may use model-provider
credentials. They are not CI blockers:

```text
uv run python tests/checks/platform_api_e2e_check.py
uv run python tests/checks/ade_mvp_smoke_e2e_check.py
uv run python evals/chat_memory_eval/run.py --config evals/chat_memory_eval/config.toml --rounds 1
uv run python evals/comment_persona_eval/run.py --config evals/comment_persona_eval/config.toml
uv run python evals/provider_model_probe/run.py --source-id ark --mode chat-probe --write
```

Read each workflow README before running it. Provider probing with `--write`
updates reviewed catalog artifacts and should be a deliberate refresh, not a
routine test command.

## Maintenance Utilities

See [scripts/README.md](scripts/README.md) for reset, diagnostics, tool-sync, and
persona-library commands. Review diagnostics bundles before sharing them outside a
trusted environment.

## Current Boundaries

- Prompts and label schemas are file-backed content under `prompts/` and `schemas/`.
- `agent_platform_api/seed_data/personas.jsonl` is the reviewed persona source;
  runtime SQLite belongs under `data/runtime/`.
- The model router is the canonical model-discovery and provider-routing layer.
- Browser API calls use the frontend's same-origin `/api/v1/...` proxy. Its
  upstream URL and bearer credential are server-only runtime configuration.

The default prompt is resolved by the backend option API. Do not depend on a
hard-coded prompt key in runbooks; query `/api/v1/options?scenario=chat` when a
specific environment needs to verify its configured default.
