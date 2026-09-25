# ADE Manual

This runbook operates the local ADE stack. For code ownership, use the
[codebase map](docs/codebase-map.md); for runtime boundaries, use the
[request flows](docs/architecture/request-flows.md).

## Before Starting

- Install Docker Compose, Python 3.12 with `uv`, and Node.js 22 for web checks.
- Create `.env` from `.env.example` and replace every placeholder secret.
- Review `config/model-router/sources.json` and enable only reachable providers.
- Treat the stack as local-only. Loopback binding is not an internet deployment design.

## Start And Stop

```text
make up
make status
make logs SERVICE=ade-api
make down
```

The Compose services are `postgres`, `model-router`, `ade-runtime-migrate`,
`ade-runtime-worker`, `ade-api`, and `ade-web`. Do not run two Compose projects
from the same checkout: both would mount `data/pgdata`.

The migration job applies the Alembic schema before the API and runtime worker
serve Agent Studio. The worker executes accepted Agent Studio runs from the same
ADE PostgreSQL authority as the API.

## Endpoints

- ADE Web: `http://127.0.0.1:3000`
- ADE API health: `http://127.0.0.1:8000/api/v2/health`
- ADE API OpenAPI: `http://127.0.0.1:8000/openapi.json`
- Agent Studio worker readiness: authenticated `GET /api/v3/worker-health`

Model Router and PostgreSQL are Compose-network services. Diagnose them through
Compose rather than exposing extra host ports:

```text
docker compose logs --tail=200 model-router
docker compose logs --tail=200 ade-runtime-worker
docker compose exec ade-api python -c "import urllib.request; print(urllib.request.urlopen('http://model-router:8010/v1/health').read().decode())"
```

## Rebuild One Service

Rebuild after changing dependencies, a Dockerfile, or copied runtime assets:

```text
docker compose build ade-api
docker compose up -d --force-recreate ade-api
```

Replace `ade-api` with `model-router` or `ade-web` as appropriate. Recreate the
runtime worker after changing execution, persistence, or release-policy code.

## Verification

```text
uv sync --all-packages --frozen --group dev
uv run ruff check services packages workflows scripts tests
uv run python -m pytest
uv run python scripts/export_openapi.py --check
npm ci --prefix apps/ade-web
npm --prefix apps/ade-web run test
npm --prefix apps/ade-web run lint
npm --prefix apps/ade-web run build
docker compose --env-file .env.example config --quiet
```

Run live checks only after the stack and selected providers are healthy:

```text
make smoke
make eval-chat-memory
make eval-comment-persona
make probe-models SOURCE=ark
```

## Runtime Qualification And Recovery

The release ledger binds the reviewed runtime revision, API/worker build
identity, policy hashes, active model aliases, agent bundle, deterministic
conformance, native qualification, and compatibility of the selected routes under
[ADR 0027](docs/adr/0027-provider-neutral-release-and-embedding-space.md).
A particular DGX or llama-server endpoint is not a permanent release requirement. Use the
release commands documented by `make help`; a failed gate requires a new
qualification and promotion, not a hidden fallback.

Recovery is an explicit deployment rollback paired with PostgreSQL
backup/restore. Existing PostgreSQL data is preserved across normal rebuilds.
For a deliberately clean local database, use `scripts/reset_database.sh` on
POSIX or `scripts/reset_database.ps1` on Windows. Those commands remove
`data/pgdata` and restart Compose; they do not delete reviewed `content/` or
`config/` assets.

## Content And Runtime State

- Reviewed prompts, personas, schemas, and model reports live under `content/`.
- Model sources and profiles live under `config/model-router/`.
- Agent Studio state and Test Center runs live in PostgreSQL and ignored runtime
  artifact directories.
- Browser requests use ADE Web's same-origin `/api/v2/...` and `/api/v3/...`
  proxies. Both route to the one ADE API and keep `ADE_API_ADMIN_KEY` server-side.

The backend resolves feature options through `/api/v2/model-catalog/options`.
Operational automation should query that endpoint rather than hard-code a
model, prompt, persona, or embedding key.
