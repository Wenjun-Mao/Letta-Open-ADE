# ADE Model Router

Model Router is ADE's single provider-facing service. It discovers configured
models, applies reviewed capability and sampling profiles, assigns canonical
model keys, and forwards OpenAI-compatible requests upstream.

## Request Flow

1. Load source configuration from `config/model-router/sources.json` and local
   secrets from the environment.
2. Discover provider models and merge `model-profiles.json` metadata.
3. Expose canonical models through `/v1/models` and the ADE catalog endpoints.
4. Resolve a request, inject only omitted profile defaults, and forward exactly
   one upstream attempt.

Explicit caller values always win. The router owns no feature prompts, personas,
schemas, memory, or retry policy. ADE features and the native runtime own their
user-visible timeout and additional retry behavior.

## Boundaries

- Owns provider discovery, authentication, model IDs, profile defaults, and
  OpenAI-compatible forwarding.
- Does not contain product feature policy or persistent agent state.
- Does not add transport retries. Connection-pool renewal is not a second
  provider attempt.
- Keeps credentials in `.env` or a secret store, never tracked source config.

## Key Files

| Change | Start here |
| --- | --- |
| Add or expose a source | `config/model-router/sources.json`, then `settings.py` |
| Change capability metadata | `config/model-router/model-profiles.json`, then `profiles.py` |
| Change discovery | `catalog.py` |
| Change forwarding | `app.py` and `forwarding.py` |

## Verification

```text
uv run python -m pytest services/model-router/tests -q
uv run ruff check services/model-router
```

The Compose service is `model-router` and is internal-only. Use
`docker compose exec model-router` for runtime diagnostics.
