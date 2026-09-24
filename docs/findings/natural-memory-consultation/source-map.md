# Memory Design: Current-Code Evidence Map

Date: 2026-09-23. Read-only inspection; tests were not rerun for this map.
Authoritative source anchor: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` on
`codex/character-continuity` in [Wenjun-Mao/Letta-Open-ADE](https://github.com/Wenjun-Mao/Letta-Open-ADE).
This is the implementation baseline, not the later documentation checkpoint.

The [proposal](../../architecture/natural-memory-design.md) is deliberately not a
description of already implemented behavior. Links below pin the inspected source.

## Read In This Order

| Question | Evidence | Finding / limitation |
| --- | --- | --- |
| Who owns the turn? | [TurnExecution.execute](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py#L70) | Loads subject/definition, may compact, retrieves, generates, reviews, embeds proposed writes. Reviewer is after conversation generation. |
| What can be stored? | [fact_registry.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/fact_registry.py) | Seven named fact types; preference key has category but no separate context/value identity. No concern, plan, event, or character-private continuity type. |
| How is an update selected? | [MemoryReviewer.review](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/reviewer.py#L198) and [memory_intent.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/memory_intent.py) | Regex selects forget/correct/add mode before schema generation. Ordinary conflicting statements are instructed to fail closed; current user plus eight recent users and all active facts are supplied. |
| What are proposal shapes? | [memory_review.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/memory_review.py#L53) | Closed add/correct/forget union, at most 20 proposals, exact current-message span binding. No general merge, supersede, or end proposal in the current reviewer. |
| What does ADE validate? | [prepare_memory_review](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/memory_policy.py#L64) | Current evidence, subject/entity ownership, active target and version, unique projected key, no repeated mutations. Uncertainty and value-support checks are heuristics, not complete semantic proof. |
| Where are facts committed? | [memory_commit.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/memory_commit.py#L14) | Creates revision/source lineage and embeddings. Forget changes status to forgotten; correction remains active. |
| What is atomic? | [RunFinalizer.commit_success](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py#L36) | Rechecks cancellation/lease, locks conversation+subject, revalidates memory, then commits assistant, memory, optional summary, and terminal success transactionally. It does not serialize provider computation across all conversations for a subject. |
| What reaches the conversation? | [context.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/context.py#L155) | System/persona, active profile, count metadata, lossy summary, retrieved facts, recent turns, current user. Current memory data is inserted in the system message. Untrusted data separation deserves scrutiny. |
| How are context records selected? | [turn_execution.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py) | Top 12 most recently updated facts for profile. Automatic query embeds current user; up to eight results with a distance cutoff. Retrieval is deduplicated from profile. No general old-message search. |
| What does deep search do? | [MemoryRepository.search_active_facts](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/persistence/memory.py#L386) | Subject on facts and embeddings, active status, current revision, embedding-space and retrieval-policy checks. Explicit tool query uses the same store without the automatic distance cutoff. |
| What is the schema authority? | [metadata.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/persistence/metadata.py#L434) | Existing relational fact/revision/source/embedding tables; definition roots and versions already exist. Proposed continuity tables and inactive state do not. |
| Where is tool policy? | [tool_policy.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/tool_policy.py#L165) and [executor.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/executor.py#L115) | Free-form action matching can require a tool. DeepSeek uses auto choice; missing required tool fails the turn. This is not a measurement of memory usefulness. |
| What is compressed? | [compaction.py](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/4905ce15dbda6466b12f2d1ed7908eb3d03995a0/services/ade-api/src/ade_api/features/agent_runtime/compaction.py#L53) | Versioned conversation derivative, not deletion of raw history or a subject memory authority. |

## Existing Contracts To Preserve Or Explicitly Amend

- [ADR 0021](../../adr/0021-evidence-scoped-memory-and-affirmative-tools.md):
  evidence-clause uncertainty and locally affirmative tool intent. The proposal
  changes natural recall policy, not permission to infer facts from unrelated text.
- [ADR 0022](../../adr/0022-incumbent-memory-first-product-slice.md): subject-level
  fact sharing, no implied character-private relationship history, Option A removal.
  New continuity scope would be an additive decision requiring acceptance.
- [ADR 0026](../../adr/0026-memory-removal-reply-boundary.md): no premature memory
  success, historical erasure, future nonmention, or proactive outreach promises.
- [ADR 0027](../../adr/0027-provider-neutral-release-and-embedding-space.md):
  DeepSeek conversation/reviewer candidate and movable Qwen embedding route with
  stable semantic identity. No fixed Spark host dependency should enter the design.
- [ADR 0028](../../adr/0028-agent-runtime-qualification-request-ledger.md):
  existing request caps; unused Stage A allowance does not authorize another run.

## Evidence That Exists, And What It Does Not Establish

- [M3 native findings](../m3-native-acceptance-2026-09-23.md) document bounded
  profile correction/removal, subject isolation, UI citations, and original
  misleading replies. They do not establish natural long-term companionship.
- [Failed Stage A](../stage-a-provider-neutral-preflight-2026-09-23.md) and
  [offline diagnosis](../stage-a-required-tool-offline-diagnosis-2026-09-23.md)
  preserve the missing required tool and conditional-fixture mismatch. The exact
  failed response text/reasoning and wire request were not retained. Do not infer
  why the model omitted the call, whether it remembered correctly, or whether the
  target was absent from context. `profile_token_override` was unused natively.
- [M2 findings](../m2-memory-approach-comparison.md) separate storage/filter tests,
  supplied-context dialogue, and unexecuted ADE/Hindsight comparison.
- [Original external reports](README.md#reports-and-provenance) were not repo
  audits. Their architecture comparisons and behavioral examples are proposals;
  exported citation tokens are not automatically resolvable sources.

Ignored JSONL captures, SQLite request ledgers, live PostgreSQL, `.env`, local
services, and browser sessions are **not available** in GitHub-only review. The
committed findings above are maintainer reports about them, not direct access.
No secrets, raw production user conversations, or provider reasoning are required.

## Existing Test Entry Points

Read tests as specifications, not proof of passing on the reviewer's environment:

- `services/ade-api/tests/agent_runtime/test_reviewer.py`
- `services/ade-api/tests/agent_runtime/test_memory_policy.py`
- `services/ade-api/tests/agent_runtime/test_context.py`
- `services/ade-api/tests/agent_runtime/test_executor.py`
- `services/ade-api/tests/agent_runtime/test_worker_finalization.py`
- `services/ade-api/tests/agent_runtime/persistence/test_postgres_memory_lifecycle.py`
- `services/ade-api/tests/agent_runtime/persistence/test_repository_contracts.py`
- `workflows/evals/character_memory_dev/fixtures/m1/`
- `workflows/evals/character_memory_dev/fixtures/m2/`

## Local Grounding Review

The following limitations were found by tracing source rather than relying on the
research reports: mutually exclusive reviewer modes, single-category preference
slots, reviewer after generation, all-active-fact input, profile recency selection,
fact-only deep search, and atomic successful-turn finalization. The proposed design
calls these out rather than attributing new behavior to existing code.

Still hypotheses: continuity entries' usefulness, composite preference reliability,
the new selection policy's advantage, acceptable latency, and sufficient natural
dialogue quality. No local source review proves those. Ask Pro to identify any
additional mismatch and cite exact paths/functions at the stated source anchor.
