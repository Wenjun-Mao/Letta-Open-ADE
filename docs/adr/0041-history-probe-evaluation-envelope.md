# ADR 0041: Bound the H4 Probe to the H2 Provider and Frozen Capacity

Status: evaluation implementation checked on 2026-09-26; H4 live dispatch blocked by the frozen reviewer envelope.

## Problem

The H2 decision selected Qwen cosine using a specific configured deployment fingerprint. H4 also fixes separate DeepSeek generation and reviewer limits. Route aliases and a provider's advertised 16,384-token capacity alone cannot prove that a native turn uses either exact evaluation binding.

## Decision

An automatic Qwen history probe requires the H2 deployment fingerprint in its immutable probe configuration. Before ranking, the worker checks that the persisted retriever snapshot has that fingerprint, route, artifact reference, revision and 1,024 dimensions. A mismatch fails before a history embedding dispatch.

The H4 runner binds a named evaluation-only capacity profile to the persisted conversation and reviewer snapshots after catalog resolution. Acceptance and execution check the same profile, original DeepSeek fingerprints, evaluation purpose, H-capable policy, provider capacity and zero reviewer repairs. The frozen limits are generation 16,384 context and 4,096 output, reviewer 6,759 input and 4,096 output, two conversation requests, one reviewer request and no retry. Existing H3 probes without this H4 profile retain their established deployment budget.

The one-shot campaign reseeds complete source-linked exchanges in a disposable database for each arm. It uses an isolated official DeepSeek router and the configured Qwen container whose catalog fingerprint equals H2's; it does not re-label a host-side Qwen deployment as the H2 one. Captures retain ranked, admitted and omitted source IDs, provider dispatch observations, exact mutation readback and paired base-packet checks.

Before any live dispatch, the runner checks the smallest H-capable reviewer request with a full 4,096-token candidate reserve. That request already estimates 7,958 input tokens, exceeding the frozen 6,759 limit. The runner therefore stops before creating campaign output or sending a model request. This is a contract conflict requiring an explicit H4 replan; changing the reserve, prompt, schema, output limit or reviewer input limit inside the frozen run would change the evaluated treatment.

## Alternatives and consequences

Rejected mutable route-only selection, spoofed fingerprints, silent reviewer budget widening and post-generation-only capacity checks. The H4 live schedule and semantic outcome remain unobserved. The isolated database replay and fake-provider worker test verify fixture topology and the deterministic preflight rejection; they do not supply a dialogue score.
