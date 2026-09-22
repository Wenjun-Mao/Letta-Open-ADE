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
| Separately correctable preference | `person.preference` is typed by qualifier; a correction preserves its normalized key, binds one user evidence span, and advances the existing fact. | PostgreSQL storage path verified with synthetic vectors; semantic retrieval quality pending. |
| Forgetting/no resurfacing | Explicit forget creates a revision and marks the fact forgotten; active-profile and semantic-search queries filter `status=active`. The fixture requires store and recall of a separate milk-tea fact before deletion. | PostgreSQL lifecycle and active-query behavior verified; chronological provider-backed replay pending. |
| Source inspection | Revision sources preserve message ID, exact character span, quote, message hash, and predecessor lineage. | Revision/source rows and predecessor links verified against PostgreSQL. |
| Subject isolation and cross-conversation recall | Facts and embeddings are queried with the bound subject ID; a conversation loads that subject's active facts. | PostgreSQL subject-filter behavior verified across two subjects and two conversations for one subject; semantic recall quality pending. |
| Concern lifecycle | Registry has no concern type, expiry, resolution, or current-versus-historical lifecycle. | Unsupported; do not encode it as a preference. |
| Promise/shared transcript event | Reviewer evidence is one current user-message span; registry has no promise/shared-event type. | Unsupported; no invented schema in M2. |
| Relevance/repetition | Up to twelve recency-sorted active facts enter the profile before semantic retrieval. Dog/travel distractors can therefore reach dialogue context when current stress may make them irrelevant. | Context-selection risk, not a proved bad dialogue or embedding outcome. |
| No fabricated physical shared experience | No dedicated transcript-event representation or dialogue assertion establishes this boundary. | Not yet an ADE dialogue contract; live negative review is required. |

The fixture test validates the fixed input contract. Separate native structural
checks exercise typed correction/forget preparation, active subject/status
retrieval predicates, active-profile context, and absent temporal/transcript
types.

### PostgreSQL Storage Check (2026-09-22)

An isolated PostgreSQL integration test exercised the existing review and
repository path: add a preference in one conversation, correct it in a second
conversation for the same subject, then forget it. It checked versioned
add/correct/forget revisions, exact source-message quotes and predecessor
links, current-revision embedding selection, no active retrieval after
forgetting, and retrieval isolation from a second subject. Three-dimensional
deterministic vectors exercise pgvector SQL only. This verifies storage and
filter correctness; it says nothing about semantic embedding quality, LLM
extraction correctness, runtime qualification, or Hindsight parity.
Each add, correction, second-subject add, and forget commits in its own
transaction. The test reads the committed state through a separate connection
between stages, including after forgetting.
The test used the fresh local `pgvector/pgvector:0.8.1-pg15` container and
database `ade_m2_memory_test_01a0ca1b`, migrated to the current Alembic head.

### ADE PostgreSQL Read-Back Dialogue Slice (2026-09-22)

One fresh synthetic case then connected the committed typed-fact path to the
existing Luna dialogue task. Scripted add/correct/forget proposals passed the
existing Pydantic review validation, `prepare_memory_review`, and
`commit_memory_review` path; they were not model-generated extraction. Each
operation committed before a separate repository read-back. Each of four
serial `gpt-6-luna` dialogue prompts contained the active facts returned for
that subject and one new recall question only—no source, correction, or forget
transcript and no expected answers. The shared prompt builder appended only its
existing task instructions and persona. Subject Two had a distinct music
preference. The exact prompts, raw calls, transport manifests, repository
contexts, and case IDs are captured under the ignored
[case manifest](../../workflows/evals/character_memory_dev/outputs/m2-postgres-luna-4b1c473a550247ec9ba51b61c82a6981/case.json) and its sibling per-call artifacts.

The database lineage is inspectable in `case.json` and each call's
`database-context.json`: Subject One fact
`2b1b0b43-24dd-43ed-96fd-9d3f3a9f0ff7` had add revision
`f74a3ddf-abb7-4344-9626-d47aac3b1fc2` (source message
`3681d78c-d670-4851-a800-978cdbe4ae41`, quote `喜欢红茶`), correction revision
`ac8f8072-dff9-474a-9610-38835194479b` (second conversation, source
`6e026b89-6809-4cf6-93b5-a0d01a715ec5`, quote `更喜欢绿茶`), and forget revision
`3cd6b197-085a-49bf-b1c9-8bca00b8d8f1` (source
`32197e72-6798-41b7-b3fd-93b401c936ae`, quote `请把这个偏好忘掉`). The
separate Subject Two fact `7534ce5e-f858-47a7-aede-25b34d8ed665` remained
active at revision `26885fb1-e1de-4e8c-860d-7c2b1b2a1b4e` (source
`918a9687-2733-4c08-9cce-fe241926a6a4`, quote `喜欢听民谣`).

