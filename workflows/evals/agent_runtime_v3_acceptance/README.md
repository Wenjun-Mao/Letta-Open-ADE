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

Build the native runtime through `make native-runtime-up` (or
`make eval-agent-runtime-v3`) so Compose records the exact Git revision and
clean/dirty state in the API and worker images. A direct `docker compose up`
uses fail-closed `unknown`/dirty provenance defaults and therefore cannot emit a
promotion proposal.

Set `AGENT_RUNTIME_V3_ACCEPTANCE_API_KEY` and
`AGENT_RUNTIME_V3_ACCEPTANCE_DATABASE_URL` before a host-side live run. Inside
the ADE API container, the runner safely falls back to `ADE_API_OPERATOR_KEY` or
`ADE_API_ADMIN_KEY` and `ADE_API_DATABASE_URL`, so Test Center does not need a
second credential set. The database URL is required: cleanup writes a recovery
manifest before executing one scoped transaction and fails closed on ambiguity.

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

Only the canonical `3` rounds, `180` second timeout, and zero-retry run can emit
a proposal. Every round keeps raw SSE JSONL plus normalized turns, attempt counts,
tool outcomes, and final facts beside its content-addressed summary. Provenance
binds the image source revision, clean-build state, shared contract version,
production policy hashes, exact role deployments, and effective config.

A failed primary round is completed and written in full, then later primary
rounds are skipped because three consecutive passes are no longer possible in
that run. The requested llama compatibility round remains diagnostic and still
runs.

Test Center cancellation sends `SIGTERM`; the CLI converts that signal into a
controlled unwind, requests cancellation for any accepted v3 run, waits for its
terminal state, and then executes the same scoped PostgreSQL cleanup transaction.

## Review And Promotion

Test Center and the acceptance runner never edit the deployment manifest. Review
an eligible proposal first, then perform a separate explicit apply only after the
check succeeds:

```bash
uv run python -m workflows.evals.agent_runtime_v3_acceptance.promote \
  --proposal workflows/evals/agent_runtime_v3_acceptance/outputs/<run-id>/promotion-proposal-<sha>.json \
  --check

uv run python -m workflows.evals.agent_runtime_v3_acceptance.promote \
  --proposal workflows/evals/agent_runtime_v3_acceptance/outputs/<run-id>/promotion-proposal-<sha>.json \
  --apply
```

Both modes revalidate the clean source revision, current path-bound policy hashes,
three round and event digests, the exact current case matrix, raw event coverage,
zero-retry attempt counts, deployment aliases and fingerprints, and all
conversation/reviewer/retriever role gates. They independently reconstruct and
re-score every normalized case observation. `--apply` updates the two bound DGX
manifest entries atomically; it does not approve a production cutover or enable v3
in the ordinary stack.
