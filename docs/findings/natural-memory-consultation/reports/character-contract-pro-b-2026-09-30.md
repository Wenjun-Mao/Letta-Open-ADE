# ADE review: expressive freedom should not create evidential authority

**Keep the current architecture and bounded attribution clarification. The next useful decision is what an improvised first-person episode means—not how to add another mechanism to reject it.**

Three distinctions materially change the next step.

First, **a correct fact delta does not establish trustworthy conversational memory**. A successful turn also persists the assistant’s reply, which can later become historical evidence. An invented episode can therefore affect future conversation without ever becoming a typed fact.

Second, **the existing reviewer is intentionally not a general reply-faithfulness judge**. Its acceptance of unsupported placement or personal anecdotes is not, by itself, an implementation failure. Broadening that mandate would be a product and technical-contract change, with false-positive costs.

Third, **the reported personal anecdote is not yet a well-defined acceptance failure**. It is unsupported by the supplied history, but the product has not decided whether Xiaotang may improvise a fictional life. That decision should precede prompt optimization. Meanwhile, the separately reported conversion of listening frequency into preference is a more direct saved-fact concern and deserves a small Mandarin test.

My recommended first investment is **a written boundary decision plus eight controlled Mandarin target turns**, not another service, reviewer, store, or retrieval adjustment.

## 1. Source and evidence boundaries

I inspected the GitHub source at exactly:

**`2e3322db32946df947f002143a964ec440628715`**

All file links below point to that revision. The inspected-file inventory is at the end. I did not access local worktrees, services, databases, private receipts, or prior conversation history, and I did not run tests or provider experiments.

The three revision boundaries must remain distinct:

| Boundary | Revision | What this review can establish |
|---|---|---|
| **Reviewed source** | `2e3322db32946df947f002143a964ec440628715` | The source-level contracts and call paths discussed below. |
| **Reported bounded live confirmation** | `5af403b53fbf40c2be4bfc9250d70973c77783b5` | Only what the published findings report about the private executions. |
| **Reported isolated-trial adoption** | `9cb6aa047ddb30f216aa097cd0f21dd90b0a81e8` | Adoption is reported, not independently observed here. GitHub’s comparison confirms that the intervening commit changes only packaging, its regression test, and setup documentation. |

