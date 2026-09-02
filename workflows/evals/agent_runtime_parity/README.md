# Agent Runtime Paired Baseline Comparison

This self-contained workflow compares the Letta-backed Agent Studio public API
(``/api/v2``) with the ADE-native Agent Studio session API
(``/api/v3/agent-studio/sessions``). It is Milestone 4 candidate-qualification
evidence, not a runtime qualification run and not a cutover switch.
It imports neither Letta nor internal ADE runtime services.

Each run executes three paired DGX rounds against the same seven user turns from
``workflows/evals/chat_memory_eval/fixtures/recent_user_chat_turns.json``. The
comparison intentionally scores only observable product behavior:

- no forbidden bot/AI self-disclosure in assistant replies;
- durable capture of ``张伟``, ``Rocky``, and ``哈士奇``/``Husky``;
- a successful result for every submitted turn; and
- exact ``timeout_seconds=180`` and ``retry_count=0`` controls with one client
  transport attempt per turn.

It does not compare assistant prose or require Letta's mutable ``human`` block
to resemble ADE-native typed facts. LLM judging is deliberately out of scope.
It also does not pretend that Letta exposes native subjects, revisions, or event
semantics: those native-only capabilities are proven by qualification and
deterministic conformance, then composed with this paired result by the cutover
ledger.

## Candidate Gate

Schema-v2 artifacts treat Letta v2 as the observed incumbent baseline and native v3
as the cutover candidate. The comparison qualifies the candidate only when all three
native rounds pass, the inputs are comparable, exact zero-retry controls are
observed, cleanup completes, and native is not worse than Letta in any round. If
Letta passes a round, native must pass it too. If Letta fails a round and native
passes, the incumbent failure remains visible but does not veto the candidate.

The summary and every round report separate native and Letta outcomes plus the
non-regression result. This is a paired baseline comparison, not a statement that
the products are equivalent. Schema-v1 bundles are readable history but cannot meet
this cutover gate because they do not encode these separate outcomes.

The checked-in configuration uses the required three-round evidence run;
``--rounds 1`` or ``--rounds 2`` is allowed for diagnostics but cannot by itself
meet Milestone 4's three-round evidence requirement.

## Run

Start both the ordinary v2 stack and the isolated native v3 runtime first. Set
credentials and the application database URL in the shell; the database URL is
mandatory because native generated resources are removed through
``ScopedPostgresCleanup`` after every result, including failures.

For a container run, invoke the workflow in ``ade-native-api`` with the v2 and
v3 Compose service URLs. That service already carries the build-bound
``ADE_SOURCE_REVISION``, ``ADE_SOURCE_DIRTY``, and ``ADE_SOURCE_FINGERPRINT``
values used to prove that the evaluator and native worker are the same build.
For a host run, the workflow derives the corresponding identity from the local Git
worktree. Either identity must exactly match ``/api/v3/worker-health`` or the
comparison fails closed.

```bash
export AGENT_RUNTIME_PARITY_LEGACY_API_KEY="$ADE_API_ADMIN_KEY"
export AGENT_RUNTIME_PARITY_NATIVE_API_KEY="$ADE_API_OPERATOR_KEY"
export AGENT_RUNTIME_PARITY_DATABASE_URL="$ADE_API_DATABASE_URL"

uv run python workflows/evals/agent_runtime_parity/run.py \
  --config workflows/evals/agent_runtime_parity/config.toml \
  --legacy-api-base-url http://127.0.0.1:8000 \
  --native-api-base-url http://127.0.0.1:8002 \
  --rounds 3 \
  --timeout-seconds 180 \
  --retry-count 0
```

The runner rejects all retry counts other than zero. It writes one immutable
bundle below ``outputs/<run-id>/``:

- ``parity-spec.json``: the shared fixture, product checks, exact requested
  model/prompt/persona/deployment inputs, and controls;
- ``provenance.json``: source revision/dirty/fingerprint, selected legacy
  catalog/template snapshots, native worker/definition snapshots, and cleanup
  receipts;
- ``normalized-turns.jsonl``: user-visible replies, terminal states, tool
  observations, memory outcomes, and control evidence only;
- ``comparison.json``: fail-closed input comparability, separate observed-incumbent
  and candidate results, and deterministic per-round non-regression; and
- ``summary.json``: a compact pass/fail receipt bound to the other artifacts.

JSON artifacts embed a SHA-256 of their canonical content. The JSONL artifact is
hashed byte-for-byte and its digest is bound by the other artifacts. The workflow
never records private reasoning, model-router provider bodies, credentials, or
raw SSE payload bodies.

Legacy agents are archived and purged through ``/api/v2``. Native sessions are
created atomically, archived, and restored through the Agent Studio session API.
Their definition and subject keys begin with the exact parity run ID before any
request is issued, so scoped PostgreSQL cleanup can delete only generated v3 resources. An
ambiguous legacy creation or either incomplete cleanup path makes the comparison
fail even when behavior otherwise passes.

The workflow intentionally reuses the repository's shared
``ScopedPostgresCleanup`` contract. Run it only after that cleaner has been kept
in step with the installed native schema; if a schema migration makes the scoped
deletion sequence invalid, this workflow records the failed recovery receipt and
returns nonzero rather than broadening its deletion scope.

## Tests

```bash
uv run python -m pytest workflows/evals/agent_runtime_parity/tests -q
```
