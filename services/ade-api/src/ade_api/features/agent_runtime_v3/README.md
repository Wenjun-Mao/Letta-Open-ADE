# ADE-Native Agent Runtime

This package owns Agent Studio's `/api/v3` runtime. It is deliberately isolated
from the retained Letta-backed `/api/v2` service graph: it uses PostgreSQL and
Model Router, does not use Redis, and has no importer, dual-write path, or
per-request fallback to Letta.

## Domain Map

- `agent_studio_api.py` exposes the product-level definitions, subjects,
  sessions, state, and reset operations.
- `api.py` exposes lower-level conversations, turns, runs, events, and health.
- `agent_studio_sessions.py`, `definition_service.py`, `resource_service.py`, and
  `run_service.py` own application behavior; `application.py` is their thin
  facade.
- `agent_studio_reset.py` owns the admin-only, purpose-scoped fresh-start
  boundary and its durable idempotency receipt.
- `database_boundary.py` centralizes readiness, workspace isolation, and
  repository error translation.
- `turn_execution.py` assembles context and coordinates the conversation model,
  required memory reviewer, semantic retrieval, and one ADE-owned attempt.
- `worker.py` coordinates work. The `worker_*` modules separately own claims,
  cancellation and leases, event recording, finalization, and health.
- `memory_review.py` defines the closed operation schema; `memory_policy.py`
  validates subject-bound, evidence-backed, optimistic memory proposals.
- `persistence/` contains SQLAlchemy Core tables and repositories. Alembic is the
  only schema creation path.

Agent definitions bind immutable prompt, persona, deployment, tool, and policy
snapshots. Memory subjects own durable typed facts and revisions. Conversations
own immutable history and summaries. Runs and normalized events explain each
execution without persisting private reasoning or provider response bodies.

The release product exposes only subject-bound `search_memory`. The deterministic
`get_weather` fixture remains available for development and qualification tests,
not release Agent Studio definitions. A separate reviewer proposes typed memory
operations; the conversation model cannot write memory or choose another subject.

## Running Locally

The supported Compose stack starts migration, native API, worker, and ADE Web by
default. It runs the native API and worker in release mode, which rejects unknown,
dirty, stale, or unqualified deployment identities.

```text
make up                         # supported stack, including native Agent Studio
make agent-studio-db-test       # real PostgreSQL repository and migration checks
make agent-studio-lane-check    # prove the native dependency boundary
make agent-studio-release-gate  # require the exact promoted release identities
make agent-studio-development-up # explicit unqualified local-development lane
```

Database administrator credentials are available only to the one-shot migration
service. The API and worker use the least-privilege application role. The
migration target rebuilds before applying Alembic so a new migration cannot be
skipped by a stale image.

`GET /health` is unauthenticated container liveness only. Authenticated
`GET /api/v3/worker-health` is the readiness authority: it succeeds only when
PostgreSQL is ready and a fresh worker has the same compatibility and source
identity as the API. A draining worker finishes at most one active attempt and
does not begin another retry.

## Release Identity

Release mode accepts only the aliases, prompt, persona, and tool set in
`release_policy.py`. Executable runtime, migration, Compose, content, schema, and
retrieval files are grouped into content-addressed policy bundles. Definition
creation and every turn compare promoted deployment fingerprints with those
current bundles and require a clean, known source identity.

Any change to a bound source, model deployment, prompt, tool, schema, or retrieval
policy invalidates qualification. Rebind and rerun qualification before promotion;
do not weaken release checks or switch to development mode to bypass that gate.
Product Agent Studio routes additionally fail closed until the reviewed cutover
ledger binds three-round qualification, paired Test Center evidence, deterministic
conformance, and rollback rehearsal. Generic v3 resources remain available in the
development lane so evidence can be collected without creating a fallback path.
See [ADR 0010](../../../../../../docs/adr/0010-production-path-runtime-qualification.md),
[ADR 0011](../../../../../../docs/adr/0011-agent-runtime-operational-readiness.md),
and [ADR 0016](../../../../../../docs/adr/0016-ade-native-agent-studio-cutover.md).
The exact operator sequence lives in the
[cutover runbook](../../../../../../docs/operations/agent-studio-cutover.md).

The persisted `preview` purpose is retained only to classify and clean up data
created by the superseded pilot. It is not a product mode or public route.
