# ADE Steady-State Simplification And Letta Removal

Status: Approved

## Outcome

Complete the ADE-native runtime transition and leave one comprehensible,
steady-state product stack. The public `/api/v3` runtime contract remains
stable, while Letta, Redis, rollback/parity scaffolding, duplicate services,
and migration-era internal naming are removed.

## Scope

- Consolidate product and native APIs into one `ade-api` process.
- Keep only PostgreSQL, Model Router, migration job, runtime worker, ADE API,
  and ADE web in Compose.
- Make canonical Model Router keys the only model identity.
- Keep native runtime conversations, immutable messages, typed/versioned
  memory, run events, leases, cancellation, and ADE-owned retries.
- Preserve `/api/v3/agent-studio/*`; remove the Letta-backed v2 surface and
  generic public runtime provisioning CRUD.
- Use isolated evaluation-session endpoints for Test Center workflows.
- Retain Chat Memory Eval, native runtime qualification, and current-stack
  smoke; remove parity, rollback, and executable historical-study workflows.
- Reduce Test Center to behavior evaluation, native qualification, and
  current-stack smoke with one canonical options contract.
- Replace cutover evidence with schema-v3 steady-state release evidence bound
  to runtime source, API/worker identity, policies, model routes, and an
  approved deployment manifest.
- Update current-system documentation and record the architecture in ADR 0019.

## Non-Goals

- No legacy Letta-data importer or compatibility aliases.
- No arbitrary user-authored tool execution or replacement sandbox worker.
- No Redis retention without a demonstrated native-runtime requirement.
- No project-wide rename beyond the runtime and service terminology in scope.
- No weakening of subject isolation, memory provenance, retry ownership,
  cancellation, or artifact-path security.

## Consequential Decisions

- PostgreSQL is the ADE state authority and historical Letta data remains
  dormant rather than migrated.
- Production Agent Studio exposes curated tools only; deterministic weather
  and failure tools are evaluation-only.
- Existing ADE runtime data must survive the migration non-destructively.
- DGX Qwen is the primary qualification route and `qwen3527b` is the required
  llama-server compatibility route; underlying model artifacts are recorded in
  release evidence rather than hard-coded as permanent product assumptions.
- SDK/framework retries remain disabled. `retry_count` means additional
  ADE-owned attempts.
- Deployment rollback plus PostgreSQL backup/restore replaces Letta rollback.
- Simplicity and cognitive reduction take precedence over transitional
  compatibility or speculative configurability.

## Delivery Checkpoints

1. Consolidate services, runtime modules, persistence ownership, and APIs.
2. Simplify Test Center, evaluations, model identity, and frontend state.
3. Establish steady-state release evidence, promotion, and documentation.
4. Verify focused and full test suites, Ruff, OpenAPI, frontend, Compose, and
   image builds.
5. Verify migrations against both the existing PostgreSQL store and a fresh
   pgvector volume.
6. Run live current-stack smoke, three DGX qualification rounds, llama-server
   compatibility, deterministic conformance, and Chat Memory Eval.
7. Promote one schema-v3 release ledger from the exact implementation revision.
8. Start the reduced release stack and manually accept all retained product
   surfaces in the built-in browser.
9. Fast-forward the completed implementation to `main`, push, and remove the
   implementation branch and clean worktree.

## Acceptance Evidence

- Only the six intended Compose services remain; no Letta, Redis, or native API
  sidecar container exists.
- Existing and fresh PostgreSQL migrations reach the current schema without
  data loss.
- Removed Agent Studio v2, Tool Center, parity, and generic provisioning routes
  return `404`.
- Focused tests, full Python tests, Ruff, OpenAPI drift and terminology checks,
  frontend tests/lint/build, Compose rendering, and image builds pass.
- Current-stack smoke, three-round DGX qualification, llama compatibility,
  conformance, and Chat Memory Eval pass with zero hidden retries.
- Release promotion produces valid schema-v3 evidence for one clean revision,
  matching API/worker identities, policy hashes, model routes, and manifest.
- Built-in browser verification covers Agent Studio memory/persona settings,
  Comment Lab, Label Lab, Prompt Center, Schema Center, Model Catalog, and the
  reduced Test Center.
- Final `main` is pushed and temporary implementation branches/worktrees are
  removed safely.

## Execution Authority

The coordinator may inspect and modify this repository, run local tests and
Compose workflows, use the configured DGX and llama-server endpoints, rebuild
containers, promote release evidence after all gates pass, commit changes,
fast-forward or merge the completed branch to `main`, push `main`, and perform
non-force cleanup of clean implementation branches/worktrees.

## Escalation Conditions

Pause and report rather than weakening a gate if any of these occur:

- Existing PostgreSQL data cannot be preserved.
- A live provider fails repeatedly after its endpoint is confirmed healthy.
- Required memory correctness, subject isolation, exact retries/timeouts,
  cancellation, tool correctness, or trace preservation regresses.
- Release evidence cannot be bound to one clean source revision and matching
  API/worker identity.
- Cleanup encounters a dirty or otherwise unowned worktree/branch.
- Completing the work requires expanding a non-goal or changing a public
  contract beyond the approved scope.
