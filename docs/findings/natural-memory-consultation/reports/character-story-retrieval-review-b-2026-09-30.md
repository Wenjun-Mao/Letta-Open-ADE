## Recommendation: leave runtime unchanged; revise the interpretation before selecting another retrieval mechanism

**The most useful finding is that the diversity experiment does not yet distinguish general source diversity from simple exact-duplicate handling.** In all five positive cases where the candidate improves labeled coverage, seven windows contain **exactly four distinct user–assistant text pairs**. The budget is four. Selecting one representative of each distinct text therefore makes every labeled evidence group available, without needing a general novelty objective. This follows from the published fixtures and selections, not from a hypothetical model response. [Sources: `cases.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/cases.json), [`observed.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/observed.json).

That is **not** a recommendation to deploy deduplication. Identical text at different times can have different evidential significance. It means the present experiment has not demonstrated why the more general diversity mechanism earns its complexity.

My decision recommendation is:

**Retain the baseline, keep the candidate evaluation-only, and make a narrowly scoped methodological clarification.** Preserve the failed native gate and existing observations. Distinguish query-relative evidence sufficiency from diagnostic source-group coverage, and distinguish exact-duplicate pressure from semantic redundancy. Further experimentation is conditional on a decision that these distinctions alone do not resolve.

### Review scope

I inspected **27 files at exactly `79852e6ee8c17f2efdd7492dfae6627d91d12c7d`**, through GitHub. The inventory appears below. I did not substitute `main`, inspect private captures or databases, execute the repository’s test suite, or make provider calls. I independently recomputed the distinct-text counts and irrelevant-selection breakdown from the published fixtures.

The native outcomes below remain **maintainer-reported results**, recorded in the inspected repository. Their private receipts and earlier execution revisions were not independently validated by this review. No external literature is needed for the conclusions.

---

## 1. Faithful continuity requires appropriate evidence—not universally an original

### Separate three kinds of claim

PC-11 permits creating a new solo fictional episode. It does not make every detail need a pre-existing source. But it creates obligations when later replies concern that episode. PC-03/05 separately constrain statements about the user and actual interaction history. [Source: `docs/product-contract.md`, PC-03–05 and PC-11](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/product-contract.md).

A useful assessment distinguishes:

| Claim being made | Appropriate evidential requirement |
|---|---|
| “This happened in my fictional life.” | May be newly improvised, provided it respects established commitments and authored biography. |
| “Here is that episode again.” | Evidence sufficient to preserve the relevant established details and handle material corrections or conflicts. |
| “You said this,” “I told you this before,” or “we experienced this together.” | Actual interaction evidence supporting the speaker, participation, disclosure time and scope claimed. |

**My proposed evaluation principle:** judge sufficiency relative to the current question and the assertions the reply actually makes. Do not require every potentially useful source for every answer. Conversely, an answer-supporting passage is not enough when other relevant supplied evidence materially defeats that interpretation.

This is compatible with ADR 0050’s distinction between new fiction and faithful recollection. It is not an “earliest statement always wins” rule. [Source: `docs/adr/0050-consistent-improvised-character-history.md`, Decision and Consequences](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/adr/0050-consistent-improvised-character-history.md).

### When the original matters

The original can be necessary when it uniquely contains a disputed detail, supplies the antecedent of an anaphoric correction, or establishes what was initially disclosed. It need not be necessary when a faithful, self-contained retelling supplies the answer.

For example, a later exchange accurately saying the cat left after the rain and was not found the next day can answer a question about the outcome. Requiring the initial telling adds provenance coverage, not necessarily answer-relevant information. Your pressure tests already contain this counterexample. [Source: `test_story_retrieval_pressure.py::test_faithful_echoes_can_preserve_core_without_original`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/tests/agent_runtime/test_story_retrieval_pressure.py).

