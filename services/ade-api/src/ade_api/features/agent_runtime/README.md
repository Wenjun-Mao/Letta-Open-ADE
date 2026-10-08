# Agent Runtime

This package owns the current Agent Studio `/api/v3` runtime. It uses ADE
PostgreSQL for state and Model Router for model and embedding access.

## Product Model

### Evaluation Version Creation

The opt-in development-only history-trial API exposes operator-authenticated
`POST /api/v3/history-trial/definitions/{root_id}/versions` using
`CreateAgentDefinitionRequest`. Supply the existing root/key and a positive
`expected_current_version`; only evaluation roots in the active workspace are
eligible. The response is the new immutable `AgentDefinitionResponse` (201).
The current version must itself satisfy the trial binding, checked under the
same workspace/root locks as allocation; unrelated evaluation roots cannot be
converted into the trial character.
Select its `id` when creating a subsequent trial session. Previous sessions retain
their original binding. Trial configuration/capacity/fingerprint guards remain
unchanged; stale or archived roots conflict (409), invalid requests return 422,
and inaccessible roots return 404. Session-created definitions remain version 1.
See ADR 0051; this does not qualify PC-11 behavior or authorize provider calls.

### Persistent Resources

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
- `GET /api/v3/conversations/{id}/activity` reads retained per-turn dispatch,
  tool, and context evidence with one conversation-scoped batch. It reports
  incomplete traces as observed lower bounds and leaves missing history
  unavailable. It does not estimate billing or prove which source caused a reply.
- `application.py` and the narrow service modules own runtime behavior.
- `turn_execution.py` assembles context and coordinates model, retrieval, and
  memory-review work for one ADE-owned attempt.
- `turn_result.py` owns the internal `AttemptResult` shared by execution and
  worker collaborators; consumers import it directly from this module.
- `executor.py` owns conversation generation and its finite curated-tool loop.
  `compaction_executor.py` dispatches the existing summary protocol using the
  conversation's deployment/adapter. Planning and provenance stay in
  `compaction.py`; eligibility and deadline policy stay in `turn_compaction.py`.
  `model_response.py` shares only response-envelope and integer-usage mechanics.
- `worker.py` and `worker_*` own leases, cancellation, events, and finalization.
- `memory_policy.py` validates proposals; `persistence/` owns SQLAlchemy Core
  repositories and Alembic remains the only schema creation path.
- `evaluation_sessions.py` provisions and cleans isolated `purpose=evaluation`
  resources for maintained workflows.

## Private Evaluation Capture

`ADE_NATURAL_MEMORY_CAPTURE=1` remains restricted to development, evaluation
purpose and isolated loopback test databases. Capture-v1 fields are unchanged;
the optional `private_observations` extension has named contract
`ade-private-evaluation-observations-v1` ([ADR 0053](../../../../../../docs/adr/0053-private-evaluation-observations.md)).
PC-11 requires it; historical workflows are not silently upgraded or rebound.

`turn_memory_snapshot.py` reads before-state in the accepted-generation RR
snapshot; `natural_evidence_readback.py` independently reads after-state and
terminal outcome in a new RR snapshot. `persistence/evaluation_observations.py`
owns full facts, entities (including orphans), revisions, source links,
predecessors and generation, run/attempt/scope/hash binding and bounded activity
checks. `history_observations.py` retains reader and selection omission reasons
without changing eligibility, ranking or prompts. Empty/not-read, unavailable
and truncated inventories never claim completeness. No new public history API.

Capture disabled means no extra SQL/provider calls. Observation SQL uses
savepoints; errors produce unavailable evidence, never a different run outcome.
Snapshots allow 512 rows per component and 600 KB; the full private artifact
retains the 2 MB cap. Missing or inconsistent observations stop PC-11 qualification.
Auth, provider wire bodies, private reasoning and raw exceptions remain excluded.
Artifacts stay under ignored workflow outputs; tests use temporary directories.

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
