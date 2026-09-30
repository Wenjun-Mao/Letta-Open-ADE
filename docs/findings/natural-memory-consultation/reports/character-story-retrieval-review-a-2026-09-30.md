## Recommendation: change the decision criterion before changing retrieval

**Keep the runtime unchanged. The smallest justified next step is a bounded, independently reviewed audit of packet sufficiency—not another selector implementation.**

The important distinction is between **retrieving a designated source** and **supplying enough evidence for a faithful answer to the particular question**. Your evidence establishes that top-four selection can hide a material difference between histories. It does **not** establish that every omitted original causes a continuity failure, that every labeled evidence group is necessary, or that the novelty candidate improves model behavior.

In particular, the reported **2/7 → 7/7** improvement combines several objectives: answering the current question, exposing contradictions, recovering correction history, and retaining compatible details. Those are related but not interchangeable. Some apparent baseline deficits disappear under a narrower, question-specific interpretation; others remain credible evidence-loss risks.

My recommendation is therefore conditional: **first determine which omissions change what the model can justifiably say. Only then investigate whether those omissions persist with native ranking and whether a different packet improves actual behavior.**

### Review scope and evidence status

I inspected **27 repository files at exactly `79852e6ee8c17f2efdd7492dfae6627d91d12c7d`**, listed at the end. Default-branch searches were used only to locate additional callers; those implementations were then fetched at the pinned revision. All repository links below are pinned to that revision.

This is a source review, not a native reproduction. I did not access private captures, databases, services, or chat history, and did not execute repository tests or provider calls. I independently recomputed the published scorecard arithmetic from its source-ID selections and labels; the reported counts agree. Claims about native execution, annotation chronology, and pre-observation freezing remain **maintainer-reported**, albeit documented in inspectable files.

## 1. What faithful continuity should require

### Sufficient faithful evidence—not an original on every recall

PC-11 permits creating solo fictional history while requiring subsequent consistency, compatible elaboration, and genuine correction. It separately prohibits inventing user facts, earlier user statements, or shared participation. Neither PC-11 nor ADR 0050 imposes universal original-source admission or an unconditional earliest-statement-wins rule. [Sources: `docs/product-contract.md`, PC-03–11](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/product-contract.md); [ADR 0050, “Decision”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/adr/0050-consistent-improvised-character-history.md).

I would distinguish three evaluation questions:

**Can the packet support the requested answer?** A faithful later retelling can suffice. If the question asks whether Xiaotang was alone, an explicit, correctly attributed later denial of shared participation may answer it without the original.

**Can the packet expose a material disagreement?** A packet containing four erroneous retellings may look coherent while concealing an incompatible establishing account. Recovering a conflicting source improves the opportunity to recognize the problem; it does not decide which account governs.

**Can the packet resolve the disagreement?** A self-contained correction may suffice without the original. An anaphoric correction—“还是最初说的那一天”—requires an antecedent. Conversely, a later suggestion to rewrite an episode is not correction authority merely because it is newer.

Thus, I would evaluate **question-relative evidential sufficiency, attribution, and material conflict coverage** separately. “Every relevant correction must itself be retrieved” would be another unnecessarily strong requirement when a faithful, self-contained subsequent account already carries the corrected information.

### The strict probe gate remains failed

The archive condition in `validate_turn` explicitly requires the original run to be admitted, archived, and bound to a different version; it also rejects qualifying the archive probe through unarchived intermediate echoes. This is a particular provenance challenge, not the complete definition of PC-11 behavior. [Source: `story_continuity/evidence.py`, `validate_turn`, final `archive_probe` branch](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/evidence.py).

The appropriate interpretation remains:

> The sequence failed its frozen original-admission gate, while the reported turn-7 reply remained consistent and archived prior-version retrieval occurred.

A future behavioral gate may accept sufficient faithful evidence without the original. That would be a **prospective change to the evaluation contract**, not permission to reclassify or continue the closed sequence.

### A product question remains unresolved

“Genuine correction” is not yet fully operationalized. ADR 0050 deliberately leaves correction and establishment semantics open. A transcript can establish who said something, when, and whether it contradicts earlier dialogue; it cannot make every newly asserted “correction” legitimate through structural validation alone. [Source: ADR 0050, “Consequences And Open Design”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/adr/0050-consistent-improvised-character-history.md).

Human judgment is needed for genuinely ambiguous examples—not to reopen permission to improvise, but to decide what this product treats as error correction rather than deliberate rewriting. Until resolved, those examples should permit an uncertainty response rather than receive an invented single “correct” answer.

## 2. What the inspected runtime actually does