Similarly, “conflict/correction coverage” should not mean collecting every contradictory echo. The relevant question is whether the packet preserves the distinction needed for this response. One self-contained correction may suffice; an anaphoric correction may require another window.

There is nevertheless no finite selection rule that can certify the absence of an omitted material correction merely from the selected text. The indistinguishable-packet controls demonstrate that limit. Abstention can avoid a particular false assertion, but a model receiving apparently coherent echoes may have no packet-visible reason to abstain.

### The native gate remains failed

`evidence.py::validate_turn` explicitly requires an admitted archived original bound to a prior version, and rejects unarchived intermediate admissions for that archive probe. Those are stricter conditions than general PC-11 continuity. [Source: `evidence.py::validate_turn`, final `origin_run_id` / `archive_probe` checks](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/evidence.py).

For a **future** probe, I would separate three outcomes: archive/version eligibility and actual packet admission; faithful conversational behavior; and original-source provenance. That would not reclassify turn 7, reopen turns 8–10, or qualify the earlier sequence.

One human product judgment remains consequential: **what constitutes a genuine correction when the fictional past itself was improvised?** A correction supported by earlier dialogue is different from an arbitrary replacement introduced as “actually, I misspoke.” Retrieval can expose that distinction; it cannot settle the open correction contract. Mandating original-source admission, treating any correction wording as authoritative, or requiring blanket refusal under uncertainty would each need an explicit product decision.

---

## 2. What the inspected runtime establishes—and where its guarantees end

The principal boundary is well chosen: source integrity and ownership are application responsibilities; interpretation remains a model responsibility.

| Inspected mechanism | Consequence for this review |
|---|---|
| `persistence/history.py::read_history_corpus` reads succeeded, complete pairs, scoped by workspace, subject, purpose and character root. It does not exclude archived conversations or require the current version ID. | Archive and ordinary-version eligibility are separate from selection. The reader also has an upstream limit of 128 exchanges and whole-message/content and annotation exclusions. A selector cannot recover a source absent from this corpus. |
| `history_ranking.py::rank_windows` orders independent scores, then newer source time, then stable ID, and truncates to four. | It does not represent episode relationships, correction authority or evidence sufficiency. |
| `history_admission.py::admit_history` applies another four-window cap and generation/reviewer capacity checks. | Ranking loss and capacity loss must be measured separately. A rejected large window is not replaced by the fifth-ranked source, because that source has already been truncated. |
| `natural_memory_binding.py` places historical messages in separate H handles; `natural_memory_policy.py::_bind_evidence` binds write support through the local U/A map and a current-user quote. | Historical H text cannot directly become write support merely because retrieval found it. This is a structural protection, not semantic proof that the current quote supports the proposed fact. |
| `HistoryAttempt` and `persistence/history_guard.py` reauthorize source identity, scope, hashes and memory generation, with different treatment before and after exposure. | These protect the evidence being used. They do not determine whether a valid source is a faithful recollection, an error, a hypothetical or a correction. |

Sources: [`history.py::read_history_corpus`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py), [`history_ranking.py::rank_windows`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py), [`history_admission.py::admit_history`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/history_admission.py), [`natural_memory_binding.py::build_natural_binding_map`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py), [`natural_memory_policy.py::_bind_evidence`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py), [`history_guard.py`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/persistence/history_guard.py).

Three implications deserve emphasis.

**First, the reviewer is not a general unsupported-history detector.** `HISTORY_REVIEWER_INSTRUCTION` explicitly distinguishes missing evidence from contradiction and requires exact historical grounding for an H conflict. That avoids fabricating grounds to reject a reply, but means more retrieval does not automatically make unsupported user-history claims rejectable. Moreover, `_validate_conflict` validates the binding of a reported conflict; it does not independently adjudicate its meaning. [Sources: `natural_memory_reviewer.py::HISTORY_REVIEWER_INSTRUCTION`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py), [`natural_memory_policy.py::_validate_conflict`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py).

