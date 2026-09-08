# Test Center

Test Center launches maintained workflows, persists run state, and exposes
rooted artifacts to ADE Web. It does not implement workflow behavior; every
workflow remains self-contained under `workflows/` and consumes public ADE APIs.

## Supported Workflows

1. **Behavior evaluation**: `chat_memory_eval` records deterministic chat,
   memory, tool, and advisory-judge evidence.
2. **Agent runtime qualification**: `agent_runtime_acceptance` records release
   evidence for the native runtime. Focused cases are diagnostic-only.
3. **Current-stack smoke**: `ade_api_e2e_check` verifies the running product
   stack.

## Boundaries

- `contracts.py` uses discriminated run requests; fields belonging to one
  workflow cannot be applied to another.
- `run_descriptors.py` is the sole command-definition and run-options authority.
- `orchestrator.py` owns process lifecycle, cancellation, persisted manifests,
  and restart recovery.
- Artifact access is rooted to each run directory through `TestRunDescriptor`.
  No endpoint may read an arbitrary path.

Test Center never edits model configuration, promotion state, or runtime data
directly. Evaluation sessions isolate the resources a workflow may create and
provide idempotent cleanup.

## Tests

```text
uv run python -m pytest services/ade-api/src/ade_api/features/test_center/tests -q
```
