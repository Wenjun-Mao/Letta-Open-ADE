# Story Retrieval Reviews: Source-Checked Assessment

Date: 2026-09-30. Status: reports integrated; runtime unchanged, candidate still
unadopted. No new experiment, provider call, deployment or native requalification.
Current agreements: PC-03/04/05/06/09/10/11. This assessment does not settle the
open definition of genuine fictional-history correction or introduce a new gate.

## Recommendation

Stop choosing retrieval mechanisms for now. The reviews identify a more useful
decision question: **which missing passages change what can justifiably be said
in response to the actual question?** Our scorecard measures designated source
groups, not that criterion. Its arithmetic is valid, but the apparent diversity
gain does not distinguish general novelty from handling exact text duplicates.

Keeping the current runtime is justified without another experiment. If further
investment is needed, the next step should be a bounded, independently reviewed
packet-sufficiency audit, not another selector implementation. The proposals
below are conditional and unlaunched. The native turn-7 gate remains failed;
turns 8-10 remain unrun, and no production reliability is established.

## Report Provenance

The user supplied two reports in response to the
[published review packet](character-story-retrieval-review-brief-2026-09-30.md).
They are preserved byte-for-byte, without inserting our corrections or headings:

- [Review A](reports/character-story-retrieval-review-a-2026-09-30.md), SHA-256
  `d77a7671563c0442f9695982b034fa1cabdcfa3f8095d87da38243c2e0243050`.
- [Review B](reports/character-story-retrieval-review-b-2026-09-30.md), SHA-256
  `90f0e8842e8a00b8df504c5770ffd6746d28c603951f8bdf25264ddea9f75771`.

Both state that they inspected 27 files at source
`79852e6ee8c17f2efdd7492dfae6627d91d12c7d`, did not execute tests or provider calls,
and did not access private native receipts. Reviewer identities, human status
and independence from each other are not established by the supplied text. Their
agreement is not replication. They already saw arm outputs; these reports are
not blinded, pre-outcome validation of the labels.

The relevant runtime, fixtures and tests were unchanged between their anchor
and pre-integration HEAD `f87313dec8bfe79e52b83c6a688601800eeb5500`. We checked the
claims below against that source and recomputed fixture properties locally.
Private native results were not re-executed or independently re-audited here.

## Verified Findings And Corrections

### 1. The Scorecard Does Not Identify A General Diversity Benefit

All five cases newly meeting the frozen coverage metric have seven windows but
exactly four distinct `(user text, assistant text)` pairs:
`wrong_repeated_echoes`, `supported_error_correction`, `unsupported_rewrite`,
`compatible_new_detail`, and `anaphoric_correction`.

The candidate selects one representative of each pair. Every possible choice of
one representative per pair would satisfy the declared evidence groups in these
five cases. This verifies B's duplicate-budget objection without building a new
selector or running an additional arm. It does not mean a particular production
deduplication rule is safe: identical wording can have different times, speakers,
source bindings and conversational functions. The native selected windows were
not exact duplicates, so this fixture pattern is not a faithful native replay.

Evidence: [frozen cases](../../../workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/cases.json),
[recorded selections](../../../workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/observed.json),
and the added `test_improved_cases_do_not_distinguish_novelty_from_duplicate_handling`
in [the runtime-owned characterization tests](../../../services/ade-api/tests/agent_runtime/test_story_diversity_candidate.py).
No fixture, expected group, recipe, source hash or selection snapshot was changed.

### 2. Correct The Irrelevant-Source Breakdown

The total eight candidate admissions under the existing irrelevant-source labels
is correct. Their composition is **one other-episode source plus seven unrelated
sources**, not two plus six. In `distinct_similar_episodes`, selected `f` concerns
the second encounter; selected `g` concerns food. The earlier prose mistakenly
treated both flagged selections in that case as other-episode sources.