**Second, unchanged user-memory state does not mean an erroneous story disappears.** A successfully delivered assistant exchange remains eligible dialogue. An invented claim about past user participation can therefore be harmful without creating a typed fact. Repeated retrieval would not provide independent corroboration of that claim; it could merely repeat the same assistant-origin error. This is an inference from the completed-exchange reader and the distinct dialogue/fact boundaries.

**Third, existing lineage is not an available character-episode graph.** `history_lineage.py` follows memory revision sources and fact predecessors. The pure-story fixtures have empty annotations. A related-source proposal cannot assume that these edges already link fictional originals, retellings and corrections. [Source: `persistence/history_lineage.py::read_history_annotations`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/persistence/history_lineage.py).

Also assess evidence against the **whole supplied context**, not H alone. The reader excludes the current run, not all runs already represented in the local suffix. The binding map keeps local and historical sources separately. Marginal historical value can therefore differ from raw H coverage. This does not explain turn 7’s fresh-chat result, but matters to future evaluations. [Sources: `natural_context.py::build_natural_context`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_context.py), [`natural_memory_binding.py`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py).

---

## 3. Evidence critique: strong limitations work, insufficient selector qualification

### Native sequence: useful feasibility evidence, narrower than lifecycle reliability

The native finding reports consistent responses, unchanged user-memory state, and the original’s fifth-place rank with no packet-capacity omissions. Its diagnosis of the **gate failure** is coherent with the inspected code. It does not establish an observed semantic recall failure. [Source: `character-story-native-2026-09-30.md`, Outcome and Turn-7 Root Cause](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-native-2026-09-30.md).

Two additional limits matter:

The four selected native exchanges were an elaboration, rewrite refusal, cross-chat retelling and participation denial—not four identical strings. Calling them all “echoes” obscures their distinct information. The later duplicate-heavy fixtures consequently do not closely reproduce this aspect of the native selection problem.

Also, the reported new version changed only its name; prompt and persona hashes were identical. This supports crossing immutable version identities, not reconciliation after content-changing persona edits. Genuine correction behavior and the unrun isolation controls likewise remain unqualified.

The annotation-ownership amendment is appropriately explicit. Agent annotation is not a procedural violation after that amendment, but neither independent readback nor accurate hash binding makes it independent human semantic validation. [Source: `ADR 0054`, Annotation-Ownership Amendment](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/adr/0054-bounded-native-story-probe.md).

### Pressure controls: a sound information-loss demonstration

The paired-origin tests make a strong, appropriately limited claim: different source histories can yield identical generation and reviewer packets. The correction control also refutes the sufficiency of oracle origin reservation. Neither result depends on a model answering badly.

The supplied scores, identical V2 query vectors and generous packet limits deliberately isolate this mechanism. They do **not** estimate its frequency, compare the native ranking recipes meaningfully, or show that a real Qwen embedding would place these particular texts in this order. The findings mostly maintain that distinction well. [Sources: `test_story_retrieval_pressure.py`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/tests/agent_runtime/test_story_retrieval_pressure.py), [`character-story-retrieval-pressure-2026-09-30.md`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-retrieval-pressure-2026-09-30.md).

### Diversity comparison: the missing duplicate-handling control is decisive

The five newly covered cases are:

`wrong_repeated_echoes`, `supported_error_correction`, `unsupported_rewrite`, `compatible_new_detail`, and `anaphoric_correction`.

