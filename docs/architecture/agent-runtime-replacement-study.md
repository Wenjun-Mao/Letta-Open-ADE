# ADE-Native Agent Runtime Replacement Study

- Study date: 2026-08-27
- Production impact: none
- Decision state: architecture proposed; replacement not approved
- Reproducible workflow: [`workflows/evals/agent_runtime_study/`](../../workflows/evals/agent_runtime_study/README.md)
- Proposed decision: [ADR 0009](../adr/0009-ade-owned-agent-runtime.md)

## Executive Conclusion

ADE should own its eventual Agent Studio persistence and orchestration model. The
right boundary is not “rewrite Letta”; it is a smaller product-specific runtime:

1. Reusable, immutable agent-definition versions.
2. Explicit memory subjects independent of agents.
3. Conversations binding one definition version to one subject.
4. Immutable messages and versioned summaries.
5. Typed, evidence-backed memory operations and projections.
6. A bounded model/tool loop using curated tools.
7. PostgreSQL transactions, run leases, and normalized events.

The MemGPT principles of hierarchical context, immutable recall, deliberate memory
management, and bounded working context remain valuable. ADE should not adopt
Letta's coding-agent-specific filesystem/Git/Bash direction, free-text
model-controlled memory blocks, arbitrary tool execution, or opaque runtime policy.

The static executor comparison favors the minimal custom OpenAI-compatible loop.
It preserves one ADE retry owner and recovers malformed protocol messages without a
framework retry. The exact PydanticAI `2.35.1` adapter tested here is disqualified;
that result does not claim every possible PydanticAI integration is impossible.

No runtime candidate is approved for cutover. The custom loop passes the static
executor contract and both models' curated weather-tool checks, but the live
conversation suite still exposes model-compliance and memory-normalization gaps.
The proposed ADR therefore remains **Proposed**, not Accepted.

## Scope And Method

This study changed only a workflow, tests, and documentation. It did not change
production OpenAPI, ADE Web, ADE API behavior, Compose, Letta, PostgreSQL, Redis, or
existing agents.

Evidence came from four sources:

- Repository trace of every current Letta dependency.
- Disposable black-box agents operated only through ADE API.
- Pinned Letta image/source inspection and upstream primary sources.
- One shared deterministic/live runtime harness with two executor adapters.

The implementation paraphrases upstream ideas and implements independent study
contracts. No Letta source was copied.

## Provenance

The workflow records provenance in every run. The studied runtime was:

| Item | Resolved value |
| --- | --- |
| Compose image | `letta/letta:0.16.8` |
| Runtime version | `0.16.8` |
| Local image digest | `sha256:aa66c3eeee13d2dfc40c650d709b550237ee31bfc91942a52fa488a13fa8c102` |
| Upstream release commit in notes | `1131535` |
| PydanticAI distribution | `pydantic-ai-slim[openai]==2.35.1` |
| Primary live model | `dgx_vllm::qwen3.6-35b-a3b-fp8` |
| Compatibility model | `local_llama_server::gemma4` |

Artifacts also contain the repository revision/status, workflow-tree hash, fixture
hash, `uv.lock` hash, prompt/persona hashes, effective non-secret config, and live
Model Router catalog.

Primary upstream references:

