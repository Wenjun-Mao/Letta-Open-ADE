# Verdict: proceed after one narrow lifecycle clarification

**Revision 2 is sufficiently bounded and substantially closes the earlier product-semantic blockers.** I would proceed with its implementation checkpoints after tightening one point in §2: **a correction to a stored fact is not necessarily a correction—or retraction—of the user’s original statement.**

That clarification belongs in H1, before the lifecycle envelope’s meaning is frozen. It does not require another memory component, another evidence mode, or proof of reviewer reliability. The remaining concerns about next-turn acknowledgment, fresh assertions, clarification, resolved concerns and repetitive callbacks are now appropriately framed as empirical questions for the proposed probe. The automatic-packet versus empty-history comparison is also a materially cleaner first experiment.  

## What I inspected

All reads used GitHub at **`8e298881e4165128c5a680a0b02c1789c894d8ff`**. Access succeeded; I did not substitute another branch or revision.

| Material | Inspection |
|---|---|
| Required documents, complete | `docs/plans/natural-history-recall.md`; `docs/product-contract.md`; ADRs **0035/0036**; `docs/findings/natural-memory-factual-followup-2026-09-24.md`, including both reviewer-only contrasts |
| Current write-boundary implementation | Complete `natural_memory_binding.py` and `natural_memory_review.py`; lines 1–280 of `natural_memory_policy.py`, including decision preparation and `_bind_evidence`, under `services/ade-api/src/ade_api/features/agent_runtime/` |
| Prior review closure, checked afterward | Complete `history-recall-review-assessment.md`, `history-recall-pro-product-report.md` and `history-recall-pro-architecture-report.md` under `docs/findings/natural-memory-consultation/` |

I formed the findings from the revised plan, contracts and implementation excerpts before consulting the assessment and archived reports. I did not inspect private captures, access local services, execute tests or make model calls.

**Evidence labels:** “Observed” means visible in the inspected source. “Repository-reported” refers to a findings document’s account, not a reproduced result. **All dialogues below are constructed counterexamples or acceptance cases, not observed ADE failures.**

# 1. Remaining contract clarification: distinguish correction of memory from correction of testimony

**Priority: resolve in H1 before freezing the envelope semantics. This is the only remaining issue I would put on that side of the implementation boundary.**

### What is already correct

**Observed:** §2 now follows the originating source span through recorded revision paths, retains intervening corrections even when the latest value returns to the original, preserves branching and unknown meaning, and prohibits replacing this with a latest-status label. That closes the earlier missing-history problem. It also explicitly says history establishes what was said, not whether it was true. 

### The remaining ambiguity

The envelope contains recorded operations, reasons, statuses and ordering. But **what was corrected—the saved representation or the user’s account—is not necessarily encoded by `reason="correct"`**.

**Observed:** the current schema describes `revise` as changing or correcting an active *target fact*. The binder applies its value, status and reason to that target. Those fields do not independently establish that the user recanted the original source utterance.  

This distinction matters for an input state ADE has already encountered. **Repository-reported:** a source explicitly saying `我早上更喜欢喝咖啡。` produced a saved preference lacking the morning scope. That was an extraction error, not an ambiguous original statement. 

### Counterexample A: the user never changed their account

> 【聊天 A，角色 v1；后来归档】  
> 用户：我早上更喜欢喝咖啡。  
>   
> 【假设保存的偏好遗漏了“早上”】  
> 用户：我说的是早上，别记成全天。  
> 小棠：嗯，是早上。  
>   
> 【聊天 B，同一角色根，v2】  
> 用户：我第一次说的时候，是不是忘了说早上？  
> 小棠：没有，你第一次就说了“早上”。  
> 用户：对，我没有改口。

Assuming the relevant dialogue is supplied, this is compatible with a recorded correction to the fact. It is **not** compatible with:

> 你最开始说全天都喜欢咖啡，后来才改口说早上。

The wrong answer would convert an extraction mistake into invented user testimony. On the final acknowledgment, an already-correct morning preference needs no new mutation.

**Inference:** the plan does not require this mistake, but an implementation that translates a linked `correct` transition into “the original report was corrected” could make it. “Unknown meaning” should cover this case even when the operation code itself is perfectly known.

