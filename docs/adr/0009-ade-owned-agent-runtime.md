# ADR 0009: ADE Owns The Conversational Agent Runtime

- Status: Accepted for implementation; production cutover not approved
- Date: 2026-08-29
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

## Decision

ADE will eventually own a fresh conversational agent runtime with these boundaries:

- PostgreSQL is the sole authority for agent-definition versions, memory subjects,
  conversations, immutable messages, runs/events, structured memories, and
  replaceable derivatives.
- An immutable agent-definition version is reusable across memory subjects.
- A conversation explicitly binds one definition version to one subject.
- Durable memory initially uses typed `add`, `correct`, and `forget` operations with
  source-message spans, hashes, optimistic versions, and auditable tombstones.
- `merge` is deferred until the fact registry defines a typed rule whose result can
  be derived and validated server-side. The active-key uniqueness invariant makes a
  generic same-key merge unreachable, so exposing it would be a misleading contract.
- ADE resolves memory keys through a versioned fact-type registry with value shape,
  cardinality, aliases, and entity-binding rules; models cannot invent persisted
  key namespaces.
- A required memory reviewer runs after conversation generation. It receives only
  subject-bound active facts/entities and user-authored evidence, never assistant
  prose or a model-selectable subject ID. There is no fallback reviewer.
- Assistant output, validated memory revisions, and any summary required for that
  same turn commit atomically. Reviewer, summary, evidence, or optimistic-version
  failure commits neither output, memory, nor a partial summary.
- Raw messages are immutable. Summaries and optional episodes are versioned
  derivatives and never replace their source history.
- Context construction, memory policy, retries/timeouts, tools, and normalized events
  remain ADE-owned and outside the replaceable executor adapter.
- Model Router remains the only provider-facing generation boundary.
- Initial tools are curated ADE handlers. Arbitrary Tool Center code execution,
  approvals, and a replacement sandbox are not part of the core runtime.
- Redis is not retained without a separately demonstrated requirement.
- Multilingual fact retrieval uses versioned embeddings and PostgreSQL `pgvector`.
  Qwen3-Embedding-0.6B passed the held-out recall, cross-lingual, hard-negative,
  isolation, and latency gates. Persisted memory episodes are deferred because
  semantic fact retrieval passes without them; they require separate evidence.
- The eventual API is a clean breaking `/api/v3`; no Letta agent importer or v2
  compatibility layer is required for the fresh-start cutover.

The minimal custom OpenAI-compatible executor is the current provisional choice. It
is the only adapter that passes the deterministic mandatory contracts with one ADE
retry owner. The study now has ADE-owned fact typing and passing multilingual
retrieval. Under the final policy fingerprint, the complete DGX matrix passed
`12/12`; the llama-server compatibility matrix passed `11/12` and failed because its
conversation model claimed a weather-tool failure without issuing the required tool
call. Independent role scoring correctly left that failure with llama conversation
while the DGX reviewer passed. No deployment is release-ready: DGX reviewer and
retriever have two consecutive passing rounds, DGX conversation has one, and llama
conversation has zero.

Model route names are not qualification identities. Conversation, reviewer, and
retriever deployments must be tracked by exact artifact revision or digest, runtime,
hardware, context/sampling settings, and prompt/tool/schema/retrieval policy hashes.
Every changed fingerprint starts a fresh lifecycle and requires three consecutive
passing complete rounds. Focused diagnostics never count as qualification rounds.

## Required Runtime Semantics

- A database-backed conversation lease serializes accepted turns across workers.
- Shared-subject writes serialize transactionally and use optimistic fact versions.
- State changes, terminal run state/events, and outbox records commit atomically.
- When context compaction is required, summary generation is a sub-operation of the
  accepted turn. Its versioned summary, provenance, assistant message, reviewer
  changes, terminal state, events, and outbox records commit together or none do.
