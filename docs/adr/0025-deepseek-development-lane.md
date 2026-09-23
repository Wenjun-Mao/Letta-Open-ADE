# ADR 0025: Official DeepSeek API Is the Bounded Development Lane

- Status: Accepted for development integration; not release qualification
- Date: 2026-09-23
- Scope: Agent Studio, Comment Lab, and Label Lab on this operator's ADE checkout

## Problem

The subscription Luna bridge investigated in ADR 0024 cannot yet prove an
ADE-only tool boundary. Sending a private Agent Studio turn through that bridge
would therefore exceed the known isolation contract. The operator supplied an
official DeepSeek API key and base URL and authorized synthetic development
tests. Existing Model Router/native ADE authority should remain in place.

## Decision

Add an explicit `deepseek_openai` Model Router adapter for only
`deepseek-flash` (DeepSeek-V4.1-Flash). Its source reads `DEEPSEEK_API_KEY` and
optional `DEEPSEEK_API_BASE` at runtime; credentials never enter the catalog,
manifest, logs, or test fixtures. The base URL must resolve to the official
`api.deepseek.com` HTTPS endpoint so an override cannot redirect the key to an
unrelated host. The configured source allowlist excludes other
models even if the account's discovery endpoint advertises them. DeepSeek uses
`thinking: {"type":"enabled"}`, `reasoning_effort: "high"`, and
`stream: false` as profile defaults. Explicit supported overrides remain
caller-owned: non-thinking mode can use temperature or forced tool choice,
and thinking mode can select a supported effort. Thinking mode still rejects
parameters the provider ignores and required/named tool choice. Unsupported
provider payloads fail before the upstream call; no implicit provider
substitution or transport retry is introduced.

ADE's native executor remains the owner of prompts, subject-bound tools,
memory writes, request budgets, and validation. DeepSeek thinking mode does not
accept a forced named/required tool choice. For a locally required curated tool,
the adapter sends `auto`, then ADE fails the turn closed unless the exact
required call occurs before final text. Preserve the provider's
`reasoning_content` in the assistant tool-call message replayed to DeepSeek,
but never turn it into user-visible dialogue or lab result content.

DeepSeek's structured output is `json_object`, not the vLLM JSON Schema wire
mode. The reviewer, compaction, and labs include the schema and a JSON example
in their prompts, then perform the existing strict local parsing and typed
validation. The DeepSeek reviewer deployment names a zero-repair budget;
older deployments retain their existing one-repair default. Invalid output
remains a failure unless a repair is budgeted. Comment/Label Lab UI omits
thinking-mode sampling fields the provider ignores; other adapters retain
their existing behavior. In ordinary native execution, the DeepSeek
conversation deployment permits at most six model requests (including tool
continuations), followed by at most one reviewer request; the synthetic
single-turn smoke applies a stricter two-generation-request transport cap.

Enable the existing Spark Qwen3-Embedding-0.6B source for the retriever path,
without changing its fingerprint, dimensions, vector policy, or qualification
record. DeepSeek has no embedding role and Spark chat is not a fallback. Add a
separate unqualified DeepSeek deployment entry for conversation and reviewer;
development mode may bind it, release mode may not. Existing qualified entries
and the release ledger are not rebound or promoted by this decision.

## Rejected alternatives and consequences

- Do not continue the Luna/AppServer live experiment until its isolation gate
  is independently resolved. Its four unspent turn starts are not transferred
  into the DeepSeek budget.
- Do not masquerade DeepSeek as a generic OpenAI/vLLM source: endpoint paths,
  thinking/tool restrictions, and JSON output semantics differ.
- Do not disable local memory/tool validation to accommodate provider output.

Hosted DeepSeek calls send the prompt and synthetic or operator-selected input
to DeepSeek's API. Private historical conversations are out of scope for the
initial smoke. The development evidence does not establish model quality,
production safety, release qualification, or data-retention suitability.
Before any release use, run governed native qualification and approve the
external-data boundary separately.

The initial live budget is at most eight DeepSeek generation requests including
tool continuations, zero rerolls, at most four Spark embedding requests plus
read-only discovery, and 180 seconds per request. Count/reserve requests before
launch and stop on a contract failure. No live call should be hidden in tests.

References: [DeepSeek API first call](https://api-docs.deepseek.com/),
[thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/),
[tool calls](https://api-docs.deepseek.com/guides/tool_calls/), and
[JSON output](https://api-docs.deepseek.com/guides/json_mode/).
