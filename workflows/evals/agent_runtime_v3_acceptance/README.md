# Agent Runtime v3 Acceptance

This workflow is a black-box client of the authenticated `/api/v3` runtime. It
creates isolated definitions, subjects, and conversations, executes the full
canonical matrix through REST/SSE, records content-addressed round evidence,
and performs scoped PostgreSQL cleanup.

It never edits `config/model-router/deployment-manifest.json`. A promotion
proposal is emitted only after exactly three complete, passing `live-api`
primary rounds with identical deployment fingerprints. The optional llama pass
is recorded as compatibility evidence and is never promotion-eligible.

## Run

Set `AGENT_RUNTIME_V3_ACCEPTANCE_API_KEY` and
`AGENT_RUNTIME_V3_ACCEPTANCE_DATABASE_URL` before starting a live run. The
database URL is required: resource cleanup is fail-closed and writes a recovery
manifest before it executes a single scoped transaction.

```bash
uv run --project workflows python workflows/evals/agent_runtime_v3_acceptance/run.py \
  --config workflows/evals/agent_runtime_v3_acceptance/config.toml \
  --output-dir workflows/evals/agent_runtime_v3_acceptance/outputs \
  --conversation-model-key dgx_vllm::qwen3.6-35b-a3b-fp8 \
  --reviewer-model-key dgx_vllm::qwen3.6-35b-a3b-fp8 \
  --embedding-model-key dgx_embedding_sidecar::qwen3-embedding-0.6b \
  --rounds 3 \
  --timeout-seconds 180 \
  --retry-count 0 \
  --include-llama-compatibility
```

The runner also accepts `--no-include-llama-compatibility`. Focused,
fake-transport, incomplete, or non-primary rounds remain diagnostic artifacts
and cannot generate a proposal.