Each has seven windows but only four distinct complete dialogue texts. The candidate makes exact copies have zero novelty utility after one is selected. The remaining distinct texts—including irrelevant ones—then occupy the available slots. Thus the coverage improvement is consistent with **freeing slots occupied by exact copies**, rather than evidence of robust recovery among many nonidentical related sources. [Sources: `cases.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/cases.json), [`selector.py::select_diverse`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/selector.py).

Freezing the cases before observing output and excluding labels from selector input are worthwhile controls. They do not make the cases independent of the selector’s motivating hypothesis. Nor does the absence of fitted coefficients eliminate design overfitting through templates, exact repetition, query wording or the chosen overlap representation.

### Several evidence groups measure more than minimum answer sufficiency

The groups are valid definitions of a **particular coverage target**. The problem arises when their recovery is interpreted as necessarily improving the answer.

| Fixture | Challenge to the necessity of its labels |
|---|---|
| `unsupported_rewrite` | The baseline selects explicit denials of shared participation. Those can answer the current participation question without retrieving the earlier rejected rewrite. The extra source matters more for a question about that actual prior request. |
| `supported_error_correction` | The correction itself states that the first object was a bowl and the cup belonged to another occasion. Requiring the original as well is not obviously necessary. The current question also lacks an explicit “first occasion” restriction. |
| `compatible_new_detail` | Recovering the wet-corner detail may improve richness, but the broader paper-bag question does not clearly require every established detail. Conversely, retrieving it must not justify backdating its disclosure. |
| `anaphoric_correction` | Here the original-plus-correction dependence is substantively stronger: the correction refers back to the initially stated day without naming it. |
| `wrong_repeated_echoes` | Selecting both accounts exposes a conflict. That is an evidence-availability success, not proof of which account the model will retain or whether it will explain the conflict appropriately. |

These observations are based on the exact queries, exchanges and groups in [`cases.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/cases.json).

For prospective labels, separate **minimum supported answer**, **material counterevidence**, **optional useful detail**, **forbidden attribution**, and **legitimate unresolved ambiguity**. Keep these evaluation annotations, not runtime fact types. Allow independently justified alternative sufficient packets rather than universally demanding an original/correction pair.

### One concrete reporting error

The aggregate candidate count of eight irrelevant admissions is correct. Its stated composition is not.

In `distinct_similar_episodes`, the candidate selects `c,f,g,a`: `f` concerns the other encounter; `g` concerns food. Across all seven positive cases, the eight irrelevant selections therefore comprise **one other-episode source and seven unrelated-topic sources**, not two and six. The baseline’s three irrelevant selections all concern the other encounter. This does not reverse the recommendation, but changes the characterization of the tradeoff. [Sources: `observed.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/observed.json), [`cases.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/cases.json), [`source-diversity finding`, Observed Results](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-source-diversity-2026-09-30.md).

Finally, packet-integrity tests use empty facts/entities and 100,000-token input limits. They establish passage through both builders under ample capacity—not performance at the actual shared capacity boundary. The tests preserving unfavorable outcomes are good characterization tests, not acceptance tests. [Source: `test_story_diversity_candidate.py::_assert_packets`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/tests/agent_runtime/test_story_diversity_candidate.py).

---

## 4. Option comparison

| Option | Best argument for it | Main limitation | Present disposition |
|---|---|---|---|
| **Retain baseline** | Avoids changing a working experimental path on evidence that has not demonstrated native benefit. | Leaves a demonstrated possible evidence-loss mechanism unresolved. | **Preferred now; not a reliability endorsement.** |
| **Recover related sources** | Could recover a short correction through its antecedent rather than requiring direct query similarity. | Same-conversation adjacency is not episode identity; cross-chat corrections may lack adjacency. Similar episodes can be incorrectly linked. Existing fact lineage does not supply the missing story relation. | Consider only against a concrete missed-dependency example. |
| **Diversity with relevance and abstention** | Could reduce redundant consumption while permitting fewer than four admissions. | Lexical novelty can suppress small but decisive corrections and promote unrelated text. A cutoff can discard anaphoric evidence. | Plausible hypothesis, not the next default. |
| **Simpler evaluation reframing: marginal evidence and duplicate ablations** | Reveals whether novelty adds anything beyond duplicate handling or sources already present locally. | Does not itself solve semantic correction or episode identity. | **Best next analytical step, without runtime integration.** |

A few boundaries apply to all options.

