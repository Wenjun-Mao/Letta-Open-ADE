# Project Guidelines

## Architecture

- The browser calls the Next.js same-origin `/api/v1/...` proxy, which injects a
  server-only Agent Platform credential.
- `agent_platform_api` owns ADE HTTP contracts and feature orchestration.
- `model_router` is the canonical provider discovery and generation boundary.
- Persistent Agent Studio calls flow through Letta; stateless Comment and Label
  calls go from Agent Platform API to the router.
- Do not add direct provider traversal, browser-visible secrets, or a second model
  source configuration.

## Code Structure

- Use Python 3.12 and locked `uv` dependencies.
- Keep Pydantic contracts under `agent_platform_api/models/` and feature logic in
  cohesive services, registries, clients, or routers.
- Keep frontend feature modules under `apps/ade-web/app/<feature>/` and API clients
  under `apps/ade-web/lib/api/`.
- Keep workflow-specific runner, config, fixtures, docs, and ignored outputs
  together under `workflows/evals/<workflow>/`.
- Do not create generic `utils` or compatibility facades. Split a module only when
  its current owner actually loses a responsibility.

## Runtime Contracts

- The model router performs one upstream attempt per generation request. Feature
  services own explicit request-scoped retry behavior.
- Letta clients disable implicit SDK retries unless the incoming Agent Studio
  request explicitly asks for retries.
- Reviewed persona seeds live at `agent_platform_api/seed_data/personas.jsonl`;
  generated runtime state lives under ignored `data/runtime/`.
- Keep public `/api/v1/...` routes stable unless an ADR intentionally changes a
  contract.

## Verification

Use the deterministic commands in `MANUAL.md`. The baseline includes:

- `uv sync --frozen --group dev`
- `uv run ruff check agent_platform_api model_router ade_core evals scripts tests`
- `uv run python scripts/check_python_format.py --base origin/main`
- `uv run python -m pytest`
- OpenAPI drift and Chinese artifact checks
- frontend tests, zero-warning lint, dependency audit, and production build
- Compose rendering and first-party image builds

Provider probes, evals, live E2E, and browser smoke checks remain explicit
operator-run gates when a change touches their behavior.

## References

- `README.md`: onboarding and runtime overview
- `MANUAL.md`: operational runbook and complete verification commands
- `docs/codebase-map.md`: ownership and common change locations
- `docs/maintenance-roadmap.md`: completed cleanup record and future extraction triggers
- `docs/adr/`: durable architecture decisions
- `scripts/README.md` and `tests/README.md`: maintained utilities and checks
