# Agent Runtime Acceptance

This is the black-box qualification workflow for the current ADE Agent Runtime.
It uses the authenticated `/api/v3` contract, but all created resources are
evaluation-only sessions rather than public definitions, subjects, or
conversations.

For each fixture case, the runner creates the needed graph through
`POST /api/v3/evaluation-sessions`. When a case shares an agent definition or
memory subject across conversations, later sessions bind the IDs returned by
the first session. Initial facts are written through a separate no-tool
evaluation session for the same subject. The workflow observes messages and
typed facts through `GET /api/v3/evaluation-sessions/{conversation_id}/state`.

Every created conversation is recorded. On success, failure, or controlled
cancellation, the runner calls the idempotent
`DELETE /api/v3/evaluation-sessions/{conversation_id}` endpoint in reverse
creation order. The API retains shared evaluation resources until their last
conversation is purged, so this workflow never needs database credentials or
direct SQL cleanup.

## Run

Start the unified ADE API and runtime worker with matching clean-build identity,
then provide an operator API key:

```bash
AGENT_RUNTIME_ACCEPTANCE_API_KEY="$ADE_API_OPERATOR_KEY" \
uv run python workflows/evals/agent_runtime_acceptance/run.py \
  --config workflows/evals/agent_runtime_acceptance/config.toml \
  --output-dir workflows/evals/agent_runtime_acceptance/outputs
```

The selected candidate runs three primary DeepSeek conversation/reviewer and
Qwen retriever qualification rounds. Llama-server compatibility is optional
and disabled for this candidate; select it only when that route belongs to
the supported deployment contract. The runner records preflight evidence,
normalized SSE events, typed facts, tool outcomes, deployment snapshots, and
a promotion proposal. A focused `--case-key` run is diagnostic only: it runs
one round, skips compatibility, and cannot create a promotion proposal.

```bash
uv run python workflows/evals/agent_runtime_acceptance/run.py \
  --case-key old_memory_deep_search \
  --case-key weather_tool_failure
```

The primary qualification requires exactly three clean, passing full matrices,
zero requested retries, matching API/worker source identity, and consistent
deployment fingerprints. Provider errors, cancellations, malformed events, or
missing reviewer and memory evidence fail closed. Promotion review remains an
explicit separate step; this workflow only produces evidence.

The checked-in DeepSeek and Qwen manifest entries are candidates with zero
passing rounds, not approved release routes. If `QWEN_EMBEDDING_API_BASE`
changes the effective endpoint, rebind its manifest URL and deployment
fingerprint, prove vector-space compatibility with paired synthetic query and
document canaries, and run fresh qualification before promotion. Merely
changing the environment variable fails the Agent Runtime deployment binding.

Each round artifact includes a per-turn `chronology` diagnostic assembled from
the event log already collected here. It orders context/retrieval, generation,
reviewer proposals after validation, storage commits, and provider observations
by event sequence. An empty stage means unobserved or unnecessary, not
automatically failed. Validation has no independent event when a proposal is
rejected; inspect the run trace before assigning a cause.

`m3_profile_memory_diagnostic.json` is an opt-in chronological M3 case, kept
out of the canonical qualification matrix. When the native provider, reviewer,
and embedding routes are separately authorized, run it with
`--diagnostic-fixture workflows/evals/agent_runtime_acceptance/m3_profile_memory_diagnostic.json`.
This runs one diagnostic round, produces no promotion proposal, and uses the
existing evaluation-session cleanup. Merely checking the fixture and event
annotation makes no model calls; executing this command does.
