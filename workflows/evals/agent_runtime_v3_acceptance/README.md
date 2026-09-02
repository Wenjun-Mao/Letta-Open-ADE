# Agent Runtime v3 Acceptance

This workflow is a black-box client of the authenticated `/api/v3` runtime. It
creates isolated definitions, subjects, and conversations, executes the full
canonical matrix through REST/SSE, records content-addressed round evidence,
and performs scoped PostgreSQL cleanup.

Before creating resources, the runner calls authenticated
`GET /api/v3/worker-health`. It writes `preflight.json` and stops immediately when
PostgreSQL, worker freshness, compatibility, or exact source-content matching is not
ready. Transport, authentication, and malformed responses also produce a safe failed
receipt. Preflight is diagnostic evidence and never counts as a round.

It never edits `config/model-router/deployment-manifest.json`. A promotion
proposal is emitted only after exactly three complete, passing `live-api`
primary rounds with identical deployment fingerprints. The optional llama pass
is recorded as compatibility evidence and is never promotion-eligible.

## Run

Build the native runtime through `make agent-studio-release-up` (or
`make eval-agent-runtime-v3`) so Compose records the exact Git revision, clean/dirty
state, and SHA-256 fingerprint of every Git-visible file in the native API and worker
images. The Make target runs this workflow inside the isolated `ade-native-api`
service against `http://ade-native-api:8000`; it never uses the normal v2 API
service. A direct `docker compose up` uses fail-closed `unknown` provenance defaults
and therefore cannot pass preflight.

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
  --embedding-model-key dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B \
  --rounds 3 \
  --timeout-seconds 180 \
  --retry-count 0 \
  --include-llama-compatibility
```

The runner also accepts `--no-include-llama-compatibility`. For a focused runtime
diagnostic, repeat `--case-key` in the canonical fixture order:

```bash
uv run python workflows/evals/agent_runtime_v3_acceptance/run.py \
  --case-key old_memory_deep_search \
  --case-key weather_tool_failure
```

A non-empty selection is always a single `live-api-diagnostic` round: it skips
llama compatibility and cannot create a promotion proposal, even if it happens to
list every canonical case. Focused, fake-transport, incomplete, or non-primary
rounds remain diagnostic artifacts and cannot generate a proposal.

When any path-bound runtime policy input changes, explicitly rebind the checked-in
deployment fingerprints before collecting new evidence:

```bash
make agent-studio-policy-rebind
```

Rebinding resets prior qualification rounds only for deployments whose policy
identity changed. It never silently carries evidence across a behavior change and
does not erase valid qualification when all four policy hashes are already current.

Only the canonical `3` rounds, `180` second timeout, and zero-retry run can emit
a proposal. Every round keeps raw SSE JSONL plus normalized turns, attempt counts,
tool outcomes, and final facts beside its content-addressed summary. Provenance
binds the image source revision, clean-build state, exact source fingerprint, shared contract version,
production policy hashes, exact role deployments, and effective config.
Accepted setup runs are written to the same evidence stream even when setup fails,
so scoped cleanup never erases the terminal trace needed to diagnose the failure.
Provenance and any proposal also bind the preflight digest. Provider request failure
or cancellation events are recorded as infrastructure failures and cannot contribute
behavioral score credit.

Canonical cases that declare a conversation summary cannot pass on dialogue
alone: the production path must emit `summary.committed` within the same accepted
turn as the assistant result, and the conversation state must still expose the
expected immutable raw-message count. The long-history count check also rejects
approximate answers such as “more than forty”; containing the expected numeral alone
is insufficient.

The shared fixture's `summary_through_sequence` is an in-memory study seeding hint,
not a required live compaction boundary. Live boundaries depend on the exact token
sizes of model responses. Promotion independently validates that at least one
positive, contiguous, fully provenanced `summary.committed` event exists while the
raw-history count remains complete.

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
the preflight digest/readiness/build identity, three round and event digests, the
exact current case matrix, raw event coverage,
zero-retry attempt counts, deployment aliases and fingerprints, and all
conversation/reviewer/retriever role gates. They independently reconstruct and
re-score every normalized case observation. `--apply` updates the two bound DGX
manifest entries atomically; it does not approve a production cutover or enable v3
in the ordinary stack.
