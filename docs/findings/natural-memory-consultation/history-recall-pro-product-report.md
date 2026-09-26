# Verdict: revise narrowly, then proceed with the bounded probe

**The proposed architecture is appropriate. The remaining work is to make the evidence contract precise—not to add another memory subsystem.** I would approve the read-only repository/ranking work after clarifying source-relative lifecycle annotations. I would hold runtime integration and the three-arm comparison until the fresh-assertion boundary and failure-scoring rules below are frozen.

Three distinctions must survive implementation:

1. **“The user said this” is not “this was true,” and neither establishes “this is still true.”**
2. **Acknowledging a historical quotation is not necessarily making a current assertion.**
3. **Finding a relevant old passage is not successful recall when the missing passage contains its correction or resolution.**

The plan already recognizes these distinctions in substantial part. My findings concern places where its wording still permits materially different implementations, rather than requirements it has wholly overlooked. Its scope exclusions, character-root boundary, archive eligibility, frozen corpus, one-reviewer design, and separation of `H` from writable evidence should remain. 

## Inspection and evidence basis

I accessed **`cece5bedd6032da3ebc3802c7be604eb505967e6`** successfully through GitHub. All source references below are pinned to that commit. I did not substitute `main`, consult prior chats, access local services or private captures, execute tests, or make model calls.

| Material | Actually inspected |
|---|---|
| Required documents, in full | `docs/plans/natural-history-recall.md`; `docs/product-contract.md`; ADRs **0035** and **0036**; `docs/findings/natural-memory-factual-followup-2026-09-24.md`, including both low-effort contrast sections |
| Additional contract | ADR **0022**, for removal, retained history, and the scope of shared subject facts |
| Reviewer implementation, in full | `natural_memory_binding.py`, `natural_memory_review.py`, `natural_memory_reviewer.py`, `natural_memory_policy.py` under `services/ade-api/src/ade_api/features/agent_runtime/` |
| Selected supporting implementation | `natural_context.py` lines 1–280; `persistence/memory.py` lines 1–460; `persistence/memory_source_read.py` in full |
| Evaluation documentation | The returned portions of `workflows/evals/character_memory_dev/README.md`, including verification and native factual-diagnostic descriptions—not the entire file or its referenced private artifacts |

**“Observed” below means observed in those documents or source code.** Where a findings document reports a live result, I identify it as a repository-reported observation, not an independently reproduced measurement. **Every Mandarin dialogue below is a constructed counterexample or acceptance case, not measured ADE behavior.**

The relevant product agreements are PC-01, PC-03–07, PC-09 and PC-10. I recommend no change to the settled character, archive, removal, or architectural boundaries. 

# Prioritized findings

## 1. Blocker: define lifecycle annotations relative to the recovered statement—not just the current fact

**Observed.** “Past Reports Versus Current Facts” says linked source spans should receive current lifecycle annotations, including eligible current descriptors, without exposing forgotten revision values. It correctly distinguishes correction, ending, removal and unknown status. However, it does not specify how annotations preserve an earlier correction when the chain subsequently changes again. Existing persistence retains ordered revisions and predecessor relationships; the current projection points to the latest revision.   

**Inference.** An annotation such as “this source belongs to a currently active Hangzhou residence fact” is insufficient. The endpoint cannot establish what happened to the original claim.

### Counterexample: correction followed by a genuine later change

> 用户：我现在住杭州。  
> 小棠：在杭州啊。  
> 用户：刚才说错了，我住苏州，杭州只是出差。  
>   
> 【后来，新聊天，同一角色】  
> 用户：这周我真的搬到杭州了。  
>   
> 用户：我第一次跟你说住杭州，那时候是什么情况？

A supported answer is:

> 你那次后来更正过：当时住苏州，去杭州只是出差。真正搬到杭州是这周。

The latest value is again Hangzhou. That must not retrospectively validate the first statement or produce “你一直住杭州，后来又搬回去了.”

The same problem arises with **invalidated → reasserted** chains: a later valid assertion does not prove an earlier invalidated report was true.

### Minimal correction