### Counterexample B: knowing a correction occurred is not knowing its content

> 用户：我住杭州。  
> 用户：刚才说错了，我住苏州，杭州只是出差。  
>   
> 【后来】  
> 用户：这周我真的搬到杭州了。  
>   
> 用户：我第一次提杭州，那时是什么情况？

Revision 2 correctly prevents the final Hangzhou value from establishing continuous residence.

There is a second boundary: **an envelope showing `correct → supersede`, plus the original and current Hangzhou values, does not by itself supply “苏州” or “只是出差.”** Those details require admitted evidence that actually contains them.

If the corrective dialogue is present, the reply can attribute the clarification:

> 你后来解释过，当时住苏州，去杭州只是出差；真正搬过去是这周。

If that dialogue is absent, the reader must not manufacture its content from lifecycle codes. The result may be sufficient to flag a recorded correction, but insufficient to answer the historical circumstances. The plan’s sufficient-evidence scoring already provides the right place to record that limitation.  

### Smallest correction

Add wording equivalent to:

> **Lifecycle transitions describe recorded changes to fact representations. They do not, by themselves, establish that a linked utterance was false, retracted, or replaced in every component. The scope and content of a historical correction must come from admitted evidence; otherwise that meaning remains unspecified.**

Then freeze two contrasts: **repair of an incorrectly extracted fact** versus **correction of the user’s earlier account**.

This does not require adding intermediate forgotten values to model context. Nor does it require every old quotation to bring an entire correction history’s text. Supply only what the answer needs; otherwise retain uncertainty or report insufficient evidence. The reviewer still interprets language, while ADE reports the provenance it actually possesses.

# 2. Next-turn authority: the policy gap is closed; test its application rather than adding restrictions

**Observed:** §4 now explicitly distinguishes historical acknowledgment, fresh current assertion, genuine local endorsement and an `H`-only referent. It also acknowledges that namespaces cannot prevent a reviewer from semantically misusing a genuine current quotation. These are the right contracts. 

The implementation excerpts support the need for the separation: admitted local messages become `U/A` support, while forgotten facts are excluded from the `F` target map. The existing write modes remain direct, user-resolution and assistant-endorsement; `H` is not currently one of them.  

## Removal followed by acknowledgment—and then a real change

> 【旧聊天已归档，乌龙茶偏好已由操作员移除】  
> 用户：我以前说最喜欢什么茶？  
> 小棠：你那时说最喜欢乌龙茶。  
> 用户：对，你记得很准。  
> 用户：不过现在早上最喜欢的是红茶。

The expected distinction is clear:

The historical question and acknowledgment produce **no preference resurrection**. The final turn can support **a new morning-scoped red-tea preference**. The removed chain remains forgotten.

This mixed sequence is more informative than testing only “zero writes after recall.” A reviewer that refuses all subsequent writes concerning tea would also be wrong. Revision 2’s complete-delta scoring and fresh-restatement contrast already accommodate both sides.

The same distinction survives an ordinary persona-version change because character continuity changes neither the quotation’s time scope nor the user’s current write authority.

## An `H`-only referent may guide clarification without authorizing the write

> 用户：我现在又喜欢之前说的那种茶了。  
> 【只有 H 能确定是哪种茶】  
> 小棠：你是说，现在又喜欢乌龙茶了，对吗？  
> 用户：对。

The initial mutation should be deferred under the proposed boundary. The later genuine confirmation can support the current proposition through ordinary local evidence.

The assistant’s use of history to formulate that question is not itself a violation. **Read-only history is allowed to inform conversation; what it cannot do is substitute for the fresh authority needed to save a fact.**

Contrast:

> 用户：我以前说的是哪种茶？  
> 小棠：你那时说的是乌龙茶，对吗？  
> 用户：对。

Here, the confirmation is historical. There is still no supported current preference.

**Assessment:** this is now an empirical interpretation test, not an unresolved permission question. Do not add a permanent “history-derived topic” restriction, ban short confirmations, or require a special storage command. ADR 0035 assigns precisely this semantic judgment to the reviewer, rather than a phrase validator. 

