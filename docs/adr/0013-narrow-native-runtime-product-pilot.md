# ADR 0013: The First Native Runtime Product Pilot Is Separate And Memory-Focused

- Status: Accepted for implementation; exposure pending ADR 0010 qualification
- Date: 2026-08-30
- Related: [ADR 0009](0009-ade-owned-agent-runtime.md),
  [ADR 0010](0010-production-path-runtime-qualification.md), and
  [ADR 0011](0011-agent-runtime-operational-readiness.md)

## Context

The ADE-native runtime has a real PostgreSQL/worker implementation, but production
Agent Studio remains Letta-backed. A useful product pilot must expose the new domain
model and evidence without creating an implicit cutover, a second hidden Agent Studio
mode, or browser-orchestrated partial resources. The pilot also needs a smaller tool
contract than Letta Tool Center parity.

## Decision

- The pilot is a separate `/native-runtime-preview` ADE Web route. It is never a
  toggle, fallback, or model option inside Agent Studio.
- Browser `/api/v3` traffic uses a dedicated server proxy to `ade-native-api`. The
  native API service initializes only `/health`, authenticated `/api/v3`, PostgreSQL,
  Model Router access, and native runtime resources; it does not initialize v2,
  Letta, or Redis. The normal `ade-api` application does not mount `/api/v3`, and
  the preview web service does not depend on `ade-api`, so selecting the preview
  Compose lane cannot pull the legacy Letta/Redis graph transitively.
- `POST /api/v3/preview-sessions` atomically creates one exact agent-definition
  version, one explicit memory subject, and one conversation. The server derives
  internal keys from a request idempotency key. Exact replay returns the same
  resources; changed-payload reuse is `409 Conflict`; partial creation rolls back.
- The first product tool scope is only subject-bound `search_memory`. Arbitrary Tool
  Center Python, sandboxing, approval flows, and the deterministic development-only
  `get_weather` fixture are outside this pilot.
- The UI emphasizes architecture evidence: deployment roles, qualification and exact
  fingerprints, prompt/persona content hashes, immutable messages, versioned summary
  provenance, typed memory revision lineage and source quotes, explicit timeout/retry
  ownership, cancellation, and normalized SSE events.
- `NEXT_PUBLIC_ADE_NATIVE_PREVIEW_ENABLED` is built as false by default. The checked-
  in and local `.env` control remains false until promotion. Navigation is conditional;
  the direct route renders a truthful gated explanation while disabled, and the
  server-side `/api/v3` proxy independently returns `404` unless
  `ADE_NATIVE_PREVIEW_ENABLED=true` at runtime.
- `make native-runtime-preview-up` must first run a fail-closed gate. It enables the
  route only when the exact conversation, reviewer, and retriever aliases have each
  been promoted for three complete rounds, have no stale rounds, and still match the
  current prompt/tool/schema/retrieval policy hashes. Release execution rechecks the
  same exact aliases and policy hashes on definition creation and every turn. The
  source tree must also match its committed Git-visible fingerprint; dirty or unknown
  source identity fails closed.
- The first release pilot fixes its complete execution identity to conversation and
  reviewer route `dgx_vllm::qwen3.6-35b-a3b-fp8`, retriever route
  `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B`, prompt
  `chat_v20260516`, persona `chat_linxiaotang`, and tool `search_memory`. The UI
  displays these fields as qualified evidence rather than editable configuration.
- This pilot does not migrate existing agents, dual-write state, change `/api/v2`, or
  authorize a production cutover. A later cutover ADR remains mandatory.

## Consequences

Operators can inspect ADE-native behavior as a coherent product slice rather than a
raw API demo, while the current product authority remains unmistakable. The separate
proxy and Compose lane add a small amount of explicit configuration, but preserve the
ability to prove that native execution itself has no Letta/Redis dependency. Model
route aliases remain operationally replaceable through a new qualification and policy
review, not through a release UI override; each created definition freezes the exact
resolved deployment identity.

The pilot intentionally does not claim tool parity. Additional curated tools require
their own product contract, security review, deterministic tests, and qualification
evidence before becoming selectable.

## Guardrails

- Never enable preview navigation merely because unit tests or focused diagnostics
  pass; the reviewed deployment manifest is the gate.
- Never silently fall back from the native proxy to the v2 API or Letta.
- Never let browser code construct the definition/subject/conversation with three
  independent writes.
- Never expand the pilot to arbitrary executable tools through UI-only filtering.
- Never treat a clean commit alone as qualified: executable policy hashes and exact
  promoted deployment identities must still match independently.
- Never describe a successful pilot as cutover approval.
