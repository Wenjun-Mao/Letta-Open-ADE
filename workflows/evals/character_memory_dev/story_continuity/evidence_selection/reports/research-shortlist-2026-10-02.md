## My top five for ADE

**I would prioritize these papers for improving ADE’s character continuity—not for replacing its memory architecture or optimizing GPU serving.**

I screened the papers across **all the briefs above**, then inspected ADE through the connected GitHub account. The repository revision I used was **`ffaf24dab13a9b74b78339a600c032bf1adba899`**, the October 2 commit **“Freeze bounded D04 behavioral comparison.”** That matters: the latest work has already moved beyond simply proposing a semantic selector. 

| Rank | Paper | Most useful contribution to ADE | My recommendation |
|---|---|---|---|
| **1** | [**The Recall Trap**](https://arxiv.org/abs/2608.14838) | Select an interpretable evidence packet, not merely individually relevant exchanges. | Apply to the current retrieval decision. |
| **2** | [**When Knowledge Changes**](https://arxiv.org/abs/2607.26843) | Test continuity through controlled changes to evidence, rather than static recall questions alone. | Borrow the testing method. |
| **3** | [**The RAT**](https://arxiv.org/abs/2608.24753) | Separate retrieval success, warranted uncertainty, answer quality, and downstream correctness. | Use its distinctions in existing evaluation. |
| **4** | [**ReCAP: Persistent Context Graphs**](https://arxiv.org/abs/2609.40118) | Preserve dependencies between historical messages and recover previously omitted evidence. | Borrow the principle; defer the machinery. |
| **5** | [**Repair or Resample?**](https://arxiv.org/abs/2608.25920) | Determine whether a change fixes the recorded failure rather than merely producing a luckier rerun. | Reinforce ADE’s existing controlled-comparison approach. |

The ranking reflects ADE’s current product contract: natural continuity with **Lin Xiaotang**, faithful recollection of established solo stories, correct handling of user facts and shared experiences, and uncertainty when supporting history is incomplete. It also respects the explicit preference for **one product runtime, one reviewer, PostgreSQL ownership, and no speculative memory service, episode store, or generic framework**. 

---

## 1. The Recall Trap — the closest match to ADE’s current problem

### What the paper contributes

In a controlled code-repair study, a configuration that improved retrieval coverage made actual task completion worse. Under a fixed context budget, retrieving more distinct files displaced useful detail within files. Disabling that deduplication improved one model’s resolution rate from **39.2% to 46.8%**, despite lower gold-file coverage. Importantly, the effect reversed with a BM25 retriever and was not detected when agents could freely read files: this is evidence about a particular context-budget tradeoff, not a universal prescription to retrieve more neighboring text. [arXiv](https://arxiv.org/abs/2608.14838?utm_source=chatgpt.com)

### Why it is number one for ADE

ADE has an unusually direct counterpart.

Your D04 fixture contains an original statement locating the wind chimes at the **entrance to an old bookstore**, followed later by a correction that rejects the teahouse account and refers back to **the originally stated place**. The literal-four packet retrieves the correction but omits the original location. It therefore contains something highly relevant without containing enough information to answer. 

The code confirms that this is not merely an evaluator’s abstraction: `history_ranking.py` selects at most four exchanges, and `history_admission.py` separately limits admission to four while checking the generation and reviewer budgets.  

**The transferable lesson is that relevance belongs partly to combinations of sources.** A correction and its antecedent may be valuable together even when one ranks poorly in isolation.

Your latest measurement makes the decision sharper: **all eight D04 exchanges fit both unchanged request budgets**, including the reviewer’s reserved candidate reply. Four-source compression is therefore not required by those measured budgets for this fixture. That establishes capacity and source availability—not improved model behavior. 

### What I would take from it

Keep the already-frozen comparison as the immediate decision point:

- **Literal-four:** the current incomplete selection.
- **Repaired-four:** replace one redundant mistaken retelling with the missing antecedent.
- **Whole-pool:** supply all eight exchanges.

Your protocol correctly treats repaired-four as an **evaluator intervention, not a deployable selector**, and whole-pool as a change in content and order as well as count. 

This paper supports finishing and interpreting that comparison **before investing in an additional selection model**. It does not justify automatically increasing production limits, adopting neighborhood expansion, or assuming that more context is always better.

**My practical conclusion:** ADE first needs to establish which evidence-packet change improves the actual reply. A better retrieval score is insufficient.

---

## 2. When Knowledge Changes — the best testing approach for continuity over time

### What the paper contributes

This paper evaluates RAG through **metamorphic tests**: controlled changes are made to the corpus or supplied context, and the test checks whether the answer changes—or stays stable—in the appropriate way. It distinguishes upstream retrieval/index changes from downstream context changes, allowing the same apparent answer failure to be investigated at different stages. Its evaluation covers eleven mutation operators across five datasets. [arXiv](https://arxiv.org/html/2607.26843v1)

### Why it fits ADE particularly well

ADE’s hardest requirements are not ordinary “remember this fact” questions. They concern **what should happen when history develops**.

The product contract distinguishes factual ending, correction, and removal; preserves archive eligibility; maintains same-user/same-character continuity across ordinary persona versions; and allows new solo fictional stories without permitting invented user participation or fabricated recollection of missing details. 

A static question-and-answer benchmark only partially exercises those distinctions. A family of related histories can test them much more directly.

For a future authorized evaluation slice, I would borrow three kinds of controlled variants:

**Meaning-preserving changes.** Add unrelated dialogue, change paraphrasing, or archive an eligible conversation. The supported recollection should remain available without forcing an irrelevant callback into the answer.

**Meaning-changing changes.** Append a genuine correction or qualification. The answer should respond to its meaning—not blindly prefer the earliest statement, latest statement, or most repeated version.

**Evidence-removing changes.** Omit a necessary antecedent from the supplied packet. A model that previously named the answer should now express appropriate uncertainty rather than reconstruct the missing detail from guesswork.

These would be **copied fixtures and append-only histories**, not edits to ADE’s immutable production messages or historical experiment results.

### What I would take from it

Use the existing continuity fixtures and assessment structure. Do not import a new evaluation framework or expand the frozen D04 protocol.

One especially valuable ADE-specific distinction is:

> Removing an active fact must not silently erase the historical conversation, but recovering that conversation must not silently reactivate the removed fact.

That expectation follows from ADE’s product and history-admission contracts; the paper supplies a useful way to test related states systematically.  

**My practical conclusion:** this is the strongest paper for turning ADE’s product agreements into discriminating continuity tests without adding production complexity.

---

## 3. The RAT — prevent “correct answer” from hiding an incorrect process

### What the paper contributes

The RAT models **retrieval success, abstention, and answer correctness separately**. Its central distinction is between the user receiving a correct answer and the generator behaving appropriately given the evidence it actually received. It also treats automated judges as potentially noisy observations rather than unquestioned ground truth. [arXiv](https://arxiv.org/abs/2608.24753?utm_source=chatgpt.com)

### Why ADE needs this distinction

Your D04 protocol already captures a crucial example: when the original location is absent from literal-four, **honest uncertainty can be correct behavior**. Naming the old-bookstore entrance would not become grounded merely because it happens to match the evaluator’s full ledger. Conversely, uncertainty after receiving both the original statement and its resolving correction could indicate failure to use available evidence. 

D02 exposes another problem. Your readout shows that the historical `named_answer_supported` field is true for several packets, yet those packets warrant different degrees of certainty. A packet with competing Monday and Wednesday accounts is not equivalent to one that also includes the correction resolving the disagreement. 

For ADE, I would therefore keep the following questions distinct:

**Was the necessary source available? Was it admitted with its qualifications? Did the reply use it faithfully? Did the reviewer propose the appropriate delta? Was the intended result actually persisted and delivered?**

Those are different failure locations. A successful source lookup does not establish a faithful reply; a reviewer returning no changes does not establish reply correctness; and a valid citation does not establish correct interpretation. ADE explicitly recognizes these limits already. 

### What I would take from it

**Borrow the decomposition, not necessarily the Bayesian implementation.**

Your existing source-quoted rubric is a better immediate home for these distinctions than a new probabilistic scoring subsystem. In particular, preserve separate observations for unsupported detail, correction handling, ownership, uncertainty, naturalness, reviewer interpretation, and persistence where the experiment actually exercises it.

I would also avoid reducing ADE’s nuanced evidence states to a simple binary “retrieved/not retrieved.” Partial evidence, unresolved conflict, and a missing referent are materially different.

The author-linked RAT repository currently has an **“Under construction…”** README, so this is not a recommendation to install a ready-made package. 

**My practical conclusion:** this paper helps ADE avoid choosing the wrong repair because several distinct failures were collapsed into one success rate.

---

## 4. ReCAP — the most relevant architectural idea, but not a drop-in solution

### What the paper contributes

ReCAP retains references to original historical blocks, importance scores, and dependencies between blocks. Selection is conditioned on the new request and can bring back previously omitted material, including supporting predecessors that would not rank highly on their own. Its implementation is oriented toward interactive coding histories and uses attention-derived information plus code-identifier relevance signals. [arXiv](https://arxiv.org/html/2609.40118v1)

### Why the idea fits ADE

The dependency problem is almost exactly what your character-history fixtures expose:

> A passage saying “the original account was right” depends on the passage containing that original account.

Independent exchange ranking does not represent that dependency. ReCAP offers a useful conceptual alternative: **select a source together with the context needed to interpret it**.

It also aligns with ADE’s decision to preserve original history rather than making a newly written summary the sole authority. ADE’s historical evidence remains attributed, read-only source data; it does not independently authorize current memory writes. 

### Why I would not implement ReCAP now

There are important qualifications to the earlier brief’s “no extra model calls” description.

ReCAP normally reads attention from the agent model. For closed APIs, the paper instead tests a small **proxy model that replays the served context** to obtain attention statistics. It also uses coding-oriented identifier matching and heuristics for potentially superseded blocks. Those mechanisms do not establish how Mandarin conversational corrections should be interpreted. [arXiv](https://arxiv.org/html/2609.40118v1)

For ADE, importing those mechanisms would raise exactly the questions you are trying to resolve: another model’s cost and failure modes, new derived state, and whether a selection heuristic accidentally suppresses the original statement that a later correction restores.

Also, during this check, GitHub reported the paper-linked **ReCAP repository as empty**. I could inspect the paper, but not a runnable implementation.

### What I would take from it

For now, use ReCAP as a design reference for **dependency-preserving selection of original sources**, not as justification for a persistent graph service.

The current experiment can first establish whether delivering the missing antecedent improves behavior. Only after a broader need is demonstrated should ADE decide whether dependencies need explicit representation—and how to obtain them without turning retrieval metadata into factual authority.

**My practical conclusion:** keep the architectural insight; do not import the attention pipeline, proxy model, or supersession heuristics.

---

## 5. Repair or Resample? — make sure an apparent fix addresses the same failure

### What the paper contributes

The paper distinguishes a genuine repair from a successful rerun that happened to take a different path. Its SymTrace approach reconstructs recorded interactions before a selected intervention point, then resumes live execution downstream. Importantly, the guarantee concerns the reconstructed prefix—not deterministic future model output. Replaying a recorded tool response also does **not** recreate a persistent external side effect. [arXiv](https://arxiv.org/html/2608.25920v2)

### Why it is useful for ADE

ADE is changing several interacting elements: query construction, source selection, packet composition, generation instructions, reviewer instructions, and provider configuration.

Without controlled comparisons, an improved answer could reflect any of them—or ordinary sampling variability.

Your latest D04 protocol already follows much of the useful discipline: frozen inputs, independent arms, fixed effective model settings, no cross-arm answer leakage, no rerolls, complete outcome capture, and explicit acknowledgement that one result per arm is **a diagnostic witness, not a reliability estimate**. 

That existing work is why I rank this fifth rather than first: **ADE already has much of the mechanism; the paper helps defend its interpretation.**

### What I would take from it

Preserve the distinction between two kinds of evaluation.

A **packet-level comparison** asks whether changing the supplied evidence changes generation or review under otherwise fixed conditions. It does not qualify database persistence.

A **native-turn comparison** also depends on the relevant PostgreSQL state, fact versions, conversation/persona bindings, and actual commit behavior. Replaying HTTP responses is not a substitute for restoring that state.

For future repairs, use ADE’s existing frozen requests, captures, and disposable-state tests rather than introducing a generic replay framework. Change one consequential boundary at a time where feasible, and keep the original failed outcome intact.

**My practical conclusion:** a successful new answer is useful evidence, but it should not automatically become “the retrieval problem is fixed.”

---

## Why the obvious “memory papers” did not make the top five

**LycheeMemory V2 and Jev-Mem** are relevant, but their main contributions involve changing memory construction or adding a specialized control and relational-memory architecture. I do not see a demonstrated need to replace ADE’s current ownership and lifecycle model to address the missing-antecedent problem. Their benchmark results do not establish that such a replacement would improve ADE’s character continuity. [arXiv](https://arxiv.org/abs/2608.12990?utm_source=chatgpt.com) 

**SANE** is closer to your proposed selector, but it adds selection and evidence-extraction stages. Given the current capacity result, I would first establish what a better original-source packet achieves before introducing a model-generated intermediate representation. [arXiv](https://arxiv.org/abs/2608.00658?utm_source=chatgpt.com) 

I would likewise defer the impressive **KV-cache, serving, and multimodal-generation work** for this decision. My ranking is about the current continuity problem, not their general engineering importance.

## What this means for ADE’s next decision

**The research does not currently justify a larger architecture. It reinforces the direction of your already-prepared D04 comparison.**

My interpretation guide would be:

- **Repaired-four and whole-pool both improve the reply:** evidence selection/composition deserves attention; an extra model phase still has to justify itself.
- **Complete evidence arrives but the reply remains wrong:** investigate interpretation and generation rather than assuming another retrieval layer will solve it.
- **The reply is faithful but reviewer behavior is wrong:** address that separately; retrieval success does not qualify mutation or persistence.

These are proposed interpretations, not observed results. At the inspected revision, the behavioral comparison was prepared but **live-unrun**. 

**Bottom line: read The Recall Trap first. Use When Knowledge Changes and The RAT to judge improvements. Keep ReCAP as a constrained design reference, and use Repair or Resample? to avoid mistaking a better sample for a durable repair.**

*Evidence scope: I inspected ADE read-only and checked the shortlist against primary sources. Full texts were accessible for When Knowledge Changes, ReCAP, and Repair or Resample?; for The Recall Trap and The RAT, I verified the author abstracts but could not retrieve the full texts. I did not reproduce paper benchmarks, modify ADE, or run its providers.*