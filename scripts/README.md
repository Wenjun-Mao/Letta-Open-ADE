# Repository Utilities

Run repository-wide utilities from the repository root. Self-contained evals,
qualification, probes, and smoke checks belong in `workflows/`; scripts are for
small cross-repository maintenance tasks.

## Stack Lifecycle

```text
make up
make status
make logs SERVICE=ade-api
make down
```

The ordinary Compose services are `postgres`, `model-router`,
`ade-runtime-migrate`, `ade-runtime-worker`, `ade-api`, and `ade-web`. Inspect
internal services through `docker compose logs` or `docker compose exec`.

## OpenAPI Artifacts

```text
uv run python scripts/export_openapi.py
uv run python scripts/export_openapi.py --check
uv run python scripts/generate_openapi_zh_manual.py
```

The export writes the single ADE API specification and its ADE Web copy. The
Chinese generator updates the matching web artifact and missing-term report.

## Release Evidence

- `check_agent_studio_release_gate.py` validates the promoted native runtime ledger.
- `record_agent_studio_conformance.py` records deterministic runtime contracts.
- The release-promotion utility validates proposal, conformance, reviewer
  approval, manifest update, and ledger promotion as one operation.

Use the Make targets and the [release evidence guide](../docs/operations/agent-studio-release.md)
for the current sequence. A release failure requires new qualification and
promotion evidence.

## Diagnostics And Recovery

```text
scripts/collect_diagnostics.sh .env
scripts/reset_database.sh
./scripts/reset_database.ps1
```

The diagnostics collector creates a redacted bundle. The reset scripts delete
the local `data/pgdata` volume and restart Compose; they do not delete reviewed
`content/` or `config/` assets. Use reset only for an intentionally clean local
environment.
