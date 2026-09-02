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

## Agent Runtime Product Parity

`agent_runtime_parity_eval` is the Milestone 4 product-comparison launcher. It
compares the Letta v2 and ADE-native v3 public APIs under the same fixture,
prompt, persona, paired DGX model selection, timeout, and zero-retry policy. It
is intentionally separate from `agent_runtime_v3_acceptance`: qualification
proves the native runtime's bounded contract, while parity measures the paired
operator outcome.

The launch form may select one to three rounds. Three rounds are evidence runs;
one or two rounds are diagnostic evidence only. Test Center always passes
`--retry-count 0` and rejects other values. It does not expose a mutable
decision action because the current append-only decision ledger is specific to
chat-memory candidate/baseline comparisons.

The descriptor forces workflow output beneath the run-owned Test Center output
directory and gives the evaluator an alphabetic `parity-<test-center-run-id>`
scope for its generated resource cleanup. API keys, database URL, and Compose
service URLs are injected only into the child process environment. They are not
included in the command, `run.json`, logs, or parity artifact read model.

`GET /api/v2/test-center/agent-runtime-parity-evaluations` lists product parity
runs. `GET /api/v2/test-center/agent-runtime-parity-evaluations/{run_id}`
returns evidence only after Test Center verifies the signed parity spec,
provenance, normalized turns, comparison, and summary form one coherent
content-addressed bundle. Incomplete or mismatched artifacts remain visible as
not ready in the list and return a conflict on detail reads.

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
