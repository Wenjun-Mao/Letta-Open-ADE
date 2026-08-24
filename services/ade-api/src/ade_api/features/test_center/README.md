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
- Runtime data: `data/runtime/test-runs/`

## Request Flow

1. ADE Web submits a typed run request.
2. `run_descriptors.py` validates fields and builds the command.
3. `TestRunOrchestrator` delegates subprocess work to `process_executor.py` and
   durable status updates to `run_store.py`.
4. `artifact_access.py` exposes only files inside the run-owned output directory.

## Tests

```bash
uv run python -m pytest services/ade-api/src/ade_api/features/test_center/tests -q
```
