# Project Guidelines

## Architecture

- ADE Web (`apps/ade-web/`) calls its same-origin `/api/v2/...` proxy. The proxy
  injects a server-only ADE API credential.
- ADE API (`services/ade-api/`) owns product HTTP contracts and feature
  orchestration.
- Model Router (`services/model-router/`) is the canonical provider discovery,
  model-profile, and generation boundary.
- Agent Studio uses Letta for persistent agents. Comment Lab and Label Lab use
  Model Router through ADE API.
- Do not add direct provider traversal, browser-visible credentials, or a second
  model-source configuration.

## Structure

- Use Python 3.12 and locked `uv` dependencies.
- Keep backend behavior in `services/ade-api/src/ade_api/features/<feature>/`.
  `platform/` owns composition/auth/settings; `integrations/` owns Letta and
  Model Router protocol adapters.
- Keep web routes thin in `apps/ade-web/src/app/`; keep feature UI, state, API
  clients, and tests in `apps/ade-web/src/features/<feature>/`.
- Keep only stable cross-service contracts in
  `packages/model-catalog-contracts/`. Do not create a generic shared package.
- Keep reviewed prompts, personas, schemas, tools, and model reports in
  `content/`; configuration belongs in `config/model-router/`.
- Keep eval/probe runner, config, fixtures, docs, artifacts, and tests together
  in `workflows/evals/<workflow>/`. Keep live smoke checks in `workflows/smoke/`.
- Do not create generic `utils`, compatibility aliases, or duplicate feature
  implementations. Remove replaced code after a verified vertical slice.

## Runtime Contracts

- Model Router performs one upstream attempt per generation request. Features own
  explicit request-scoped retry behavior.
- Letta clients disable implicit SDK retries unless an Agent Studio request
  explicitly asks for retries.
- Reviewed persona seeds live at `content/personas/personas.jsonl`; generated
  state lives under ignored `data/runtime/`.
- Public ADE API routes use `/api/v2/...`. Model Router retains its
  OpenAI-compatible `/v1/...` surface.
- ADE Web and ADE API expose host ports `3000` and `8000`; Model Router and Letta
  remain Compose-network services.

## Verification

Use the deterministic commands in `MANUAL.md`. The baseline includes:

- `uv sync --all-packages --frozen --group dev`
- `uv run ruff check services packages workflows scripts tests`
- `uv run python scripts/check_python_format.py --base origin/main`
- `uv run python -m pytest`
- OpenAPI drift and Chinese artifact checks
- ADE Web tests, zero-warning lint, dependency audit, and production build
- Compose rendering and all first-party image builds

Provider probes, evals, live E2E, and browser smoke checks remain explicit
operator-run gates when a change touches their behavior.

## References

- `README.md`: onboarding and runtime overview
- `MANUAL.md`: operations and verification commands
- `docs/reading-guide.md`: concise maintainer tour
- `docs/codebase-map.md`: ownership and common change locations
- `docs/architecture/`: system boundaries and request flows
- `docs/adr/`: durable architecture decisions
- `scripts/README.md` and `tests/README.md`: utility and verification entrypoints