Specify a **bounded, source-relative lifecycle envelope**. For a structurally linked source, it should identify the originating revision and the material recorded transitions needed to interpret that source, alongside the eligible current descriptor. This is a projection of existing provenance—not a new temporal database, model-generated history summary, or semantic linkage service.

The envelope must preserve these meanings:

- **Correction/invalidation:** do not affirm the affected earlier report as a true past state.
- **Supersession/ending:** describe the supported change without inventing its opposite or continuity.
- **Removal:** the record is removed from current memory; removal alone says nothing about whether the old report was true.
- **No usable linkage:** current status remains unknown.

Apply annotations to the linked claim/span, not indiscriminately to every clause in the surrounding exchange. Existing source records distinguish current authority from antecedent and assistant-referent support; a source link itself is not proof that every sentence asserts the fact. 

Keep the plan’s existing omission rule: when essential annotations cannot fit, omit the optional source rather than expose misleadingly unqualified text.

### Counterexample: an ending is not an opposite state

> 用户：我和阿哲在一起。  
> 小棠：听起来你很开心。  
> 用户：我们已经分手了。  
>   
> 用户：周末想出去散散心。

Neither “叫你男朋友阿哲一起去” nor “你现在肯定很讨厌阿哲” follows. The first resurrects an ended relationship; the second invents a new attitude.

**Blocking issue:** the annotation contract needs this specificity before its reader implementation is frozen. Whether the reviewer reliably interprets the resulting envelope remains empirical.

---

## 2. Blocker: close the gap between “`H` cannot authorize writes” and fresh conversational assertions

**Observed.** The proposed `H` separation is sound. The current implementation makes its importance concrete:

`build_natural_binding_map` converts admitted prior messages into `U`/`A` handles; the write schema permits direct current evidence, `resolve_user` with `U`, and `endorse_assistant` with `A`. Mutation targets use `F`. Binding verifies exact quotations and roles, while the reviewer decides their meaning.   

Therefore, historical-only messages must not simply be appended to `source_messages`: doing so would promote them into the existing writable-support namespace.

But namespace separation alone does **not** settle the multi-turn semantics.

### Counterexample: removal followed by a historical acknowledgment

> 【旧聊天】  
> 用户：我最喜欢乌龙茶。  
>   
> 【操作员移除这条已保存事实；原对话保留】  
>   
> 用户：我以前说最喜欢哪种茶来着？  
> 小棠：你那时说最喜欢乌龙茶。  
> 用户：对，你记得真清楚。

The quotation is permitted. **The preference delta should remain zero**, including after the last turn. That turn confirms the recollection; it does not necessarily assert a current preference.

A plausible hypothetical failure is indirect resurrection: the historical quotation becomes a newly committed assistant message, then the next reviewer treats the user’s acknowledgment as endorsement of a current preference. This could be structurally valid `A`-supported output yet semantically wrong. ADR 0035 explicitly acknowledges that structurally valid but semantically incorrect decisions can pass. 

Compare genuinely fresh authority:

> 用户：现在我最喜欢的还是乌龙茶。

That can support a new current fact under the proposed removal interpretation. The forgotten chain must remain forgotten.

Also preserve ordinary contextual endorsement:

> 小棠：你现在也最喜欢乌龙茶吗？  
> 用户：是的。

A short answer can genuinely assert a current proposition. **Do not solve resurrection by banning short confirmations, banning all assistant-supported writes after retrieval, or permanently marking retrieved topics as unwritable.** Those would introduce new semantic restrictions rather than clarify the existing boundary.

### The unresolved edge: a fresh assertion whose referent exists only in `H`

> 用户：我现在又喜欢之前说的那种茶了。

Suppose only retrieved history identifies the tea as 乌龙茶.

The assertion is temporally fresh, but its referent is not established by the admitted writable evidence. The plan forbids `H` as earlier write support. It must therefore say what happens here.

**My recommendation for this bounded implementation:** retain that prohibition. Do not save “乌龙茶” as a supposedly direct assertion whose missing referent was supplied exclusively by `H`. Defer the mutation; a natural clarification can establish an ordinary local proposition:

> 小棠：你说的是乌龙茶？  
> 用户：对，最近又喜欢喝它了。

This accepts a small conversational limitation rather than silently creating another evidence mode.

### Minimal correction

Add an explicit contrast to the contract:

> Historical acknowledgment alone authorizes no current fact. A fresh assertion or endorsement can authorize a current fact through the existing evidence modes when the complete claim is supported by admitted current/local evidence. An `H`-only referent does not qualify as direct evidence.

Keep `H` in a separate read-only binding map. Independently admitted local evidence should retain its normal authority; the restriction is against **promoting historical-only evidence**, not against a source appearing through two legitimate read paths.

### `H` conflict review needs the same temporal distinction

The existing reviewer instruction says to report conflict when a candidate contradicts held memory. Adding `H` must not turn that into “reject any answer differing from an old quotation.” 

> 【历史】用户：早上我更喜欢咖啡。  
> 【当前】用户：现在早上更喜欢茶了。  
> 【候选回复】小棠：那早上就换成茶。

The old `H` passage does not make this a conflict. Conversely, answering a historical question with “你以前说早上更喜欢咖啡” does not contradict a current tea preference.

**Blocking issue:** freeze these authority and temporal-conflict semantics before extending the schema. Do not add a phrase recognizer or another reviewer.

---

## 3. Empirical question: “whole exchanges” do not guarantee retrieval of corrections or resolutions

**Observed.** The plan already recognizes unlinked dialogue, differently worded corrections, chronological context, resolved concerns and the absence of guaranteed historical truth repair. That is appropriately cautious. Its whole-exchange rule prevents some misleading clipping, but not omission of a later exchange in another conversation. 

**Inference.** H2 needs to measure **evidence sufficiency**, not merely whether a top-ranked passage mentions the right topic.

### Counterexample: archived concern, resolved later, recalled after a persona update

> 【聊天 A，角色版本 v1，后来归档】  
> 用户：明天去那家公司面试，我怕一紧张就说不出话。  
> 小棠：要不要先练一遍开场？  
>   
> 【聊天 B，同一角色根】  
> 用户：拿到 offer 了，昨天已经签了，终于不用担心了。  
> 小棠：恭喜，终于踏实了。  
>   
> 【聊天 C，角色版本 v2】  
> 用户：我朋友也要去那家公司面试。

A supported callback might be:

> 是你后来拿到 offer 的那家？你朋友准备面什么岗位？

A bad callback is:

> 你还在为那场面试焦虑吧。

Recovering the archived anxiety exchange is a **topic hit**, but not sufficient evidence for the latter current-state assertion. When the later resolution is supplied, ignoring it is a generation/reviewer failure. When it exists in the eligible corpus but was not retrieved, the packet may instead be insufficient.

This case is especially important because the concern need never become a typed fact. A lifecycle annotation cannot resolve what was never linked to a fact chain.

### Minimal correction

For the existing correction/resolution fixtures, specify the **smallest sufficient evidence set**, which may contain more than one exchange. Record separately whether the system found the initial report and whether it admitted the qualifying correction or resolution.

Do not require global semantic linkage or a second search on every turn. Bounded neighboring context is reasonable where useful, but it will not solve distant cross-chat resolutions. When current status is unsupported, attribution to the past remains available; presenting a concern as ongoing does not.

**Not an implementation blocker:** whether the chosen ranker reliably finds the resolution. That is precisely a question H2/H4 should answer. A miss should not automatically justify an episode store.

---

## 4. Empirical question, with a small wording fix: natural continuity includes knowing when not to mention history

**Observed.** The product contract rejects repetitive personalization and says a drinking habit must not silently become a preference. H4 already lists habit/preference, ambiguous dialogue and inappropriate callbacks. These categories are present; the improvement needed is to test their interaction across a short sequence.  

### Counterexample: behavior recalled accurately, preference invented

> 用户：这周早上都喝茶，家里的咖啡喝完了。  
> 小棠：原来是咖啡断货了。  
>   
> 用户：明早喝点什么好？

