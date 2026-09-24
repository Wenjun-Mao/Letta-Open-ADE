# Natural Memory Consultation Review

Third-round reports are preserved as [Round 3 A](reports/pro-round3-a.md) and
[Round 3 B](reports/pro-round3-b.md). The [third-round assessment](pro-round3-assessment.md)
is now incorporated into the [revision-4 amendment](../../architecture/natural-memory-design.md)
and [bounded implementation plan](../../plans/natural-memory-implementation.md).
The [plan-review brief](pro-review-brief.md) requests Pro scrutiny before implementation.
Full-snapshot admission is a provisional control, not an accepted production rule.
No runtime changes or provider experiments accompanied this documentation checkpoint.

Second-round feedback is preserved as [Round 2 A](reports/pro-round2-a.md) and
[Round 2 B](reports/pro-round2-b.md). The [second-round assessment](pro-round2-assessment.md)
records the reasoning behind revision 3 (preserved at `c01f45a`):
independent narrative guards, one mutation-generation check, shared lifecycle and
clarification views, explicit endorsement, and atomic operator removal. The
third review is preserved at `c01f45a`; the brief at the current path now reviews
the implementation plan. All contracts remain proposed, not implemented.

Follow-up: two independent repository critiques are preserved as
[Pro A](reports/pro-a.md) and [Pro B](reports/pro-b.md). The separate
[assessment](pro-review-assessment.md) records verified counterexamples and
recommended design revisions, without changing the original reports or accepting
a new runtime contract. Revision 1 remains pinned at `243d8d0` and revision 2 at
`d80afb4`, and revision 3 at `c01f45a`. Current paths hold revision 4 and its first
implementation plan, both awaiting review. No runtime changes were made for them.

Date: 2026-09-23. Status: research synthesis for discussion, not an accepted
architecture, implementation plan, or release qualification.

Next review: [concrete proposed design](../../architecture/natural-memory-design.md),
[worked conversations](design-scenarios.md), [pinned source map](source-map.md),
and [ChatGPT Pro brief](pro-review-brief.md). The user selected design scrutiny
before the experimental milestone suggested below. These documents are proposals,
not an accepted ADR or permission to run provider experiments.

## Reports and provenance

The user supplied two external reports. Neither consultant inspected ADE source;
both worked from a maintainer summary and public material. Their recommendations
are evidence to review, not instructions or authorization.

- [Behavior report](reports/behavior.md): *Natural Memory for a Persistent
  Conversational Character*. SHA-256:
  `54896073704177cf25f976890cd650a3d30e0eb2199b88358bf2f8562284a503`.
- [Architecture report](reports/architecture.md): *A Simple Memory Architecture
  for Natural Conversational Continuity*. SHA-256:
  `488a934d242fe427a403a6e8ac57b59ee552e22d492f427ed654496215f8df68`.

These are byte-identical copies of the supplied Markdown. Embedded citation and
file-reference tokens do not resolve independently from these exports. Preserve
them unchanged; use the checked primary links below for the claims we rely on.
The imported architecture report exceeds the usual module-length guideline
because it is an original evidence artifact, not authored implementation code.
The originals also retain 22 trailing-space Markdown hard breaks reported by
`git diff --check`. They are deliberately not normalized, preserving the hashes
above. Authored review documents are checked separately for whitespace and links;
this evidence-preservation exception does not apply to runtime code.

## Assessment

The most useful reframing is to measure three things separately: whether the
stored understanding is current, whether useful evidence reaches the response,
and whether the response uses it appropriately. Memory need not announce itself.
Natural updates and relevant recall are product goals; tool conformance is a
lower-level engineering check.

Neither report establishes a winning ADE implementation. The architecture
comparison's high/medium/low ratings are hypotheses, not measurements. Its
recommended ledger, episode retrieval, temporal normalization, hybrid search,
and background processing would be several changes, not one small patch.

## Checked evidence and qualifications

