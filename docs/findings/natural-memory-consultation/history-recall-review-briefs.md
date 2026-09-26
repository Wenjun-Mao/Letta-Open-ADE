# Natural History Recall: Independent Pro Review Briefs

Prepared: 2026-09-25. Status: **Ready for manual Pro review.** The user approved
publication of the source checkpoint; all 15 required plan, contract, finding and
source files at the pinned revision were fetched anonymously from GitHub and
matched local Git blobs byte-for-byte.

Source/plan anchor: `cece5bedd6032da3ebc3802c7be604eb505967e6`.
Discovery repository: https://github.com/Wenjun-Mao/Letta-Open-ADE
Discovery branch: `codex/character-continuity`.
Publication advanced the review branch from `6915ceec2f953b44f653c4fbb3f012e56a0e418a`
to `bae922feb4383d0cc500f80bf53bef93de5128a8` with the source and draft briefs;
this later documentation checkpoint records readiness. The source/plan anchor
above remains unchanged. Outgoing-history checks found no private capture/runtime
paths or high-confidence credential patterns. No merge, deployment, release
promotion or model calls occurred. The user will paste each prompt into a separate Pro
conversation. Neither reviewer should see the other's findings before reporting.

Purpose: critique a proposed bounded read-only historical-recall plan before
implementation. Wrong decisions risk stale-current assertions, invented shared
experiences, write-authority expansion and unnecessary runtime complexity.
One role examines product semantics; the other examines repository-grounded design
and simplification. Neither supplies behavioral or release acceptance evidence.

## Pro 1: Product And Memory Semantics

```text
Independently review ADE's proposed historical-recall plan for product and memory semantics. We will use your report to revise or approve bounded implementation, not to certify model quality. Prioritize concrete counterexamples and the smallest necessary corrections, not a larger memory platform.

ACCESS AND ANCHOR: GitHub only. Repository https://github.com/Wenjun-Mao/Letta-Open-ADE ; discovery branch codex/character-continuity ; exact source/plan commit cece5bedd6032da3ebc3802c7be604eb505967e6. State the commit and paths actually inspected. If inaccessible, report that limitation; do not silently substitute main, a different revision, or inferred code. You cannot access local worktrees, private captures, databases, services or prior chats. Published findings summarize observations; they are not raw live evidence available to you.

PLAN: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/cece5bedd6032da3ebc3802c7be604eb505967e6/docs/plans/natural-history-recall.md
CURRENT PRODUCT AGREEMENTS: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/cece5bedd6032da3ebc3802c7be604eb505967e6/docs/product-contract.md
CURRENT TECHNICAL DECISIONS: At that commit, docs/adr/0035-compact-natural-review-and-observational-dispatch.md and docs/adr/0036-discretionary-curated-tools-and-structured-requirements.md. Use docs/adr/README.md to distinguish superseded rules.
LIVE-EVIDENCE LIMITS: docs/findings/natural-memory-factual-followup-2026-09-24.md at that commit. Scope loss and reviewer truncation were observed; two low-effort reviewer-only replays succeeded but do not qualify native defaults or historical recall.

CONTEXT: ADE is a local-first character workspace, now using its own PostgreSQL runtime rather than Letta. The immediate character is Lin Xiaotang (林小棠). Existing facts are versioned and subject-owned; messages are immutable. The model reviewer interprets natural meaning while ADE binds provenance, ownership, versions and atomic writes. Current search_memory retrieves facts, not transcripts. The proposal reuses dialogue through bounded read-only search/read and compares existing behavior, automatic history retrieval, and discretionary tool retrieval.

SETTLED CONSTRAINTS: Natural conversation, not memory commands. Shared experiences are same user plus same character definition root across chats and ordinary persona versions. Profile facts may be shared with another character without implying participation in its conversations. Archived conversations remain recall-eligible without restoration. Explicit operator fact removal is not transcript erasure. No conversational privacy/no-save/consent subsystem, phrase-specific semantic regex or equivalent keyword rules, episode store, writable notebook, second reviewer, new memory service or spending gates. Structural isolation and provenance still apply. Challenge contradictions, but flag any suggested change to these agreements rather than quietly redesigning the product.

YOUR MANDATE: Scrutinize the distinction between what was said and what is currently true, including corrections, invalidation, endings, removed facts with retained dialogue, habits versus preferences, resolved concerns and vague follow-ups. Does the proposed read contract make natural continuity possible without repetitive personalization or unsupported promises? Does retrieval-only no-write authority adequately prevent resurrection while allowing genuinely fresh statements? What should the character say when linked lifecycle metadata is absent or history is incomplete? Test these questions with short natural Mandarin multi-turn examples, including an archived conversation and a persona-version change. Do not turn examples into production phrase rules.

Also challenge the evaluation: identify missing negative cases, misleading tool-call assertions, false precision and whether the comparison separates retrieval quality from reviewer/generation quality. You may recommend simplifying or not implementing part of the proposal. Do not conduct a vendor survey or claim live behavior you cannot observe.

OUTPUT: Give an answer-first verdict (ready, targeted revision, or not ready), then prioritized issues with exact plan/source references, a concrete failure example, and the smallest correction. Separate implementation blockers from questions best resolved by the bounded experiment. State which proposed contracts you would keep, change or leave empirical. Include a compact natural-dialogue acceptance set and source/access limits. Label observations, inferences and hypotheses; do not manufacture issues or treat plausible examples as observed failures. Consultation is not implementation or release acceptance.
```