This is an aggregation/reporting error, not a selector error. The correction
belongs in the finding and scorer-side regression guard, not in runtime or
frozen labels. `test_positive_irrelevant_breakdown_separates_other_episode_and_chatter`
now verifies baseline `(3, 0)` and candidate `(1, 7)` with unchanged aggregate
counts. The no-match case's four admissions per arm remain separate.

The [finding](character-story-source-diversity-2026-09-30.md) explicitly marks the
correction. Whether another episode is useful contrast rather than genuinely
irrelevant remains a prospective labeling question; we do not silently relabel
the frozen metric to improve either arm.

### 3. Some Required Groups Exceed The Question's Demonstrated Needs

Both reports ground these objections in actual fixture text:

| Existing case | Verified distinction; not a new historical score |
| --- | --- |
| Unsupported rewrite | The baseline's selected replies explicitly deny shared participation. The query asks about participation, not whether a rewrite was requested. Requiring the rejected-request exchange adds provenance beyond the demonstrated answer requirement. |
| Supported correction | The correction names the first bowl and distinguishes a later cup. Its antecedent requirement differs from an anaphoric correction; the query itself does not specify the first class. |
| Compatible detail | The query broadly asks what was special about the bag. Contents can support an answer; whether omitting the wet corner is a failure requires a narrower query or an explicit completeness criterion. |
| Anaphoric correction | The correction points back to the initial day without naming it. The earlier passage is a genuine dependency, but episode/chronology attachment and correction authority still require interpretation. |

These are source-backed methodological objections, not independent determinations
of model response quality. Keep 2/7 versus 7/7 as **diagnostic source-group
coverage**, not minimum answer sufficiency or behavioral accuracy. The glossary
now distinguishes those concepts without changing the product contract.

A also correctly qualifies our pressure prose. With the broad question "Tell me
again about the cat you met after work", a shared-core answer can fit both
histories. Identical packets prevent reliable choice of the differing location
and weather, not every faithful answer. The [pressure finding](character-story-retrieval-pressure-2026-09-30.md)
now states that narrower conclusion. Its frozen tests/inputs/results are intact.

### 4. Preserve Structural Boundaries; Do Not Infer Semantic Guarantees

| Claim relied on | Source check and limit |
| --- | --- |
| Reader bounds precede ranking | `persistence/history.py::read_history_corpus` scopes successful pairs by workspace/subject/purpose/root, excludes only the current run, and considers 128 exchanges plus an overflow sentinel. Archive state and current version identity are not exclusion predicates. Reader eligibility is not unlimited recall. |
| Rank four is not admission four | `history_ranking.py::rank_windows` truncates before `history_admission.py::admit_history` checks both capacities. There is no rank-five backfill. Existing packet tests use empty facts/entities and generous 100,000-token limits. |
| Historical windows are not the whole context | `natural_context.py::build_natural_context` supplies a bounded local suffix in variant B. `natural_memory_binding.py::build_natural_binding_map` separately creates U/A and H handles. Identical source text may appear in both; we verified this is possible, not its measured frequency or cost. |
| Handle classes have different authority | `natural_memory_policy.py::_bind_evidence` resolves local support plus a current-user anchor; `_validate_conflict` may bind an H quote. Blind text deduplication could remove a permitted evidence handle while retaining its prose elsewhere. No deduplication patch follows. |
| Quote binding is not semantic adjudication | `natural_memory_reviewer.py::HISTORY_REVIEWER_INSTRUCTION` distinguishes missing evidence from contradiction; `_validate_conflict` checks supplied quote/reference binding, not logical truth. An unchanged fact store does not establish absence of erroneous persisted dialogue. |
| Existing lineage is fact lineage | `persistence/history_lineage.py::read_history_annotations` traverses fact revisions and predecessor sources, not fictional-episode identity. A story graph is not already available to reuse as if it were merely plumbing. |
| Candidate scores are not native-compatible by default | `retrieval_diversity/selector.py` accepts only finite [0,1] relevance. `history_ranking.py::cosine_score` returns -1 for antiparallel vectors. This confirms an interface distinction, not negative scores in the native observation. No clipping/transformation is introduced. |

