# M3 Provider-Neutral Release Preparation

Status: static candidate prepared under [ADR 0027](../adr/0027-provider-neutral-release-and-embedding-space.md); independent review, live qualification, and promotion pending.

1. Trace schema-v3 evidence, promotion, native qualification configuration,
   router source resolution, and stored vector lookup. Preserve the historical
   ledger and immutable definitions.
2. Introduce a versioned selected-role evidence contract and conditional
   compatibility validation. Bind the current unqualified DeepSeek + Qwen
   candidate without carrying forward DGX or llama passing evidence.
3. Separate Qwen vector-space identity from endpoint provenance for new
   bindings, with explicit semantic validation and legacy-vector continuity.
   Make the embedding endpoint configurable; require fresh deployment and
   compatibility review for relocation.
4. Add fail-closed tests for stale/missing roles, failed configured
   compatibility, old schema semantics, provider selection, embedding semantic
   mismatch, and preserved legacy vectors. Run proportional Python, web,
   OpenAPI, formatting, and compose checks.
5. Leave generation, qualification, promotion, production deployment, merge,
   and private-data use to the director's separately reviewed next stage.

End state: a clean source checkpoint with exact candidate routes and a bounded
synthetic qualification request budget estimate, not a release claim.

## Next-stage request envelope (no calls made here)

The canonical matrix has 10 cases and 20 scored turns, plus one initial-fact
setup turn and 40 long-history prelude turns per round. Three full rounds mean
183 runtime turns. With the candidate's six conversation requests per turn,
one reviewer request (zero repair), and at most one compaction request per
turn, the conservative DeepSeek ceiling is 1,464 requests: 1,098
conversation + 183 reviewer + 183 compaction. Ordinary execution should be
much lower, but the prelude turns are real model calls, not inserted history.
Each request must observe the configured 180-second turn deadline and zero
requested turn retries; a fresh failed round requires separate authorization.

Every turn can make one Qwen retrieval query, and a nonempty fact-write batch
adds one document-embedding request. Search-memory tool calls add further
query requests. An illustrative envelope of one search call per conversation
continuation is 1,281 Qwen requests (183 retrieval + at most 183 fact batches
+ 915 tool searches); this is **not a hard upper bound**, because a model
response may contain multiple tool calls. The next stage must set an external
aggregate Qwen spend cap and stop when reached; do not interpret the estimate
as permission for unlimited calls. A relocated endpoint additionally needs
four synthetic canary embeddings (query and document at origin and candidate)
and independent provenance review. An origin endpoint needs no relocation
receipt.

For one separate synthetic release-mode API/worker turn, reserve up to eight
DeepSeek requests (six conversation, one reviewer, one possible compaction)
and, assuming one search per continuation, up to seven Qwen requests (one
retrieval, five tool searches, one document batch). This is an estimate per
turn, not a new qualification round or a claim that release mode is enabled.
The director should approve actual global request caps and exact acceptance
cases before any live run.
