# Letta Open ADE

Letta Open ADE is a local-first environment for building, tuning, and evaluating
agent experiences. It combines a browser workspace, a product API, a provider
router, and Letta's persistent-agent runtime. An opt-in ADE-owned `/api/v3`
runtime preview is implemented separately; it does not replace Agent Studio.

## Start Here

1. Create `.env` from `.env.example`, then replace placeholder secrets and
   enable only the model sources available on your machine.
2. Start the local stack:

```text
docker compose up -d --build
```

3. Open ADE Web at `http://127.0.0.1:3000`.
4. Check ADE API health at `http://127.0.0.1:8000/api/v2/health`.

Only ADE Web (`3000`) and ADE API (`8000`) are host-facing. Model Router,
Letta, PostgreSQL, and Redis communicate on the Compose network. Use
`docker compose ps` and `docker compose logs --tail=200 <service>` when a
service needs investigation.

## Repository Map

```text
apps/ade-web/                         # Next.js product UI
services/ade-api/                     # FastAPI product API
services/model-router/                # OpenAI-compatible provider boundary
packages/model-catalog-contracts/     # Small shared catalog/probe contracts
content/                              # Reviewed prompts, personas, schemas, tools, reports
config/model-router/                  # Model sources and model profiles
workflows/evals/                      # Repeatable evaluations and provider probes
workflows/smoke/                      # Live stack smoke checks
infra/                                # Container support assets
```

For current product and runtime authority, read the
[ADE System Status Map](docs/architecture/system-status.md). For the rationale
and dependency rules, read the [architecture overview](docs/architecture/overview.md).
For an end-to-end view of browser, API, Letta, router, and workflow calls, read
the [request flows](docs/architecture/request-flows.md). The
[codebase map](docs/codebase-map.md) is the practical "where do I change this?"
guide.

## Daily Commands

The root `Makefile` is the concise operator entrypoint:

```text
make setup                  # install locked Python and web dependencies
make up                     # build and start the stack
make status                 # show service health
make logs SERVICE=ade-api   # inspect a service
make smoke                  # run the API smoke workflow inside ade-api
make down                   # stop the stack without deleting data
```

## Verification

Run deterministic checks from the repository root:

```text
uv sync --all-packages --frozen --group dev
uv run ruff check services packages workflows scripts tests
uv run python -m pytest
uv run python scripts/export_openapi.py --check
uv run python scripts/generate_openapi_zh_manual.py
git diff --exit-code -- docs/openapi/ade-api-openapi-zh.json apps/ade-web/public/openapi/ade-api-openapi-zh.json docs/openapi/zh_openapi_missing_terms.json
npm ci --prefix apps/ade-web
npm --prefix apps/ade-web run test
npm --prefix apps/ade-web run lint
npm --prefix apps/ade-web run build
docker compose --env-file .env.example config --quiet
```

Live checks require a healthy stack and reachable providers. They are deliberate
operator workflows, not default pull-request checks:

```text
make smoke
make eval-chat-memory
make eval-comment-persona
make probe-models SOURCE=ark
```

The ADE-native Agent Studio runtime is part of the supported default stack. The
migration job, native API, and worker start with `make up`; the legacy v2 API,
Letta, and Redis remain available for the product areas not yet migrated.

```text
make agent-studio-migrate          # usually automatic with `make up`
make agent-studio-db-test          # opt-in PostgreSQL integration suite
make agent-studio-lane-check
make agent-studio-development-up   # unqualified development runs
make agent-studio-qualification    # canonical three-round release candidate run
make agent-studio-conformance      # exact retry/cancel/idempotency contracts
make agent-studio-release-gate     # revalidates promoted policy identity
make agent-studio-release-up       # runs the gate, then starts the supported stack
```

The development target marks runs as unqualified. The release gate requires exact
promoted conversation, reviewer, retriever, and current policy identities. See the
[`agent_runtime_v3` guide](services/ade-api/src/ade_api/features/agent_runtime_v3/README.md)
and [ADR 0016](docs/adr/0016-ade-native-agent-studio-cutover.md) for the cutover
contract. Use the
[cutover runbook](docs/operations/agent-studio-cutover.md) for the complete
promotion, paired-evidence, rollback-rehearsal, and activation sequence.

See [workflows/evals](workflows/evals/) for each evaluation's inputs, outputs,
and interpretation. See [workflows/smoke](workflows/smoke/) for live API and
ADE checks.

## Content And Configuration

- `content/prompts/system/`: reviewed system prompts by scenario.
- `content/personas/`: reviewed persona seed and reusable persona material.
- `content/label-schemas/`: Label Lab schema records.
- `content/custom-tools/`: managed custom-tool registry material.
- `content/model-catalog/`: reviewed provider probe reports and allowlists.
- `config/model-router/sources.json`: portable model-source configuration.
- `config/model-router/sources.local.json`: ignored machine-local source overlay.
- `config/model-router/model-profiles.json`: model capability and sampling profiles.

Runtime state belongs under ignored `data/runtime/`; it is not reviewed product
content. [ADR 0003](docs/adr/0003-persona-source-and-runtime-storage.md)
describes the persona source/projection boundary.

## Further Reading

- [Product roadmap](docs/product-roadmap.md): outcome-oriented Now/Next/Later direction and decision gates.
- [ADE System Status Map](docs/architecture/system-status.md): current product authority and native-runtime status at a glance.
- [Operational manual](MANUAL.md): lifecycle, recovery, and live verification.
- [Maintainer reading guide](docs/reading-guide.md): a short route into the codebase.
- [Development conventions](docs/development-conventions.md): feature, workflow, and ADR rules.
- [Architecture decisions](docs/adr/): durable system decisions.
- [OpenAPI artifacts](docs/openapi/): generated API specifications.

## Local-Only Default

This is a local development stack, not a hardened public deployment. Loopback
bindings, role-based bearer authentication, narrow CORS, and server-only web
credentials are the local baseline. Public exposure still requires reviewed
ingress, TLS, secret management, rate limits, monitoring, and a deployment
threat review. See [ADR 0001](docs/adr/0001-local-only-access-boundary.md).