For the follow-up experiment, retain whether the original `H` packet was supplied again on the next turn. A correct result with repeated historical evidence and a correct result supported by local dialogue alone are useful but different observations. The existing packet-level records can show this; no persistent tracking mechanism is needed.

# 3. Temporal conflict review: correctly specified, but do not confuse recorded disagreement with grounds for rejection

**Observed:** §4 expressly permits both a current assertion differing from old text and an attributed historical answer differing from current facts. The extension is limited to read-only conflict grounding, with atomic rejection retained. This closes the previous false-conflict contract gap. 

Two contrasts should remain paired:

> 【历史】用户：早上我更喜欢咖啡。  
> 【当前】用户：现在早上更喜欢茶了。  
> 小棠：那早上就换成茶。

The historical coffee statement is not a reason to veto the current change.

> 【当前事实已是早上偏好茶】  
> 用户：我以前说早上更喜欢什么？  
> 小棠：你那时说更喜欢咖啡。  
> 用户：对，但现在是茶。

The historical quotation is not a reason to veto the reply either. The last turn confirms the existing current preference; it need not generate another revision.

**Remaining empirical question:** whether the reviewer applies those distinctions without either missing genuine contradictions or rejecting legitimate updates. An exact `H` citation makes a conflict structurally grounded, not semantically justified. Revision 2 already says this and separately scores false, missed and correct conflicts. 

The clarification in finding 1 matters here too: a fact-record correction must not automatically become evidence that an accurately quoted original utterance is false.

# 4. Resolved concerns, habits and repetitive callbacks: retain the tests, not more machinery

I do not find another missing product decision in these areas. The remaining risks are concrete, but Revision 2 already gives them appropriate evidence and scoring boundaries.

## A resolved concern is not an ongoing emotional state

> 【聊天 A，v1，后来归档】  
> 用户：明天面试，我怕紧张得说不出话。  
> 小棠：我们先练一下开场？  
>   
> 【聊天 B，同一角色根】  
> 用户：拿到录用通知了，终于放心了。  
>   
> 【聊天 C，v2】  
> 用户：朋友也要去那家公司面试。  
> 小棠：是后来给你发录用通知的那家？他准备面什么岗位？  
> 用户：对。顺便帮我看看这个键盘。

A callback to the completed interview may be useful. Treating the user as still awaiting that interview is unsupported. Continuing to mention interview anxiety while discussing the keyboard would be an inappropriate callback.

If only the anxiety exchange was retrieved, the packet is not sufficient to establish the later resolution. Conversely, its absence does not establish that the anxiety continues. The plan now explicitly separates a topic hit from sufficient qualification/resolution evidence and includes unrelated follow-ups. That is adequate for the probe.  

Do not require the callback shown above as the sole successful answer. A relevant response focused on the friend can also be natural.

## A repeated behavior is not necessarily a preference

> 用户：这周早上都喝茶，咖啡还没买。  
> 小棠：咖啡断货了啊。  
>   
> 用户：明早喝什么好？  
> 小棠：咖啡补上了吗？没有的话，先喝茶也行。

This can be useful continuity without saving a tea preference. A reply such as “你一直更喜欢茶” invents both preference and continuity.

The revised interpretation table now explicitly labels its coffee/tea preference example as **preferences**, rather than leaving it ambiguous between behavior and liking. That earlier wording issue is closed. 

## Ranking cannot resolve every ambiguous antecedent

> 用户：面试和体检都约好了。  
> 小棠：最近安排得挺满。  
> 用户：那个推迟到下周了。

Retrieving the interview discussion at rank one does not prove that “那个” denotes the interview. A clarification remains appropriate.

This is not necessarily a retrieval failure, and better retrieval is not guaranteed to fix it. Revision 2 correctly treats ambiguous antecedents and subsequent trajectory effects as semantic sequence tests. No additional state representation follows from this case. 

# Successfully closed issues

“Closed” here means **specified sufficiently to implement and test**, not demonstrated reliable behavior.

