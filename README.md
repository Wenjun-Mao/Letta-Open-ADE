# Letta Open ADE

ADE is a local-first workspace for building, testing, and refining agent
experiences. Its current system is intentionally small: **ADE Web** is the
browser product, **ADE API** is the single product backend, **Model Router** is
the provider boundary, and PostgreSQL stores Agent Studio state.

The repository name is historical. A project-wide rename is a separate future
decision; the running system has no Letta dependency.

## Start Here

1. Create `.env` from `.env.example`, replacing placeholder secrets and enabling
   only model sources reachable from this machine.
2. Start the stack:

```text
docker compose up -d --build
```

3. Open ADE Web at `http://127.0.0.1:3000`.
4. Check ADE API at `http://127.0.0.1:8000/api/v2/health`.

Only ADE Web and ADE API are host-facing. The ordinary Compose graph contains
PostgreSQL, Model Router, the one-shot migration job, the runtime worker, ADE
API, and ADE Web.

## System Map

```text
apps/ade-web/                         # Next.js product UI
services/ade-api/                     # FastAPI product API and native runtime
services/model-router/                # OpenAI-compatible provider boundary
content/                              # Reviewed prompts, personas, schemas, reports
config/model-router/                  # Source and model-profile configuration
workflows/                            # Evals, qualification, probes, and smoke checks
```

Read [the system status map](docs/architecture/system-status.md) for the
current authority, then [the reading guide](docs/reading-guide.md) to find the
right code home.

## Daily Commands

```text
make setup
make up
make status
make logs SERVICE=ade-api
make smoke
make down
```

Run deterministic verification from the repository root:

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

Live workflows are deliberate operator checks:

```text
make smoke
make eval-chat-memory
make eval-comment-persona
make probe-models SOURCE=ark
```

## Product Boundaries

- Agent Studio is the current native runtime at `/api/v3`. It owns reusable
  definitions, explicit memory subjects, immutable conversations, typed memory,
  run events, cancellation, and ADE-owned retries.
- Comment Lab and Label Lab remain stateless product features that resolve
  canonical model keys through Model Router.
- Prompt Center and Schema Center own reviewed workspace content.
- Model Catalog presents router-backed choices to ADE features.
- Test Center has three workflows only: behavior evaluation, agent runtime
  qualification, and current-stack smoke testing.

PostgreSQL is the persistent authority. Model Router is the provider and model
identity authority. Release recovery uses deployment rollback and PostgreSQL
backup/restore, not a second application runtime.

## Further Reading

- [Operational manual](MANUAL.md): start, verify, diagnose, and recover the stack.
- [Architecture overview](docs/architecture/overview.md): service and data boundaries.
- [Request flows](docs/architecture/request-flows.md): browser, runtime, and workflow paths.
- [Codebase map](docs/codebase-map.md): where to change a capability.
- [Product roadmap](docs/product-roadmap.md): current product direction.
- [ADR 0019](docs/adr/0019-ade-steady-state-runtime.md): steady-state runtime and release policy.

## Local-Only Default

This is a local development stack, not a hardened public deployment. Loopback
bindings, bearer authentication, narrow CORS, and server-side web credentials
are the local baseline. Public exposure requires reviewed ingress, TLS, secret
management, rate limits, monitoring, and a deployment threat review.
