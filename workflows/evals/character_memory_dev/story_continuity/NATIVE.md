# Bounded Native Execution

The user separately approved the existing ten-turn ceiling on 2026-09-30, and
approved local commits and the isolated live-runner preparation. This permission
does not authorize another sequence, rerolls, changed prompts/models, retained
trial access, pushing or deployment. See [ADR 0054](../../../../docs/adr/0054-bounded-native-story-probe.md).

## Start And Resume

Commit the verified iteration first. The runner rejects dirty or changed source
and requires the configured DeepSeek credential and `DGX_SPARK_HOST` in `.env`
or the process environment. It never writes credentials into evidence files.
Choose a new direct child of the ignored parent workflow `outputs/` directory:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity.native start \
  --approved --directory workflows/evals/character_memory_dev/outputs/pc11-native-YYYYMMDD-UNIQUE
```

This creates a fresh owned pgvector database, migrates it, launches isolated
authenticated loopback services, validates their actual catalog/source identities,
and executes only the already-frozen prompts. Up to two conversation requests and
one reviewer request per turn are the existing finite runtime limits; embedding
requests are counted observationally. Each turn has `retry_count=0` and the
unchanged 180-second timeout. No post-outcome prompt or policy edits are allowed.

The router process alone maps the pinned `dgx-spark` alias to the configured IPv4
address, as Docker does. Its URL, adapter and full deployment fingerprint remain
unchanged. This does not install a global resolver override or replace a model.

All services stop at an annotation pause or exit. The new container stays stopped
with its data intact. The retained trial is never contacted. To continue the same
sequence after freezing a human annotation:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity.native resume \
  --directory workflows/evals/character_memory_dev/outputs/pc11-native-YYYYMMDD-UNIQUE
```

## Human Annotation

After committed turn 1, inspect its actual reply and freeze exact core quotes,
establishment rationale and the turn-4 replacement suggestion **before turn 2**.
After committed turn 3, freeze an actual compatible new detail **before turn 4**.
Use a private JSON file containing `reviewer_kind: "human"`, the human's `reviewer`
name, `usable`, `rationale`, `quotes`, and (for usable turn 1)
`replacement_suggestion`. Agent-proposed annotations need real human approval;
the runner does not perform semantic judgment or fabricate such approval.

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity.native annotate \
  --directory workflows/evals/character_memory_dev/outputs/pc11-native-YYYYMMDD-UNIQUE \
  --turn 1 --annotation /absolute/path/to/private/human-annotation.json
```

An unusable origin requires a reason, not replacement model output. Turn 2 can
still run; dependent probes become unassessable. Rejected origins establish
nothing. Structural/capture failure stops dispatch rather than becoming a pass.

## Receipts And Cleanup

The private directory contains the clean preparation/approval, owned database ID,
per-launch catalog/options/worker-health/settings/logs, immutable sessions and
version changes, archive receipts, per-turn intents, acceptance receipts, exact
capture bytes, public readback, validation results and human annotations.

An existing dispatch intent without a completed turn record is an uncertain
outcome. Do not delete it, create another sequence, or retry submission. Inspect
the accepted run and private capture first. A failed candidate remains a failed
candidate; no rerolls or fabricated replacement story. Keep semantic misses
separate from evidence failures and native quality separate from scripted tests.

When complete or explicitly abandoned, remove only this stopped owned database:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity.native cleanup \
  --directory workflows/evals/character_memory_dev/outputs/pc11-native-YYYYMMDD-UNIQUE
```

Private evidence remains ignored. Publish only a concise source-bound finding
after reviewing the real outcomes. Do not commit source changes mid-sequence:
they would invalidate continuation of the frozen baseline.

## Runner Verification (2026-09-30)

Portable workflow checks: 123 passed. Combined runtime/workflow checks: 417
passed, three explicit missing-historical-evidence skips, one existing
Starlette/httpx deprecation warning. Ruff and format checks passed.

The real PostgreSQL native-runner mechanics test executes all ten turns over
actual HTTP handlers, worker, captures and persistence with **scripted providers
and annotation fixtures**. It verifies both pauses, ordinary version creation,
both archived source chats, archived-origin admission and other-subject/root
isolation. Together with the existing successful/rejected-origin story tests:
three passed, no skips, in 2.36 seconds.

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity/tests --ignore=services/ade-api/tests/agent_runtime/persistence -q -rs
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32773/ade_history_test_20260930 \
  uv run --locked python -m pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py services/ade-api/tests/agent_runtime/persistence/test_postgres_native_story_runner.py -q
```

The newly owned `ade-pc11-runner-check-20260930` pgvector 0.8.1/PG15 container
was migrated to Alembic head and removed with its anonymous volume afterward.
The initial integration caught the API's declared `sha256` inside its fingerprint
payload; the runner now separates that field for recomputation and checks both
declared and computed hashes. No runtime guard or baseline pin was relaxed.
These checks dispatched no real model requests and establish no native quality.
