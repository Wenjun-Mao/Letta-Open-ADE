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

## Private Integration Observations

`MODEL_ROUTER_OBSERVATION_ROOT` enables private, create-only request/outcome
records at the final provider send boundary. Router authentication is required.
The authenticated `GET /v1/router/observations` metadata index supports `run_id`,
`offset` and `limit`; `GET /v1/router/observations/{request_id}` exports a record.
The response header `X-Model-Router-Request-Id` joins provider requests and outcomes.
Private reasoning and credentials are excluded; incomplete records remain explicit.

`MODEL_ROUTER_ACTIVATION_ROOT` additionally requires a valid finite activation
lease and private observation root. A closed, expired, missing or changed lease
rejects inference before upstream dispatch. Discovery/health remain available.
These controls are opt-in for the approved synthetic integration stack; ordinary
source configuration and the one-attempt forwarding policy remain unchanged.
See [ADR 0071](../../docs/adr/0071-private-wire-observations-and-activation-leases.md).