A near-verbatim correction such as changing Saturday to Friday can be **high-overlap but indispensable**. A stylistically different retelling can be **low-overlap but informationally redundant**. Similar distinct episodes may require almost identical vocabulary yet must not be merged. An assistant suggestion and a user assertion may share words without sharing authority. These are reasons to test the proposals—not reasons to build an episode service.

A retrieval abstention should mean *no historical material is admitted*, not *the character may no longer improvise*. Converting low retrieval confidence into a blanket ban on solo fiction would change PC-11.

The current candidate is also not a drop-in Qwen selector: it requires relevance in `[0,1]`, whereas the cosine scorer admits signed cosine values. A native comparison would need an explicit frozen compatibility choice, not silent clipping or post-result transformation. This is an interface issue, not evidence that negative scores occurred in the native run. [Sources: `selector.py::select_diverse`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/selector.py), [`history_ranking.py::cosine_score`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py).

Neither origin reservation nor larger top-k resolves the authority problem. A threshold is not excluded by PC-06, but keyword privacy/no-save machinery remains excluded; nothing here justifies reintroducing it.

---

## 5. Smallest bounded next decision and experiment

### An experiment is not required to justify today’s decision

The available evidence already justifies leaving runtime unchanged. A small addendum can record the duplicate-budget confound, correct the irrelevant-source breakdown, and distinguish coverage labels from minimum answer sufficiency. Preserve the original fixtures, observations and failed gate as historical evidence.

The named unresolved question is:

> **Does a proposed selector recover decision-relevant evidence under nonidentical retelling pressure, beyond what simpler duplicate handling achieves, without increasing harmful attribution or losing corrections?**

That is narrower than “make retrieval better.”

### Conditional offline experiment: one fixed comparison, not a search for a winning recipe

Further work should begin only when answering that question would affect investment. A bounded design would use **four paired Mandarin case families**, plus the existing faithful-echo and no-match controls:

| Pair family | Controlled distinction |
|---|---|
| Repeated error | Exact repeated exchanges versus independently worded retellings preserving the same erroneous claims. |
| Correction dependency | A self-contained supported correction versus an equivalent anaphoric correction requiring an antecedent. |
| Episode identity and detail | Closely similar encounters with an explicit first/second distinction; test a compatible detail whose attachment matters. |
| Attribution | Similar content originating in assistant speech versus user testimony or later endorsement; preserve the distinction between endorsement time and original speaker. |

Keep more than four distinct plausible sources in the decision-critical corpora. Otherwise the experiment repeats the present capacity shortcut.

Compare the unchanged baseline, the existing novelty candidate, and an **evaluation-only exact-text duplicate-handling ablation** with a predeclared representative rule. Add manually assembled sufficient packets only as diagnostic controls—not as deployable selectors or oracle labels available to them.

Have someone independent of selector/case authorship review labels **before seeing arm outputs**. Each label should expose the exact supporting passages, antecedent dependencies, acceptable claims, prohibited claims and reasons clarification may be appropriate. Disagreement is an unresolved label, not automatically an algorithm failure.

Use the same frozen relevance scores across selector arms. A separate scoring ablation can remove serialization scaffolding from the *ranking representation* while preserving attributed source packets unchanged. Do not mix that ablation with the selector comparison and call the combined difference a diversity gain.

### Keep the measurements separate

| Layer | Observable outcome | What can be established offline |
|---|---|---|
| Corpus and ranking | Availability, rank of needed sources, duplicate concentration, query-format effects. | Synthetic/literal mechanics; **not actual Qwen ranking** without measured embeddings. |
| Joint packet admission | Whole-window passage, configured estimated request sizes, omissions, generation/reviewer H equality. | Exercise realistic bounds, long windows and nonempty annotations; distinguish reader, selector and capacity omissions. |
| Model interpretation | Correct answer, correction handling, participation/speaker attribution, appropriate uncertainty. | Human packet-sufficiency judgments only. Actual generator/reviewer behavior needs separately approved calls. |
| Naturalness | Useful recall, compatible elaboration, unnecessary interrogation or moralizing, excessive refusal. | A rubric and review of available text—not native comparative performance. |
| Persistence | Expected no-change for pure story turns; correct change for an explicit supported current user update. | Validator and scripted mechanics. Native effects require complete independently read before/after state. |

