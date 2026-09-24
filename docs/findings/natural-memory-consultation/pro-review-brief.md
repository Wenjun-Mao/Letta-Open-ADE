# ChatGPT Pro: Second Memory Design Review

Date: 2026-09-23. Brief version: natural-memory-pro-review-2.
Purpose: scrutinize the revised design before any implementation plan.
The first-round brief and design remain in Git at documentation commit
`243d8d0b4e850aca304eea2699e58ec24d45479b`.

## Evidence Anchors And Access

- Repository: <https://github.com/Wenjun-Mao/Letta-Open-ADE>
- Discovery ref: `codex/character-continuity`, not `main`.
- Unchanged implementation baseline: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.
- Revised design/packet: the documentation commit in this round's handoff.
  Record that exact revision separately from implementation; do not review the
  old design as though it were revision 2.
- Public GitHub only: no local files, services, database, ignored captures,
  credentials, browser sessions, execution, or previous conversations assumed.

If required evidence is inaccessible, report the limitation rather than silently
substituting another branch or treating a summary as a direct code audit.

## Product And Existing Foundation

ADE is a local-first conversational-character product using Lin Xiaotang (林小棠).
We want natural factual updates and useful, restrained recall across conversations,
without requiring memory commands, inventing physical shared experiences, or
promising unimplemented memory/control behavior.

ADE already has PostgreSQL subjects, immutable messages, typed/versioned facts,
source spans, embeddings, automatic fact retrieval, optional search, compaction,
leases, run events, and ADE-owned retry semantics. Conversation generation precedes
the reviewer; successful assistant/memory finalization is atomic. Shared subject
facts span characters. Option A removal excludes saved records from active memory
but retains history; it is not erasure or global suppression.

DeepSeek conversation/reviewer and relocatable Qwen embeddings are unqualified
candidates behind Model Router. A previous synthetic Stage A failed a mismatched
required-tool contract. Exact response/wire contents are unavailable; that result
does not establish a memory quality failure. No calls, rollout, or release waiver
are authorized by this consultation.

## What Changed After Round One

Two independent source reviews challenged the initial design. The maintainer
reproduced six synthetic in-process counterexamples involving context truncation,
deduplication, telemetry, current-only clarification evidence, and entity labels.
No live provider behavior was reproduced.

The revised proposal:
- Keeps one fact system, not a new memory framework or continuity schema.
- Gives independently mutable preferences separate application-owned IDs.
- Defines lifecycle for uncertain history, invalidation without replacement,
  inactive removal, and reassertion; no inferred legacy decomposition.
- Permits bounded earlier user spans only with a current clarification anchor;
  assistant exchanges provide reference context, not factual authority.
- Protects mandatory policy, packs whole records, handles revision conflicts,
  carries provenance, and accounts for final provider requests.
- Proposes current-identity derivation and conservative stale-narrative guards.
- Keeps synchronous post-response review and its explicit availability/snapshot
  tradeoffs; adds a proposed exact-target operator removal escape at capacity.
- Defers generic historical-fact search, arbitrary retrospective history repair,
  continuity tables, and broad transcript search. Source-window comparison comes
  before introducing another durable memory lifecycle.

The changed design includes new decisions that deserve independent challenge:
summary watermarks/guard-or-withhold behavior; absence-dependent add read sets;
typed operator-action provenance; reported-residence semantics; and the bounded
clarification window. Do not accept these simply because they respond to reviewers.

## Required Reading

At the revised documentation commit, read:
1. `docs/architecture/natural-memory-design.md`
2. `docs/findings/natural-memory-consultation/design-scenarios.md` (22 arcs)
3. `docs/findings/natural-memory-consultation/source-map.md`; follow the pinned
   implementation links and relevant tests.
4. `docs/findings/natural-memory-consultation/pro-review-assessment.md`
5. Original round-one `reports/pro-a.md` and `reports/pro-b.md`.
6. ADRs 0022 and 0026 for current scope/removal authority.

The source map remains anchored to unchanged code. The assessment distinguishes
source inspection, executed synthetic probes, logical counterexamples, and
unmeasured behavior. Original public-research reports are optional background;
their agreement and exported citation tokens are not independent validation.

## Review Questions

Has revision 2 fixed each material design issue, explicitly bounded it, or merely
renamed it? Map first-round findings to resolved, partial, unresolved, or deferred
with consequences. A legitimate deferral is not implementation of the capability.

Specifically challenge:
- Are fact identity and transition rules closed over the worked cases? Are legacy
  records, removal/reassertion, and unknown history treated without fabrication?
- Can clarification evidence preserve ownership, negation, scope, and source
  lineage without enabling unrelated historical extraction?
- Does guard-or-withhold actually cover stale summaries AND raw dialogue? Is its
  watermark/concurrency design worth the complexity, or is a smaller policy enough?
- Does exact-target operator removal create a coherent product contract and
  provenance path, rather than a hidden bypass or imaginary authentication?
- Are source eligibility, archived conversations, shared facts versus private
  dialogue, and Option A limits internally consistent?
- Are absence-read checks narrowly justified? Distinguish stale mutations, duplicate
  adds, and intentionally allowed stale no-op replies.
- Do the historical-repair and source-search deferrals leave an acceptable first
  product target, with honest limitations rather than silently weakened tests?
- What should still be deleted or simplified before implementation planning?

## Requested Output

Start with a verdict and exact inspected commits. Give prioritized remaining
findings with code/design evidence, concrete counterexamples, and smallest
sufficient corrections. Include a compact disposition of the first-round findings.
Distinguish proved source behavior, logical design contradictions, product tradeoffs,
and hypotheses. Tests read are not tests executed.

Recommend a simpler alternative wherever it meets the same requirements with fewer
independent correctness obligations. Do not optimize merely for table or line count.
Conclude whether this design is ready to become an implementation plan and list
only the blocking design decisions or missing bounded experiments.

Do not produce the implementation plan, write code, make provider calls, or approve
a release. Consultant agreement is not acceptance or authorization.
