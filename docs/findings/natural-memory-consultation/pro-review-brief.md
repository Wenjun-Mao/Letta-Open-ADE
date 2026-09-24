# ChatGPT Pro: Repository-Grounded Memory Design Critique

Date: 2026-09-23. Brief version: natural-memory-pro-review-1.
Purpose: challenge a proposed design before implementation, not approve a release.
Publication authorization covers this review branch and both supplied reports;
it does not authorize operating the user's ChatGPT account or a deployment.

## Evidence Anchors

- Repository: <https://github.com/Wenjun-Mao/Letta-Open-ADE>
- Discovery ref: `codex/character-continuity`, not `main`.
- Implementation baseline: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.
- Design/packet: this documentation checkpoint. The handoff must supply its
  full commit SHA and an immutable link after publication; record the actual
  documentation revision inspected, separately from the implementation anchor.
- Access: public GitHub only. No local files, database, services, ignored captures,
  credentials, browser state, previous conversations, or execution assumed.

If a required source or document cannot be read, report that limitation. Do not
silently substitute main, infer ignored artifacts, or call a summary a code audit.

## Self-Contained Assignment

ADE is a local-first conversational-character product. The initial character is
Lin Xiaotang (林小棠). We want natural factual updates and useful, restrained recall
across conversations, not a profile editor that requires "search memory" commands.
Users should feel listened to without false physical co-presence, invented facts,
automatic psychologizing, constant callbacks, or unsupported future promises.

The native runtime already owns PostgreSQL subjects, immutable messages, typed
facts, revisions/source spans, pgvector retrieval, a model reviewer, compaction,
run events, leases, and ADE-owned retries. The conversation model is followed by
the reviewer; assistant/memory success commit atomically. Subjects intentionally
share facts across characters. Current removal only excludes saved active facts;
history remains (accepted Option A), not all-context suppression or erasure.

Current shortcomings include regex-selected add-only versus correction modes,
one preference slot per category, no durable concerns/events, recency-first
profile selection, and fact-only deeper search. A failed synthetic run mixed
mandatory tool validation with provider auto choice and conditional user wording.
Its exact failed reply/wire request is unavailable; it is not proof the provider
cannot recall. Qualification remains blocked and historical evidence unpromoted.

Selected unqualified provider candidate: DeepSeek conversation/reviewer with
Qwen embeddings behind a relocatable Model Router route. This is not a request
to research provider pricing, make calls, deploy, or resume qualification.

Our proposed direction keeps the current architecture. It adds natural fact
reconciliation with change-versus-error semantics, initially retains composed
scoped preference text, improves automatic context selection, and proposes small
character-scoped continuity entries in a later increment. Transcript retrieval
is an experiment, not an assumed production feature. Background extraction,
graphs, generic temporal engines, autonomous outreach, and framework replacement
are deferred. The design explicitly preserves the limitations of Option A.

Read in order, in the documentation revision supplied in the handoff:

1. `docs/architecture/natural-memory-design.md`
2. `docs/findings/natural-memory-consultation/design-scenarios.md`
3. `docs/findings/natural-memory-consultation/source-map.md`, following its pinned
   implementation links and inspecting relevant tests directly.
4. `docs/adr/0022-incumbent-memory-first-product-slice.md` and
   `docs/adr/0026-memory-removal-reply-boundary.md`.
5. The consultation `README.md` and original `reports/` for context, not authority.

The two earlier reports did not inspect this repo. Their exported citation tokens
may not resolve; the separate assessment gives verified links and qualifications.
Challenge their assumptions and our synthesis as freely as the design itself.

## Questions That Matter

- Does the proposal actually support natural change and recall without new forms
  of stale memory, over-personalization, or inferred biography?
- What current capability did we miss or duplicate? Which code contracts must
  change? Cite paths/functions at the implementation anchor.
- Are composite preference values a fragile shortcut? Can scope and deletion
  remain correct without a generic assertion model? Offer the smallest counterexample.
- Do continuity entries earn three new tables, or can a smaller fact-plus-source
  approach satisfy the same cases? Account for temporal state and read costs.
- Does definition-root scope appropriately separate shared user facts from
  character-private continuity across persona versions?
- Is post-response atomic review acceptable? Inspect failure, cancellation,
  concurrency, stale reads, and no-write-on-failed-turn consequences.
- Can summaries/raw history undermine current-state accuracy or the limited
  removal promise? Distinguish bugs from deliberately unsupported stronger promises.
- Are source attribution, ambiguity, entity matching, and prompt-injection
  boundaries specified honestly, without treating exact quotes as entailment proof?
- Which selection/budget choices should be measured rather than baked in? Are
  the proposed test expectations fair and separate write/retrieval/reply quality?
- What should be removed, deferred, or implemented first to reduce cognitive load?

## Requested Report

Start with a verdict: workable as proposed, needs targeted revision, or rethink.
State exact source/document commits and what you actually inspected. Present
findings ordered by consequence, with code/design evidence, a concrete failure
scenario, and the smallest sufficient correction. Distinguish demonstrated
contradictions, design tradeoffs, hypotheses, and missing evidence.

Then provide a simplified recommended design, a keep/change/defer table, and a
short sequence of falsifiable tests before implementation. Include a case where
the proposed approach loses to a simpler alternative. Do not invent benchmark
results, turn subjective warmth into substring tests, or propose a larger platform
without showing why a smaller solution fails. Consultant agreement is not product
acceptance, provider qualification, or authorization to change release evidence.
