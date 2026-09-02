# Repository Utilities

Run these repository-wide utilities from the repository root. Use
`workflows/evals/` for evaluators and provider probes, and `workflows/smoke/`
for live product checks; each workflow owns its own configuration and artifacts.

## Stack Lifecycle

The root Make targets are the usual entrypoints:

```text
make up
make status
make logs SERVICE=ade-api
make down
```

The Compose service names include `ade-web`, `ade-api`, `ade-native-api`,
`ade-runtime-worker`, `model-router`, `letta`, `postgres`, and `redis`. Model
Router, Letta, and the worker are internal services; inspect them through
`docker compose logs` or `docker compose exec`, not stale host ports.

## OpenAPI Artifacts

```text
uv run python scripts/export_openapi.py
uv run python scripts/export_openapi.py --check
uv run python scripts/generate_openapi_zh_manual.py
```

The command exports both the retained v2 API and the ADE-native Agent Studio v3
API, with copies under `apps/ade-web/public/openapi/`. The Chinese
generator updates its matching web copy and missing-term report.

## Content Utilities

Synchronize reviewed personas with the local runtime projection or export a
persona library:

```text
uv run python scripts/persona_library.py --help
```

## Diagnostics And Recovery

The Agent Studio release utilities are intentionally separate and fail closed:

- `check_agent_studio_release_gate.py` validates the final content-addressed ledger.
- `record_agent_studio_conformance.py` records exact deterministic runtime contracts.
- `rehearse_agent_studio_rollback.py` proves the prior v2 web/API artifact by creating,
  reading, updating, re-reading, and purging a disposable Agent Studio agent through
  the legacy web proxy, then verifies native state preservation.
- `review_agent_studio_cutover.py` composes reviewed qualification, parity,
  conformance, and rollback evidence.

Run them through the Make targets and sequence documented in the
[Agent Studio cutover runbook](../docs/operations/agent-studio-cutover.md).

Create a redacted diagnostics bundle:

```text
scripts/collect_diagnostics.sh .env
```

The collector reads the current Compose service names, probes ADE Web and ADE
API on their host ports, and probes Model Router from inside `ade-api`. Review
the bundle before sharing it.

Reset only local Letta/Postgres data when a clean environment is intended:

```text
scripts/reset_database.sh       # POSIX shell
./scripts/reset_database.ps1    # Windows PowerShell
```

Both reset scripts accept an optional environment-file path. They delete
`data/pgdata` and restart Compose; they do not delete reviewed `content/` or
`config/` assets.

Migrate runtime files from a checkout predating `data/runtime/`:

```text
uv run python scripts/migrate_runtime_data.py --dry-run
uv run python scripts/migrate_runtime_data.py --remove-source
```

Pre-seed NLTK data when Letta needs it:

```text
scripts/seed_nltk_data.sh
```
