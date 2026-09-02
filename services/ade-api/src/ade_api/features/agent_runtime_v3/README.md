# Agent Runtime v3 Preview

This feature is the disabled-by-default ADE-owned conversational runtime. It is
independent from the Letta-backed Agent Studio v2 path and has no compatibility or
dual-write behavior.

## Boundaries

- `api.py` owns the focused `/api/v3` resource and SSE contracts.
- `application.py` is a thin facade over `definition_service.py`,
  `preview_session_service.py`, `resource_service.py`, and `run_service.py`;
  `database_boundary.py` centralizes
  readiness, workspace isolation, and repository error translation.
- `turn_execution.py` assembles context and coordinates the conversation executor,
  required memory reviewer, and semantic retrieval for one attempt.
- `worker.py` coordinates work. `worker_claims.py`, `worker_control.py`,
  `worker_finalization.py`, and `worker_events.py` separately own recovery,
  timeout/cancellation/leases, atomic terminal commits, and normalized traces.
- `provider_tracing.py` records safe request-level evidence for failed or cancelled
  attempts; `worker_health.py` and `persistence/workers.py` own boot-scoped worker
  presence independently of conversation leases.
- `memory_review.py` defines the closed operation schema; `memory_policy.py` binds
  proposals to the current subject, evidence, entities, and optimistic versions.
- `persistence/` contains SQLAlchemy Core tables and repositories; Alembic is the only
  schema creation path. `metadata.py` intentionally keeps the reviewed relational
  graph together while repositories remain split by domain.
- `executor.py`, `reviewer.py`, and `fact_registry.py` contain the model/tool loop,
  dedicated review protocol, and allowed durable-fact vocabulary. `tool_policy.py`
  resolves versioned explicit external-action requirements independently of model
  inference and evaluation expectations.

The conversation model may call only its definition-selected curated tools:
subject-bound `search_memory` and the deterministic preview `get_weather` fixture.
Available tools remain discretionary unless the current request unambiguously
matches the versioned explicit-action policy. A required action uses exact named
function selection and fails closed without a hidden repair if the model returns
final text, another tool, or malformed arguments. Tool results, including typed
failures, are authoritative and requirement events contain no user text. Evaluation
availability and expected observations are separate fields. See
[ADR 0014](../../../../../../docs/adr/0014-curated-tool-invocation-and-external-source-authority.md).
The model cannot write memory or select a subject. A separate reviewer proposes closed
typed operations bound to user-authored evidence. ADE generates a contiguous-prefix
summary before context assembly when more than 64 messages are unsummarized or
their estimated size exceeds the recent-history budget. It retains up to the newest
10 raw messages only when they fit; every older unsummarized message must be covered
by the new summary, and an over-budget compaction fails closed. The narrative summary
is a lossy derivative: exact completed-turn counts are derived from user messages
whose run has a committed assistant reply, while summary boundaries come directly
from immutable history. ADE injects both as authoritative history metadata.
ADE atomically commits the summary's source links, model/request identity,
policy/content/input hashes, assistant response, and memory revisions together.

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
make native-runtime-lane-check # prove the selected Compose dependency graph is native-only
make native-runtime-preview-gate # require exact promoted role/policy identities
make native-runtime-preview-up # release-mode native lane + gated ADE Web preview
```

The migration target rebuilds its image before applying Alembic, so a newly checked-
in migration cannot be skipped by a stale local container image.

Development mode permits fingerprinted but unqualified local deployments and marks
every run `unqualified`. Release mode rejects them. ADE Web has a separate,
build-gated `/native-runtime-preview` pilot; it is never an Agent Studio mode and its
navigation cannot be enabled by the release Make target until the exact role and
policy qualification gate passes. The preview has no legacy importer, dual-write
path, arbitrary Python tools, or production-cutover approval. Its atomic
`POST /api/v3/preview-sessions` operation fixes the pilot tool scope to
subject-bound `search_memory` and creates the definition, subject, and conversation
in one transaction. See [ADR 0013](../../../../../../docs/adr/0013-narrow-native-runtime-product-pilot.md).

### Native-only Compose lane

`make native-runtime-up` targets the profile-gated `ade-native-api` service, not
the normal `ade-api` service. It binds `127.0.0.1:${ADE_NATIVE_API_PORT:-8002}` and
runs `ade_api.native_main:app`. Its transitive Compose dependencies are
only PostgreSQL, Model Router, the one-shot migration service, and
`ade-runtime-worker`; it does not start or initialize Letta or Redis. The legacy
`ade-api` process does not mount `/api/v3`, and ADE Web has no Compose dependency on
that service in the native preview lane.

`GET /health` is an unauthenticated container-liveness probe only. All `/api/v3`
operations, including the readiness check below, retain the configured operator
authentication. `/api/v3/worker-health` is the actual readiness gate, so a healthy
container alone never means the runtime may accept a preview session or evaluation.
`make native-runtime-lane-check` resolves the Compose configuration and fails if
that service's dependency graph changes to include Letta or Redis.

`GET /api/v3/worker-health` returns `200` only when PostgreSQL is ready and a fresh,
compatible worker with the same revision, dirty state, and exact Git-visible source
fingerprint is visible; otherwise it returns the same typed body with `503`. Unknown
source identity fails closed. A draining worker finishes at most one active attempt
within Compose's 650-second grace period and never starts another retry. Provider
failures persist only bounded stage/status/retry metadata,
never prompts, inputs, response bodies, headers, or exception text. Completed chat
requests in a failed attempt additionally retain only allowlisted envelope states,
capped choice/tool counts, bounded token usage, and a normalized finish reason.
Local validation failures add a stable detail code, and acceptance normalization
preserves that code with the run ID and last provider stage so cleanup does not erase
the causal category. See
[ADR 0011](../../../../../../docs/adr/0011-agent-runtime-operational-readiness.md).
Disposable live checks must purge the definitions, subjects, conversations, runs,
messages, and memories they create.

### Release identity

Release mode is deliberately narrower than development mode. The preview accepts
only the aliases, prompt, persona, and tool set named in `release_policy.py`. Those
constants and the executable runtime, migration, Compose, prompt, tool, schema, and
retrieval inputs form four content-addressed policy bundles. Definition creation and
every turn compare the promoted deployment fingerprints against the current bundle
hashes. The preview gate also requires a clean, known Git-visible source identity.
Changing release behavior therefore requires a fresh qualification and reviewed
promotion; changing an unrelated committed document does not.