- [LoCoMo-Conv](https://arxiv.org/abs/2609.03467) studies conversational rather
  than only QA-style memory queries. Its abstract supports distinguishing
  retrieval from response quality and memory use without explicit fact recitation.
  This is research evidence for evaluation design, not a proven ADE improvement.
  Exact report claims about a September 22 revision were not independently
  confirmed and are not used here.
- [STALE](https://arxiv.org/abs/2605.06527) explicitly studies implicit invalidation,
  state resolution, stale-premise resistance, and downstream adaptation. Its
  reported results do not establish a universal failure rate or justify applying
  inferred changes to unrelated stored preferences.
- [MemSyco-Bench](https://arxiv.org/abs/2607.01071) evaluates applicability, factual
  authority, updates, and appropriate personalization after retrieval. It supports
  testing memory use separately from lookup success.
- [Mem0's current algorithm description](https://mem0.ai/blog/mem0-the-token-efficient-memory-algorithm)
  describes additive extraction, unlike its older reconciliation pipeline. The
  [pinned prompt source](https://github.com/mem0ai/mem0/blob/47a69e1e72dc562b6fdd49a9ef892229afc7508a/mem0/configs/prompts.py)
  contains `ADDITIVE_EXTRACTION_PROMPT` and its ADD-only description. This corrects
  our earlier generic account of Mem0 as an update/delete system. We did not
  independently audit its entire executable path. Its
  [README](https://github.com/mem0ai/mem0/blob/main/README.md) distinguishes managed
  benchmark optimizations from the OSS implementation; no performance transfer
  to ADE is assumed.
- [Character.AI's announcement](https://blog.character.ai/memory/) confirms
  advertised Story Memory, Facts, pins, and background context management.
  This review does not independently verify every UI detail in the report,
  proprietary internals, or reliability.

The reports' remaining numerical comparisons, source revisions, and vendor
features have not all been revalidated. None is required to select the first
ADE experiment. Agreement between consultants is not independent replication.

## ADE-specific corrections and boundaries

- ADE already has immutable source messages, typed facts, revisions, current
  projections, subject ownership, and source links. Keep these foundations.
  The missing distinction is semantic: a formerly true state changing is not
  the same as retracting an erroneous assertion. More generic ledger plumbing
  is not automatically needed.
- The current reviewer receives all active subject facts, not merely a retrieved
  candidate subset. Relevant-candidate selection is a possible later scaling
  change, not something already implemented.
- Current saved-fact removal is the previously accepted limited operation:
  exclude the fact from active profile/search while retaining source history.
  The reports propose stronger suppression/deletion behavior. That is a product
  contract decision, not an already-authorized bug fix or promise we can make.
- A request not to mention something, a superseded fact, a request not to use
  information, and physical erasure have distinct effects. The reports themselves
  differ on how to map ordinary "forget" wording. Do not automatically change
  retention or destructive behavior based on either report.
- An evidence-kind field alone does not prevent false memories. Source binding,
  authorization, semantic validation, and verified tool outcomes still matter.
  Assistant narration must not become evidence of physical shared experience.
- PostgreSQL lexical retrieval is a hypothesis to test on Chinese as well as
  English. Built-in full-text search is not automatically BM25 or adequate Chinese
  tokenization. Avoid introducing a new search service before a measured need.
- The recommendation to abandon vector-only retrieval is too categorical for
  our present evidence. Retain it as a baseline and test a lexical addition.
- Background review plus a pending-message bridge introduces ordering, privacy,
  failure recovery, and cross-conversation consistency work. Defer it until
  measured latency justifies changing the synchronous path.
- Conversation/source retrieval would broaden what the model can see. It needs
  subject boundaries, suppression/deletion rules, and treatment of old messages
  as untrusted evidence before becoming a production fallback.

## Insight disposition

These are review recommendations, not adoption decisions.

| Disposition | Insight | Next action |
| --- | --- | --- |
| Use | Natural updates and appropriate recall are the primary product criteria. | Make the next proposal behavior-first. |
| Use | Keep provenance, versions, explicit subjects, and bounded context. | Preserve existing protections in every candidate. |
| Use | Score write correctness, evidence retrieval, and dialogue quality separately. | Use independent annotations and human comparison for style. |
| Test | Broader natural state reconciliation through the existing reviewer. | Shadow proposals for completed changes versus intentions, history, and ambiguous references; no writes. |
| Test | Memory can help without an explicit callback. | Compare responses using identical supplied evidence; do not claim retrieval evidence from this test. |
| Test | Source snippets may recover experiences omitted by typed facts. | Compare a small authorized synthetic source baseline before adding episode schemas. |
| Test | Lexical signals may complement embeddings. | Fixed-budget retrieval comparison, including Chinese names and paraphrases. |
| Park | Generic assertion schema, full temporal intervals, graphs, rerankers, reflection agents, background learning. | Require residual failures and measured benefit first. |
| Discard | Treating one successful tool call or a vendor leaderboard as product acceptance. | Keep conformance and conversational outcomes distinct. |
| Discard | Treating user assertions or assistant prose as universally authoritative truth. | Preserve attribution, uncertainty, and verified-outcome distinctions. |

## Recommended next milestone

Propose a bounded **natural continuity baseline and natural-update experiment**,
not the whole architecture report as an implementation plan:

1. Review 10-12 short synthetic, multi-conversation arcs, reusing useful M1/M2
   scenarios. Include completed moves, unfulfilled plans, historical statements,
   preference scope, changing concerns, ambiguous entities, irrelevant-memory
   controls, and discussion-versus-physical-experience attribution. Mark unsupported
   capabilities explicitly rather than weakening expected behavior to fit ADE.
2. For each arc, annotate expected current/historical understanding, admissible
   evidence, prohibited claims, and whether mentioning the memory helps. Mark
   suppression/erasure scenarios as unresolved product-contract probes, not claims
   of existing implementation support.
3. Compare current reviewer decisions with one candidate natural-update policy in
   shadow mode. Measure missed changes and false updates separately. Do not add
   episode storage, asynchronous jobs, or retrieval changes in this experiment.
4. Separately test reply quality using fixed evidence to isolate response behavior
   from extraction/retrieval quality. Human preference is not a deterministic gate.
5. Use the failure breakdown to decide whether the next smallest implementation is
   update semantics, context selection, or a source-retrieval experiment.

These steps are proposals. Provider use needs a new explicit budget; no calls
were made for this review. The earlier failed Stage A result and unused balance
remain unchanged. Stage B/C, release promotion, and production changes remain
blocked. No schema, runtime, dependency, or forgetting behavior changes were made.
