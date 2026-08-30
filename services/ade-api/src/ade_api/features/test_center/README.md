# Test Center

## Purpose

Test Center launches bounded smoke and evaluation workflows, persists run state,
and exposes logs and artifacts to ADE Web. It does not implement the workflows;
those live under `workflows/` and use public ADE HTTP contracts.

## Ownership

- API routes: `api.py` under `/api/v2/test-center/`
- Request and artifact contracts: `contracts.py`
- Feature-facing run interface: `orchestrator.py`
- Persisted run manifests and restart recovery: `run_store.py`
- Subprocess lifecycle and cancellation: `process_executor.py`
- Bounded artifact discovery and content reads: `artifact_access.py`
- Run-type command definitions: `run_descriptors.py`
- Typed chat-memory evaluation artifact reads: `chat_memory_evaluations.py`
- Runtime data: `data/runtime/test-runs/`

## Request Flow

1. ADE Web submits a typed run request.
2. `run_descriptors.py` validates fields and builds the command.
3. `TestRunOrchestrator` delegates subprocess work to `process_executor.py` and
   durable status updates to `run_store.py`.
4. `artifact_access.py` exposes only files inside the run-owned output directory.

`agent_runtime_v3_acceptance` is the production-path qualification launcher. It
forwards an exact conversation/reviewer/retriever deployment set to the opt-in v3
workflow and exposes its raw evidence through the ordinary run-owned artifact view.
The workflow may propose promotion, but Test Center never edits the deployment
manifest.

Operators can select one or more canonical `case_keys` for focused v3 diagnostics.
Test Center rejects unknown or duplicate keys, emits the runner's repeated
`--case-key` arguments in canonical order, and forces a one-round no-llama command.
These focused runs are diagnostic-only and cannot be promotion eligible.

## Chat-memory evaluation reads

`GET /api/v2/test-center/chat-memory-evaluations` lists persisted
`chat_memory_eval` runs newest first. Active or incomplete runs remain visible
with `ready=false` and their stored launch options. Completed runs are `ready`
only when their scoped summary and JSONL artifacts validate together.
The read model fills omitted launch values with the chat-memory runner defaults;
the manifest still stores only the options the caller supplied.

`GET /api/v2/test-center/chat-memory-evaluations/{run_id}` returns the fixture,
per-round scores, turns, tool calls, and final persistent memory layers. Missing
or malformed artifacts return a clear conflict response rather than breaking the
list endpoint. New manifests persist request options; older manifests without
them remain readable.

## Tests

```bash
uv run python -m pytest services/ade-api/src/ade_api/features/test_center/tests -q
```
