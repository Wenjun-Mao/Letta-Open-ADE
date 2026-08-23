# Maintenance Roadmap

This roadmap records the remaining simplification work identified by the August
2026 repository audit. The current local stack is release-green; these are
maintainability improvements, not hidden release blockers.

Use [the codebase map](codebase-map.md) for current ownership and
[ADR 0005](adr/0005-incremental-feature-modularization.md) for the rule that
splits follow behavior boundaries rather than arbitrary line counts.

## Baseline Established

- `agent_platform_api` is the only ADE backend package and exposes an API-only
  surface.
- `model_router` is the only normal model discovery and provider-routing path.
- Browser requests use the same-origin frontend proxy; provider and API secrets
  stay server-side.
- Runtime state lives under ignored `data/runtime/`; reviewed seed/config content
  remains tracked.
- Backend catch-all facades and the frontend API monolith have been removed.
- CI now covers Python tests and lint, OpenAPI drift, frontend tests/lint/audit/build,
  Compose rendering, and all first-party image builds.
- Local container, API E2E, ADE smoke, and desktop/mobile browser checks are green.

## Next Priorities

### 1. Agent Studio Controller

`frontend-ade/app/agent-studio/page.tsx` still coordinates many independent
concerns even though presentation components, formatters, types, and memory-diff
logic are now local modules. Move state/effects into feature-local controllers or
hooks grouped by agent selection, creation settings, chat execution, and
inspection. Preserve request-identity and abort behavior with tests before each
slice moves.

### 2. Persona Persistence

`agent_platform_api/registries/persona_sqlite.py` currently owns schema setup,
CRUD/search, full-text indexing, seed synchronization, and record mapping. Split
the SQL store from seed projection policy and exchange/import behavior. Keep seed
hash and managed-key semantics explicit and transaction-tested so runtime-only
personas can never be removed by seed synchronization.

### 3. Generation Services

Comment and label services now share one OpenAI-compatible transport and explicit
retry contract, but request construction and response diagnostics remain dense.
Extract feature-local payload builders and response mappers. Do not move retry
ownership back into the router or add generic provider helpers without a second
real consumer.

### 4. Test Center

Replace branching in `agent_platform_api/testing/orchestrator.py` with a small
registry of run descriptors: validation model, command builder, and artifact
discoverer. Split the Test Center's chat-memory form and run/artifact viewer into
local components after the descriptor contract is stable.

### 5. Model Router Boundaries

Keep `model_router/catalog.py` focused on discovery and profile enrichment. Move
OpenAI HTTP forwarding from `model_router/app.py` into a transport module when the
next provider behavior is added. The router must continue to perform exactly one
upstream attempt per incoming generation request.

## Lower-Priority Cleanup

- Review the numbered Letta learning scripts and bundled MemGPT paper under
  `docs/`. If they are still useful, move them into a documented `examples/` or
  references area; otherwise replace them with authoritative links.
- Split the Chinese OpenAPI generator only when a behavior change requires it.
  Its size alone is not a reason to fragment a cohesive generation workflow.
- Track the upstream Letta provider-listing warnings and move to a newer pinned
  image only after compatibility checks pass.
- Move to ESLint 10 when the Next.js plugin dependency tree supports it. The
  current locked ESLint 9 setup is clean but receives an upstream support warning.

## Change Gates

For each slice, keep public routes and payloads stable unless an ADR explicitly
changes them. Run the focused tests first, then the deterministic checks in
`MANUAL.md`; run live E2E and browser checks for changes that touch runtime or UI
behavior. A split is complete only when the former owner loses a responsibility,
not when code is merely forwarded through another facade.