A natural reply could use the history:

> 前几天你说咖啡喝完了。现在补上了吗，还是继续喝茶？

It should not infer “你一直更喜欢茶,” nor save a tea preference.

**Small document correction:** the plan’s first interpretation-table row says “old morning coffee; current morning tea” and then calls tea the latest *preference*. Label that row explicitly as **stated preferences**. Otherwise its shorthand is ambiguous beside the correct habit/preference rule. This is a wording issue, not evidence of a runtime defect. 

### Counterexample: two plausible antecedents

> 用户：周五我要面试，周六陪妈妈复查。  
> 小棠：这两天都挺忙的。  
> 用户：那个改到下周了。

A high-ranked historical interview passage must not settle which appointment moved. A clarification such as “面试还是妈妈的复查？” is appropriate; a definite update is not.

Here, ambiguity is not necessarily a retrieval problem. Searching more can increase confidence without resolving the current utterance.

### Counterexample: a good callback becomes a repetitive one

After the drink exchange:

> 用户：帮我看看这个键盘。  
> 小棠：你喜欢早上喝茶，这个键盘很适合你……

The old passage may still be retrievable. Its availability is not a reason to use it.

### Minimal correction

Extend a few existing cases by two or three follow-ups: a relevant continuation, an ambiguous reference, then an unrelated topic. Score the sequence, not just the first successful callback.

For archive/persona cases, preserve a paired boundary test: the same subject and root may recall an archived v1 exchange in v2; another root may use eligible shared profile facts but must not claim “我们上次聊过.” This preserves PC-03/04/10 rather than reopening them. 

No callback ledger, phrase table, or removed-topic suppression mechanism is warranted. In particular, **removal should not become a relevance veto**: an explicitly relevant historical quotation remains allowed.

---

## 5. Evaluation blocker: make failure attribution explicit before comparing arms

**Observed.** H2’s ranker selection before trigger comparison, H4’s separate retrieval/dialogue scoring, independently seeded chronological arms, retained passages, and H5’s refusal to equate small samples with reliability are strong design choices. 

The remaining problem is operational: “retrieval and dialogue separately” is not quite enough to distinguish the failures this repository has already encountered.

The findings document reports both a committed morning-scope omission and a separate reviewer truncation with no decision. The truncated turn cannot establish whether the model would have inferred a preference from a habit. The two low-effort replays produced appropriate **proposed** deltas, but were not a coherent native sequence and did not repair the earlier stored value.  

### Minimal correction: retain one per-turn outcome record with distinct stages

| Stage | Question it answers |
|---|---|
| Eligibility and corpus | Was the required source legitimately available to this attempt? |
| Retrieval | Was a sufficient evidence set found—not merely a topic match? |
| Admission | Did the generator and reviewer actually receive the needed passages, roles and annotations within the allowance? |
| Candidate generation | Given that packet, was the proposed reply relevant, correctly attributed and temporally scoped? |
| Reviewer | Was the complete proposed delta correct? Was a conflict justified, missed, or falsely asserted? |
| Delivery and persistence | What was delivered and committed, rejected, unavailable, or unrun? |

This prevents misleading outcomes:

A correct candidate rejected by an erroneous reviewer is not a retrieval failure. A bad candidate caught atomically is a successful safety boundary but **not a successful delivered answer**. An empty search is not evidence that the history never existed. A setup failure or unrun continuation must not enter the denominator as a passed recall case.

Score **all** fact changes and their complete values, scopes, lifecycle effects and provenance—not only the intended target. That is the lesson of the documented morning-scope miss.

### What the three arms can establish

They compare end-to-end retrieval policies. Because queries, passages, tool decisions and round trips may differ, they do not isolate a pure causal “trigger effect” or establish ranker/model superiority from aggregate reply scores. This is acceptable for the product decision; describe it accurately.

Do not require a search/read call where existing context already suffices. ADR 0036 distinguishes observed tool behavior from runtime forcing, and the new plan correctly avoids turning every recall case into a tool-use requirement.  

