# Repository Utilities

Run these utilities from the repository root. Evaluation and provider-probe
workflows live under `workflows/evals/` with their own documentation and artifacts.

## Reset The Letta Database

This deletes local Letta/Postgres state and restarts the stack. Use it only when a
clean local environment is intended.

Windows PowerShell:

```text
./scripts/reset_database.ps1
```

POSIX shell:

```text
scripts/reset_database.sh
```

Both reset scripts accept an optional environment-file path, for example `.env`.

## Common Utilities

Regenerate Letta tool constants after publishing a tool:

```text
uv run python scripts/sync_tools.py
```

Pre-seed NLTK data used by Letta:

```text
scripts/seed_nltk_data.sh
```

Import or export the persona library:

```text
uv run python scripts/persona_library.py --help
```

Migrate runtime files created by older checkouts, first as a dry run and then
optionally removing only sources whose destination was copied or verified identical:

```text
uv run python scripts/migrate_runtime_data.py --dry-run
uv run python scripts/migrate_runtime_data.py --remove-source
```

Collect a diagnostics bundle:

```text
scripts/collect_diagnostics.sh .env
```

Diagnostics may contain service topology or operational metadata. Review the
bundle before sharing it, even when its filename says it is redacted.

## Start And Verify

Start the local stack with the default `.env` file:

```text
docker compose up -d --build
```

Run deterministic Python coverage:

```text
uv sync --frozen --group dev
uv run python -m pytest
```

Run live checks only after the stack and providers are ready:

```text
uv run python tests/checks/platform_api_e2e_check.py
uv run python tests/checks/ade_mvp_smoke_e2e_check.py
```

There is no `ui` Compose profile. `ade_frontend` is a normal service and starts
with the default stack.