### The demonstrated omission is at selection, not archive eligibility

`read_history_corpus` filters completed, two-message exchanges by workspace, subject, purpose, and character-definition root. It does not require the current immutable version and does not exclude archived conversations. It reads the newest **128** candidate exchanges, excludes oversized messages, checks hashes, and can omit exchanges whose required fact-lineage annotations cannot be supplied. Consequently, archive eligibility does not promise unlimited historical availability: reader bounds precede ranking. [Source: `persistence/history.py`, `read_history_corpus`, `MAX_EXCHANGES`, `MAX_MESSAGE_CHARS`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py).

For the reported turn 7, however, the finding says all six prior exchanges reached the reader inventory, with no reader, content, annotation, or packet-capacity omissions. The original was fifth by score. That localizes the reported failure without blaming archive or version filtering. [Source: native finding, “Turn-7 Root Cause”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-native-2026-09-30.md).

### Four windows is a selection ceiling followed by a separate capacity check

`rank_windows` sorts by relevance, then newer source time, then stable ID, and returns only four. `admit_history` considers those four complete windows against **both** generation and reviewer capacity. It can skip a window that does not fit, but it does not search rank five onward for a replacement. Thus, “ranked,” “admitted,” and “available to both models” are distinct measurements. [Sources: `history_ranking.py`, `rank_windows`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py); [`history_admission.py`, `admit_history`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/history_admission.py).

The native recipes score role-serialized complete exchanges against the current request and, where applicable, the local suffix. V2 mixes current-only and contextual cosine scores at 0.7/0.3. The diversity comparison instead uses current-only **literal** scoring. It is not a replay of native selection quality. [Source: `history_native_rank.py`, `rank_native_history`, recipe definitions](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/history_native_rank.py).

### Four historical windows is not the entire evidence context

Variant B also supplies a bounded shared local suffix. The history reader can return exchanges already represented there, and the inspected selection/binding path does not subtract those sources when choosing historical windows. This creates a plausible, simpler source of redundant context worth **measuring**, particularly within a chat; it does not explain the fresh-chat turn-7 result by itself. [Sources: `natural_context.py`, `build_natural_context`, `_complete_exchange_suffix`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_context.py); [`natural_memory_binding.py`, `build_natural_binding_map`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py).

Do not immediately remove these duplicates, however. **Identical text in local U/A context and historical H context does not have identical operational permissions.** H handles can ground historical conflicts; local handles can support appropriately anchored current writes. A byte-level deduplication that changes available handle classes could change behavior even when the prose remains visible.

### Structural integrity is strong evidence about structure—not semantics

Historical sources are separately bound as H handles. `_bind_evidence` binds writes through the exact current-user quote and eligible local support, not H handles. `_validate_conflict` can bind an exact H quote, but the application does not establish that the quoted passage logically contradicts the reply. The reviewer instruction explicitly states that missing evidence alone is not a contradiction. [Sources: `natural_memory_policy.py`, `_bind_evidence`, `_validate_conflict`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py); [`natural_memory_reviewer.py`, `HISTORY_REVIEWER_INSTRUCTION`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py).

The history guards revalidate sources before exposure and finalization. `RunFinalizer.commit_success` places final history validation, memory processing, assistant-message persistence, and successful run completion inside the same database transaction. These are safeguards to preserve, not evidence that a model will interpret corrections correctly. [Sources: `persistence/history_guard.py`, validation functions](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/persistence/history_guard.py); [`worker_finalization.py`, `RunFinalizer.commit_success`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py).

Finally, existing lineage describes **user-fact revisions and their source relationships**, not episode origins and fictional-story corrections. Reusing that machinery as an episode graph would be a semantic expansion, not merely recovering relationships already recorded. [Source: `persistence/history_lineage.py`, `read_history_annotations`, `_linked_path`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/src/ade_api/features/agent_runtime/persistence/history_lineage.py).

## 3. Assessment of the evidence and labels

### Native sequence: useful feasibility evidence, narrowly bounded

The finding reports seven delivered turns, no rerolls, unchanged user-memory projections, and empty reviewer decisions. It also explicitly reports agent—not independent human—semantic assessment. ADR 0054 records the evaluator-ownership amendment rather than silently treating agent annotations as human validation. That separation is appropriate. [Sources: native finding, “Outcome” and “Source And Execution Binding”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-native-2026-09-30.md); [ADR 0054, “Annotation-Ownership Amendment”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/adr/0054-bounded-native-story-probe.md).

Three limits matter to the decision:

* These are dependent turns in one developing story, not seven independent reliability trials.
* The version transition changed the version name while preserving prompt/persona content hashes. It does not test reconciliation after substantive biography edits.
* Pure-story no-change outcomes do not demonstrate preservation of legitimate user-fact updates, nor do empty reviewer decisions establish that the reviewer would catch a misleading retelling. Native turns 8–10, including further scope controls, remain unrun.

Those limitations are substantially acknowledged in the finding; they should remain attached to any summary of “early feasibility.”

### Pressure controls: a real information-loss result, but narrower than unavoidable failure

The paired-origin controls correctly show that different complete histories can produce identical generation packets and identical reviewer requests when the differing source is omitted. Oracle origin reservation can likewise leave a correction invisible. These are useful controlled demonstrations, and the tests clearly distinguish synthetic vectors from measured Qwen embeddings. [Source: `test_story_retrieval_pressure.py`, paired-origin and correction tests](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/tests/agent_runtime/test_story_retrieval_pressure.py).

One qualification strengthens the interpretation: the pressure query is broadly “Tell me again about the cat you met after work.” A common-core answer—meeting the cat alone after work—could be faithful to both histories. Identical packets prevent reliable choice of the **differing weather/location details**, not every possible faithful response.

A future discriminating query should explicitly request those details. Otherwise, “the model cannot distinguish these histories” risks becoming “the model must fail this broad question,” which the control does not prove.

Also, restoring the original only restores disagreement visibility. In your test, the reviewer receives a constructed candidate reply but produces no decision. The pressure finding is right to stop short of claiming semantic resolution. [Source: pressure finding, “Observations” and “Root Cause And Disposition”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-retrieval-pressure-2026-09-30.md).

### Diversity: the arithmetic is correct; the interpretation needs finer labels

I verified the published counts: baseline 2/7 versus candidate 7/7 complete labeled cases; positive-case irrelevant admissions 3 versus 8 of 28 slots; no-match admissions four for both. These are exactly the outputs of the declared source-group metric. [Sources: `retrieval_diversity/observed.json`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/observed.json); [`test_story_diversity_candidate.py`, `_assess`, scorecard test](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/services/ade-api/tests/agent_runtime/test_story_diversity_candidate.py).

However, several group requirements deserve challenge:

| Case | Question-specific critique |
|---|---|
| **Unsupported rewrite** | The baseline selects four explicit denials that the encounter was shared. Those appear sufficient for “是我们一起遇到的吗？” Requiring the separate rejected-rewrite exchange measures additional conversational provenance, not necessarily answer sufficiency. |
| **Supported error correction** | Exchange `e` explicitly distinguishes the first misshapen bowl from a cup made on another occasion. It can be a self-contained correction; requiring `a` as well needs justification. Moreover, “陶艺课最后做成了什么？” does not itself identify which class. |
| **Compatible new detail** | “纸袋有什么特别的？” does not necessarily require recounting every previously disclosed property. Bag contents may answer it; a wet-corner omission is decisive only under a more specific callback or a stronger completeness requirement. |
| **Distinct similar episodes** | Second-encounter evidence does not establish first-encounter weather, but it may help distinguish the two. Treating every such selection as equally “irrelevant” conflates potentially useful contrast with unrelated food or music chatter. |
| **Anaphoric correction** | Requiring the earlier day plus the backward-pointing correction is much more defensible. But antecedent attachment and chronology must be explicit; a generic correction should not automatically attach to whichever episode is convenient. |

These observations follow from the actual queries, passages, and group definitions—not hypothetical alternative fixtures. [Source: `retrieval_diversity/cases.json`, named cases](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/cases.json).

**Do not replace the frozen scorecard with my preferred interpretation.** Preserve it as the result under its declared metric. Add a separately reviewed, prospective measure of task-relative sufficiency.

### Duplicate pressure and lexical formatting materially favor this candidate

Several cases repeat the **entire user/assistant exchange exactly**, including the target question. Once one such exchange is selected, identical copies receive zero novelty utility. Any different source with positive utility can outrank them. This is a valid stress condition, but unusually favorable to a bigram-novelty method.

The inspected finding also identifies lexical overlap contributed by serialization and role labels. Its wrong-echo example gives unrelated text nontrivial relevance partly through `er`, `nt`, `se`, and `us`. The candidate then always fills available slots—even at zero utility. Neither behavior is an abstention policy. [Sources: `selector.py`, `_bigrams`, `select_diverse`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/workflows/evals/character_memory_dev/story_continuity/retrieval_diversity/selector.py); [diversity finding, “Root Cause And Disposition”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/79852e6ee8c17f2efdd7492dfae6627d91d12c7d/docs/findings/natural-memory-consultation/character-story-source-diversity-2026-09-30.md).

