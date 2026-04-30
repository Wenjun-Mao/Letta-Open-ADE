# Provider Model Probe

Probes configured router upstreams and can regenerate checked-in model allowlist reports. This is intentionally a workflow folder because the command has a specific operational purpose and writes durable probe artifacts.

## Commands

Print an Ark chat probe report without writing:

```bash
uv run python evals/provider_model_probe/run.py --source-id ark --mode chat-probe
```

Regenerate the checked-in Ark chat allowlist:

```bash
uv run python evals/provider_model_probe/run.py --source-id ark --mode chat-probe --write
```

Regenerate the checked-in Ark Label Lab structured-output allowlist:

```bash
uv run python evals/provider_model_probe/run.py --source-id ark --mode label-structured --write
```

## Arguments

| Argument | Meaning |
| --- | --- |
| `--source-id` | Required router source id from `config/model_router_sources.json`. |
| `--mode` | `chat-probe` or `label-structured`. |
| `--write` | Write to the configured checked-in allowlist path instead of printing. |
| `--output` | Optional explicit report path, mostly useful for tests or ad hoc probes. |

The workflow loads `.env` for upstream credentials and reads router source config through `model_router.settings`.
