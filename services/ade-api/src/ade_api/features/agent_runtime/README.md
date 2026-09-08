# Agent Runtime

This package owns the current Agent Studio `/api/v3` runtime. It uses ADE
PostgreSQL for state and Model Router for model and embedding access.

## Product Model

- An immutable **agent definition** snapshots prompt, persona, deployment,
  curated tools, and runtime policy.
- A **memory subject** owns typed durable facts and revisions.
- A **conversation** binds one definition to one subject and retains immutable
  messages plus replaceable, versioned summaries.
- A **run** records one asynchronous turn, attempts, cancellation, and normalized
  events.

The runtime accepts typed, source-bound memory proposals only. Corrections
supersede prior values; forgetting creates an auditable tombstone. Model-provided
arguments cannot choose another subject.

## Module Boundaries

- `agent_studio_api.py` exposes Agent Studio sessions and state.
- `api.py` exposes turns, runs, events, cancellation, and worker health.
- `application.py` and the narrow service modules own runtime behavior.
- `turn_execution.py` assembles context and coordinates model, retrieval, and
  memory-review work for one ADE-owned attempt.
- `worker.py` and `worker_*` own leases, cancellation, events, and finalization.
- `memory_policy.py` validates proposals; `persistence/` owns SQLAlchemy Core
  repositories and Alembic remains the only schema creation path.
- `evaluation_sessions.py` provisions and cleans isolated `purpose=evaluation`
  resources for maintained workflows.

## Tool Boundary

Release Agent Studio exposes curated product tools only, currently including
subject-bound memory search. Deterministic weather and failure tools live in the
evaluation-only registry. Arbitrary tool authoring and execution are out of scope.

## Release Boundary

The release ledger binds the exact runtime and worker identities, policies,
model aliases, agent bundle, qualification, conformance, and approval. A change
to governed runtime inputs requires new evidence. See
[ADR 0019](../../../../../../docs/adr/0019-ade-steady-state-runtime.md) and the
[release evidence guide](../../../../../../docs/operations/agent-studio-release.md).

## Tests

```text
uv run python -m pytest services/ade-api/tests/agent_runtime -q
```