Important omitted counterexamples include a decisive correction differing from a long retelling by only a negation or date, and two genuinely distinct episodes with nearly identical wording. Both can be important despite high overlap. Conversely, diverse paraphrases can repeat the same error without looking lexically redundant.

The label-mutation tests demonstrate that scorer labels are not direct selector inputs. They do not remove fixture-authoring bias. Snapshot hashes bind the recorded artifacts; the current tree alone does not independently establish preregistration chronology or absence of earlier exploratory tuning. None of this invalidates the reported characterization—it limits generalization.

## 4. Options within the existing design

| Option | What it offers | Principal limitation | Present recommendation |
|---|---|---|---|
| **Retain baseline** | Avoids unqualified change and preserves current ownership and safeguards. | Known possibility of losing material evidence remains. | **Preferred now**, explicitly unqualified for general PC-11 reliability. |
| **Make selection aware of already supplied evidence** | May avoid spending H capacity on sources already in the local suffix. | Text duplication and handle permissions differ; does not solve fresh-chat echo pressure. | Measure first; not an immediate deduplication patch. |
| **Recover related sources from existing history** | Could recover an antecedent or surrounding exchange for a short correction. | No general episode links currently exist; adjacency fails across chats or interleaved topics. | Plausible if the audit identifies dependency loss as the bottleneck. |
| **Diversity with relevance and optional nonselection** | Could trade redundant evidence for useful coverage without mandatory filler. | Novelty is not authority; relevance cutoffs can remove the least lexically explicit correction. | Reasonable research option, but the current selector is not qualified. |

Related-source recovery must still operate within workspace/subject/root boundaries, preserve original user/assistant attribution, include archived versions, and feed the same admitted history to both model stages. A recovered user proposal plus assistant rejection must not become a merged statement that “we visited together.”

I would not select origin reservation or a larger top-k now. The pressure controls already show why an origin can coexist with a missing correction, and more slots do not establish an episode relationship. Nor should a new threshold be fitted to these eight examples: it could simply remove weakly scored anaphoric evidence while appearing to fix irrelevant admissions.

The simplest useful reframing is **marginal evidence value for this question**, not generic source novelty. That is an evaluation objective, not a request to build a semantic evidence optimizer.

## 5. The smallest bounded experiment that could change the decision

### First: a packet-sufficiency audit, with no provider calls

Cap the work at the **existing eight cases plus two pre-frozen wording controls**: one paraphrased wrong-echo case without exact question repetition, and one minimally worded correction whose interpretation depends on its antecedent.

Keep the old fixtures, recipe, results, and native gate unchanged. This is a new diagnostic, not a revised historical score.

**Competing hypotheses**

**H₀ — Metric/fixture explanation:** much of the apparent gain comes from unnecessary source requirements and exact-duplicate/format effects. The baseline already supports acceptable answers on the disputed cases.

**H₁ — Material evidence loss:** baseline packets omit information that changes a justified answer, and the problem survives nonidentical paraphrases.

**H₂ — Authority/interpretation bottleneck:** recovered sources expose competing accounts but do not establish a unique answer under the currently agreed correction semantics. A selector change alone cannot settle the case.

An offline audit can distinguish H₀ from important parts of H₁ and identify unresolved H₂ cases. It cannot establish actual model performance.

### Labels should describe permissible claims and necessary dependencies

Have a reviewer who did not author the fixtures or selector assess the transcripts and exact query without seeing arm names, rankings, or coverage totals. Prefer an identified independent human for this small audit; another agent should be labeled as such, not treated as human independence. A second adjudicator is needed only for material disagreements.

For each case, record exact supporting passages for:

* permissible retrospective claims and prohibited claims;
* speaker, episode, and temporal attachment;
* alternative sufficient evidence sets;
* whether disagreement is resolved, merely visible, or genuinely ambiguous.

For each allegedly necessary group, perform a **deletion challenge**: does removing it change what can be justified, or merely reduce provenance detail? Apply this especially to the rewrite, self-contained correction, and paper-bag cases.

Compare the frozen baseline and candidate packets with a **minimal sufficient reference packet** assembled for evaluation only. This reference is an oracle control, not a proposed runtime selector. Include empty history on the no-match case and a faithful-original-omitted control.

### Separate the measurements

**Ranking and representation:** On the offline pass, report literal scores and format contributions as diagnostics. Do not call them Qwen measurements. Check whether the paraphrased pressure case retains the same failure mechanism.

**Evidence availability:** Report task-relative sufficiency, material conflict visibility, missing antecedents, and irrelevant selections separately. Distinguish another episode from wholly unrelated chatter.

