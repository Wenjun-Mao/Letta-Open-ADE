# ADR 0073: Hindsight Reply Runtime

Status: Accepted for approved Stage 1 implementation, 2026-10-19. Controlled
product/API/SQL checks exist; browser and live end-to-end qualification remain pending.

## Problem

The incumbent's normal executor/finalizer required subject-wide fact generations,
reviewer decisions and embedding writes for every successful reply. Adding a
Hindsight client beside that contract would preserve a second Memory engine or
require fake reviewer output. Its run-first claim/finalization locks also conflict
with conversation-first admission and saved-input Retry (PC-02/03/05/08/09/14).

## Decision

Replace the maintained path directly. Definitions bind conversation and compaction
deployments, not reviewer/retriever model roles. Hindsight owns its extraction and
embedding configuration; its frozen relationship profile remains independently
identified. The shared deployment-manifest parser can still read historical role
records without making them executable definitions in the new runtime.

Every reply attempt performs required scoped recall, independent from queued
delivery. Character receives authored instructions/persona, its current input,
bounded current-chat dialogue, any summary and relevant contextual memories.
Discretionary `search_memory` uses the same relationship and failure contract.
Automatic/tool lookup failure pauses before a reply commit, including when the
whole-attempt deadline expires during lookup. It never becomes an empty result,
automatic model retry or a model-generated apology. Successful empty recall is valid.

Initial, tool-continuation and compaction payloads include serialization overhead
in their bounded input estimate. Mandatory input/persona is not truncated. Preserve
the existing token-bounded dialogue and compaction policy; introduce no eight-turn
policy or persona tuning. Summary source prefix, previous version and model/request
provenance commit atomically with the successful reply (PC-04/11/12/14).
The new default prompt `chat_v20261019` explicitly replaces the old memory-block
editing protocol. Non-Memory style, private-planning and dialogue-format sections
are preserved from `chat_v20260516`, and the persona is unchanged. Historical
prompts/global exports remain untouched; there is no runtime string-stripping or
misleading hash for a rewritten prompt.

Acceptance and finalization enqueue their respective immutable messages within
the source transaction (ADR 0070/0072). No native fact write/review is required.
Independent delivery consumers run alongside reply scheduling; neither holds ADE
SQL across native/provider HTTP. Native progress is an allow-listed last-reported
snapshot, not a completion percentage or a raw error/task-payload channel.

All lifecycle claims/mutations lock conversation before run and subject where
needed. Pausing releases the worker lease but keeps the active-input index guard.
Explicit Retry uses one idempotent receipt per observed attempt; each accepted
Retry starts another bounded automatic-retry group for that saved input. Recovery
cannot obtain a fresh automatic budget merely by restarting a worker. Cancel and
stale leases cannot create an assistant source.
Recovery must acquire its replacement lease before abandoning an original attempt
or failing an exhausted run; an expiry observed during selection may already be
obsolete. Recheck run state after the conversation lock, and preserve a pending
cancellation even when the automatic attempt budget is exhausted.

Use an explicit fresh workspace key, deterministically scoped session identities
and an immutable persisted Hindsight authority marker. Reject missing/default keys
and retained incumbent workspaces instead of adopting, converting or resetting
them. Ordinary persona versions retain the same root/bank. Retire maintained
subject-only Memory reads, manual removal/reset, native history-trial serving and
SQL-only evaluation purge. Old stored records and historical evidence remain.
Migration `20261019_0010` enforces workspace key/identity/authority immutability
in SQL; the already published `0009` migration is not edited.

The first candidate is development-only and has a separate manifest with zero
qualification rounds. Source publication changes neither existing services nor
historical release records. Browser/capture and actual native product checks must
still establish their respective Stage 1 gates; SQL/network-substitute tests do
not establish Memory semantics or Character acceptance.

## Rejected Alternatives And Guardrails

Reject dual writes, a generic backend selector, empty reviewer adapters, native
fallback, resending input for Retry and silent same-ID payload reconstruction.
Regression tests use application-role PostgreSQL for both atomic source/outbox
boundaries, concurrent Retry, cancellation, stale workers, lock order, bank
continuity, failed-generation eligibility and compaction provenance. Independent
native, Interface, capture and Character conclusions remain separate.
