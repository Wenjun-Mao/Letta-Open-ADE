# ADE Model Router

## Purpose

The Model Router is ADE's single provider-facing service. It discovers configured
models, applies checked-in capability profiles and sampling defaults, and exposes
an OpenAI-compatible chat endpoint. ADE API and Letta use router model IDs such
as `dgx_vllm::qwen3.6-35b-a3b-fp8`; they do not select provider URLs directly.

## Request Flow

1. Sources are loaded from `config/model-router/sources.json` plus local environment
   secrets.
2. `catalog.py` discovers provider models and merges `model-profiles.json` metadata.
3. `/v1/models` exposes Agent Studio-compatible models; router catalog endpoints
   expose the richer ADE catalog.
4. `/v1/chat/completions` resolves the source, applies missing defaults, and
   `forwarding.py` sends the request upstream.

Forwarding uses one lifespan-managed HTTP client and exactly one upstream request.
Idle pooled connections expire before the local servers' observed five-second
closure boundary; connection renewal never retries a provider request. See
[ADR 0002](../../docs/adr/0002-router-transparent-retry-policy.md).

Thinking defaults may be model- and protocol-specific. A profile can keep normal
dialogue thinking enabled while setting `tool_call_thinking_default_enabled=false`
for tool-bearing vLLM requests. Explicit caller values are always preserved. See
[ADR 0015](../../docs/adr/0015-model-scoped-tool-call-thinking-mode.md).

## Boundaries

- Owns provider discovery, provider authentication, model IDs, capability profiles,
  sampling and tool-protocol defaults, and upstream forwarding.
- Uses `model-catalog-contracts` only for stable allowlist report contracts.
- Must not contain ADE feature policy, prompt content, personas, schemas, or Letta
  agent lifecycle behavior.
- Must not add transport retries; connection-pool freshness and request-attempt
  ownership are separate contracts.
- Secrets belong in `.env` or Docker secrets; tracked source configuration must not
  contain machine-specific credentials.

## Key Files

| Change | Start here |
| --- | --- |
| Add or expose a source | `config/model-router/sources.json`, then `settings.py` |
| Change model capability metadata | `config/model-router/model-profiles.json`, then `profiles.py` |
| Change catalog discovery | `catalog.py` |
| Change forwarded request behavior | `app.py` and `forwarding.py` |

## Verification

```bash
uv run python -m pytest services/model-router/tests -q
uv run ruff check services/model-router
```

The Compose service is `model-router` and is intentionally internal-only. Use
`docker compose exec model-router` for runtime diagnostics.
