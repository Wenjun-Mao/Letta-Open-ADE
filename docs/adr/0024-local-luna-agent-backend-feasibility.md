# ADR 0024: Investigate A Private Luna Backend Through A Separate Tool Bridge

- Status: Proposed feasibility checkpoint, not backend acceptance
- Date: 2026-09-22
- Scope: one operator on this Mac; no public, multi-user, production, or release claim

## Question and current position

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
operator entrypoint performs only ChatGPT/version preflight, stdio `initialize`,
and a *filtered* `config/read` in an empty temporary cwd; it never starts a
thread or turn. The installed app-server accepted the handshake and reported
the requested `gpt-6-luna`, medium effort, default tier, read-only sandbox,
`never` approval, disabled web search, and ChatGPT-only login setting. Three
fake-server tests passed for framing, prospective thread fields, one
allowlisted synthetic tool response, interruption response shape, and rejection
of an unlisted tool. These tests prove the client-side spike's behavior against
synthetic messages, **not** a live Codex tool invocation. No generation call
was made for this checkpoint.

## Classified gaps

| Class | Evidence and implication |
|---|---|
| Demonstrated local control | `features.shell_tool`, Apps, hooks, multi-agent, browser use, and computer use report disabled with invocation overrides. The app-server filtered config confirms the listed model/auth/sandbox settings. This is narrower than proving an ADE-only tool set. |
| Hard under the requested zero-internal-retry contract | [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) exposes `request_max_retries` and `stream_max_retries` only under `model_providers.<id>`. Parser-only override of `model_providers.openai.request_max_retries=0` fails because `openai` is a reserved built-in provider. The existing adapter has zero *application* retries, but zero subscription transport retries cannot currently be configured through this documented path. Do not claim exactly one network attempt. A supported control or an explicitly revised risk contract is needed before backend use. |
| Testable isolation unknown | App-server help has no `--ignore-user-config`. `mcp_servers={}` on the invocation did not clear inherited MCP entries; a fresh isolated `CODEX_HOME` reported “Not logged in.” The candidate flags disabled `shell_tool`, but `features.unified_exec=false` still reported `unified_exec=true` in `features list`. Neither observation proves a command tool remains callable, yet neither proves only ADE's dynamic tool is exposed. A complete effective tool inventory or independently enforced process boundary remains necessary. |
| Testable protocol unknown | `baseInstructions`, `developerInstructions`, and per-thread `config` are schema fields, not verified instruction or override precedence. The fake bridge handles `item/tool/call`, but actual dynamic tool choice, required-call enforcement, event order, timeout, and `turn/interrupt` cleanup need live and fault-injected qualification. Unknown server requests must fail closed before ADE side effects. |
| Ordinary ADE integration work | Add a local-subscription deployment/provenance kind without pretending it is a Router fingerprint; keep immutable snapshots, subject-bound context, reviewer validation, attempt/retry ownership, and release rejection. This is a named contract change with tests, not a transparent `/chat/completions` proxy. |
| Separate local retrieval work | Luna supplies no embedding route. Current `dgx_embedding_sidecar` source is disabled and Spark-based; its Qwen3-Embedding-0.6B fingerprint names a specific artifact revision, vLLM runtime, 1024 dimensions, and retrieval policy. A local OpenAI-compatible embedding service is architecturally possible through Model Router's existing source/embedding path, but read-only checks found no installed `ollama`, `llama-server`, or `mlx_lm` executable, running embedding process, or matching Hugging Face cache in the checked locations. This is not proof none exists elsewhere. A candidate needs its own artifact/runtime fingerprint, vector compatibility or re-embedding plan, and calibrated retrieval policy. No service or model was installed. |

## Layered next gates

1. **Standalone tool-bridge gate (no embeddings or ADE database required):**
   establish a complete invocation-scoped tool inventory or stronger host
   isolation, resolve the internal-retry requirement, validate effective
   per-thread instructions, and pin experimental app-server protocol/event
   shapes. Expand fake-server tests for malformed IDs/arguments, unexpected
   tool and approval requests, timeout, interruption, and process-tree cleanup.
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

## Exact proposed live-call budget (not authorized or run)

After gate 1 is resolved, request permission for **at most four serial calls**
under ChatGPT login, `gpt-6-luna`, medium effort, default tier, one ephemeral
thread per call, 180-second timeout, synthetic inputs, no adapter reroll or
fallback. Stage A is calls 1-2; stop if either fails. Stage B is calls 3-4 only
after inspecting Stage A:

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
This is a proposal for director/user review, not permission to call.

## Consequences

ADE product, release protections, Spark configuration, and global Codex
configuration remain unchanged. The spike is a workflow-local disposable
feasibility artifact, not an SDK or production backend. This proposed ADR
should be revised after the tool-authority and retry questions have evidence.
