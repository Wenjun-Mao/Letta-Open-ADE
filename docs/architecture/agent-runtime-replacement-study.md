# ADE-Native Agent Runtime Replacement Study

- Study date: 2026-08-29
- Production impact: none
- Decision state: implementation accepted; Phase 4 paired-baseline candidate
  qualification and Phase 5 effective cutover evidence remain pending
- Reproducible workflow: [`workflows/evals/agent_runtime_study/`](../../workflows/evals/agent_runtime_study/README.md)
- Accepted implementation decision: [ADR 0009](../adr/0009-ade-owned-agent-runtime.md)
- Cutover contract: [ADR 0016](../adr/0016-ade-native-agent-studio-cutover.md)
- Baseline gate semantics: [ADR 0017](../adr/0017-incumbent-baseline-does-not-veto-native-cutover.md)

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

The study now has the core product contracts that were previously missing: a closed
fact/entity registry, a separate subject-bound memory reviewer, atomic review and
assistant commit, multilingual semantic retrieval, and exact deployment
qualification. These additions strengthen the custom loop recommendation without
making it production-ready.

The study establishes a candidate architecture, not effective product cutover
evidence. Qualification and compatibility artifacts are necessary technical inputs,
but they do not prove that the native candidate satisfies the shared product outcome.
Under [ADR 0016](../adr/0016-ade-native-agent-studio-cutover.md) and
[ADR 0017](../adr/0017-incumbent-baseline-does-not-veto-native-cutover.md), three
clean content-addressed schema-v2 paired DGX rounds with native `3/3` and
non-regression, current requalification, and reviewed Test Center comparison
artifacts are still required before any cutover claim.

The follow-up implementation lives under
`services/ade-api/src/ade_api/features/agent_runtime_v3/`. It adds an opt-in
`/api/v3` API, separate PostgreSQL schema, worker, Router-routed embeddings, typed
memory review, and normalized run events. It does not change the supported `/api/v2`
Agent Studio path or this study's recorded qualification evidence.

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
| Primary chat/reviewer artifact | `Qwen/Qwen3.6-35B-A3B-FP8` at `95a723d08a9490559dae23d0cff1d9466213d989` |
| DGX runtime | vLLM `0.19.2rc1.dev134+gfe9c3d6c5`, image `sha256:ffa30d66ff5c9346c6389507cc529827fc9934a6d2ee37855934f94fe1061cdc` |
| Compatibility artifact | `unsloth/Qwen3.5-27B-GGUF/Qwen3.5-27B-UD-Q4_K_XL.gguf` at `30d153c8bdfd8ea1f25d47c4d2c4933cbb5bca52` |
| Compatibility artifact SHA-256 | `13cb6228344898afa50d963c02ae0d991ae25094eea8837db8d0e452e91c5888` |
| llama-server runtime | build `b1-225088e`, `8192` context tokens, `4` slots |
| Retriever artifact | `Qwen/Qwen3-Embedding-0.6B` at `97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` |

