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
After a failed terminal turn or case score, the runner retains the observed
turn and stops before later turns, cases, rounds, or optional compatibility.
An exhausted request cap has the same scheduling effect. A partial matrix is
failed and cannot qualify; reaching the cap on the final required turn does
not retroactively fail an otherwise complete matrix.

The checked-in DeepSeek and Qwen manifest entries are candidates with zero
passing rounds, not approved release routes. If `QWEN_EMBEDDING_API_BASE`
changes the effective endpoint, rebind its manifest URL and deployment
fingerprint, prove vector-space compatibility with paired synthetic query and
document canaries, and run fresh qualification before promotion. Merely
changing the environment variable fails the Agent Runtime deployment binding.

Full qualification now fails preflight unless API and worker use the same
configured, source-bound request budget. Configure all four
`ADE_API_AGENT_RUNTIME_BUDGET_*` settings in an isolated host **only after**
its stage caps are approved: a unique ignored ledger path under
`data/runtime`, stage `qualification`, and positive generation/embedding
limits. The API and worker share that volume. Each outbound generation or
embedding request reserves a SQLite slot before send; failed and interrupted
requests remain spent across restart. A different cap, stage, source build, or
runtime mode cannot reopen the same ledger. The runner checks the worker's
budget compatibility fingerprint and requires zero requested retries. A
diagnostic preflight can use stage `preflight` with its own ledger; it cannot
produce a promotion proposal. Do not reuse one stage's ledger as a reroll.

No-generation verification from the repository root:

```bash
uv run pytest -q services/ade-api/tests/agent_runtime/test_request_counts.py \
  workflows/evals/deepseek_dev_smoke/test_m3_host.py \
  workflows/evals/agent_runtime_acceptance/tests/test_run.py \
  workflows/evals/agent_runtime_acceptance/tests/test_rounds.py
ADE_ENV_FILE=.env.example docker compose --env-file .env.example config --quiet
```

For an approved stage, start clean API/worker builds with the *same* four
budget settings and a disposable database, confirm matching build health,
then invoke this runner inside the ADE API container. Stage A uses
`--case-key correction_chain --case-key old_memory_deep_search` and stage
`preflight`; stage B uses the entire matrix and stage `qualification`. See
the [stage plan](../../../docs/plans/m3-provider-neutral-release-preparation.md)
for proposed caps and stop conditions. These settings are disabled in the
checked-in example and do not authorize calls. The 180-second transport
limit is per request; the worker also passes the **remaining** turn deadline
to each request, so it does not restart a 180-second turn for each
continuation. Direct origin/candidate relocation canaries are not sent by
the canonical runner and must be reserved through the same approved ledger
before any such calls.

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