A separately bound, supplied-correct-evidence diagnostic could help localize an ambiguous failure, but should remain optional—not a fourth product arm, a second reviewer, or a reroll counted as success.

**Blocking issue:** freeze these labels, expected evidence sets and per-case answer/delta boundaries before H4. Do not demand general reviewer qualification before writing the read-only H2 module; structural reader work can be tested independently.

# Compact acceptance set

These are bounded acceptance cases, not a model-quality certification suite. The examples above supply the semantic contrasts.

| Case bundle | Required outcome |
|---|---|
| **Character and archive boundaries** | Same subject/root can retrieve archived v1 dialogue in v2 without restoring the archive or executing the old binding. Different root does not receive the transcript or claim participation merely because facts are shared. Subject/workspace/purpose boundaries remain enforced. |
| **Source-relative lifecycle** | Correction followed by a later return to the original value does not validate the original mistaken report. Ended state does not become its opposite. Missing linkage does not establish currency. |
| **Removal and restatement** | Relevant old quotation and acknowledgment of that recollection produce zero preference mutation. A genuinely fresh, supported current assertion may create current memory while the removed chain remains forgotten. |
| **Writable evidence boundary** | `H` cannot serve as mutation target, current anchor, or historical-only `U`/`A` support. An `H`-only referent is not disguised as a direct assertion. Genuine local current endorsement remains possible. |
| **Temporal conflict review** | A current supported change is not vetoed merely for differing from `H`; an attributed historical answer is not vetoed merely for differing from current facts. A genuinely grounded conflict retains atomic rejection. |
| **Habit and resolved concern** | Behavior does not become preference. A supplied resolution is respected. An unavailable resolution yields no unsupported claim that the concern continues. Complete deltas remain within the current turn’s authority. |
| **Ambiguity and repetition** | Competing plausible antecedents remain unresolved until clarified. Relevant recall can occur naturally, but unrelated follow-ups do not repeatedly reuse it. No tool call or callback is required merely because history exists. |
| **Evidence delivery and accounting** | Previews and exact reads obey the same boundaries; both models receive identical admitted `H` evidence and annotations. Capacity/omission, stale or purged sources, guessed references and cumulative tool allowances preserve the planned structural behavior. Every failed or unrun stage remains visible. |

Structural cases should be deterministic gates. Semantic results should be reported individually with exact evidence and disagreements. A small clean result supports proceeding; it does not establish population reliability.

# Scope and simplification recommendation

Retain one cohesive reader, the existing persistence and embedding route, one selected ranker, one reviewer, and the isolated comparison. **Do not add durable machinery to compensate for uncertainty revealed by a small probe.**

There is also no need to make a two-step search/read interaction ceremonial. A whole annotated exchange exposed in a search result is already evidence. Where that is sufficient, do not require `read_history` solely to satisfy an evaluation expectation. Keep exact read for cases that genuinely need a larger bounded window.

H1’s native diagnostic remains useful for separating existing reviewer limitations from historical retrieval. A failure there should prevent an unsupported end-to-end success claim—not force changes to reviewer settings mid-comparison or prevent independent reader tests. Keep the plan’s subsequent decision point for production indexing, scale, freshness, defaults and release qualification. 

# Evidence limitations

The repository supports a narrower conclusion than “historical recall works.” The plan is explicitly proposed, the current product contract leaves historical-recovery mechanics open, and the existing reviewer’s structural validation does not prove semantic correctness.   

The live findings describe earlier source bindings. I read those reports, but not their private request captures or independent PostgreSQL readbacks. Their hashes establish what artifacts the authors reference; they do not let me independently validate the artifacts. The documented correct scoped recall, scope loss, truncation and two successful reviewer-only proposals must remain separate observations.  

I therefore cannot select automatic versus discretionary retrieval, estimate callback or resurrection rates, or certify the proposed `H` implementation from this inspection.

**Bottom line:** proceed after tightening the source-relative lifecycle envelope, fresh-assertion boundary and stage-level evaluation contract. The strongest part of this proposal is that useful historical continuity need not become a new current fact. Preserve that distinction through the *next* conversational turn, not just through the retrieval call.