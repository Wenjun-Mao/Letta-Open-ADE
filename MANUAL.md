# Letta Open ADE Manual

This runbook operates the local Compose stack. For code ownership, use the
[codebase map](docs/codebase-map.md); for runtime boundaries, use the
[request flows](docs/architecture/request-flows.md).

## Before Starting

- Install Docker Compose, Python 3.12 with `uv`, and Node.js 22 for web checks.
- Create `.env` from `.env.example`. Replace every placeholder secret and keep
  `LETTA_ENCRYPTION_KEY` stable and backed up; changing it makes existing
  encrypted Letta credentials unreadable.
- Review `config/model-router/sources.json` and enable only reachable providers.
- Treat the stack as local-only. Loopback bindings are a development baseline,
  not an internet deployment design.

## Start And Stop

```text
make up
make status
make logs SERVICE=ade-api
make down
```

The Compose services are `ade-web`, `ade-api`, `model-router`, `letta`,
`postgres`, and `redis`. Do not run two Compose projects from the same checkout:
they would both mount `data/pgdata`. If a previous checkout used another Compose
project name, inspect its working directory before stopping it and do not use
`-v` unless a database reset is intentional.

```text
docker compose ls
docker inspect <container-name> --format '{{ index .Config.Labels "com.docker.compose.project.working_dir" }}'
docker compose -p <old-project-name> down --remove-orphans
```

## Endpoints And Network Boundary

- ADE Web: `http://127.0.0.1:3000`
- ADE API health: `http://127.0.0.1:8000/api/v2/health`
- ADE API OpenAPI: `http://127.0.0.1:8000/openapi.json`

`model-router`, `letta`, `postgres`, and `redis` are intentionally not exposed
on host ports. Diagnose them through Compose:

```text
docker compose logs --tail=200 model-router
docker compose logs --tail=200 letta
docker compose exec ade-api python -c "import urllib.request; print(urllib.request.urlopen('http://model-router:8010/v1/health').read().decode())"
```

## Rebuild One Service

Rebuild after changing a service's dependencies, Dockerfile, or copied runtime
assets:

```text
docker compose build ade-api
docker compose up -d --force-recreate ade-api
```

Replace `ade-api` with `model-router` or `ade-web` as appropriate. If Letta
cannot find local NLTK data, run `scripts/seed_nltk_data.sh`, then recreate the
`letta` service.

## Verification

Run the deterministic suite before sharing a change:

```text
uv sync --all-packages --frozen --group dev
uv run ruff check services packages workflows scripts tests
uv run python scripts/check_python_format.py --base origin/main
uv run python -m pytest
uv run python scripts/export_openapi.py --check
uv run python scripts/generate_openapi_zh_manual.py
git diff --exit-code -- docs/openapi/ade-api-openapi-zh.json apps/ade-web/public/openapi/ade-api-openapi-zh.json docs/openapi/zh_openapi_missing_terms.json
npm ci --prefix apps/ade-web
npm --prefix apps/ade-web run test
npm --prefix apps/ade-web run lint
npm audit --prefix apps/ade-web --audit-level=high
npm --prefix apps/ade-web run build
docker compose --env-file .env.example config --quiet
```

Run live checks only after the stack and required providers are healthy:

```text
make smoke
make eval-chat-memory
make eval-comment-persona
make probe-models SOURCE=ark
```

Each workflow records its own artifacts and interpretation notes under
`workflows/evals/` or `workflows/smoke/`. Provider probe writes update reviewed
catalog material, so use `make probe-models` only for a deliberate refresh.

## Recovery And Diagnostics

Create a redacted diagnostics bundle when the stack is unhealthy:

```text
scripts/collect_diagnostics.sh .env
```

Review the archive before sharing it. For a deliberately clean local database,
use `scripts/reset_database.sh` on POSIX systems or `scripts/reset_database.ps1`
on Windows. Both commands remove `data/pgdata` and restart the stack; they do not
delete reviewed `content/` or `config/` assets.

## Content And Runtime State

- Reviewed prompts, personas, schemas, tools, and model reports live under
  `content/`.
- Model sources and profiles live under `config/model-router/`.
- Runtime SQLite, test runs, and local service state live under `data/runtime/`.
- Browser requests use ADE Web's same-origin `/api/v2/...` proxy; the proxy keeps
  the `ADE_API_ADMIN_KEY` server-side.

The backend resolves scenario defaults through
`/api/v2/model-catalog/options`. Query that endpoint rather than hard-coding a
prompt, persona, model, or embedding key in operational automation.