- [MemGPT paper](https://arxiv.org/abs/2310.08560)
- [Letta repository](https://github.com/letta-ai/letta)
- [Letta 0.16.8 release](https://github.com/letta-ai/letta/releases/tag/v0.16.8)
- [Letta Agents API](https://docs.letta.com/api/resources/agents)
- [Letta memory blocks](https://docs.letta.com/api/typescript/resources/agents/subresources/blocks)
- [Letta Code prompt](https://github.com/letta-ai/letta-code/blob/main/src/agent/prompts/letta.md)
- [PydanticAI 2.35.1](https://pypi.org/project/pydantic-ai/2.35.1/)
- [PydanticAI agents](https://pydantic.dev/docs/ai/core-concepts/agents/)
- [PydanticAI message history](https://pydantic.dev/docs/ai/core-concepts/message-history/)
- [PydanticAI OpenAI provider](https://pydantic.dev/docs/ai/models/openai/)

## What ADE Uses Today

### Runtime Dependency Map

```text
ADE Web Agent Studio
  -> ADE API Agent Studio
     -> Letta SDK
        -> Letta agent loop, blocks, messages, tools, compaction
        -> PostgreSQL and Redis
        -> Model Router
           -> local/cloud providers

Tool Center
  -> ADE API registry metadata
  -> Letta global tool catalog and execution runtime

Model Catalog
  -> Model Router for generation models
  -> Letta catalog for embedding handles and Letta-visible chat handles

Test Center/chat-memory eval
  -> ADE API Agent Studio
  -> disposable Letta agents and projected Letta state
```

Agent creation embeds the chosen system prompt, persona/human blocks, model,
embedding, tools, and a `16384` context limit in
[`agents_api.py`](../../services/ade-api/src/ade_api/features/agent_studio/agents_api.py).
Letta owns the resulting agent, message history, block mutations, tool loop, search,
and compaction. ADE projects those objects in
[`state_api.py`](../../services/ade-api/src/ade_api/features/agent_studio/state_api.py)
and normalizes turn traces in
[`message_parser.py`](../../services/ade-api/src/ade_api/integrations/letta/message_parser.py).

ADE disables retries on the base Letta SDK client, then applies request-scoped SDK
timeout/retry options in
[`agent_service.py`](../../services/ade-api/src/ade_api/integrations/letta/agent_service.py).
Model Router forwards exactly one upstream request in
[`forwarding.py`](../../services/model-router/src/model_router/forwarding.py).
Agent Studio has one separate context-limit fallback for datetime-hint messages,
which may issue a second Letta message request after a context error. This behavior
must become an explicit compaction/repair event in v3, not a hidden fallback.

Archive/restore is ADE-owned lifecycle metadata; purge deletes the Letta agent. Tool
Center stores reviewed metadata locally but creates and executes arbitrary
Python/npm/pip tools through Letta. Model Catalog still asks Letta for embedding
handles. Comment Lab and Label Lab do not use Letta for generation.

### Frontend Coupling

Agent Studio currently consumes a Letta-shaped projection:

- `sequence` reasoning/tool/assistant steps.
- `memory_diff.old/new` free-text blocks.
- `memory_blocks` with labels such as `human` and `persona`.
- Letta message types and raw-prompt history.
- Letta agent model, embedding, context-window, and attached tools.

The relevant types are in
[`apps/ade-web/src/features/agent-studio/api.ts`](../../apps/ade-web/src/features/agent-studio/api.ts).
A replacement is therefore an Agent Studio API/UI migration, not an internal SDK
swap.

### Capability Disposition

| Capability | Current authority | v3 disposition |
| --- | --- | --- |
| Prompts, personas, schemas, model profiles | ADE | Keep |
| Provider discovery and forwarding | Model Router | Keep |
| Agent definitions and conversation binding | Letta agent | Rebuild explicitly |
| Raw history | Letta | Rebuild as immutable ADE messages |
| Human memory | Free-text Letta block | Replace with structured facts/revisions |
| Persona memory | Letta block | Agent-definition snapshot, not subject memory |
| Conversation search | Letta tool | Rebuild as subject/history search |
| Context compaction | Letta | Rebuild as versioned derivatives |
| Embedding discovery/retrieval | Letta | Defer pending semantic benchmark |
| Agent/tool loop | Letta | Rebuild small curated loop |
| Timeout/retry request controls | ADE plus SDK | Make ADE sole owner |
| Archive metadata | ADE | Move into PostgreSQL conversation/definition status |
| Global custom-tool catalog | Letta plus ADE mirror | Defer arbitrary execution |
| Tool approvals | Exposed by Letta metadata, no ADE workflow | Defer |
| Sandboxing | Letta runtime | Do not rebuild in core v3 |
| Eval orchestration/artifacts | ADE Test Center | Keep |
| Telemetry | Parsed traces/artifacts only | Rebuild normalized events; OTel optional |

Redis has no demonstrated ADE-native requirement. It should be removed with Letta
unless a later measured queue/cache/coordination need justifies it.

## Upstream Design Findings

The MemGPT paper frames limited model context as a memory hierarchy: a small active
context, larger archival/recall stores, and agent-directed movement between them.
The principles that fit ADE are bounded active context, explicit retrieval, durable
state outside the model, and preserving source history.

Pinned Letta `0.16.8` still exposes persistent agents, memory blocks, messages,
tools, recall search, and server-managed persistence. Its nearby releases also
expanded context/compaction and memory filesystem behavior. Current Letta Code
material increasingly centers coding-agent needs: filesystem memory, Git history,
Bash, subagents, and long-running workspace continuity. That direction is coherent
for coding agents but is broader and differently shaped than ADE's conversational
companions and structured user memory.

ADE should learn from the architecture, not inherit the product scope. A user fact
should not become an arbitrary text-file edit merely because files are effective
memory for coding agents.

## Black-Box Baseline

The API-only probe created a DGX Qwen Agent Studio agent with the current prompt and
persona, then purged it. Observed behavior:

- Agent creation and initial `human`/`persona` blocks succeeded.
- `memory_replace` recorded `张伟`, then `Rocky`, then refined Rocky to `哈士奇`.
- A forced `conversation_search` request produced an actual tool-call/return pair.
- Persisted Letta messages grew `6 -> 12 -> 18 -> 24` across four turns.
- Raw prompt inspection retained only the latest ten projected messages and varied
  from roughly 6.7K to 19.2K characters as reasoning/tools entered context.
- Manual `human` block editing succeeded.
- A missing model with `retry_count=0` returned one ADE `400` response.
- Archived-agent chat returned `410`; purge succeeded.

The probe proves externally visible behavior, not internal retry counts. It did not
force long-history compaction, concurrent writes, provider timeout races, approval,
or sandbox execution. Those remain explicit study limitations.

## Target Domain Model

### `AgentDefinition`

An immutable, reusable version that contains model/profile selection, prompt and
persona snapshots/hashes, memory-policy version, output policy, and a versioned
curated tool set. Editing creates a new version. Existing conversations retain the
version they were created with unless explicitly rebased.

### `MemorySubject`

The person or account whose durable facts are stored. It is scoped to an ADE
workspace and has an explicit ID even in local-first single-user operation. A model
never receives authority to select or change this ID.

### `Conversation`

Binds one exact agent-definition version to one exact memory subject. It owns
ordered immutable messages, summary lineage, run serialization, and archive state.
Two definitions may share one subject; two subjects must never share projections.

### `Message`

An immutable source record with a monotonically increasing conversation sequence,
role, content, run provenance, and timestamps. Raw history is never replaced by a
summary. Redaction or hard deletion is a separate explicit privacy operation.

### `MemoryFact` And `MemoryRevision`

`MemoryFact` is the current projection of one canonical subject key. The key is
resolved by ADE from a versioned, product-owned fact-type registry; production v3
must not persist arbitrary model-generated key strings. Types define namespace,
value shape, cardinality, aliases, and whether an entity reference is required. For
example, a pet name and breed attach to the same stable pet entity rather than
becoming unrelated keys. Every mutation creates an immutable `MemoryRevision` with
operation, optimistic version, source-message spans/hashes, prior revision lineage,
and run provenance.

- `add`: creates one active fact.
- `correct`: advances one fact and supersedes its prior value.
- `merge`: supersedes two or more active facts and creates one combined fact.
- `forget`: advances the fact to an auditable forgotten tombstone.

Only explicit durable user facts are committed by default. Inferences remain
uncommitted. Forgetting a memory does not silently rewrite immutable conversation
history.

### Derivatives

`ConversationSummary` is immutable and versioned, covers a validated contiguous
message prefix, records generation policy/model/run, and may supersede an earlier
summary. `MemoryEpisode` is the equivalent optional subject/conversation derivative
for episodic retrieval. Both are replaceable projections, never source authority.

### `Run`, `RunAttempt`, `RunEvent`, And `ToolDefinition`

A `Run` owns one accepted turn and idempotency contract. Attempts record exact
timeouts/retries/provider outcomes. Events form the ordered audit/stream surface.
`ToolDefinition` is immutable, curated, schema-versioned, and mapped to an
ADE-controlled handler rather than arbitrary uploaded code.

## Proposed Breaking v3 API

No `/api/v2` compatibility layer or legacy importer is proposed.

| Operation | Proposed endpoint |
| --- | --- |
| Create/list definitions | `POST/GET /api/v3/agent-definitions` |
| Add immutable definition version | `POST /api/v3/agent-definitions/{id}/versions` |
| Create/list subjects | `POST/GET /api/v3/memory-subjects` |
| Inspect subject facts/revisions | `GET /api/v3/memory-subjects/{id}/memories` |
| Manual typed memory operation | `POST /api/v3/memory-subjects/{id}/memory-operations` |
| Create/list conversations | `POST/GET /api/v3/conversations` |
| Conversation state | `GET /api/v3/conversations/{id}/state` |
| Accept turn | `POST /api/v3/conversations/{id}/turns` |
| Inspect/cancel run | `GET /api/v3/runs/{id}`, `POST /api/v3/runs/{id}/cancel` |
| Stream normalized events | `GET /api/v3/runs/{id}/events` |

Turn acceptance is asynchronous (`202`). The request contains `content`,
`idempotency_key`, `timeout_seconds`, and `retry_count`. It cannot contain a subject
ID, model override, memory block label, or arbitrary tool code. The response returns
the run ID and event stream URL. Agent Studio renders normalized events and refreshes
conversation/subject projections at terminal state.

## PostgreSQL Authority

PostgreSQL becomes the sole ADE state authority. Use an `ade` schema and a separate
least-privilege application role. The target ownership model is:

```text
ade.workspaces
ade.agent_definitions
ade.tool_definitions
ade.agent_definition_tools
ade.memory_subjects
ade.conversations
ade.messages
ade.runs
ade.run_attempts
ade.run_events
ade.outbox
ade.memory_facts
ade.memory_revisions
ade.memory_revision_sources
ade.conversation_summaries
ade.summary_sources
ade.memory_episodes             # contract retained; feature initially gated
ade.episode_sources
ade.memory_embeddings           # only if semantic retrieval is accepted
ade.conversation_run_leases
```

Required constraints:

- Unique `(workspace_id, definition_key, version)` agent definitions.
- Conversations reference an exact immutable definition-version row and subject.
- Unique `(conversation_id, sequence)` immutable messages.
- Unique `(conversation_id, idempotency_key)` runs plus stored request hash.
- Partial unique active run/lease per conversation.
- Unique `(run_id, sequence)` events and `(run_id, attempt_number)` attempts.
- Partial unique active `(subject_id, normalized_key)` memory facts.
- Unique `(fact_id, fact_version)` memory revisions.
- Evidence foreign keys to immutable messages with validated offsets/content hashes.
- Unique `(conversation_id, version)` summaries with validated contiguous sources.
- Foreign keys include workspace/subject consistency; model arguments cannot bypass
  these boundaries.

State changes, terminal run status, terminal events, and outbox records commit in
one transaction. Event streaming reads the outbox/run-event sequence. Redis is not
part of this design.

`pgvector` remains an implementation choice rather than an assumption. Phase 1 can
start with active-profile selection, exact matching, PostgreSQL text/trigram search,
and explicit deep search, but the live Chinese-to-English miss proves that lexical
search alone cannot pass cutover. Benchmark multilingual embeddings against explicit
normalization; if embeddings win at acceptable p95 latency/storage cost, add
`memory_embeddings` with explicit embedding model/version/dimension.

## Context Construction

The context order is fixed:

1. Agent system prompt and persona snapshot.
2. Compact active profile for the bound subject.
3. Latest valid conversation summary.
4. Automatically retrieved relevant facts and accepted episodes.
5. Recent raw turns after the summary boundary.
6. Current user message.

The model profile supplies its real context window and tokenizer. For each run:

```text
input_budget = context_window
             - max_output_tokens
             - serialized_tool_schema_tokens
             - max(256, 5% context_window safety margin)
```

The current user message is never silently truncated. Prompt/persona snapshots use
configured hard caps. Profile, summary, retrieval, and recent-history sections each
have measurable caps; overflow drops lowest-ranked retrieval, then oldest recent
turns. If the current message plus mandatory prompt cannot fit, reject before a
provider call. Every run event records the tokenizer/model profile, section token
counts, omitted IDs, retrieved IDs, and output cap.

Summarization triggers before a future turn when raw eligible history would exceed
its section budget. It summarizes only complete turns through a validated sequence,
emits its own run/events, and never deletes source messages. A failed summary either
falls back to a previously valid version or produces an explicit context error.

## Memory Write Contract

The server binds every proposal to the run's subject and current user source
messages. Validation proceeds in this order:

1. Parse the closed operation schema; reject unknown fields and subject selectors.
2. Resolve an exact user-message evidence span and verify its content hash.
3. Reject hypothetical, uncertain, inferred, temporary, or third-party-only claims.
4. Resolve the requested fact type/entity through the versioned registry; validate
   value shape, cardinality, aliases, size, and operation-specific required fields.
5. For `correct`/`forget`, lock and verify `fact_id` plus `expected_version`.
6. For `merge`, verify every target belongs to the subject and every version matches.
7. Prove a new value is a lossless canonicalization of current evidence plus any
   explicitly referenced prior facts. Store original-language values by default.
8. Stage proposals during the model loop; commit only with the successful assistant
   message and terminal run events.

Conflicts are not silently overwritten. A subject write conflict may trigger one
explicit memory-replan step within the same run if budget remains; it is not a
transport retry and is visible as an event.

## Concurrency, Idempotency, Cancellation, And Recovery

### Locking

A durable conversation lease, not an in-process lock, prevents concurrent accepted
turns across API workers. The acceptance transaction creates the user message, run,
and lease atomically. A worker owns/heartbeats the lease with expiration.

Model calls do not hold a PostgreSQL transaction open. At commit, the worker locks
the conversation and subject rows in deterministic UUID order, rechecks lease,
conversation version, cancellation, and memory optimistic versions, then commits.
Different conversations sharing one subject may execute concurrently but serialize
their final subject writes.

### Idempotency

`(conversation_id, idempotency_key)` is unique. ADE stores a canonical SHA-256 of
content, definition/model/tool/policy snapshots, timeout, and retry count. Repeating
the same key/hash returns the existing run. Reusing the key with a different hash is
`409 Conflict`, including after completion.

### Cancellation

Cancellation is idempotent. It records `cancellation_requested_at`; workers poll and
cancel local tasks/provider streams when supported. A provider may continue remotely,
so cancellation means “ADE will not commit its late result,” not proof that remote
compute stopped. The accepted user message remains immutable; no assistant message
or staged memory is committed. A terminal success committed before cancellation
wins; otherwise cancellation wins at the final transaction check.

Abandoned `running` runs are detected by expired leases. Recovery marks the attempt
failed and either performs an explicitly allowed ADE retry or terminates the run. It
never guesses whether a side-effecting tool succeeded. Initial v3 tools are staged or
read-only, avoiding ambiguous external side effects.

### Retry And Timeout Ownership

- All provider SDK/framework retries: `0`.
- Model Router forwarding retries: `0`.
- `retry_count`: additional ADE attempts after the first, capped at `5`.
- `timeout_seconds`: cap for one complete model/tool attempt.
- Retryable: connect/read/write/protocol transport failures, `429`, and `5xx` before
  irreversible effects.
- Non-retryable: validation, auth, ordinary `4xx`, cancellation, and exhausted
  protocol/model-step budget.
- Backoff: full jitter over `0.5 * 2^(attempt-1)` seconds, capped at `4s` and by the
  run deadline; bounded `Retry-After` is honored.
- The absolute run deadline records all attempt budgets plus the maximum backoff
  budget. Attempts and repair/model steps are separate concepts in events.

## Normalized Event Contract

Every event has this immutable envelope:

```json
{
  "id": "event UUID",
  "schema_version": 1,
  "run_id": "run UUID",
  "sequence": 7,
  "attempt": 1,
  "type": "tool.call.completed",
  "occurred_at": "UTC timestamp",
  "correlation_id": "run UUID",
  "causation_id": "prior event UUID or null",
  "visibility": "operator|private",
  "payload": {}
}
```

Initial event types are run accepted/started/completed/failed/cancel-requested/
cancelled; context built; model request/response/protocol-repair; tool call requested/
completed; memory proposed/rejected/committed; message committed; summary committed;
and retry scheduled. Tool request/result events require the same call ID. Provider
request IDs, model/profile, finish reason, usage, latency, and error class are
normalized. Raw provider payload and reasoning are retained for synthetic evals;
production reasoning is private, redacted from normal UI, and governed by retention.

## Tools, Approval, And Sandboxing

The prototype exposes only:

- `propose_memory_change` (staged write).
- `search_memory` (subject-bound read).
- `get_weather` (deterministic read-only fixture).

Production v3 begins with curated, versioned handlers and explicit side-effect
classification. Arbitrary Tool Center Python/npm/pip execution, arbitrary shell,
sandbox workers, and approval UI are deferred. If later required, they need their
own threat model, isolation boundary, idempotency contract, and ADR; they must not be
smuggled into the core runtime migration.

## Retrieval Experiment

The deterministic lexical benchmark produced:

| Variant | Recall | Cases |
| --- | ---: | ---: |
| Fact only | `0.40` | 5 |
| Fact plus episode | `0.80` | 5 |

This is enough to retain the optional `MemoryEpisode` contract in the v3 model. It
is not enough to enable episode persistence by itself: the cases are small and
handcrafted. More importantly, both variants miss the Chinese query for an English
`Royal Ontario Museum` fact. The corrected live deep-search fixture reproduces that
miss on both local models even though both correctly call `search_memory`. A
multilingual semantic retrieval capability is therefore required before cutover;
the next benchmark must compare embeddings/pgvector against explicit multilingual
normalization using held-out aliases, false positives, p50/p95 latency, index/storage
cost, and provenance-valid episode generation.

## Executor Comparison

Both adapters share context building, memory policy, tools, timeout/retry ownership,
event normalization, fixtures, repository, and scoring.

PydanticAI was installed as the official slim OpenAI extra. Its OpenAI client uses
`max_retries=0`, and agent tool/output retries are both zero. In deterministic tests,
the minimal custom loop passes normal replies, multiple tools, malformed arguments,
provider failures, cancellation, exact retries/timeouts, idempotency, reasoning,
tool failure, and reasoning-only protocol repair. The tested PydanticAI adapter
cannot recover a malformed tool call with tool retries at zero; enabling framework
tool retries would create a second retry/model-step owner. A custom PydanticAI
argument adapter could be studied later, but its added protocol code must be counted.

The mandated weights are comprehension/maintainability `30%`, explicit control
`25%`, observability `15%`, provider/tool fidelity `15%`, dependency/security `10%`,
and measured overhead `5%`. Source/dependency/overhead metrics are diagnostics, not
proof of product correctness. Mandatory gates always override weighted score; exact
ties favor fewer ADE-owned protocol lines.

Current static result: the minimal custom loop passes all `12/12` contracts with a
weighted diagnostic score of approximately `82.5`. The tested PydanticAI adapter
passes `10/12`, fails mandatory reasoning-only and malformed-argument recovery, and
scores approximately `76.3`.
Those scores do not override its failed gate.

### Live Model Evidence

Live requests went through Model Router with every SDK/framework retry set to zero:

- DGX Qwen passed the restored seven-turn fact-capture assertions for `张伟`,
  `Rocky`, and `哈士奇`, assistant disclosure checks, and normalized trace checks.
  It required an explicit reasoning-only protocol-repair model step. The run also
  produced two active Rocky-name facts under semantically duplicate free-form keys;
  this is why the target contract now requires ADE-owned fact types and cardinality
  rather than arbitrary model keys.
- llama-server completed the same seven turns and captured Rocky plus Husky, but it
  omitted `张伟`. Increasing the output allowance to `4096` did not fix the miss.
- DGX initially repeated an identical staged `name` proposal and failed only at
  commit. Moving batch-conflict validation to proposal time made the focused
  cross-subject isolation rerun pass without weakening subject boundaries.
- After removing seeded-memory leakage from recent conversation history, both models
  called `search_memory` for the Chinese museum query and received no lexical match
  for the English fact. This is a real retrieval failure, not a tool-selection
  failure.
- The custom loop passed weather selection and deterministic weather failure on both
  DGX Qwen and llama-server with correlated tool events.
- The PydanticAI adapter passed the focused weather-selection smoke on both models,
  but that does not repair its deterministic mandatory-gate failures.

Accordingly, the custom loop is a provisional implementation direction, not a
production-qualified runtime. No candidate currently passes all required memory
correctness, normalization, multilingual retrieval, and both-local-model gates.

## Roadmap

### Phase 0: Decision Review

Review this study and proposed ADR. Resolve live model gates, retention policy, and
the memory-review strategy. No production implementation begins without approval.

### Phase 1: Native Persistence

Add ADE PostgreSQL migrations/repositories for immutable definitions, subjects,
conversations, messages, runs/events/outbox, and facts/revisions. Add transaction,
lease, optimistic-lock, isolation, and crash-recovery tests. Keep Letta production.

### Phase 2: Runtime Behind An Internal Flag

Implement the selected executor, context builder, staged memory policy, curated
tools, cancellation, and normalized events against native repositories. Run shadow
synthetic evals only; do not dual-write real agents.

### Phase 3: Breaking v3 API And Agent Studio UI

Add v3 definitions/subjects/conversations/runs/events and migrate Agent Studio to the
new mental model. Keep v2/Letta as the current product until v3 passes acceptance.

### Phase 4: Eval Parity

Require deterministic and live parity for memory correctness, isolation, old-memory
retrieval, compaction, false-memory prevention, tools, retries, cancellation, and
both local models. Test Center owns comparison artifacts.

### Phase 5: Fresh-Start Cutover

Switch new Agent Studio to v3 with a fresh store. Do not import legacy Letta agents.
Provide an explicit operator reset boundary and archive old evidence as needed.

### Phase 6: Remove Letta And Redis

Delete Letta adapters, v2 Agent Studio runtime paths, embedding-handle coupling,
Letta Tool Center runtime behavior, Compose services, environment variables, tests,
and docs. Retain PostgreSQL; add pgvector only if accepted by evidence.

### Phase 7: Rename Project

After Letta is absent from code, runtime, docs, and operator vocabulary, decide and
execute a separate coordinated project rename.

## Acceptance Gates

Replacement work may not cut over until all are true:

- Memory add/correct/merge/forget correctness and provenance pass.
- Cross-agent sharing and cross-subject isolation pass under concurrency.
- Exact timeout, cancellation, idempotency, and retry ownership pass.
- Tool calls/results correlate and failures preserve complete traces.
- Raw history survives summary/compaction and old memory remains retrievable.
- False memories are not committed.
- DGX Qwen passes the restored `张伟`/`Rocky`/`哈士奇` baseline with no forbidden
  disclosure.
- llama-server passes the defined compatibility protocol and memory gate.
- Full Python tests, Ruff, `make check`, and live artifacts pass.
- ADR 0009 is explicitly reviewed and accepted by the user.

## Open Questions

- Should a dedicated required memory-review model step be used when conversational
  models skip optional tool calls, or should memory quality remain prompt-driven?
- What production retention/redaction period should apply to private reasoning and
  raw provider payloads?
- Which multilingual semantic strategy passes held-out recall/precision and latency,
  and does its evidence justify pgvector and persisted episodes?
- Which initial production weather/search provider and error contract should replace
  the deterministic fixture?
- Is Tool Center arbitrary execution still a product requirement after curated v3
  tools, and if so, what separate sandbox/approval architecture should own it?
