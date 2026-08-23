# Letta Open ADE

Letta Open ADE is a local agent-development environment with three first-party
components:

- `model_router`: one OpenAI-compatible gateway for configured local and cloud models.
- `agent_platform_api`: the API used by ADE workspaces and operator tooling.
- `frontend-ade`: the Next.js Agent Development Environment.

Letta, Postgres + pgvector, and Redis run alongside those components in Docker
Compose. See [the codebase map](docs/codebase-map.md) for ownership and entrypoints.

## Local Quick Start

1. Create a local `.env` from `.env.example` with your editor or file manager.
   Supply non-placeholder API keys and review the enabled model sources before startup.
2. Start or rebuild the local stack:

```text
docker compose up -d --build
```

3. Check service status:

```text
docker compose ps
```

4. Open ADE at `http://127.0.0.1:3000`.

The default configuration binds services to loopback. `8283` is the Letta API,
`8284` is the Agent Platform API, and `8290` is the model router. Letta does not
ship a supported UI on `8083` in this stack.

Use `docker compose logs --tail=200 <service>` to investigate a service, and
`docker compose down` to stop the stack. `scripts/README.md` lists reset,
diagnostics, and other repository-wide utilities.

## Deterministic Verification

Install the locked development environment and run the checks that do not require
provider credentials or a running stack:

```text
uv sync --frozen --group dev
uv run ruff check agent_platform_api model_router ade_core evals scripts tests
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

The GitHub Actions workflow runs this deterministic suite on pull requests and
pushes to `main`, including all three first-party service image builds.

Provider probes, live E2E checks, browser smoke tests, and eval workflows are
operator-run checks because they need a configured stack, reachable models, or
credentials. Run them deliberately from their workflow documentation:

- `tests/checks/`: maintained API and ADE smoke checks.
- `evals/chat_memory_eval/`: chat memory evaluation.
- `evals/comment_persona_eval/`: Comment Lab persona evaluation.
- `evals/provider_model_probe/`: provider capability probing and allowlist refresh.

## Content And Configuration

- `config/model_router_sources.json`: portable model source defaults and module visibility.
- `config/model_router_sources.local.json`: ignored machine-local endpoint overrides when needed.
- `config/model_router_model_profiles.json`: model-specific sampling and capability metadata.
- `prompts/system_prompts/`: file-backed prompt templates.
- `schemas/label/`: file-backed Label Schema Center records.
- `agent_platform_api/seed_data/personas.jsonl`: reviewed persona seed source.

Runtime SQLite persona data belongs under `data/runtime/` and is not a reviewed
source artifact. The migration policy is recorded in
[ADR 0003](docs/adr/0003-persona-source-and-runtime-storage.md).

## Documentation

- [Operational manual](MANUAL.md): setup, recovery, and manual verification.
- [Codebase map](docs/codebase-map.md): where features and responsibilities live.
- [Development conventions](docs/development-conventions.md): structure, workflow, and decision-record rules.
- [Architecture decisions](docs/adr/): accepted directions and implementation status.
- [OpenAPI artifacts](docs/openapi/): English and curated Chinese API specifications.

## Local-Only Default

This repository is a local development stack, not a hardened public deployment.
Loopback bindings, role-based bearer authentication, narrow CORS, and server-only
browser credentials provide the local baseline described in
[ADR 0001](docs/adr/0001-local-only-access-boundary.md). Exposing the stack outside
the local machine still requires reviewed ingress, TLS, secret management, rate
limits, monitoring, and a deployment-specific threat review.
