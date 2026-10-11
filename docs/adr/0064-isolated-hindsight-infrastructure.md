# ADR 0064: Isolated Hindsight Infrastructure and Observational Supervision

Status: Accepted for the assigned P0 offline package, 2026-10-11. No deployment,
provider qualification, semantic acceptance or native adoption is implied.

## Problem

Revision 4 needs reproducible OCI infrastructure without touching incumbent ADE
or other host services (PC-08/13), and complete observational provider requests
without spending controls or another product runtime (PC-09). A guessed outbound
payload cannot prove shared adapter/profile serialization. Best-effort capture
can silently lose evidence. SSH-connected expiry or a permanent stop latch cannot
support the authorized autonomous campaign's disconnects, repairs and persistence
restarts under one immutable hard cap.

Source review found concrete default mismatches: a one-slot worker's default
reserved consolidation slots exceed capacity; global embedding retries are not
forwarded by the OpenAI factory; startup verification has its own LLM attempts.
The deployment loader rejects `{}` as a manifest. Compose env-file string escapes
do not provide the required actual query-prefix newline. These belong at owned
configuration/capture/supervision boundaries, not shared router tolerance patches.

## Decision

Own all assets in `workflows/evals/hindsight_memory_probe/`: explicit candidate
Compose, dedicated pinned PostgreSQL17 pgvector/PGroonga recipe, pinned full
Hindsight0.10.3 with one embedded worker/BGE CPU cache, existing router service
with a workflow-only instrumented entrypoint, and one-shot documented feature CLI
runner (ADR0063). No ADE API/native DB/reviewer is constructed. Recipes/configuration,
model revision and clean source SHA contribute to candidate identity; actual
image IDs and semantic fixtures belong to subsequent evidence.

Inject an observed httpx client through the shared app lifespan, retaining the
existing catalog/routes/adapters/defaults/policy. Durable exclusive/fsync inbound
capture and final outbound request bytes precede upstream dispatch. Capture failure
prevents forwarding and invalidates qualification. Project only status/usage/time/
embedding shape from responses; exclude authentication, error text, raw responses
and private reasoning. Disable the pinned native raw LLM trace and external
OTEL export; retrieval/recall trace remains available. Reject streaming and secret/reasoning request fields.
The existing Character profile remains frozen high thinking, while Memory explicitly
disables thinking and uses JSONobject. Tests use the real shared forwarding/catalog
path to fake HTTP. Pinned-image actual Hindsight providers remain P1 qualification.

Use private generated candidate env, separate UI access/dataplane auth, the exact
built-in API tenant extension and disabled MCP. Existing Spark provider auth remains
optional; candidate router/API/DB auth does not. Owned named volumes/network and
loopback API/UI ports preserve isolation. Explicit absent deployment qualification
manifest means unqualified binding, not a fabricated deployment record.

A temporary detached Linux stdlib supervisor persists immutable start/target/hard
cap, baseline and initial owned release; flock prevents duplicates. Audited,
append-only operating epochs allow diagnosis-backed rearm, measured allocation
changes and admission of new verified clean SHA releases. Prior release paths
remain explicitly owned for safe stop. Deadlines never extend; no implicit restore
project ownership is added. A 300-second cleanup margin blocks fresh work before
the absolute hard cap. Positive container labels/release checks and unique
PID-token/start/UID identity prevent broad kills or PID reuse. Registered owned
processes include builds; source quotas alone do not bound BuildKit work. OCI
sleep/disconnect and daemon-side build-cancellation proofs precede live operation.

## Alternatives and consequences

- Shared router edits or reconstructed adapter requests: rejected; observation
  belongs to the isolated workflow and must see actual serialization.
- Best-effort receipts, raw responses or exception logs: rejected; missing captures
  invalidate experiments and provider reasoning/credentials are not evidence.
- Mac/SSH-only expiry, silent marker deletion, or a single unrecoverable stop:
  rejected; detached expiry and explicit recovery epochs preserve both safety
  and authorized repairs without moving the campaign clock.
- Shared PostgreSQL or weaker vector-only CJK acceptance: rejected under PC-13.
- Upstream retry patch merely to force global0: not justified before diagnosis.
  Document actual SDK/startup mechanics, account for calls, bound owning work and
  prove them with pinned-image fakes.

Static validation and synthetic tests guard the contract. Offline success is
neither ARM build/extension/reranker acceptance nor OCI guard proof or semantic
qualification. The owning README contains precise future operator commands and
remaining P1/P2 gates. Semantic replay and complete-trace pre-Character reranking
admission remain the subsequent serial assignment. Initial supervision is main
project only; disposable P4 restore support requires explicit validated registry
extension and dummy qualification before use.
