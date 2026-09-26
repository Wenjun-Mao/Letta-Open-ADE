# Natural History Recall: Independent Pro Review Briefs

Updated: 2026-09-25. **Revision 2 handoff, ready for manual Pro review.**
Source/plan anchor: `8e298881e4165128c5a680a0b02c1789c894d8ff`.
Discovery repository: https://github.com/Wenjun-Mao/Letta-Open-ADE
Discovery branch: `codex/character-continuity`.

The plan, product contract, ADRs, findings/reports and relevant runtime files
(21 required files) were fetched anonymously from GitHub at this anchor and
matched local Git blobs byte-for-byte. This is publication verification, not
execution or acceptance. Runtime code is unchanged from the first review anchor
`cece5bedd6032da3ebc3802c7be604eb505967e6`; revision 2 changes documentation only.
The earlier prompts are preserved in Git history, and the two original reports
remain unchanged beside [our assessment](history-recall-review-assessment.md).

Use a separate Pro conversation for each prompt. The roles are complementary:
product semantics versus code-grounded minimal implementation. The intended
decision is whether unresolved contracts need further revision before approval
of a bounded probe. Consensus does not prove runtime or model behavior. No
consultant account operation, implementation, live call, merge or release follows
from this publication. Private generated captures and local services remain outside
the evidence boundary.

## Pro 1: Product And Memory Semantics

```text
Review ADE's historical-recall plan REVISION 2 for product and memory semantics. We revised the first draft after independent reviews; determine whether consequential ambiguities remain before bounded implementation. Do not assume prior conversation context or that reviewer agreement proves correctness.

GitHub-only access. Repository: https://github.com/Wenjun-Mao/Letta-Open-ADE ; discovery branch: codex/character-continuity ; exact source/plan commit: 8e298881e4165128c5a680a0b02c1789c894d8ff. State the revision/files actually inspected; report access failures rather than substituting main. Local services, ignored captures and private evidence are unavailable.

PLAN: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/8e298881e4165128c5a680a0b02c1789c894d8ff/docs/plans/natural-history-recall.md
PRODUCT CONTRACT: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/8e298881e4165128c5a680a0b02c1789c894d8ff/docs/product-contract.md
At the same commit, consult ADRs 0035/0036 and docs/findings/natural-memory-factual-followup-2026-09-24.md. Prior reports and synthesis are in docs/findings/natural-memory-consultation/history-recall-review-assessment.md; reason independently before using them to check issue coverage.

ADE has native PostgreSQL persistence, immutable dialogue, versioned subject facts and one reviewer before atomic commit. Lin Xiaotang should recall naturally across chats/persona versions. Historical retrieval is NOT implemented. Revision 2 proposes only baseline versus one automatic historical packet, using the same H-capable reviewer (empty H in control). Discretionary tools and separate search/read are deferred.

Settled: same-user/same-character-root experience, archived chats eligible without restoration, shared facts do not imply shared experiences, and operator fact removal does not erase transcripts. No privacy/no-save subsystem, semantic phrase rules, episodes, writable notes, extra reviewer/service or spending gates. Structural isolation and provenance remain.

Focus on source-relative corrections (including correction then return to the original value), removed facts followed by historical acknowledgment versus genuinely fresh assertion, H-only referents requiring local clarification, temporal false conflicts, resolved concerns, ambiguity and inappropriate callbacks. Does the plan preserve these meanings across the NEXT turn without expanding write authority or adding semantic heuristics? Can the proposed lineage envelope express the necessary distinctions without misleading claims? Are complete-delta outcomes and minimum sufficient evidence sets clear?

Give an answer-first verdict: ready for bounded implementation, targeted revision, or not ready. List only remaining consequential issues with pinned references, a concrete natural Mandarin counterexample and smallest correction. Separate contract blockers from questions the experiment should answer; do not demand known model reliability before a feasibility probe. Identify successfully closed issues and any simplification still warranted. State evidence limits. No implementation, model calls or release qualification is requested.
```

## Pro 2: Architecture And Simplification

```text
Review ADE's historical-recall plan REVISION 2 against the repository for correctness and minimal implementation complexity. Determine whether it is ready for a bounded automatic-recall probe, not a general memory platform. Do not assume prior conversation context.

GitHub-only access. Repository: https://github.com/Wenjun-Mao/Letta-Open-ADE ; discovery branch: codex/character-continuity ; exact source/plan commit: 8e298881e4165128c5a680a0b02c1789c894d8ff. Report inspected paths/revision and access limits; do not substitute main. Local databases, services and private captures are unavailable.

PLAN: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/8e298881e4165128c5a680a0b02c1789c894d8ff/docs/plans/natural-history-recall.md
PRODUCT CONTRACT: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/8e298881e4165128c5a680a0b02c1789c894d8ff/docs/product-contract.md
Runtime root: services/ade-api/src/ade_api/features/agent_runtime/. Inspect turn_memory_snapshot.py, natural_context.py, turn_execution.py, executor.py, embeddings.py, natural_memory_binding.py, natural_memory_review.py, natural_memory_policy.py, natural_memory_reviewer.py, worker_finalization.py, persistence/metadata.py and persistence/memory_source_read.py as relevant. Consult ADRs 0035/0036 and existing tests. Prior reports/synthesis are in docs/findings/natural-memory-consultation/history-recall-review-assessment.md; evaluate independently before checking closure.

ADE already has a short coherent state snapshot, immutable dialogue, subject-generation fencing, one reviewer and atomic finalization. Historical retrieval is proposed, not implemented; the release-policy gate remains unwaived. Revision 2 narrows to a matched empty-history control versus one automatic packet. It reuses the snapshot, uses source-relative annotations and one admission path, and extends only read-only H conflict grounding. No new history tool is exposed.

Settled: same-user/same-character-root transcripts across versions, archived sources eligible, shared facts remain subject-scoped, removal is not transcript erasure. No semantic phrase rules, privacy subsystem, episode store, writable notes, extra service/reviewer, spend gates or speculative framework.

Focus on coherent target-time snapshots, source-to-current lineage including source-less removal, packet admission for generator/reviewer/continuations, pre-dispatch and finalization purge checks with explicit race limits, read-only versus writable handles, and fatal versus optional errors. Does deferring the tool exception-wrapper fix remain safe for the automatic-only path? Does the separate probe-local transcript recipe avoid corrupting fact embeddings? Assess held-out ranking fixtures, identical reviewer controls, paired target prefixes, trajectory tests and stage-level failure accounting.

Give an answer-first verdict, remaining blockers with exact source/plan references and minimal falsification tests, and a keep/simplify/defer list. Distinguish actual defects from already-specified contracts and empirical unknowns. Challenge unnecessary implementation, but do not require production indexing or live quality certification before bounded feasibility. No implementation, provider calls or release approval is requested.
```

## Handling Results

Preserve returned reports unchanged. Synthesize and verify consequential claims
separately; distinguish Use, Test, Park and Discard. Revise the existing plan only
where needed. Do not reopen settled scope or add machinery merely to achieve
unanimous reviews; further review is for unresolved consequential issues.
