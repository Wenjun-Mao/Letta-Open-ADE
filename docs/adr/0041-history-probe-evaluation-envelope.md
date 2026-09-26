# ADR 0041: Bound the H4 Probe to the H2 Provider and Frozen Capacity

Status: H4 reviewer envelope amended for the evaluation-only campaign on 2026-09-26; live outcome pending.

## Problem

The H2 decision selected Qwen cosine using a specific configured deployment fingerprint. H4 also fixes separate DeepSeek generation and reviewer limits. Route aliases and a provider's advertised 16,384-token capacity alone cannot prove that a native turn uses either exact evaluation binding.

## Decision

An automatic Qwen history probe requires the H2 deployment fingerprint in its immutable probe configuration. Before ranking, the worker checks that the persisted retriever snapshot has that fingerprint, route, artifact reference, revision and 1,024 dimensions. A mismatch fails before a history embedding dispatch.

The H4 runner binds a named evaluation-only capacity profile to the persisted conversation and reviewer snapshots after catalog resolution. Acceptance and execution check the same profile, original DeepSeek fingerprints, evaluation purpose, H-capable policy, provider capacity and zero reviewer repairs. The generation limits remain 16,384 context and 4,096 output, with two conversation requests, one reviewer request and no retry. Existing H3 probes without this H4 profile retain their established deployment budget.

The original H1/H2 `contract.json` remains byte-for-byte frozen because the H2 ranking result hashes it. A separate, exact `h4_reviewer_amendment.json` binds that historical contract hash, H2 result hash and H4 case hash. The H4 loader accepts only the approved change to reviewer input: 16,384 context, 4,096 output and the existing 5% safety rule yield 11,469 input tokens. The `natural-history-probe-h4-v2` profile applies identically to both arms and all controls. This is an evaluation contract amendment, not a claim that H2 used the new reviewer envelope or a production setting change.

The one-shot campaign reseeds complete source-linked exchanges in a disposable database for each arm. It uses an isolated official DeepSeek router and the configured Qwen container whose catalog fingerprint equals H2's; it does not re-label a host-side Qwen deployment as the H2 one. Captures retain ranked, admitted and omitted source IDs, provider dispatch observations, exact mutation readback and paired base-packet checks.

Before any live dispatch, the runner checks the smallest H-capable reviewer request with a full 4,096-token candidate reserve. The original 7,958-token estimate exceeded H1's 6,759 input limit and correctly stopped the first preflight. The amended 11,469 input limit admits that request and every measured setup window. Optional older windows can still be omitted on a long follow-up reply; this is recorded as capacity loss, without another silent increase.

## Alternatives and consequences

Rejected mutable route-only selection, spoofed fingerprints, silent reviewer budget widening and post-generation-only capacity checks. The original preflight failure and offline capacity diagnosis remain historical evidence. The amended profile must pass native fake-provider paired packets before live dispatch; that check does not supply a dialogue score.