Runtime source paths in this table are under
`services/ade-api/src/ade_api/features/agent_runtime/` at the reviewed anchor.
The strict archive branch in workflow `evidence.py::validate_turn` still requires
the admitted archived prior-version origin. PC-11 does not make that a universal
product requirement. The seven dependent native turns remain bounded feasibility
evidence, not seven independent trials, a substantive-biography-edit test or
proof that legitimate user-fact updates are preserved.

## Insight Disposition

| Disposition | Insight | Action / boundary |
| --- | --- | --- |
| Use | Separate designated-source coverage, question-relative sufficiency, conflict visibility and actual model behavior. | Clarify findings and glossary; preserve all historical gates and scores. |
| Use | Exact-copy pressure explains the current coverage gains without establishing a general novelty advantage. | Add a fixture property regression test; keep the candidate unadopted. |
| Use | Correct the eight-admission breakdown and narrow the broad-query information-loss claim. | Explicit corrections above and in original findings, with unchanged raw reports. |
| Test | A missing passage changes permissible claims, not merely provenance detail. | Conditional independent packet audit with deletion challenges and alternative sufficient evidence sets; not launched. |
| Test | Nonidentical retellings, minimal corrections and realistic joint capacity expose a residual need. | If the audit identifies a decision-critical gap, freeze a bounded comparison with more than four distinct plausible sources and separate representation/selection effects. |
| Park | Related-source recovery, relevance thresholds, novelty changes and native ranking/model comparisons. | Require a discriminating unresolved example before investing; native calls need separate approval. |
| Discard | Treating original omission, source-group gain, or unchanged typed facts as direct proof of a bad/good reply. | These are different evidence claims. Repeated assistant dialogue is not independent corroboration. |
| Discard | Promoting deduplication, oldest-wins, a story store or broader reviewer mandate from these reports. | Neither review supplies acceptance evidence or implementation authority. |

## Conditional Next Step

A proposes the existing eight cases plus two wording controls; B proposes four
paired families with additional controls and an exact-copy ablation. Do not
automatically combine them into a larger campaign. The smallest useful first
step is a question-and-packet audit of disputed labels, only if it can change
the investment decision. Separate minimum supported claims, material opposing
evidence, optional detail, forbidden attribution and unresolved ambiguity.

An independent annotator should see transcripts and exact questions before arm
names, ranks or totals, and challenge allegedly necessary passages by deletion.
Existing author-agent judgments and these unblinded reports do not meet that
criterion. Unresolved correction authority remains a named product question,
not an algorithm failure or permission to rewrite fictional history.

Stop if the apparent benefit disappears under justified sufficiency labels or
is fully accounted for by exact copies. If a material omission survives, propose
one new comparison rather than tuning against this scorecard. Preserve paired
packet capacity, local/H authority, different-subject/root isolation and a valid
current-user-update control. No current run is resumed, no scope control receives
credit without execution, and no native measurement is implied by this plan.

## Verification

Imported report bytes match both attachments' SHA-256 values. The focused
diversity suite passes 20 checks, including both new source-property guards.
Broad portable verification:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity/tests workflows/evals/character_memory_dev/tests/test_history_ranking.py --ignore=services/ade-api/tests/agent_runtime/persistence -q -rs
```

457 passed, three explicit absent-historical-evidence skips (one H2, two H4),
and one existing Starlette/httpx warning. Ruff check/format pass. Whitespace
checks pass for authored changes; Review A retains its four original two-space
Markdown line breaks to preserve the attachment exactly. No PostgreSQL/native
run is needed for documentation and characterization-test changes. Runtime,
frozen fixtures/recipe/snapshot and the native gate have no diff. Source and
report publication do not constitute acceptance.
