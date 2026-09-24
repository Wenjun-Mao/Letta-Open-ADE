# ChatGPT Pro: Third Memory Design Review

Date: 2026-09-23. Brief version: natural-memory-pro-review-3.
Purpose: scrutinize revision 3 before any implementation plan or accepted ADR.
This is a high-leverage core design; identify overlooked interactions as well as
checking whether the previous critiques were addressed. Agreement is not proof.

## Evidence Anchors And Access

- Repository: <https://github.com/Wenjun-Mao/Letta-Open-ADE>
- Discovery ref: `codex/character-continuity`, not `main`.
- Unchanged implementation: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.
- Revision 3 packet: the exact documentation commit in this round's handoff.
  Record it separately from implementation; the new contracts are not running code.
- Previous revision 2: `d80afb422b3deefa09f13ac5e7017c5e3e8524ef`.
- Original revision 1: `243d8d0b4e850aca304eea2699e58ec24d45479b`.
- Public GitHub only. No local files, services, database, ignored captures,
  credentials, browser sessions, execution, or prior conversation assumed.

Report inaccessible evidence instead of silently substituting another revision
or presenting summaries as direct inspection. Tests read are not tests executed.

## Product And Foundation

ADE is a local-first conversational-character product using Lin Xiaotang (林小棠).
We want natural factual updates and useful, restrained recall across conversations,
without memory commands, invented physical shared experiences, or unsupported
promises. A silent relevant use of memory can be better than an explicit callback.

The existing foundation includes PostgreSQL subjects, immutable messages, typed
facts/revisions, source spans, embeddings, automatic retrieval, optional search,
compaction, leases, run events, and ADE-owned retries. Generation precedes review;
successful assistant/memory finalization is atomic. Shared subject facts span
characters; full dialogue does not. Option A removes saved records from fact
selection while retaining messages/history, not global suppression or erasure.

DeepSeek conversation/reviewer and relocatable Qwen embeddings are unqualified
Model Router candidates. A prior synthetic Stage A failed a required-tool contract
that allowed provider `auto`; its exact response/wire contents are unavailable.
That does not establish a memory-quality failure. No new provider experiment,
runtime change, merge, deployment, or qualification waiver is authorized here.

## Amendment And Deliberate Tradeoffs

Revision 2 retained the foundation but left several contract gaps. Revision 3:
- Removes summary-watermark guard elision. Even a newly generated summary can be
  stale. Before admitting prior narrative, the response context must carry the
  complete eligible lifecycle snapshot or withhold that narrative with a gap.
- Replaces specialized read sets with one monotonic subject-memory generation,
  bound at message acceptance and checked for every nonempty write. This includes
  identity dependencies and operator removals, not just the changed target row.
- Derives one lifecycle view from revisions to identify null inactive assertions
  without presenting them as current facts or exposing forgotten chains.
- Shares one bounded clarification bundle across generation/review and defines
  current user endorsement separately from bare reference selection.
- Makes direct multi-target operator removal atomic, with typed causal provenance,
  snapshot/target checks, and idempotent outcome replay. It does not promise to
  restore chat capacity for every oversized-input cause.
- Corrects the preference-versus-consumption fixture and narrows state precedence
  to the same attribute, scope, and time, including residence versus a visit.

These are proposals to scrutinize, not reviewer-approved correctness guarantees.
Complete guard packets may crowd out useful history. A subject counter may reject
harmless writes; capturing it at acceptance also affects queued/in-flight turns.
Shared evidence cannot guarantee identical model interpretation. Endorsement source
roles extend the current validation contract. These costs must remain explicit.

Still deferred: generic historical-fact search, arbitrary retrospective repair,
continuity tables, broad transcript search, global suppression, background review,
graphs, external memory adoption, and stronger dialogue linearizability. Bounded
source-window comparison precedes any additional durable continuity representation.

## Required Reading

At the revision 3 documentation commit:
1. `docs/architecture/natural-memory-design.md`
2. `docs/findings/natural-memory-consultation/design-scenarios.md` (22 expanded arcs)
3. `docs/findings/natural-memory-consultation/source-map.md`; follow pinned code
   and relevant tests at implementation `4905ce1`.
4. `docs/findings/natural-memory-consultation/pro-round2-assessment.md`
5. Unchanged `reports/pro-round2-a.md` and `reports/pro-round2-b.md` in that folder.
6. ADRs 0022 and 0026 for current product/removal authority.

The first assessment and first-round reports remain available as background.
Its six synthetic reproductions are maintainer-reported executions, not tests
performed by either Pro. Round-two design counterexamples were inspected logically,
not demonstrated as deployed bugs. Public-research reports are optional background.

## Review Questions

Map round-two findings to resolved, partial, unresolved, or explicitly deferred.
Then challenge revision 3 independently; do not stop at a checklist of prior advice.

- Does the guard admission rule close the fresh-summary counterexample without
  claiming historical completeness? Is a smaller rule equally safe and more useful?
- Do all writers advance the generation correctly, including operator removals?
  Check acceptance-to-snapshot, identity-change, empty-again, rollback, idempotency,
  queued turns, and permitted stale no-op replies. Is the cost proportionate?
- Does the derived inactive descriptor identify targets while preserving lifecycle,
  root boundaries, source attribution, and forgotten-chain exclusion?
- Can the shared bundle preserve negation/corrections and partial confirmations?
  Does the reply/reviewer agreement rule prevent hidden mutations without rejecting
  normal natural speech? Check user assent versus assistant-origin invention.
- Are typed operator provenance, all-or-nothing effects/results, and local-only
  authorization coherent with the current schema and accepted ADRs?
- Are selection, clarification, complete guard/reviewer packets, and total request
  budgets mutually consistent? What happens when each cannot fit?
- Do historical deferrals, Option A limits, and unavailable later updates remain
  honest product boundaries? Are they acceptable for a first natural-memory target?
- Do scenarios independently specify answerability, false/missed writes, unnecessary
  withholding, unsupported cases, and reply quality rather than reward abstention?
- What can be removed or simplified without hiding a correctness obligation?

## Requested Output

Give an answer-first verdict and exact inspected commits, then prioritized findings
with source/design references, concrete counterexamples, and smallest sufficient
corrections. Include a compact disposition of round-two findings. Distinguish
source-proven behavior, design contradictions, deliberate tradeoffs, and empirical
unknowns. Challenge both overengineering and unsafe simplification.

Conclude whether the design is ready for an implementation plan. List only actual
blocking contract decisions or bounded experiments; do not manufacture additional
review cycles, write the implementation plan, or mistake agreement for acceptance.
No code, provider calls, release approval, or production action is requested.
