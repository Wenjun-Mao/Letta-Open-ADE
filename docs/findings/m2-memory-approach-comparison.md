# M2 Memory-Approach Comparison: Interim Structural Evidence

Date: 2026-09-22
Status: In progress — no architecture selected or adopted

## Scope And Shared Contract

This is a bounded comparison for 林小棠's everyday Chinese companionship. The
[M2 plan](../plans/m2-memory-approach-comparison.md) and
[workflow-local specification](../../workflows/evals/character_memory_dev/fixtures/m2/comparison.json)
fix seven cases, concrete role/timestamp/subject/conversation inputs, expected
semantic state, negative probes, and this common candidate budget:

| Budget | Limit |
| --- | ---: |
| Recent role-labelled transcript | 3,000 tokens |
| Memory supplied to dialogue | 3,000 tokens |
| On-demand source inspection, not normal dialogue context | 1,500 tokens |
| Dialogue reply | 512 tokens |

Each candidate must use the same ADE dialogue stage after injecting only its
memory result. Hindsight `reflect` is not a dialogue comparator. Storage
correctness, extraction quality, retrieval quality, dialogue quality, and
latency are recorded separately; fixture/fake assertions are not semantic or
live-provider results.

[Luna development evidence](m2-luna-development-evidence.md) records a bounded
source-extraction and supplied-context dialogue pass. It remains distinct from
this candidate comparison and does not validate native retrieval or Hindsight.

The specification links the applicable M1 fixtures but adds the missing second
conversations, two-subject inputs, correction/forget/resolution turns, and
negative probes. Its loader validates references and shape only: it does not
run a candidate, retrieve memory, or score dialogue quality.

Each candidate replay must start with fresh state for the fixture's
`case_state_id` and process its `conversation_ids` in their listed
chronological order; later turns must not be retained before earlier probes.
The forgetting case has a separate `forget-user` state, so its milk-tea fact
does not collide with the corrected coffee/flower-tea case. It requires a
store-and-successful-recall checkpoint after `forget-origin` and before
`forget-request`; deletion evidence without that precondition is invalid.

## Current ADE Evidence

| Requirement | Observed contract | M2 status |
| --- | --- | --- |
| Separately correctable preference | `person.preference` is typed by qualifier; a correction preserves its normalized key, binds one user evidence span, and advances the existing fact. | Structurally supported; live semantic retrieval pending. |
| Forgetting/no resurfacing | Explicit forget creates a revision and marks the fact forgotten; active-profile and semantic-search queries filter `status=active`. The fixture requires store and recall of a separate milk-tea fact before deletion. | Structurally supported; chronological provider-backed replay pending. |
| Source inspection | Revision sources preserve message ID, exact character span, quote, message hash, and predecessor lineage. | Structurally supported. |
| Subject isolation and cross-conversation recall | Facts and embeddings are queried with the bound subject ID; a conversation loads that subject's active facts. | Boundary supported in source; cross-conversation semantic recall pending. |
| Concern lifecycle | Registry has no concern type, expiry, resolution, or current-versus-historical lifecycle. | Unsupported; do not encode it as a preference. |
| Promise/shared transcript event | Reviewer evidence is one current user-message span; registry has no promise/shared-event type. | Unsupported; no invented schema in M2. |
| Relevance/repetition | Up to twelve recency-sorted active facts enter the profile before semantic retrieval. Dog/travel distractors can therefore reach dialogue context when current stress may make them irrelevant. | Context-selection risk, not a proved bad dialogue or embedding outcome. |
| No fabricated physical shared experience | No dedicated transcript-event representation or dialogue assertion establishes this boundary. | Not yet an ADE dialogue contract; live negative review is required. |

The fixture test validates the fixed input contract. Separate native structural
checks exercise typed correction/forget preparation, active subject/status
retrieval predicates, active-profile context, and absent temporal/transcript
types. They are intentionally not a fake persistence service, candidate run,
or substitute for retrieval and dialogue-quality evidence.

### Retrieval Check Correction

The earlier structural query test only searched rendered SQL for column names
and unrelated parameter values. A missing predicate could still have left both
strings present. It now traverses the SQLAlchemy expression: each fact-subject,
embedding-subject, and active-status equality must bind its expected value, and
the fact/revision join equalities must exist. Counterfactual statements missing
each required boundary are rejected. This guards query construction only; it is
not database-backed isolation evidence.

## Hindsight Source Review

