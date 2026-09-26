# ADR 0040: Source-Guarded Probe-Local History Ranking

Status: H2 finite synthetic ranking observed on 2026-09-26; director review
pending. H4 dialogue scoring remains a separate gate.

## Problem

The H2 selector embeds exact historical dialogue after the target turn's bounded
repeatable-read snapshot closes. A source can be purged or altered before the
outbound document batch or between that batch and the query embedding. The
existing H3 guard applies to admitted generation/reviewer packets, but ranking
must authorize its broader candidate corpus without making unused candidates
finalization dependencies.

## Decision

The evaluation-only automatic probe can select one frozen literal or Qwen
recipe. Both use the same current user plus selected local B suffix and exact
user/assistant document text. The Qwen recipe uses the configured artifact and
1024-dimensional cosine in probe-local memory. It never uses the fact vector
space, fact query instruction, fact threshold or persistent vector table. One
recipe/corpus identity hashes the frozen recipe and sorted document hashes.

Native ranking consumes only `load_turn_state()`'s accepted historical snapshot.
Immediately before each source-bearing document or query embedding dispatch, a
fresh bounded read checks subject generation and every held candidate's scope,
status, complete pair, content hash and source-relative annotations. A genuine
purge before first ranking exposure removes whole windows and recomputes the
batch; ordinary read unavailability before exposure becomes explicit unavailable
history. After the first outbound batch, source loss or inability to verify is
fatal. The provider transaction never holds a database connection. Embedding
errors do not receive an internal retry or a fallback recipe. Ranking exposure
is tracked separately from H3 admitted-packet exposure, and finalization checks
only windows actually admitted to generation/review.

The finite fixture experiment is explicitly synthetic fixture-owned data. Its
redacted embedding receipts do not impersonate a native source check. It runs
both recipes on the three frozen development cases, applies the frozen adequacy
rule once, and may then run only the selected recipe on four held-out cases.
Every scheduled cell retains success, failure or unrun status, full scores,
ranked IDs, hashes, omissions and observed dispatch latency.

## Alternatives And Consequences

Rejected embedding from a later refreshed corpus, accepting unguarded provider
calls, retrying a failed embedding, borrowing fact vectors, and locking a source
through provider duration. A check authorizes only the immediately following
request; it cannot undo a purge after authorization. The selector remains a
bounded evaluation path, not a production transcript search service.

Offline guardrails include fake-router dispatch ordering, malformed vector and
source-loss checks, native PostgreSQL hash/scope/generation checks, and a
full worker turn using the Qwen recipe with fake embeddings. The first combined
worker rerun failed because `history_ranking` was missing from the trace-stage
allowlist; this was the root cause and the allowlist now names the stage.
The following fresh-database worker run passed 16 cases. The subsequent finite
synthetic H2 schedule selected Qwen cosine from three development cases and
completed four held-out cases. Its findings and exact artifact hashes are in
[the H2 evidence record](../findings/natural-memory-consultation/history-h2-ranking-feasibility-2026-09-26.md).
The synthetic calls do not prove native delivered continuity.