- Conversation generation cannot propose memory writes. The required reviewer runs
  after generation, uses a closed discriminated schema, and fails the turn atomically
  if it cannot produce a valid review. Corrections are not treated as forgetting.
- ADE recognizes explicit forgetting requests with one conservative, bilingual intent
  contract used by both reviewer selection and evidence validation. Those turns use a
  forget-only reviewer schema; add/correct memory writes from the same message are
  deferred rather than mixed with a tombstone operation.
- When a subject has no active facts, the reviewer uses an add-only schema because
  correct and forget have no reachable target. Other turns retain the full typed
  operation schema and server-side semantic validation.
- An idempotency key is bound to a canonical request hash; different payload reuse is
  `409 Conflict`.
- SDK/framework/Router retries are zero. `retry_count` means additional ADE attempts.
- Cancellation prevents late assistant/memory commit and acknowledges that remote
  provider compute may continue.
- Every tool call/result and model request/response is correlated in a versioned
  event envelope.
- The current user message is never silently truncated; model-specific token
  accounting and output reservation occur before provider calls.
- Unsummarized history is never silently omitted. Compaction retains at most the
  newest ten raw messages that fit the recent-history budget, binds every older
  message to a contiguous summary boundary, and fails before conversation generation
  if either the compaction request or the remaining raw suffix cannot fit.
- The model cannot supply a subject ID or cross a server-bound subject boundary.

## Preview Operational Readiness

The request-level provider failure trace and API-visible worker-presence blockers are
closed by [ADR 0011](0011-agent-runtime-operational-readiness.md). This removes known
observability gaps but does not qualify a deployment or approve production cutover;
the production-path rounds and reviewed promotion in ADR 0010 still apply.

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

With this decision, ADE gains explicit product semantics, inspectable PostgreSQL state,
deterministic retry/cancellation ownership, subject sharing/isolation, and a smaller
maintainer mental model. It also assumes responsibility for persistence migrations,
leases/recovery, context/summary policy, memory correctness, provider protocol
normalization, and security of curated handlers.

Agent Studio's API and UI will change materially from agents/blocks to definitions,
subjects, conversations, memories, runs, and events. Tool Center and Model Catalog
will lose Letta-backed capabilities unless deliberately replaced. Operating v3 also
adds an embedding deployment and qualification registry, but aliases may change
without invalidating durable identity only when the exact fingerprint is unchanged.
Letta and Redis remain in production until v3 passes all gates and a fresh-start
cutover is approved.

## Guardrails

- Do not make v3 the production Agent Studio path without a later cutover ADR.
- Do not describe static adapter tests as live-model qualification.
- Do not add a legacy Letta importer, dual-write path, or compatibility aliases.
- Do not expose subject selection in model-controlled tool arguments.
- Do not enable hidden framework/SDK retries.
- Do not release an unqualified deployment through an alias or reviewer fallback.
- Do not count focused diagnostic fixtures as qualification rounds.
- Do not normalize invalid `forget` plus `add` proposals into a correction; require
  the reviewer to satisfy the typed operation contract.
- Preserve the study harness and generated-artifact format for later comparison.
- The study review and implementation approval occurred on 2026-08-29; do not treat
  that approval as production-cutover approval.
- Record a later cutover ADR if implementation evidence changes material contracts.
- Apply the production qualification and reviewed-promotion rules in
  [ADR 0010](0010-production-path-runtime-qualification.md); direct study rounds do
  not qualify the `/api/v3` implementation.
- Apply the worker-readiness and safe provider-failure evidence rules in
  [ADR 0011](0011-agent-runtime-operational-readiness.md).

## Implementation Status

The user accepted this ADR for implementation on 2026-08-29. The first implementation
is a disabled-by-default `/api/v3` vertical slice with separate ADE persistence and a
worker; accepting this ADR does not authorize production cutover. Current `/api/v2`,
ADE Web, Letta `0.16.8`, and Agent Studio behavior remain authoritative until a later
cutover decision is reviewed and accepted.