The external candidate review is pinned to Hindsight
[v0.10.1, commit `f8950b0`](https://github.com/vectorize-io/hindsight/releases/tag/v0.10.1),
released 2026-09-21. The source and docs below are inspected at that tag, not
assumed from a moving `main` branch.

- Its [retain API](https://github.com/vectorize-io/hindsight/blob/v0.10.1/skills/hindsight-docs/references/developer/api/retain.md)
  accepts a full role/timestamp-labelled conversation. Re-retaining a stable
  `document_id` deletes the prior document's extracted memories and reprocesses
  it, so the documented correction unit is a document rather than ADE's typed,
  versioned fact.
- [Banks/tags](https://github.com/vectorize-io/hindsight/blob/v0.10.1/skills/hindsight-docs/references/developer/api/retain.md)
  support visibility filtering: retained tags must intersect the recall filter.
  M2 fixes one bank per subject as the trial configuration rather than adding a
  tag variant; an adversarial live run must still prove that it is isolated.
- The [recall API](https://github.com/vectorize-io/hindsight/blob/v0.10.1/skills/hindsight-docs/references/developer/api/recall.md)
  can return raw source chunks, source facts for observations, and a retrieval
  trace with timings. Its source granularity is chunks/facts, not confirmed
  character spans equivalent to ADE's revision evidence.
- [Document management](https://github.com/vectorize-io/hindsight/blob/v0.10.1/skills/hindsight-docs/references/developer/api/documents.md)
  documents bulk deletion of all associated memories. This is destructive and
  does not by itself establish ADE-equivalent tombstone/lineage semantics or an
  individually correctable preference.
- Its [installation requirements](https://github.com/vectorize-io/hindsight/blob/v0.10.1/skills/hindsight-docs/references/developer/installation.md)
  add PostgreSQL plus a vector extension and LLM-backed fact extraction/entity
  resolution; the slim deployment also requires external embeddings/reranking.
  That is material operational and provider scope beyond the ADE extension.

## Candidate Comparison

| Dimension | Smallest ADE extension | Hindsight v0.10.1 | Current evidence |
| --- | --- | --- | --- |
| Durable preference/correction/forget | Extend existing typed facts only where an M1 case demands it; preserve source spans, optimistic versioning, and tombstones. | Document replacement/deletion is documented; individual correction, tombstone, and lineage equivalence are unproven. | ADE structural advantage; no live quality result. |
| Concerns, promises, transcript events | Requires a new, explicitly designed temporal/transcript contract. | Can retain full conversations with timestamps, but extraction and lifecycle behavior on these cases are unmeasured. | No candidate winner. |
| Isolation | Existing subject ownership at write and query boundaries. | M2 fixes one bank per subject for the trial. | Both need adversarial live proof. |
| Relevance and repetition | Existing profile injects recent active facts before semantic retrieval; minimal extension must address selection rather than blame embeddings. | Recall supplies ranked results and trace diagnostics. | Context risk and Hindsight inspection features; quality/latency unmeasured. |
| Provenance | Exact message spans and revision predecessor lineage. | Documents, source chunks, source facts, and trace are available; exact-span and revision correspondence unverified. | Different observability models. |
| Operational burden | No new service; uses existing ADE PostgreSQL, Model Router, worker, and release gates. | Adds Hindsight deployment, storage/vector extension, extraction/embedding/reranking provider configuration, and lifecycle operations. | Material external-service cost. |
| Latency | Current turn embeds query and fact writes; no M2 measurement. | Retain includes extraction/entity/embedding work; recall offers timing trace; no M2 measurement. | No numeric comparison. |

## Provider Readiness And Exact Live Work

The configured qualified ADE retriever is
`dgx_embedding_sidecar::qwen3-embedding-0.6b`, but no local Compose service was
running during this check and Spark remains occupied. The manifest's historical
qualification is not availability evidence. No native ADE provider credential,
Spark generation, embedding, or Hindsight service was used. The separate
Luna-only development pass used the subscription workflow and is documented in
[its findings](m2-luna-development-evidence.md).

Before a selection can be made, run these isolated experiments with explicit
provider and external-service authority:

1. Verify available ADE conversation, reviewer, and embedding routes. For each
   fixture case, initialize fresh `case_state_id` state and process its
   conversations in order; do not retain future turns before earlier probes.
   For forgetting, record successful milk-tea storage and recall before the
   delete request. Record retrieved fact IDs, revision source/lineage, query
   and write latency, and negative probes for correction, forgetting, recall,
   distractors, and repeated callbacks.
2. Provision Hindsight **v0.10.1** outside production with one bank per
   subject for each fresh case state. Retain the same role/timestamp-labelled
   fixtures chronologically, satisfy the forgetting pre-delete recall
   checkpoint, then capture retain latency, recall traces, source facts/chunks,
   correction and delete scope, and negative cross-subject probes.
3. Feed each candidate's capped 3,000-token memory result to the same ADE
   dialogue deployment. Human-review natural Chinese voice, relevance,
   correction, forgetting, and no fabricated physical shared experience.
4. Compare the measured totals and operational obligations. Fresh ADE release
   qualification remains a separate mandatory gate because M1 policy source is
   still unqualified.

## Recommendation

**Do not select or adopt Hindsight yet.** Confidence is medium that deferral is
the only justified decision: ADE already covers the durable-fact safety
primitives at lower operational cost, while the continuity capabilities that it
lacks are precisely the ones for which Hindsight has no case-specific live
evidence here. Candidate ranking confidence is low until the identical live
experiments above are authorized and completed. This is an interim comparison,
not M2 completion or an external-service decision.

## Verification

- Before this correction checkpoint, `uv run pytest -q`: **559 passed, 5 skipped, 1 failed**. The failure is the existing checked-in production-policy fingerprint gate in `workflows/evals/agent_runtime_acceptance/tests/test_policy.py`; this work does not rebind or promote that policy artifact.
- `uv run pytest -q workflows/evals/character_memory_dev/tests/test_m2_comparison.py services/ade-api/tests/agent_runtime/test_memory_policy.py services/ade-api/tests/agent_runtime/test_tool_policy.py`: **50 passed**.
- `uv run ruff check services packages workflows scripts tests`, `uv run ruff format --check services packages workflows scripts tests`, and `git diff --check`: passed.
- Ten new Luna development calls are recorded separately in
  [M2 Luna findings](m2-luna-development-evidence.md); they do not change this
  comparison's native/provider evidence boundary.
