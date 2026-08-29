# Agent Runtime v3 Preview

This feature is the disabled-by-default ADE-owned conversational runtime. It is
independent from the Letta-backed Agent Studio v2 path and has no compatibility or
dual-write behavior.

## Boundaries

- `api.py` owns the focused `/api/v3` resource and SSE contracts.
- `application.py` is a thin facade over `definition_service.py`,
  `resource_service.py`, and `run_service.py`; `database_boundary.py` centralizes
  readiness, workspace isolation, and repository error translation.
- `turn_execution.py` assembles context and coordinates the conversation executor,
  required memory reviewer, and semantic retrieval for one attempt.
- `worker.py` coordinates work. `worker_claims.py`, `worker_control.py`,
  `worker_finalization.py`, and `worker_events.py` separately own recovery,
  timeout/cancellation/leases, atomic terminal commits, and normalized traces.
- `memory_review.py` defines the closed operation schema; `memory_policy.py` binds
  proposals to the current subject, evidence, entities, and optimistic versions.
- `persistence/` contains SQLAlchemy Core tables and repositories; Alembic is the only
  schema creation path. `metadata.py` intentionally keeps the reviewed relational
  graph together while repositories remain split by domain.
- `executor.py`, `reviewer.py`, and `fact_registry.py` contain the model/tool loop,
  dedicated review protocol, and allowed durable-fact vocabulary.

The conversation model may call only `search_memory`. It cannot write memory or
select a subject. A separate reviewer proposes closed typed operations bound to
user-authored evidence, and ADE commits a successful assistant response and memory
revisions together.

## Local Preview

Run `make native-runtime-up` after setting the ADE database password and selecting
qualified Router deployments, or explicitly use development mode for unqualified
local experiments. Development runs remain marked `unqualified` in persisted state
and events.

The normal Compose stack leaves this feature disabled. Database administrator
credentials are available only to the one-shot migration service; ADE API and the
worker use the least-privilege application role.

```text
make native-runtime-migrate   # bootstrap roles/database and apply Alembic
make native-runtime-db-test   # run repository contracts as the application role
make native-runtime-up        # development-mode API + worker preview
```

Development mode permits fingerprinted but unqualified local deployments and marks
every run `unqualified`. Release mode rejects them. The preview has no ADE Web UI,
legacy importer, dual-write path, arbitrary Python tools, or production-cutover
approval. Disposable live checks must purge the definitions, subjects,
conversations, runs, messages, and memories they create.