| Earlier concern | Revision 2 disposition |
|---|---|
| Latest value hides correction followed by return to the original | §2 retains source-relative recorded paths and intervening transitions, including branches and bounded omission. **Closed**, subject to distinguishing fact repair from user retraction as above. |
| Removal is missed because the latest revision has no message source | §2 follows the originating source revision through the chain rather than relying on the latest revision’s source rows. Source-less removal is explicitly included in H2. |
| Retrieved history accidentally acquires write authority | §4 separates `H` from `U/A/F/E`, prohibits inserting cross-chat records into `source_messages`, and preserves independently admitted local authority. |
| Historical acknowledgment is mistaken for a fresh assertion | §4 freezes the acknowledgment/restatement/endorsement contrasts and requires follow-up measurement. **The policy choice is closed; interpretation remains empirical.** |
| A fresh assertion depends on an `H`-only referent | §4 explicitly chooses deferred mutation and ordinary local clarification, without creating a fourth evidence mode. |
| Historical difference causes false conflict | §4 permits current changes and attributed historical answers in both temporal directions. |
| Archive/persona continuity is confused with shared-profile scope | §1 keeps same-root transcript continuity across versions and archives while explicitly leaving shared subject facts outside the root restriction. |
| The first experiment is too broad or confounds reviewer changes | The probe now compares one automatic packet against empty history with the same `H`-capable reviewer. Discretionary tools and the preview/read protocol are deferred. |

These closures are explicit in the revised plan rather than inferred solely from the assessment’s claim that recommendations were incorporated. 

The capacity and evidence-consistency contracts are also materially clearer: history cannot displace matched local/fact context; both models receive the same admitted historical evidence; source loss before first exposure differs from loss discovered afterward; and the purge guarantee is bounded by authorization checks rather than pretending to eliminate all races. I see no reason to reopen those contracts in this product-semantic review. They still need the planned structural tests. 

# Evaluation assessment

**The proposed evaluation now separates the important failure classes well enough for a feasibility decision.**

H4/H5 distinguish independently reseeded target turns from divergent follow-up trajectories, and separate corpus coverage, retrieval sufficiency, admission, candidate quality, review and delivery/persistence. They also distinguish false reviewer vetoes from retrieval failures and caught bad candidates from successful delivered answers. Ranking-development fixtures are separate from scored dialogue cases. Those changes close the earlier evaluation-design blockers.  

Two scoring interpretations are worth making explicit when H1 freezes the cases:

**Safe incompleteness is not the same as sufficient recall.** A reply that correctly avoids guessing after missing a correction may be semantically acceptable while still failing the case’s historical-information objective. Record both judgments rather than forcing one success/failure label.

**Zero mutations is not universally the desired outcome.** It is correct for historical acknowledgment and habit-only evidence, but incorrect when a genuinely fresh, supported current assertion should change memory. The paired removal/restatement cases must test usefulness as well as restraint.

Neither requires another arm or judge. They fit the planned stage records and complete-delta scoring.

The experiment can establish whether the **automatically selected and admitted packet**, under this binding, improves delivered dialogue enough to continue. It cannot establish that automatic retrieval is universally preferable to discretion, or that the ranker, generator and reviewer are individually reliable. Revision 2 now makes appropriately narrow claims. 

# Evidence limits and final recommendation

The repository-reported diagnostic establishes a relevant limitation: a correctly scoped source can yield a mis-scoped saved fact, while a separate habit turn produced no reviewer decision because of truncation. The latter is not evidence of a wrong habit/preference judgment. The two low-effort replays produced appropriate proposed deltas but did not constitute a coherent native sequence or repair the previously committed fact. I read those accounts, not their private captures or database readbacks.  

Historical retrieval remains proposed in the inspected plan. The current reviewer files I inspected show the existing `U/A/F/E` contract, not a completed `H` implementation. The archived reviews and assessment are design evidence, not measurements of Revision 2’s behavior.   

**Recommendation:** add the fact-repair-versus-user-retraction clarification to §2/H1, then proceed with the bounded checkpoints. Do not reopen the settled removal or character boundaries, and do not delay reader work until the reviewer is generally reliable. The remaining uncertainty is chiefly whether the specified semantics work in actual packets and across the next turn—not whether another memory architecture is needed.