## Pro 2: Architecture And Simplification

```text
Independently review ADE's proposed historical-recall plan against the repository, with a primary mandate to reduce cognitive and implementation complexity while preserving explicit ownership and correctness. We need to know whether the smallest useful experiment is well designed, not how to build a general memory platform. Your report will guide a plan revision before implementation.

ACCESS AND ANCHOR: GitHub only. Repository https://github.com/Wenjun-Mao/Letta-Open-ADE ; discovery branch codex/character-continuity ; exact source/plan commit cece5bedd6032da3ebc3802c7be604eb505967e6. State the commit and files actually inspected. If unavailable, state the limitation and do not substitute main or another revision. Local services, databases, ignored captures and prior conversations are unavailable. Published findings are summaries, not independently inspected private evidence.

PLAN: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/cece5bedd6032da3ebc3802c7be604eb505967e6/docs/plans/natural-history-recall.md
PRODUCT AUTHORITY: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/cece5bedd6032da3ebc3802c7be604eb505967e6/docs/product-contract.md
DECISION MAP: docs/adr/README.md at that commit; in particular ADRs 0035 and 0036. Historical ADRs/plans are not competing current instructions.
SOURCE ROOT: services/ade-api/src/ade_api/features/agent_runtime/ at that commit. Inspect natural_context.py, turn_execution.py, executor.py, natural_memory_reviewer.py, natural_memory_review.py, natural_memory_binding.py, persistence/metadata.py, persistence/conversations.py, persistence/memory_source_read.py and relevant tests under services/ade-api/tests/agent_runtime/. Follow only additional dependencies needed to verify a consequential claim.

CONTEXT: ADE owns a PostgreSQL native runtime with immutable messages, subject facts, lifecycle revisions, persona-definition roots/versions, a bounded model/tool loop and one synchronous reviewer before atomic finalization. Model Router provides conversation/reviewer and endpoint-independent embedding routes. Existing search_memory searches facts. Historical transcript recovery is proposed, not implemented. The retained branch is not release-qualified; a known stale policy-fingerprint gate remains unwaived.

SETTLED CONSTRAINTS: Natural dialogue without storage/search commands; same-user/same-character experiences across conversations and ordinary persona versions; archived chats eligible without restoration. Profile facts are subject-owned, distinct from character experience. Operator removal retains raw history. No conversational privacy-policy system, semantic phrase rules, episode store, writable notes, extra reviewer/service, spending enforcement, compatibility scaffolding or broad refactor. Keep structural source isolation, exact attempt/timeout semantics, versions and atomicity. Prefer direct code over speculative abstraction.

YOUR MANDATE: Trace the minimum changes needed for a bounded source reader, automatic versus discretionary access, and the proposed read-only H evidence/conflict extension. Challenge whether search/read really need two operations, whether the H extension is necessary or over-scoped, and whether existing code can be reused without weakening write authority. Examine snapshots versus commit order, cross-chat definition-root joins, archive/purge races, missing provenance links, source previews, context capacity, tool continuations, reviewer visibility and optional-read failure semantics. Distinguish genuine correctness holes from production-scale work deliberately excluded from an isolated bounded probe.

Review the proposed ranking feasibility step and three-arm evaluation for confounding, future-turn leakage, mutable setup, mismatched evidence and unfair capacity. Is the baseline prerequisite useful or unnecessarily blocking? Can fewer mechanisms answer the central question? Specify the least additional contract or test required for any blocker; do not invent frameworks or demand production indexing before feasibility can be measured. No model/provider calls or implementation are requested.

OUTPUT: Give an answer-first verdict (ready, targeted revision, or not ready), a minimal component/data-flow sketch, prioritized findings with pinned code/plan references and concrete falsification tests, and a keep/simplify/defer list. Separate proven code facts from inference and empirical unknowns. Recommend revised checkpoint boundaries only where materially useful. State what cannot be established without execution. Do not treat code inspection, reviewer consensus or mock tests as live quality or release acceptance.
```

## Integration Of Returned Reports

Preserve each report unchanged. Record source corrections and synthesis separately;
classify useful insights as Use, Test, Park or Discard. Verify consequential code
claims locally and revise the existing historical-recall plan once. Further review
is warranted only for unresolved consequential decisions, not consensus polishing.
