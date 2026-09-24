# ADR 0029: Bounded Natural-Memory Lifecycle and Comparison Contract

- Status: Accepted for checkpoints 1–5 implementation; not a release or context-policy acceptance
- Date: 2026-09-24
- Authority: [natural-memory implementation plan](../plans/natural-memory-implementation.md), revision 3

## Problem

The M3 typed-fact path supports explicit correction/removal but cannot reliably
interpret ordinary changes, separately target scoped assertions, or show an
ended assertion without presenting it as current. Current generation and review
can also see different evidence, and conversation/version checks alone do not
fence concurrent subject-memory changes. A full snapshot protects against stale
narrative but can displace an immediately preceding clarification under load.

## Decision

Retain ADE's PostgreSQL subjects, immutable messages, revision lineage, existing
worker ownership, and synchronous review. Extend one lifecycle projection to
active, inactive (ended/invalidated), and forgotten; use stable assertion IDs for
independently mutable preferences. A mixed reviewer may add, revise with a closed
reason, end, reassert, or forget. Same-turn no-save/removal excludes equivalent
writes without blocking unrelated assertions. Provenance records user authority,
assistant referents, or operator causation explicitly; an assistant alone cannot
authorize a user fact.

Capture a monotonic subject-memory generation at turn acceptance, before provider
work. Effective memory/identity writes advance it in the same transaction as the
assistant response and revisions; no-op/replay does not. Initial review snapshot
and finalization check that accepted generation as well as target versions. A
conflict is terminal for that run and never triggers automatic model work. All
writer paths use a consistent lock order. Direct operator removal is a separate
idempotent, exact-target action and historical receipt, not a fake conversation
turn or proof that a later restatement is absent.

Generation and review share one bounded, complete-message clarification suffix.
The same reviewer sees the proposed reply as reference-only and gives typed
per-claim allow/defer/contradiction outcomes. Permitted deferral removes dependent
fact, staged entity, and index effects; contradiction rejects the whole attempt.
Failed opt-in synthetic attempts must retain safe, bounded, outcome-verified
evidence before their cells can be scored. Successful database behavior alone
does not satisfy that evidence gate.

Keep three workflow-bound context variants only for isolated comparison: A
requires the whole current lifecycle snapshot before optional narrative; A0
removes A's summary without reallocating evidence; B reserves local dialogue
first, then selectively admits current lifecycle views. A and B face the same
positive usefulness and safety bar; A0 is diagnostic only. The frozen offline
comparison treats A0's full-snapshot overflow as a selective B-style path:
the A/A0 nonsummary equality applies when the full snapshot fits, while the
pressure fallback deliberately diverges and must be compared on the same
eligible local pool and retrieval recipe. Full-snapshot A/A0 turns skip the
redundant automatic retrieval call; selective A0/B turns pay for it.
The frozen offline
matrix and request schedule precede any live calls. No variant becomes the
production binding merely because its implementation or fake-model tests pass.
The development-only binding IDs are `natural-user-assertions-v2-a`,
`natural-user-assertions-v2-a0`, and `natural-user-assertions-v2-b`; they are
immutable definition versions, not a turn payload selector. The natural
retrieval-policy version distinguishes lifecycle descriptors from legacy
active-only indexes while preserving the same embedding-space identity. The
reader deduplicates current revisions before applying its result limit.

## Rejected Alternatives and Consequences

- Do not add a new memory service, continuity table, graph, background reviewer,
  generic historical-revision retrieval, or model-facing source-window search.
- Do not merge preferences by category/name or infer decomposition of ambiguous
  legacy records; old location values keep their original uncertain meaning.
- Do not treat a summary date/generation as certification that old narrative is
  current, or make removed saved information a promise of historical erasure.
- Do not silently rebase stale turns, repair candidate prose, or spend a provider
  retry on semantic/generation conflicts.

The additive migration must preserve old data and compatible vector reads.
Existing policy-bound conversations remain readable/replayable, not silently
upgraded; new semantics require a new immutable binding. This ADR amends the
bounded M3 representation and composer-only removal journey in
[ADR 0022](0022-incumbent-memory-first-product-slice.md) and the reply boundary
in [ADR 0026](0026-memory-removal-reply-boundary.md), while retaining
[ADR 0021](0021-evidence-scoped-memory-and-affirmative-tools.md)'s source-bound
authority. None of those earlier decisions is rewritten as if it had covered
these new semantics. Provider qualification, checkpoint 6, policy selection, and
release remain separately gated. Governed runtime sources intentionally change
the current production policy hashes; existing candidate fingerprints and
release evidence remain historical and must fail the current-policy match
until a separate qualification and promotion rebinds them.