The [historical-source comparison](https://github.com/Wenjun-Mao/Letta-Open-ADE/compare/5af403b53fbf40c2be4bfc9250d70973c77783b5...9cb6aa047ddb30f216aa097cd0f21dd90b0a81e8) supports the unchanged-runtime-file claim across that packaging correction. It does not prove what was running. The [mainline integration finding, “Verification” and “Hosted CI Follow-Up”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/findings/mainline-integration-2026-09-30.md) explicitly separates later source and integration checks from live provider execution and runtime adoption. I preserve that limitation.

### What the reported results support

The [final live-confirmation section](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/hands-on-feedback.md#live-attribution-confirmation-and-trial-adoption-2026-09-29) reports three useful source-faithful replies with no fact changes, and one correctly grounded preference write accompanied by an unsupported personal anecdote. Its fixed-candidate reviewer calls demonstrate a bounded distinction between speaker errors and merely unsupported details.

They do **not** establish a measured improvement over the original trial. The original interactions and later seeded fixtures are different contexts, not matched pre/post executions. The unavailable original reviewer JSON also prevents attributing the earlier acceptance to a particular reviewer rationale.

My independent reading agrees with [ADR 0047, “Decision” and “Alternatives And Guardrails”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/adr/0047-recalled-dialogue-attribution.md): preserve attribution, do not change ranking on this evidence, and do not silently redefine unsupported content as a grounded contradiction. The additional issue I would foreground is **what happens when generated dialogue itself is later recalled**.

## 2. A smaller contract: distinguish speech acts and their authority, not six new memory types

The distinctions in the assignment are useful as an **acceptance rubric**, but they do not justify corresponding schemas or subsystems.

A compact governing principle is:

> **Xiaotang may be creative in expression. Claims about what was previously said, believed, done, or experienced must preserve the relevant source and scope. Authored fictional biography is a separate source of character knowledge—not user history.**

One question remains open: **may newly improvised self-events extend that fictional biography?**

| Kind of expression | Boundary | Natural Mandarin contrast |
|---|---|---|
| **Authored biography** | The bound persona authorizes its fictional background. It does not establish user participation. | “小时候跟外婆学过做桂花糖藕。” is supported by the persona. “你以前来外婆店里吃过。” is not. |
| **Improvised personal episode** | **Unresolved product choice.** Decide whether it is permitted fictional improvisation, explicitly imagined material, or disallowed autobiography. | “我昨天关花店的时候也在听她。” introduces a new past event. “她的声音让我想到雨天快打烊的小店。” need not assert one. |
| **Present opinion, emotion, metaphor** | Normally legitimate character expression; it need not have appeared in history. | “我挺喜欢你说的那股安静的倔强。” / “这只杯子算是转行成功了。” |
| **Tentative inference** | Identify it as a present interpretation, not remembered testimony. Its uncertainty must survive any memory interpretation. | “听起来你最近听她挺多，是特别喜欢这种声音吗？” differs from “你一直就最喜欢这种声音。” |
| **User history** | Preserve speaker, expressed meaning, uncertainty, and time. Historical testimony is not automatically a current fact. | “你说杯子做坏了，后来改成了放钥匙的小碟。” does not establish why, how, or where. |
| **Shared experience** | The dialogue can establish a shared conversation or collaborative activity actually present in it—not physical participation or unrecorded joint decisions. | “我们聊过你把杯子改成钥匙碟的事。” can be faithful. “我们一起想出了这个办法。” is not supported when the user had already done it before telling Xiaotang. |

The biography example comes from [`personas.jsonl`, `chat_linxiaotang`, `<identity>`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/content/personas/personas.jsonl#L1). The existing character, subject, version, and archive boundaries remain those of [PC-03/04/10](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/product-contract.md).

Two qualifications matter.

**Warm familiarity is not itself fabricated history.** “那也挺好呀，周末不用赶时间。” can be warm without claiming an established relationship. Conversely, “你这个习惯还是没变” implies prior knowledge without using any obvious memory keyword. Evaluation must examine meaning, not trigger phrases.

**Hedging is not a universal repair.** “你上次可能是舍不得扔吧” still introduces an unsupported account of the past. A genuinely present interpretation—“做坏了还能换个用途，听着倒挺有意思”—does not require inventing that motive.

## 3. Consequential findings

### A. “No memory changes” needs to mean “no fact changes,” not “no future memory effect”

**Source observation.** `commit_natural_memory_review` returns without advancing fact state when there are no operations. But `RunFinalizer.commit_success` still appends `result.assistant_text` inside the successful transaction. The historical reader subsequently considers completed user–assistant exchanges within the subject/character boundary, including archived conversations. See [`natural_memory_commit.py`, `commit_natural_memory_review`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_commit.py), [`worker_finalization.py`, `RunFinalizer.commit_success`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py), and [`persistence/history.py`, `read_history_corpus`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py).

**Inference—not an observed later failure.** Consider this sequence:

> Xiaotang: “我昨天在花店收拾东西时，也循环听了她好几遍。”  
> No typed fact is written.  
> A later chat receives that assistant message as valid historical evidence.

That source genuinely establishes **that Xiaotang said those words**. It does not independently establish that the narrated event occurred, was authorized character canon, or involved the user.

A subsequent “我们那天一起听她的时候……” would be a second, different failure: converting an assistant-authored episode into shared experience.

**Smallest correction.** Tighten the interpretation of the evidence and the reporting vocabulary first:

> Historical assistant text establishes prior dialogue. It does not independently establish user testimony, user participation, or the truth of every event narrated in that dialogue.

This clarifies PC-03 and attributed-source use; it does not require deleting assistant history, adding an episode store, or making every reply announce provenance. The next informative step is a short cross-chat continuation test, described below.

### B. The reviewer boundary is coherent, but “accepted” must not be read as “faithful”

**Source observation.** `HISTORY_REVIEWER_INSTRUCTION` expressly distinguishes positive source conflict from missing support. `natural_review_request` supplies the current user message, admitted context, fact/identity handles, candidate reply, and optionally H history. It does **not** supply the persona biography or base character template. [`natural_memory_reviewer.py`, `NATURAL_REVIEWER_SYSTEM`, `HISTORY_REVIEWER_INSTRUCTION`, and `natural_review_request`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py).

Thus, for the supplied pottery source:

> “你把它放在门口了。”

is unsupported, but its acceptance is consistent with the narrow reviewer contract when no supplied evidence contradicts the placement. The generator has still violated faithful recollection.

The opposite control is equally important:

> “我觉得放门口挺方便，出门就能拿钥匙。”

should not be rejected simply because no historical source says the dish was there.

**Source observation.** `_validate_conflict` validates quoted spans and admitted references; it does not independently determine whether their meanings conflict. `prepare_natural_memory_review` rejects the whole decision when a validly bound conflict is present, including otherwise valid sibling writes. [`natural_memory_policy.py`, `_validate_conflict` and `prepare_natural_memory_review`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py).

**Consequence.** Reviewer false positives can suppress a good reply **and** a valid current preference update. The relevant quality objective is not simply “reject more bad-looking text.”

**Smallest correction.** No runtime expansion is warranted yet. Describe the reviewer outcome as “no detected conflict under the current mandate,” not “grounded answer.”

A requirement to reject all unsupported autobiographical or recalled events would explicitly change ADR 0047’s review scope. Distinguishing authorized biography from invented autobiography would also require supplying that authority to the reviewer. That could remain one reviewer, but it is still additional responsibility and input—not a free prompt clarification.

### C. The write evidence leaves two important questions open

#### Listening behavior is not automatically preference

**Maintainer-reported result.** The earlier hands-on memo says `最近常听陈粒` became a music-preference fact and flags this as a semantic concern despite a valid citation. That is separate from both speaker attribution and the later personal anecdote. See [“Director-Run Trial,” “One-off story” and “Next Investigation”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/hands-on-feedback.md#director-run-trial-2026-09-29).

Concrete controls should include:

> “最近每天都在听 Mira，给朋友剪视频挑配乐而已。”  
> **Do not manufacture a preference.**

> “别的歌都不想放，就想听她这种唱法。”  
> **A preference can be expressed without the word ‘喜欢’.**

This is model-owned semantic interpretation under PC-05, not a reason for a keyword rule under PC-06.

**Smallest correction, only if reproduced.** Generalize the existing reviewer distinction between habit and preference rather than adding a singer-specific rule. Where the registry cannot represent the supported relation, no-change or deferral is preferable to silently changing its meaning. New fact types remain a separate product decision.

#### The endorsement fixture is stronger than everyday elliptical agreement

**Source observation.** The `later_user_endorsement` fixture repeats the relevant quality and explicitly states liking it. Its scripted write uses `mode: "direct"`. The test verifies that this current assertion can write without promoting H into authority. It does not demonstrate handling of a reply such as:

> “对，就是那股劲儿，太对我胃口了。”

See [`attribution_contrasts.json`, `later_user_endorsement`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/fixtures/history_recall/attribution_contrasts.json) and [`test_attribution_contract.py`, `test_explicit_current_endorsement_can_write_without_promoting_h_to_authority`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/tests/test_attribution_contract.py).

The implementation distinguishes local U/A support from read-only H history: `_bind_evidence` resolves support through the local message map, not the H map. [`natural_memory_binding.py`, `build_natural_binding_map`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py) and [`natural_memory_policy.py`, `_bind_evidence`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py).

**Inference.** There is a worthwhile representability question: can a current, ordinary endorsement be interpreted accurately when its referent is in H, without incorrectly representing H as authorized write support? The existing fixture cannot answer it.

**Smallest correction.** Test it before changing anything. A clarification or deferral can be structurally honest yet conversationally undesirable. Allowing additional H-backed write support would change the technical evidence contract and should be named as such—not smuggled in under “natural conversation.”

### D. The combined prompt has competing incentives, but the causal diagnosis is unproven

The generation path actually combines the bound prompt and persona with `MEMORY_CONTROL_INSTRUCTIONS`; the history path appends attributed evidence. The runtime reads the conversation’s bound definition rather than simply executing the latest seed text. [`natural_context.py`, `build_natural_context`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_context.py), [`history_admission.py`, `_context_with_history`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/history_admission.py), and [`turn_execution.py`, `TurnExecution.execute`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py).

Three tensions merit attention:

**Literal identity versus conversational performance.** The template calls Xiaotang an ADE-managed conversational agent, then demands literal human identity and complete immersion. The persona’s flower-shop biography supplies plausible material for self-disclosure. This creates an opportunity for autobiographical improvisation, but it does not prove that the literal-human wording caused the observed anecdote. [`chat_v20260926.py`, `PROMPT`, `<style>`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/content/prompts/system/chat/chat_v20260926.py).

**Broad memory promises versus the actual channels.** The persona promises to remember preferences, emotions, and recurring small details. Runtime instructions correctly prohibit unsupported future-contact promises, but also tie some “ask next time” language to committed durable facts. Historical dialogue is another continuity channel, so **“not a saved fact” should not become “cannot be remembered in conversation.”** [`context.py`, `MEMORY_CONTROL_INSTRUCTIONS`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/context.py).

For example, “等你下次想聊的时候，我们再接着说” need not promise autonomous contact or guaranteed recall. It should not automatically be replaced by a mechanical explanation of memory storage.

**Repeated operational instructions versus character style.** The template and runtime both describe reviewer timing, memory-search limitations, and dialogue-only output. Repetition is not demonstrated to be harmful here, but adding another long taxonomy would make ownership less clear.

**Smallest correction.** Do not add more rules now. During a later versioned prompt revision, keep operational memory policy in its shared runtime owner and keep the persona focused on biography and voice. Replace overlapping instructions rather than accumulating them. Preserve uncertainty, Mandarin dialogue, ordinary opinions, metaphor, and comfortable short acknowledgments.

A falsifiable hypothesis is:

> Literal-human wording increases ungrounded self-episodes, beyond what is caused by the biography and ordinary conversational pressure to reciprocate with a personal story.

Competing explanations include an unresolved fiction permission, empathy-through-self-disclosure behavior, and general narrative elaboration. The experiment below separates these.

## 4. Small, discriminating experiments

These are proposed experiments, **not authorization to execute them**. They should be staged; there is no reason to run the entire program immediately.

### First: make the unresolved product judgment without model calls

Have the product owner classify a few hand-written contrasts from Section 2, especially:

> “我昨天在花店也听了一下午。”  
> “她的声音让我想到雨天的小花店。”  
> “要是写成一个小故事，我会让她在关店时放这首歌。”

Decide whether the first is allowed, and whether an allowed invented episode becomes continuing character canon.

Three coherent choices exist: biography-bounded autobiography; explicitly framed imagination; or improvisational fictional life. The third creates more continuity obligations. None is selected by the current evidence. Repeatedly labeling all three “hallucination” would hide the decision rather than resolve it.

### Experiment 1 — Eight Mandarin target turns on the current design

Use four contrast pairs, independent synthetic subjects, first-pass outputs, and verified admitted packets. Keep model settings, persona, runtime policy, and history selection fixed within each pair.

| Pair | Competing explanations and control | Observable outcome and consequence |
|---|---|---|
| **Speaker attribution** | Put the same opinion in an assistant source versus a user source; ask what each person said. | Failure despite correct roles points to source interpretation, not missing retrieval. A present Xiaotang opinion remains allowed. |
| **Recollection versus suggestion** | Supply the cup-to-dish story without placement. Ask where it was put versus where it could go now. | Unknown past placement should not be invented; a useful new suggestion should remain natural. Failure only in the first condition identifies narrative overreach without demanding less creativity generally. |
| **Behavior versus preference** | Contrast listening for a task with a clearly expressed preference, including an implicit preference without “喜欢.” | Expect no manufactured preference in the first and the supported update in the second. This tests semantics rather than vocabulary. |
| **Full versus elliptical endorsement** | Same attributed singer discussion; compare a fully restated endorsement with “对，就是那股劲儿，太对我胃口了。” | Inspect the proposed value, evidence mode, and any deferral. A discrepancy motivates the authority/representation question, not an immediate schema change. |

For the endorsement pair, predeclare the admissible interpretation of the current assertion. Do not invent the oracle after seeing whether the model writes. If only the elliptical case fails, one additional local-A version can distinguish an H-support boundary from general difficulty resolving the phrase.

Reuse suitable packets for **four fixed-candidate reviewer controls**: faithful attribution, false attribution, an unsupported asserted placement, and an explicitly creative present response. Under the current narrow contract, the unsupported placement need not produce a conflict; its generation-faithfulness label should still fail. That separation is the point.

If these cases behave correctly, stop adding attribution instructions. Eight turns are a diagnostic screen, not a reliability estimate.

### Experiment 2 — A four-turn test of whether old assistant dialogue gains unwarranted authority

Run this when a problematic self-episode exists or when evaluating a deliberately seeded synthetic one.

Use matched prior exchanges: one contains an explicitly imagined scene; the other narrates the same scene as personal history. In fresh same-character chats, first ask a neutral recall question, then ask who experienced it or whether it was an example.

Include a faithful conversational-recollection control:

> “我们上次聊过那只改成钥匙碟的杯子。”

Verify that the intended old exchange actually enters the packet. This initially isolates source use from ranking.

**Competing explanations:** the model may preserve “what was said,” treat any previous assistant narration as established biography, or mistakenly transfer the episode to the user/shared relationship.

**Decision:** if it preserves the source and fictional status, the feared feedback problem is not demonstrated in this test. If it converts assistant narration into user/shared experience despite intact attribution, prioritize that narrow generation boundary. Neither outcome justifies an episode store by itself.

A self-episode’s continued use is not automatically failure under an explicitly chosen improvisational-fiction contract. Transfer of authorship or participation still is.

### Experiment 3 — Conditional causal ablation of literal-human wording

Run this only after the product decides that the relevant self-episodes are undesirable.

Use a small **2×2 design**:

- Literal-human claim retained versus replaced by a role-performance framing, while retaining persona and immersive style.
- Current autobiography boundary versus the chosen explicit boundary.

Use three Mandarin prompts: an ordinary short personal update, a direct request for a similar personal experience, and an explicit invitation to imagine a scene. That is **12 target turns**, not necessarily 12 provider requests.

Hold other settings and supplied context constant. Use separately bound immutable definitions and record effective source/prompt identities; changing a seed file is not evidence that an existing conversation used the new condition.

Interpret the results prospectively:

- Fewer self-episodes after only the identity change, with preserved warmth, supports the identity-wording hypothesis.
- Improvement from the explicit boundary under both identity framings supports contract ambiguity instead.
- Failures concentrated in direct self-experience questions support conversational self-disclosure pressure.
- Loss of metaphor, personality, or ordinary empathy identifies an overrestrictive candidate—not an unavoidable cost of trustworthy memory.

One pass per cell is a screen. A small prespecified replication of an apparent difference should precede adopting a causal conclusion; misses must remain in the record.

### Score four separate outputs

| Dimension | What to inspect |
|---|---|
| **Reply faithfulness** | Speaker, temporal scope, uncertainty, supported past events, and implied participation. Mark unresolved self-fiction separately rather than silently passing or failing it. |
| **Conversational quality** | Natural Mandarin, proportionate length, warmth, useful specificity, question rhythm, and preservation of legitimate creative expression. |
| **Reviewer behavior** | Actual decisions, false conflicts, missed in-scope conflicts, deferrals, and evidence bindings. Do not infer an empty decision array from zero writes. |
| **Complete memory delta** | Added/changed facts, values, qualifiers, owners, statuses, versions, revisions, source roles/spans, new entities, and memory-generation movement. Also record reply persistence separately. |

Count failed or rejected turns as outcomes. A rejected good reply with no writes is not equivalent to a successful checked no-change. Likewise, a charming answer with no fact mutation can still corrupt recalled history.

## 5. What should remain unchanged—and what needs human judgment

**Keep PC-03/04/05/06/09/10 intact.** Preserve subject and definition-root boundaries, archived-history eligibility, immutable versions, model-owned interpretation, ADE-owned structural validation, and atomic persistence. Keep H history from independently authorizing fact writes. Retain assistant messages: they are necessary evidence for whose opinion or suggestion was expressed. Do not add keyword heuristics, privacy/no-save policy, a second reviewer, a separate memory service, or speculative episode storage. These exclusions are explicit in the [product contract](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/product-contract.md).

The human choices are narrower than an architectural redesign:

**Whether Xiaotang may invent a private fictional life, whether those inventions become canon, and how much everyday self-disclosure feels desirable.** Those are character-product choices. The source does not settle them.

**Whether the product requires rejection of every unsupported past-event claim.** That would broaden the current reviewer mandate and requires explicit treatment of authorized fiction, partial evidence, and false positives.

**Whether natural elliptical endorsement must always produce a fact update when the referent exists only in H.** That needs a declared evidence interpretation; neither silently promoting H nor unnecessarily demanding full restatement is a satisfactory accidental policy.

Keeping the current design while deferring autobiography tuning is defensible. What is not defensible is treating the reviewer’s narrow acceptance as a general faithfulness certificate—or treating every expressive first-person sentence as a memory failure.

## Inspected-file inventory

All files below were inspected at **`2e3322db32946df947f002143a964ec440628715`**.

**Contract, character, and findings:**  
`docs/product-contract.md`; `content/prompts/system/chat/chat_v20260926.py`; `content/personas/personas.jsonl` **only the `chat_linxiaotang` entry**; `docs/adr/0047-recalled-dialogue-attribution.md`; `workflows/evals/character_memory_dev/hands-on-feedback.md`, including its complete final live-confirmation section; `docs/findings/mainline-integration-2026-09-30.md`.

**Fixtures and tests:**  
`workflows/evals/character_memory_dev/fixtures/history_recall/attribution_contrasts.json`; `workflows/evals/character_memory_dev/tests/test_attribution_contract.py`.

**Runtime files under `services/ade-api/src/ade_api/features/agent_runtime/`:**  
`README.md`; `context.py`; `natural_context.py`; `natural_memory_reviewer.py`; `natural_memory_policy.py`; `natural_memory_binding.py`; `history_admission.py`; `turn_execution.py`; `turn_history_setup.py`; `turn_memory_snapshot.py`; `natural_memory_commit.py`; `worker_finalization.py`; `persistence/history.py`; and **`worker.py`, lines 1–240 only**.

I also inspected the runtime directory listing and GitHub comparison metadata for the two historical revision transitions; I did not audit every changed file in those comparisons.

**Bottom line:** preserve the architecture, clarify what newly authored self-fiction is allowed to become, and test Mandarin source use and exact write meaning separately. The smallest useful improvement is a sharper acceptance contract—not a larger mechanism.