**Capacity:** Evaluate the serialized generation and reviewer bundles at the actual frozen limits, not only the tests’ generous 100,000-token budgets. Measure post-admission evidence, not selected IDs alone. Include local suffix and handle availability in the audit.

**Model interpretation, naturalness, and persistence:** Mark these **unmeasured** offline. A human’s ability to answer from a packet does not imply the generator or reviewer will do so.

### Stopping rules

Stop after the frozen cases; do not iterate thresholds or formula changes against their outcomes.

If the alleged baseline deficits are mainly unnecessary group requirements, or the apparent advantage exists only under exact duplicates, **retain the baseline and stop this retrieval branch**. That is a useful result, not a failed experiment.

If a minimal reference packet still leaves genuine correction authority ambiguous, **resolve that product example before selecting an algorithm**.

If baseline packets demonstrably lose question-critical evidence under both original and paraphrased wording, while a bounded reference packet resolves it, there is a justified question for native measurement—but still no qualified fix.

### Only subsequently, under separate native approval

First measure the frozen native embedding/ranking recipe on those texts, retaining full score vectors and source identities. Compare baseline and any explicitly nominated candidate using the **same scores**. Do not simultaneously change query formatting, model recipe, selector, and prompt.

Only if a meaningful packet difference survives should a bounded model comparison follow. A small design is up to four disputed target turns, baseline versus minimal-reference packets, adding a candidate arm only if one has been nominated. Use equivalent isolated starting states, one attempt per arm, the existing single reviewer, and retained candidate, reviewer, delivered-output, and state receipts. No rerolls.

Disqualifying regressions include invented user participation or prior user testimony; loss of a genuine correction; conflation of distinct episodes; false rejection of compatible elaboration; fabricated historical grounding; unintended user-memory mutation; or suppression of a clearly valid current-user update in a positive control. Naturalness should be judged separately: needless abstention, moralizing rewrite refusals, and irrelevant personalization are not redeemed by better source coverage.

A minimally sufficient packet that still produces bad interpretation points away from retrieval as the next intervention. A candidate that improves source coverage but worsens those behaviors should not be adopted.

## 6. What should remain unchanged

Keep the single runtime, ADE-owned PostgreSQL persistence, immutable persona bindings, scope boundaries, archive eligibility, complete-source attribution, existing write-authority restrictions, source revalidation, and atomic persistence. Keep the diversity selector evaluation-only. Do not introduce an episode store, new fact type, second reviewer, keyword privacy/no-save rules, or deployment change on this evidence.

The named unresolved question is:

> **Does the baseline omit evidence necessary for faithful answers to specific questions under realistic wording, or does the present scorecard mainly reward a richer provenance packet than those answers require?**

The current repository is sufficient to expose that uncertainty. It is not sufficient to choose a new retrieval policy. **A bounded label-and-packet audit is the smallest next investment; leaving runtime unchanged is the justified decision today.**

### Files actually inspected

All paths below are relative to the repository at **`79852e6ee8c17f2efdd7492dfae6627d91d12c7d`**.

**Contracts and findings — 6 files:**  
`docs/product-contract.md`; `docs/adr/0050-consistent-improvised-character-history.md`; `docs/adr/0054-bounded-native-story-probe.md`; and, under `docs/findings/natural-memory-consultation/`, `character-story-native-2026-09-30.md`, `character-story-retrieval-pressure-2026-09-30.md`, `character-story-source-diversity-2026-09-30.md`.

**Runtime — 14 files**, under `services/ade-api/src/ade_api/features/agent_runtime/`:  
`persistence/history.py`; `persistence/history_lineage.py`; `persistence/history_guard.py`; `history_attempt.py`; `history_native_rank.py`; `history_ranking.py`; `history_admission.py`; `natural_context.py`; `natural_memory_binding.py`; `natural_memory_reviewer.py`; `natural_memory_policy.py`; `turn_history_setup.py`; `turn_execution.py`—execution and state-loading passages, with the returned tail truncated; `worker_finalization.py`—lines 1–300, including `RunFinalizer.commit_success`.

**Tests — 2 files**, under `services/ade-api/tests/agent_runtime/`:  
`test_story_retrieval_pressure.py`; `test_story_diversity_candidate.py`.

**Evaluation workflow — 5 files**, under `workflows/evals/character_memory_dev/story_continuity/`:  
`evidence.py`; `retrieval_diversity/README.md`; `retrieval_diversity/selector.py`; `retrieval_diversity/cases.json`; `retrieval_diversity/observed.json`.