# ADR 0024: Investigate A Private Luna Backend Through A Separate Tool Bridge

- Status: On hold; superseded as the current development lane by ADR 0025
- Date: 2026-09-23
- Scope: one operator on this Mac; no public, multi-user, production, or release claim

## Question and current position

The operator put this live experiment aside on 2026-09-23. Its conditional
four-start budget remains unspent and cannot be carried into the separately
bounded DeepSeek work in [ADR 0025](0025-deepseek-development-lane.md).

Could ADE eventually use ChatGPT-authenticated GPT-6 Luna for a private local
Agent Studio without losing ADE's subject, memory, tool, and retry authority?
**Yes, it is worth a bounded protocol experiment; no, the current evidence does
not yet justify wiring it into the worker.** The incumbent Router identity model
and the lack of a Luna embedding endpoint are integration tasks, not by
themselves incompatibilities. ADR 0019 still governs the product runtime.

The existing `workflows/evals/character_memory_dev/luna.py` is an `exec`-based
development adapter. Its earlier tests and schema smoke runs establish one-turn
text task-shape feasibility only. They are *not* a test of app-server dynamic
tools, built-in tool isolation, ADE embeddings, or Agent Studio execution.

## New no-generation protocol evidence

The installed `codex-cli 0.155.0-alpha.9.2` reports ChatGPT login. Its
version-matched generated app-server v2 schema declares `thread/start` fields
for `ephemeral`, `baseInstructions`, `developerInstructions`, `dynamicTools`,
`allowProviderModelFallback`, sandbox, model, and per-thread config. A function
dynamic tool declares `inputSchema`; server `item/tool/call` requests carry
`threadId`, `turnId`, `callId`, `tool`, and `arguments`; responses carry
`contentItems` and `success`. [App-server documentation](https://learn.chatgpt.com/docs/app-server)
calls dynamic tools experimental and describes `turn/interrupt`. Schema presence
does not establish runtime instruction precedence, an exhaustive tool catalog,
or model behavior.
The [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) wraps the CLI/app-server
protocol, so it does not independently settle these controls; stdio keeps this
spike dependency-free.

The workflow-local `app_server_spike.py` pins that CLI/schema version. Its
operator entrypoint performs only ChatGPT/version preflight, a fail-closed MCP
inventory check, stdio `initialize`, and a *filtered* `config/read` in an empty
temporary cwd; it never starts a thread or turn. The installed app-server
accepted the handshake and reported
the requested `gpt-6-luna`, medium effort, default tier, read-only sandbox,
`never` approval, disabled web search, and ChatGPT-only login setting. Seventeen
spike test cases pass for framing, prospective thread fields, one allowlisted
synthetic tool response, interruption response shape, rejection of unlisted,
unbound, mismatched, or duplicate tool calls, an overall request deadline,
bounded notifications/bytes, and process-group cleanup when a child ignores
`SIGTERM`. These tests prove the client-side spike's behavior against synthetic
messages, **not** a live Codex tool invocation. No generation call was made for
this checkpoint.

## Classified gaps

| Class | Evidence and implication |
|---|---|
| Demonstrated local control | The invocation disables `shell_tool`, unified exec, Apps, plugins, hooks, multi-agent, browser use, and computer use. The app-server's own `config/read` reports all these feature values as `false` along with the requested model/auth/sandbox settings. A separate `features list` still labels unified exec `true`, so config values alone are not runtime proof that an ADE-only tool set is exposed. [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) documents these feature switches. |
| Observed inherited MCP control | Under the same sanitized environment, `mcp list --json` initially showed enabled `cua_repl`, `node_repl`, and `openaiDeveloperDocs` despite the feature flags. Per-server `enabled=false` alone failed config parsing for the two host-injected stdio servers because that invocation layer lacked their transport. Version-pinned invocation overrides provide an inert `/usr/bin/false` transport and disable those two; the HTTP docs server needs only `enabled=false`. The spike fails closed if *any* CLI-listed MCP server remains enabled and verifies every MCP entry in app-server's own `config/read` is disabled. With plugins disabled, the current no-generation probe lists four inherited servers, all disabled; `mcpServerStatus/list` likewise returned four server records with zero tools and no next page. Global configuration was not edited. This validates the observed MCP layer, not all built-in tool exposure. |
| Internal retry exception, experiment only | [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) documents `request_max_retries` and `stream_max_retries` under `model_providers.<id>`. Parser-only override of `model_providers.openai.request_max_retries=0` fails because `openai` is a reserved built-in provider. The user explicitly accepted on 2026-09-23 that this experiment may have opaque CLI transport retries. At most four serial *turn starts* and zero ADE/application retries are permitted; this is **not** a four-network-attempt guarantee. The exception does not qualify production, release, or general backend retry policy. |
| Testable isolation unknown | App-server help has no `--ignore-user-config` or tool allowlist. `mcp_servers={}` on the invocation did not clear inherited MCP entries; a fresh isolated `CODEX_HOME` reported “Not logged in.” The version-matched app-server schema has `dynamicTools` and `mcpServerStatus/list` but no exhaustive built-in `tools/list` request. [App-server documentation](https://learn.chatgpt.com/docs/app-server) describes dynamic tools as experimental while also documenting built-in request surfaces. Disabled feature values and zero MCP tools do not prove that only ADE's dynamic tool is offered. A read-only sandbox does not prevent file reads, so it cannot by itself isolate private host data from a hidden read-capable built-in tool. A complete effective tool inventory or independently enforced process boundary remains necessary before a model turn. |
| Testable protocol unknown | `baseInstructions`, `developerInstructions`, and per-thread `config` are schema fields, not verified instruction or override precedence. The fake bridge handles `item/tool/call`, but actual dynamic tool choice, required-call enforcement, event order, timeout, and `turn/interrupt` cleanup need live and fault-injected qualification. Unknown server requests must fail closed before ADE side effects. |
| Ordinary ADE integration work | Add a local-subscription deployment/provenance kind without pretending it is a Router fingerprint; keep immutable snapshots, subject-bound context, reviewer validation, attempt/retry ownership, and release rejection. This is a named contract change with tests, not a transparent `/chat/completions` proxy. |
| Separate local retrieval work | Luna supplies no embedding route. Current `dgx_embedding_sidecar` source is disabled and Spark-based; its Qwen3-Embedding-0.6B fingerprint names a specific artifact revision, vLLM runtime, 1024 dimensions, and retrieval policy. A local OpenAI-compatible embedding service is architecturally possible through Model Router's existing source/embedding path, but read-only checks found no installed `ollama`, `llama-server`, or `mlx_lm` executable, running embedding process, or matching Hugging Face cache in the checked locations. This is not proof none exists elsewhere. A candidate needs its own artifact/runtime fingerprint, vector compatibility or re-embedding plan, and calibrated retrieval policy. No service or model was installed. |

## Layered next gates

1. **Standalone tool-bridge gate (no embeddings or ADE database required):**
   establish a complete invocation-scoped tool inventory or stronger host
   isolation, validate effective per-thread instructions, and pin experimental
   app-server protocol/event
   shapes. Remaining fake-server work includes malformed arguments, unexpected
   approval requests, and cancellation races; the current bounds and cleanup
   tests are not a live turn guarantee.
2. **Small live synthetic bridge gate:** only with an approved call budget,
   observe actual dynamic-tool events and cancellation in fresh ephemeral
   threads; reject unexpected tools/events. Keep ADE memory writes disabled.
3. **Retriever gate, independently:** qualify a versioned local embedding route,
   dimensions, query instruction, distance threshold, and migration/rebuild
   behavior. No existing vector fingerprint may be silently reused.
4. **ADE integration gate:** introduce explicit deployment/provider contracts
   and run isolated add/correct/forget, required search, compaction,
   cancellation, stale-fingerprint, and no-fallback tests. Only then consider
   a private development flag. Product/release acceptance remains separate.

## Approved conditional live-call budget (none run)

The user approved **at most four serial turn starts**, conditional on an
effective tool boundary, under ChatGPT login, `gpt-6-luna`, medium effort,
default tier, one ephemeral thread per call, 180-second timeout, synthetic
inputs, no adapter reroll or
fallback. Internal CLI transport retries may occur and their count is unknown;
this exception applies only to this experiment. Stage A is calls 1-2; stop if
either fails. Stage B is calls 3-4 only after inspecting Stage A:

1. No-tool baseline: synthetic persona says the user's favorite tea is oolong;
   user asks for that value. Check requested/observed identity and event shape.
2. Native-tool probe: omit a synthetic older tea fact from active profile;
   ask for it with only `search_memory` supplied by the client. Check one
   validated call/result and the final answer's attribution to the bound user.
3. Structured reviewer probe: synthetic current message explicitly asks to
   forget a supplied active preference. Check JSON Schema and ADE's typed
   validator for `forget`, exact fact ID/version, and JSON null; do not commit.
4. Interrupted probe: start a synthetic long task, send `turn/interrupt`, and
   verify interrupted status, process cleanup, uncertain usage, and no replay.

Capture exact synthetic inputs, CLI version, requested settings, raw events,
timing, validation, and observed/missing usage—never credentials or private
transcripts. Stop after any unqualified event; unused calls are not spent.
Approval to spend this budget does not waive tool isolation. No turn has been
started; the full four-start budget remains.

The current CLI exposes no supported exhaustive built-in tool catalog in the
checked app-server protocol. A viable independent boundary would be a separate
macOS user or VM with no production/user data and a fresh interactive ChatGPT
Codex login there. The existing login cannot simply be reused with a fresh
`CODEX_HOME`; credentials must not be copied. Creating and authenticating that
environment is a user action, not part of this checkpoint.

## Consequences

ADE product, release protections, Spark configuration, and global Codex
configuration remain unchanged. The spike is a workflow-local disposable
feasibility artifact, not an SDK or production backend. This proposed ADR
should be revised after the tool-authority and retry questions have evidence.