| Probe | Exact repository-derived prompt context | Luna claim / source attribution | Review |
| --- | --- | --- | --- |
| Subject One, after add | `用户饮品偏好：红茶` (add revision `f74a3ddf…`) | “记得呀，你平时更偏爱红茶呢。” Attributes red tea to the prompted user, matching the add source. | Pass for this supplied-context sample. |
| Subject One, after correction | `用户饮品偏好：绿茶` (correction revision `ac8f8072…`) | “你之前说过喜欢绿茶呢…” The corrected value and its source are supported by the second-conversation correction. | Pass for the current preference claim; one sample does not establish robust correction behavior. |
| Subject One, after forget | empty list; fact current revision is forget `3cd6b197…`, status `forgotten` | “我这边没有记下你偏爱喝什么茶呢。” Does not resurrect either tea preference. | Pass for non-resurrection in this prompt. The follow-up “我会记住的呀” is conversational language, not a persisted write or promise-system capability. |
| Subject Two | `用户音乐偏好：民谣` (Subject Two revision `26885fb1…`) | “你平常更喜欢民谣呀。” Attributes the distinct music preference correctly and does not attribute Subject One's tea preference to Subject Two. | Pass for this repository-scoped input; not adversarial cross-subject leakage or a security proof. |

All four calls used the subscription adapter with `gpt-6-luna`, medium effort,
default tier, a 180-second cap, JSON Schema dialogue output, and zero adapter
retries. All four transport and task validations passed. Workflow fakes verify
commit/read/dialogue order and input derivation; a DB-backed fake-dialogue run
also exercised the real scripted write/read path before the four calls. This is
ADE database-backed context-conditioning development evidence only. It does
not test semantic retrieval quality, model extraction, native runtime,
embedding behavior, security, or Hindsight parity, and is not candidate
comparison evidence.

Director review: Subject Two was probed only after Subject One's tea fact was
forgotten. This sequence does not test leakage between simultaneously active
subject memories; the earlier PostgreSQL lifecycle regression, not these Luna
calls, supplies that storage-filter evidence. The full correction reply also
offers to make tea in response to a hypothetical question. That is not evidence
of an actual physical action or a passed no-physical-co-presence requirement.
Independent verification reran the workflow suite and PostgreSQL lifecycle test:
63 passed, using fake dialogue for the database workflow and no new model calls.

Recreate the local test database without a password or external service:

```sh
M2_TEST_SUFFIX="$(uuidgen | tr -d '-' | cut -c1-8 | tr '[:upper:]' '[:lower:]')"
M2_TEST_CONTAINER="ade-m2-memory-it-${M2_TEST_SUFFIX}"
M2_TEST_DATABASE="ade_m2_memory_test_${M2_TEST_SUFFIX}"
docker run -d --name "$M2_TEST_CONTAINER" \
  -e POSTGRES_USER=ade_owner \
  -e POSTGRES_DB="$M2_TEST_DATABASE" \
  -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 127.0.0.1::5432 pgvector/pgvector:0.8.1-pg15
M2_TEST_PORT="$(docker port "$M2_TEST_CONTAINER" 5432/tcp | sed 's/.*://')"
M2_TEST_URL="postgresql+psycopg://ade_owner@127.0.0.1:${M2_TEST_PORT}/${M2_TEST_DATABASE}"
docker exec "$M2_TEST_CONTAINER" psql -U ade_owner -d "$M2_TEST_DATABASE" \
  -c 'CREATE SCHEMA ade AUTHORIZATION ade_owner'
docker exec "$M2_TEST_CONTAINER" psql -U ade_owner -d "$M2_TEST_DATABASE" \
  -c "ALTER ROLE ade_owner IN DATABASE ${M2_TEST_DATABASE} SET search_path TO ade, extensions, public"
ADE_DATABASE_MIGRATION_URL="$M2_TEST_URL" uv run --locked alembic \
  -c services/ade-api/alembic.ini upgrade head
ADE_TEST_DATABASE_URL="$M2_TEST_URL" uv run --locked pytest -q \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_memory_lifecycle.py
```

The test rejects URLs that are not passwordless loopback PostgreSQL URLs for
the `ade_owner` role and a database name matching
`ade_m2_memory_test_<hex-id>`; it fails before connecting or writing otherwise.

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
- Fourteen new Luna development calls are recorded separately in
  [M2 Luna findings](m2-luna-development-evidence.md); they do not change this
  comparison's native/provider evidence boundary.
- SQLAlchemy's [2.0 installation FAQ](https://docs.sqlalchemy.org/en/20/faq/installation.html) identifies `sqlalchemy[asyncio]` as the install target that ensures `greenlet` is present. `ade-api` now declares that extra; `uv lock` and `uv sync --locked` completed, and `uv run --locked` confirms `greenlet` is installed.
- The focused storage, repository-contract, PostgreSQL migration, memory-policy, and tool-policy regression command passed: **49 passed, 1 skipped**. The skipped migration-transition test requires a separate `ADE_DATABASE_MIGRATION_URL`.
- The character-memory workflow suite passed: **61 passed, 1 skipped** (the DB-backed fake-dialogue test is opt-in). With the named local database enabled, that test plus the lifecycle regression passed: **9 passed**. Changed workflow files pass Ruff checks and formatting; checking the entire workflow directory for formatting also reports an unchanged pre-existing formatting difference in `character_memory_dev/luna.py`.
- Exactly four new serial GPT-6 Luna calls were run once for the PostgreSQL read-back dialogue slice; all four schema/task validations passed. Their evidence is scoped above and does not alter the pending native ADE/Hindsight comparison.
