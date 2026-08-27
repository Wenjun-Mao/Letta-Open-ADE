# ADR 0009: ADE Owns The Conversational Agent Runtime

- Status: Proposed; not accepted or implemented
- Date: 2026-08-27
- Study: [ADE-Native Agent Runtime Replacement Study](../architecture/agent-runtime-replacement-study.md)

## Context

Agent Studio currently delegates persistent agents, free-text memory blocks, recall
history, compaction, and the agent/tool loop to Letta `0.16.8`. ADE owns the product
UI, prompts/personas, Model Router, timeout/retry controls, lifecycle projection, and
evals, but its primary agent state and behavior remain shaped by Letta.

Letta's general and current coding-agent direction includes a much broader memory
and execution model than ADE needs. ADE's intended product is a conversational
companion with explicit, correct, isolated user memory and a small curated tool set.
Free-text model-edited blocks make correction, forgetting, provenance, subject
sharing, and deterministic validation harder than necessary.

The accompanying study traced all dependencies, black-boxed current behavior through
ADE API, independently prototyped target contracts, and compared a minimal custom
model/tool loop with PydanticAI `2.35.1`. Production behavior was not changed.

## Proposed Decision

ADE will eventually own a fresh conversational agent runtime with these boundaries:

- PostgreSQL is the sole authority for agent-definition versions, memory subjects,
  conversations, immutable messages, runs/events, structured memories, and
  replaceable derivatives.
- An immutable agent-definition version is reusable across memory subjects.
- A conversation explicitly binds one definition version to one subject.
- Durable memory uses typed `add`, `correct`, `merge`, and `forget` operations with
  source-message spans, hashes, optimistic versions, and auditable tombstones.
- ADE resolves memory keys through a versioned fact-type registry with value shape,
  cardinality, aliases, and entity-binding rules; models cannot invent persisted
  key namespaces.
- Raw messages are immutable. Summaries and optional episodes are versioned
  derivatives and never replace their source history.
- Context construction, memory policy, retries/timeouts, tools, and normalized events
  remain ADE-owned and outside the replaceable executor adapter.
- Model Router remains the only provider-facing generation boundary.
- Initial tools are curated ADE handlers. Arbitrary Tool Center code execution,
  approvals, and a replacement sandbox are not part of the core runtime.
- Redis is not retained without a separately demonstrated requirement.
- pgvector and episode persistence remain gated by held-out semantic-retrieval
  evidence. The current lexical prototype fails a Chinese query for an English fact
  on both local models, so some measured multilingual semantic capability is a
  cutover requirement even if pgvector is not the eventual implementation.
- The eventual API is a clean breaking `/api/v3`; no Letta agent importer or v2
  compatibility layer is required for the fresh-start cutover.

The minimal custom OpenAI-compatible executor is the current provisional choice. It
is the only adapter that passes the deterministic mandatory contracts with one ADE
retry owner. Live DGX exercises pass the restored fact-capture assertions only with
an explicit reasoning-only repair step and also reveal duplicate free-form memory
keys. The llama-server compatibility run omits the user's name. The executor is not
approved for production until ADE-owned fact typing, multilingual old-memory
retrieval, both local-model gates, and the complete acceptance suite pass.

## Required Runtime Semantics

- A database-backed conversation lease serializes accepted turns across workers.
- Shared-subject writes serialize transactionally and use optimistic fact versions.
- State changes, terminal run state/events, and outbox records commit atomically.
- An idempotency key is bound to a canonical request hash; different payload reuse is
  `409 Conflict`.
- SDK/framework/Router retries are zero. `retry_count` means additional ADE attempts.
- Cancellation prevents late assistant/memory commit and acknowledges that remote
  provider compute may continue.
- Every tool call/result and model request/response is correlated in a versioned
  event envelope.
- The current user message is never silently truncated; model-specific token
  accounting and output reservation occur before provider calls.
- The model cannot supply a subject ID or cross a server-bound subject boundary.

## Rejected Alternatives

### Continue Following Letta By Default

This retains mature capabilities but keeps ADE's central product state, memory
semantics, and UI mental model coupled to a broader upstream direction. It does not
solve typed memory correctness or explicit subject reuse.

### Fork Or Copy Letta

This would make ADE responsible for a large general agent platform, migrations,
sandboxing, provider integrations, and upstream security maintenance. The study
instead adopts principles and independently implements only required contracts.

### Make Filesystem/Git Memory The User-Memory Authority

Files and Git are effective for coding-agent workspaces but are a poor primary model
for typed personal facts, correction chains, subject isolation, and forgetting.
They may remain useful for other future products, not this core runtime.

### Adopt PydanticAI As The Product Runtime

The tested slim OpenAI adapter reduces executor source lines, but with framework and
SDK retries set to zero it cannot recover malformed tool arguments. Enabling its
tool retry creates a second policy owner. A future custom argument adapter can be
reconsidered only if it passes the shared harness with less total complexity.

### Dual-Write Letta And Native State

Dual writes create two authorities and ambiguous recovery. The roadmap uses
synthetic shadow evaluation, then a fresh-start cutover without legacy import.

### Rebuild Arbitrary Tool Sandboxing In The First Release

This multiplies security and operational scope before core memory/runtime parity is
known. Curated handlers meet the initial product need; sandboxing requires a later
threat model and decision.

## Consequences

If accepted, ADE gains explicit product semantics, inspectable PostgreSQL state,
deterministic retry/cancellation ownership, subject sharing/isolation, and a smaller
maintainer mental model. It also assumes responsibility for persistence migrations,
leases/recovery, context/summary policy, memory correctness, provider protocol
normalization, and security of curated handlers.

Agent Studio's API and UI will change materially from agents/blocks to definitions,
subjects, conversations, memories, runs, and events. Tool Center and Model Catalog
will lose Letta-backed capabilities unless deliberately replaced. Letta and Redis
remain in production until v3 passes all gates and a fresh-start cutover is approved.

## Guardrails

- Do not implement production replacement work while this ADR is Proposed.
- Do not describe static adapter tests as live-model qualification.
- Do not add a legacy Letta importer, dual-write path, or compatibility aliases.
- Do not expose subject selection in model-controlled tool arguments.
- Do not enable hidden framework/SDK retries.
- Preserve the study harness and generated-artifact format for later comparison.
- Update this ADR to Accepted only after the user reviews the study and explicitly
  approves implementation.
- Record a later cutover ADR if implementation evidence changes material contracts.

## Implementation Status

Only the reproducible study workflow, tests, architecture report, and this proposed
ADR exist. Current `/api/v2`, ADE Web, Letta `0.16.8`, Compose services, PostgreSQL,
Redis, and existing Agent Studio behavior are unchanged.