The route aliases `dgx_vllm::qwen3.6-35b-a3b-fp8` and
`local_llama_server::gemma4` are routing conveniences, not model identities. Every
artifact also contains the repository revision/status, workflow-tree hash, fixture
hash, `uv.lock` hash, exact policy-bundle hashes, effective non-secret config, and
live Model Router catalog.

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
- [Qwen3-Embedding-0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [vLLM pooling models](https://docs.vllm.ai/en/stable/models/pooling_models/)

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
| Embedding discovery/retrieval | Letta | Rebuild as versioned subject-bound semantic retrieval |
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
- `merge` (deferred): requires a typed, server-owned rule for combining distinct
  facts. It is not exposed by the initial v3 reviewer because one active fact per
  canonical key makes a generic same-key merge unreachable.
- `forget`: advances the fact to an auditable forgotten tombstone.

Only explicit durable user facts are committed by default. Inferences remain
uncommitted. Forgetting a memory does not silently rewrite immutable conversation
history.

### `MemoryReviewer`

Memory extraction is a required model role, not a conversation tool. It runs after
the conversation model has produced a candidate user-visible response, but it sees
only the current user message, prior user-authored messages, and an ADE-built
inventory of active facts and entity references. Assistant text is excluded to
prevent persona details or model guesses from becoming user memory. ADE binds the
subject server-side and assigns durable entity IDs; reviewer arguments cannot name
or switch subjects.

The reviewer emits a closed batch of typed proposals. ADE resolves exact evidence
spans, applies registry/cardinality/entity rules, and validates the whole batch
before any mutation. A failed review, malformed operation, conflict, or provider
failure aborts the candidate assistant response and all staged memory revisions.
There is no fallback reviewer and no partial batch commit.

### Derivatives

`ConversationSummary` is immutable and versioned, covers a validated contiguous
message prefix, records generation policy/model/run, and may supersede an earlier
summary. `MemoryEpisode` remains a possible future derivative, but it is not part of
the initial recommended v3 persistence model because held-out semantic fact
retrieval passed without episodes. Any future episode store must remain a
replaceable projection, never source authority.

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
ade.memory_embeddings
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

Use PostgreSQL `pgvector` for semantic fact vectors while retaining exact/text
filters for fact type, entity, status, workspace, and subject. Every embedding row
records source fact/revision, model artifact revision, dimensions, normalization,
and retrieval-policy version. A changed embedding fingerprint requires controlled
re-embedding into a new version before traffic switches; it must never silently mix
incompatible vector spaces. The live Qwen3-Embedding-0.6B benchmark passed the
defined multilingual quality, isolation, and latency gates, while lexical retrieval
had already failed the Chinese-to-English case.

## Context Construction

The context order is fixed:

1. Agent system prompt and persona snapshot.
2. Compact active profile for the bound subject.
3. Authoritative history metadata derived from immutable messages.
4. Latest valid conversation summary as a lossy narrative derivative.
5. Automatically retrieved relevant facts and accepted episodes.
6. Recent raw turns after the summary boundary.
7. Current user message.

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

When an accepted turn crosses the raw-history section budget, summarization is a
sub-operation of that same turn. It summarizes only complete prior turns through a
validated sequence and never deletes source messages. Its versioned summary and
provenance commit atomically with the assistant message, reviewer changes, terminal
run state, events, and outbox records; a failure commits none of those turn results
and produces an explicit context error. Exact counts and sequence boundaries are
computed from the immutable log and supplied separately; only a user message with a
same-run committed assistant reply counts as a completed turn. Generated summary
prose cannot override those values.

## Memory Review And Write Contract

The conversation executor cannot write memory. After it returns a candidate reply,
the required reviewer receives a server-built, subject-bound review packet. The
server binds every reviewer proposal to the run's subject and user-authored source
messages. Validation proceeds in this order:

1. Parse the closed operation schema; reject unknown fields and subject selectors.
2. Resolve an exact user-message evidence span and verify its content hash.
3. Reject hypothetical, uncertain, inferred, temporary, or third-party-only claims.
4. Resolve the requested fact type/entity through the versioned registry; validate
   value shape, cardinality, aliases, size, and operation-specific required fields.
5. For `correct`/`forget`, lock and verify `fact_id` plus `expected_version`.
6. Prove a new value is a lossless canonicalization of current evidence plus any
   explicitly referenced prior facts. Store original-language values by default.
7. Validate the complete proposal batch, including duplicate/cardinality conflicts.
8. Commit valid revisions only with the successful assistant message and terminal
   run events. Any reviewer or proposal failure aborts the whole candidate turn.

Conflicts are not silently overwritten. A subject write conflict may trigger one
explicit memory-replan step within the same run if budget remains; it is not a
transport retry and is visible as an event.

Operation meaning is not inferred away at the storage boundary. A correction must
use `correct`; `forget` is accepted only for explicit user intent to remove retained
information. In the final live matrix, the reviewer emitted `forget` plus `add` for
one location correction and later emitted `add` against an existing fact. Both were
rejected atomically rather than normalized into a write with different semantics.

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

The conversation prototype exposes only:

- `search_memory` (subject-bound read).
- `get_weather` (deterministic read-only fixture).

Memory review is a separate required role and protocol, not a model-visible tool.
This prevents conversation personas, assistant prose, and tool-loop choices from
becoming memory authority.

Production v3 begins with curated, versioned handlers and explicit side-effect
classification. Arbitrary Tool Center Python/npm/pip execution, arbitrary shell,
sandbox workers, and approval UI are deferred. If later required, they need their
own threat model, isolation boundary, idempotency contract, and ADR; they must not be
smuggled into the core runtime migration.

## Retrieval Experiment

The initial deterministic lexical benchmark was useful as a failure baseline: fact
only recalled `0.40` and fact plus episode recalled `0.80` across five handcrafted
cases, while both missed the Chinese query for an English `Royal Ontario Museum`
fact. That established multilingual semantic retrieval as a mandatory gate, not a
future optimization.

The implemented semantic benchmark uses the exact
`Qwen/Qwen3-Embedding-0.6B` revision
`97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3` through a dedicated vLLM pooling
sidecar. The workflow calls its OpenAI-compatible embeddings endpoint directly with
SDK retries disabled. A six-case calibration set selects an automatic-retrieval
threshold, and a disjoint 12-case held-out set evaluates eight positives, five
cross-lingual cases, four hard negatives/isolation checks, and a 1,000-document
corpus.

Latest complete live result:

| Metric | Result | Gate |
| --- | ---: | ---: |
| Calibration precision | `1.00` | `>= 0.95` |
| Calibration recall | `1.00` | `>= 0.95` |
| Overall held-out recall | `1.00` | `>= 0.95` |
| Cross-lingual recall at 3 | `1.00` | `1.00` |
| Hard-negative false-positive rate | `0.00` | `<= 0.05` |
| Held-out p95 latency | `101.3 ms` | `<= 250 ms` |

Subject isolation also passed. Automatic retrieval uses the calibrated threshold
(`0.6311` in this run). Explicit `search_memory` intentionally returns top
subject-bound candidates without that threshold because short deliberate queries
otherwise traded away recall. This difference is an explicit product contract, not
a hidden tuning exception. The acceptance case for this boundary writes more facts
than the compact profile can hold through a separate same-subject conversation, then
uses a measured below-threshold query from a fresh conversation. This prevents raw
setup history or the active profile from satisfying the case before the explicit
search tool is exercised.

Semantic fact retrieval now satisfies the study gate without persisted episodes, so
episodes are deferred from initial v3. The prototype currently re-embeds its
in-memory corpus per search; production must persist versioned vectors in pgvector
and measure incremental indexing, storage, and re-embedding operations before
cutover.

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
scores approximately `76.9`.
Those scores do not override its failed gate.

### Live Model Evidence

Live requests went through Model Router with SDK/framework retries at zero. The
explicit study command used one additional ADE retry for transient transport
failures; the final llama behavioral failure was not retryable and was not retried
away. Conversation generation used each selected model, while DGX Qwen was the
required reviewer for both matrices.

The final full DGX matrix (`agent-runtime-study-20260829_133925`) passed `12/12`:

- Baseline memory captured `张伟`, `Rocky`, and `哈士奇` on the correct typed subject
  and pet entity.
- Correction, forgetting, cross-agent sharing, cross-subject isolation, deep search,
  compaction, false-memory prevention, both weather traces, and private-reasoning
  non-disclosure all passed.
- The strict correction contract remained unchanged: the successful reviewer output
  used an accepted typed correction rather than relying on normalization of an
  invalid `forget` plus `add` batch.
- The ten runtime cases took about `653.5s` in total (`65.3s` mean); the seven-turn
  baseline accounted for `190.1s`. These are diagnostic end-to-end case timings,
  not provider throughput benchmarks.

Earlier runs under now-stale policy fingerprints rejected invalid correction
proposals from the same reviewer deployment (`forget` plus `add`, or `add` against
an existing singleton fact). Those artifacts do not count toward current
qualification, but they remain useful evidence that one successful round is not a
stability claim and that the three-consecutive-round gate is necessary.

The final full llama-server matrix (`agent-runtime-study-20260829_135040`) passed
`11/12`:

- Baseline typed memory, forgetting, sharing/isolation, deep search, compaction,
  false-memory prevention, correction, and normal weather selection passed.
- The conversation model told the user that `FAIL_CITY` lookup failed without ever
  calling `get_weather`. The assistant prose sounded plausible, but the required
  correlated tool-call/failure trace was absent, so the case correctly failed.
- Role-specific evidence marked the llama conversation role failed and the DGX
  reviewer role passed; a combined case score no longer contaminates both roles.
- The ten runtime cases took about `97.0s` in total (`9.7s` mean). The alias
  `local_llama_server::gemma4` actually resolved to the fingerprinted Qwen3.5-27B
  GGUF deployment recorded above.

The semantic retriever and DGX reviewer passed in both final complete runs, so each
has two consecutive passing rounds under the current fingerprint. DGX conversation
has one passing round because it was observed only in the DGX matrix. The llama
conversation role has zero consecutive passes after its failed round. All remain
candidates until their own three-round gates pass; the unavailable llama runtime
binary digest independently prevents that deployment from qualifying.

These results distinguish executor correctness from deployment qualification. The
custom loop is still the simplest passing executor and remains the provisional
implementation direction. The current model/reviewer fingerprints are not
production-qualified, and rerunning only the failed cases cannot advance them.

## Deployment Churn And Qualification

Local model names are expected to change as better artifacts become available. The
runtime therefore separates stable product roles from mutable routing aliases and
exact deployment identities:

- Product roles are `conversation`, `reviewer`, and `retriever`.
- A route alias selects a candidate but carries no qualification by itself.
- A deployment may publish stable selection aliases alongside the provider's current
  advertised route. At least one declared alias must match the live catalog so the
  router can attach the immutable deployment record; native definitions may then
  bind a stable alias without inheriting qualification from the alias text.
- A deployment fingerprint includes artifact revision/digest, served model, runtime
  implementation/version/image digest, endpoint role, hardware, context and sampling
  settings, plus prompt/tool/schema/retrieval policy hashes.
- A changed artifact, quantization, runtime, context, sampling profile, embedding
  space, or policy bundle creates a new effective fingerprint. Prior rounds become
  stale rather than being inherited by a familiar alias.
- Release requires three consecutive passing complete rounds for every required
  role. Conversation and reviewer rounds count only when the minimal custom loop
  covers the complete canonical fixture matrix. Focused diagnostics remain useful
  evidence but cannot advance qualification.
- Retriever rounds use the complete calibration and held-out retrieval suite.
- The normal release gate rejects candidates. The harness has an explicit
  study/development override solely to collect evidence, and every use is recorded.
- There is no reviewer fallback. A fallback would make the effective memory policy
  depend on runtime availability and hide which deployment produced state.

This turns model upgrades into measured replacement candidates rather than source
code migrations. A newer DGX or llama-server model can be registered under any
convenient alias, but it serves a role only after its exact fingerprint independently
passes the role gate. Rollback means selecting a still-qualified prior fingerprint,
not pretending two model artifacts are interchangeable.

## Roadmap

### Phase 0: Decision Review

Review this study and proposed ADR. Resolve reviewer-deployment reliability,
retention policy, and operational ownership for embedding qualification/re-indexing.
No production implementation begins without approval.

### Phase 1: Native Persistence

Add ADE PostgreSQL migrations/repositories for immutable definitions, subjects,
conversations, messages, runs/events/outbox, and facts/revisions. Add transaction,
lease, optimistic-lock, isolation, crash-recovery, and versioned pgvector tests. Keep
Letta production.

### Phase 2: Runtime Behind An Internal Flag

Implement the selected executor, context builder, required reviewer, typed memory
policy, semantic retrieval, curated tools, cancellation, and normalized events
against native repositories. Run shadow synthetic evals only; do not dual-write real
agents.

### Phase 3: Breaking v3 API And Agent Studio UI

Add v3 definitions/subjects/conversations/runs/events and migrate Agent Studio to the
new mental model. Keep v2/Letta as the current product until v3 passes acceptance.

### Phase 4: Eval Parity

Require three complementary evidence classes rather than forcing incomparable domain
models into one score. Test Center owns content-addressed paired v2/v3 artifacts for
the common conversational and durable-user-fact outcome. The canonical native matrix
proves v3-only subject isolation, retrieval, compaction, false-memory prevention,
tools, and trace semantics. Deterministic conformance proves retry, cancellation, and
idempotency contracts. Three clean schema-v2 paired DGX candidate rounds with native
`3/3` and non-regression, three native qualification rounds, conformance, and a
rollback rehearsal are all required before a release claim; llama-server remains
compatibility evidence until independently qualified.

### Phase 5: Fresh-Start Cutover

After the Phase 4 gate, switch new Agent Studio exclusively to v3 with a fresh ADE
PostgreSQL store. Do not import legacy Letta agents, dual-write, add a UI/runtime
toggle, or fall back per request. The initial selectable deployment is the exact
qualified DGX conversation/reviewer/retriever bundle; llama-server is compatibility
only. Provide an admin-only, idempotent, transactional reset scoped to
`purpose=agent_studio`; it refuses active runs, records a receipt, and increments the
workspace generation. Rollback is release-level to the prior v2 deployment while v3
state remains isolated. Retain Letta, Redis, v2 endpoints, and old evidence until
Phase 6 verifies that no product traffic or dependency remains.

### Phase 6: Remove Letta And Redis

Delete Letta adapters, v2 Agent Studio runtime paths, embedding-handle coupling,
Letta Tool Center runtime behavior, Compose services, environment variables, tests,
and docs. Retain PostgreSQL; add pgvector only if accepted by evidence.

### Phase 7: Rename Project

After Letta is absent from code, runtime, docs, and operator vocabulary, decide and
execute a separate coordinated project rename.

## Acceptance Gates

Replacement work may not cut over until all are true:

- Memory add/correct/forget correctness and provenance pass. A future typed merge
  operation requires its own accepted contract and qualification cases.
- Cross-agent sharing and cross-subject isolation pass under concurrency.
- Exact timeout, cancellation, idempotency, and retry ownership pass.
- Tool calls/results correlate and failures preserve complete traces.
- Raw history survives summary/compaction and old memory remains retrievable.
- False memories are not committed.
- Conversation, reviewer, and retriever fingerprints each have three consecutive
  passing complete rounds; no study override or fallback appears in a release run.
- DGX Qwen passes the restored `张伟`/`Rocky`/`哈士奇` baseline with no forbidden
  disclosure.
- llama-server passes the defined compatibility protocol and memory gate.
- Full Python tests, Ruff, `make check`, and live artifacts pass.
- ADR 0016 and ADR 0017's evidence gate is satisfied with current requalification
  and three clean schema-v2 paired DGX Test Center rounds where native passes every
  round and does not trail the observed incumbent; implementation authorization is
  not evidence.

## Open Questions

- Which reviewer prompt/schema/model combination can pass three consecutive complete
  rounds without weakening `correct` versus `forget` semantics?
- What production retention/redaction period should apply to private reasoning and
  raw provider payloads?
- What is the production re-embedding rollout, storage budget, and rollback process
  when the retriever artifact changes?
- Should episodes ever be introduced after fact-only semantic retrieval, and what
  held-out improvement would justify their added provenance and lifecycle cost?
- Which initial production weather/search provider and error contract should replace
  the deterministic fixture?
- Is Tool Center arbitrary execution still a product requirement after curated v3
  tools, and if so, what separate sandbox/approval architecture should own it?
