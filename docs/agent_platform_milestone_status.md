# Agent Platform ADE Milestone Tracker

Updated: 2026-04-13

## Milestone Objective

Deliver a production-ready Agent Platform backbone for a new ADE frontend while keeping the current dev_ui frontend as fallback, and prepare OpenAPI-driven Mintlify docs.

## Locked Decisions

- API name remains Agent Platform API.
- Keep current dev_ui frontend as fallback.
- Build new ADE frontend as a separate Next.js + TypeScript app.
- Tool discovery is included in ADE MVP.
- MVP auth posture is internal network boundary only (no new auth layer in MVP).
- Cutover gate is backend E2E green plus ADE smoke suite green.
- Mintlify config format is docs.json.
- Mintlify API reference source is a committed OpenAPI artifact.

## Scope Checklist

### Backend Foundation

- [x] Capability baseline and strict capability guard.
- [x] Shared backend domain layer for runtime/control operations.
- [x] Agent Platform runtime and control endpoints.
- [x] Orchestrated test-run endpoints.
- [x] Platform API E2E check.
- [x] Legacy route bridge completion for all targeted endpoints.
- [x] Feature-flag rollout and rollback behavior finalized.

### ADE Support APIs

- [x] Tool catalog discovery endpoint (MVP).
- [x] Prompt and persona metadata endpoint (MVP).
- [x] Test-run artifact listing and artifact content endpoints.
- [ ] Tool test invocation endpoint (phase-2).
- [ ] Prompt/persona revision history endpoint (phase-2).

### Frontend

- [x] Separate Next.js + TypeScript ADE app scaffold.
- [x] Agent Studio MVP.
- [x] Prompt and Persona Lab MVP.
- [x] Toolbench MVP (discovery + attach/detach).
- [x] Test Center MVP.
- [x] API Docs entry in ADE UI.

### Docs and OpenAPI

- [x] FastAPI metadata and endpoint docs quality pass.
- [x] Deterministic OpenAPI export workflow.
- [x] Committed canonical OpenAPI artifact.
- [x] docs.json Mintlify config and navigation.
- [x] CI checks for OpenAPI validity and drift.

### Verification and Rollout

- [x] Full backend Docker E2E baseline is green in latest cycle.
- [x] ADE smoke E2E suite implemented and green.
- [x] Dual-run acceptance gate passed.

## Current Implementation Delta (This Pass)

- Added migration status endpoint: GET /api/platform/migration-status.
- Added tool discovery endpoint: GET /api/platform/tools.
- Added prompt/persona metadata endpoint: GET /api/platform/metadata/prompts-personas.
- Added run artifact endpoints:
  - GET /api/platform/test-runs/{run_id}/artifacts
  - GET /api/platform/test-runs/{run_id}/artifacts/{artifact_id}
- Added feature-flag gating for legacy and platform routes.
- Bridged full legacy chat route through AgentPlatformService shared messaging path.
- Added deterministic OpenAPI export script and committed OpenAPI artifact.
- Added Mintlify docs.json configuration and overview pages in docs.
- Added OpenAPI/docs CI validation workflow.
- Added separate Next.js ADE frontend scaffold and compose profile service (`ade_frontend`).
- Implemented functional ADE MVP pages for Agent Studio, Prompt and Persona Lab, Toolbench, Test Center, and live dashboard status.
- Added frontend build validation (`npm run build`) to implementation verification.
- Added ADE MVP smoke E2E check script (`tests/checks/ade_mvp_smoke_e2e_check.py`).
- Added migration flag rollout check script (`tests/checks/migration_flag_rollout_check.py`).
- Added combined dual-run cutover gate (`tests/checks/platform_dual_run_gate.py`).
- Extended orchestrator/Test Center run types to include ADE smoke, flag rollout, and dual-run gate checks.

## Feature Flags

- AGENT_PLATFORM_API_ENABLED (default: 1)
- AGENT_PLATFORM_LEGACY_API_ENABLED (default: 1)
- AGENT_PLATFORM_MIGRATION_MODE (legacy|dual|ade, default: dual)
- AGENT_PLATFORM_STRICT_CAPABILITIES (default: off)

## Immediate Next Tasks

1. Implement tool test invocation endpoint and Toolbench phase-2 UI.
2. Add prompt/persona revision history backend API and UI timeline.
3. Add richer ADE artifact browsing (download/filters) as post-MVP polish.