For any later model comparison, hold the packet fixed when testing interpretation. An oracle-sufficient packet can distinguish “the selector lost the evidence” from “the model mishandled available evidence.” Test reviewer behavior on fixed candidate replies as well; otherwise a changed generator output confounds reviewer comparisons.

The explicit current-user-update control matters: a system that avoids invented memory by always returning no-change would fail ADE’s useful-memory goal.

### Stop rules

Predeclare that no case, formula or threshold will be tuned within the comparison.

Stop with **runtime unchanged** when the candidate shows no advantage beyond duplicate handling; depends on questionable label requirements; loses a material correction or episode distinction; worsens attribution; or fails joint packet integrity/capacity. Different-subject/root leakage and unsupported user-fact mutation are disqualifying, not tradeable against improved coverage.

Passing the offline comparison would justify, at most, seeking approval for **a small frozen Qwen ranking measurement on the discriminating cases**. It would not justify runtime adoption. Model interpretation, naturalness and persisted effects would still require their own separately approved observations. Native controls 8–10 from the closed sequence must remain unrun and uncredited.

---

## 6. What should remain unchanged

Keep one product runtime, ADE-owned PostgreSQL persistence, immutable source messages and persona bindings, workspace/subject/character-root isolation, archive eligibility, source reauthorization, paired generation/reviewer evidence, current-turn authority for user-fact changes, and atomic persistence. Keep the single runtime reviewer and PC-06 exclusions. Do not introduce a story fact type, episode store, service, origin-reservation rule or broader reviewer mandate on this evidence.

The present code also explicitly restricts the history path to its evaluation policy and development execution context. Retaining that boundary is appropriate. [Source: `turn_execution.py::TurnExecution.execute`, history-policy and runtime-mode checks](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py).

**Bottom line:** the pressure controls establish a real possible information-loss problem. The native sequence does not establish that this problem caused an observed bad reply. The diversity fixtures do not establish that general novelty selection is the right remedy. The smallest justified move is to preserve runtime and sharpen the decision evidence—not to dismiss the risk, and not to promote another mechanism prematurely.

### Files actually inspected

All paths below were inspected at **`79852e6ee8c17f2efdd7492dfae6627d91d12c7d`**.

| Path root | Files |
|---|---|
| `docs/` | `product-contract.md` |
| `docs/adr/` | `0050-consistent-improvised-character-history.md`; `0054-bounded-native-story-probe.md` |
| `services/ade-api/src/ade_api/features/agent_runtime/` | `README.md`; `history_attempt.py`; `history_native_rank.py`; `history_ranking.py`; `history_admission.py`; `natural_context.py`; `natural_memory_reviewer.py`; `natural_memory_policy.py`; `natural_memory_binding.py`; `turn_execution.py`; `turn_memory_snapshot.py` |
| Same runtime root, `persistence/` | `history.py`; `history_guard.py`; `history_lineage.py` |
| `services/ade-api/tests/agent_runtime/` | `test_story_retrieval_pressure.py`; `test_story_diversity_candidate.py` |
| `workflows/evals/character_memory_dev/story_continuity/` | `evidence.py` |
| Same workflow root, `retrieval_diversity/` | `README.md`; `selector.py`; `cases.json`; `observed.json` |
| `docs/findings/natural-memory-consultation/` | `character-story-native-2026-09-30.md`; `character-story-retrieval-pressure-2026-09-30.md`; `character-story-source-diversity-2026-09-30.md` |

This is a bounded source review and methodological consultation, not native acceptance or release evidence.