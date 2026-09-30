## What changes the next decision

**Keep the current architecture. The next decision is not whether Xiaotang should be warm or factual; it is whether she may create new personal episodes, and what authority those episodes acquire when recalled later.** The evidence does not justify another reviewer, a new memory store, a retrieval redesign, or a general unsupported-claim veto.

Three distinctions matter most.

**“No fact changes” does not mean “no memory-trust consequence.”** ADE persists an accepted assistant reply as dialogue, and the experimental history path can later supply assistant dialogue as evidence. An invented anecdote can therefore remain outside the profile-fact store while becoming available for future recollection. That is a potential propagation path, not an observed downstream failure in the supplied evidence. The existing transaction and history-admission code make the distinction consequential. [Source: `worker_finalization.py`, `RunFinalizer.commit_success`; `history_admission.py`, `_context_with_history`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py) · [history-admission permalink](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/history_admission.py).

**The anecdote is not yet an adjudicated product failure of the same kind as false user attribution.** An unsupported claim about what the user previously did violates the stated recollection contract. An invented, character-only listening anecdote also lacks historical support, but its permissibility depends on an unresolved fiction policy. Calling both “hallucinations” can conceal the decision rather than resolve it.

**The reviewer’s boundary is narrower—and more source-channel-dependent—than “checks conversational memory.”** It does not receive the persona biography, and its conflict schema can cite held facts/entities or historical H messages, but not recent U/A messages directly. Its endorsement support also distinguishes recent assistant messages from historical assistant messages. These are useful experimental targets before adding more prose to the prompts. [Source: `natural_memory_reviewer.py`, `natural_review_request`; `natural_memory_review.py`, `NaturalConflict`, `EndorseAssistantEvidence`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/features/agent_runtime/natural_memory_reviewer.py) — corrected source location: [reviewer](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py), [schema](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py).

My recommendation is to clarify the permissible fiction first, then test a few matched Mandarin cases. Do not treat generic immersion instructions as having already settled whether the character may establish new autobiographical events.

## Evidence boundary and reviewed revision

The pinned GitHub source was accessible. **The reviewed revision is `2e3322db32946df947f002143a964ec440628715`.** I inspected the files listed at the end, including the implementation rather than only the explanatory documents.

| Boundary | Revision and what it establishes |
|---|---|
| **Source inspected in this review** | `2e3322db32946df947f002143a964ec440628715`. Static implementation, prompts, fixtures, tests and documentation. |
| **Reported four-turn confirmation and eight reviewer-only calls** | `5af403b53fbf40c2be4bfc9250d70973c77783b5`. Maintainer-reported observations from private receipts—not independently replayed or inspected here. |
| **Reported isolated-trial adoption** | `9cb6aa047ddb30f216aa097cd0f21dd90b0a81e8`. The memo reports unchanged tested instructions and a packaging correction. It also says no trial turn was sent during adoption. |
| **Later mainline integration** | The integration memo reports formatting, portable-test, OpenAPI and CI corrections, with no live provider calls or runtime adoption as part of that integration. These are not another character-memory trial. |

These distinctions follow the [final live-confirmation/adoption section](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/hands-on-feedback.md#live-attribution-confirmation-and-trial-adoption-2026-09-29) and [mainline integration findings](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/findings/mainline-integration-2026-09-30.md).

I made no repository changes, provider calls, native trial turns, or live-database checks. The private original requests and reviewer decisions are unavailable to this review. In particular, I cannot independently judge the precise wording or conversational quality of the reported listening anecdote.

## 1. A smaller contract: three domains, not seven subsystems

The requested distinctions are useful as **claim-level evaluation categories**, but they do not require seven runtime categories, new tables, or a taxonomy the character must announce.

A smaller model is:

1. **Authored character canon:** what the product author establishes about Xiaotang.
2. **Actual interaction evidence:** what this user and this character said, endorsed, or experienced through their conversations.
3. **Present creative expression:** opinions, emotional responses, metaphors, suggestions and explicitly hypothetical possibilities.

The unresolved category is **new autobiographical episodes**. They are not automatically licensed by any of those three domains.

The following Mandarin examples are illustrative contrasts I authored, not quotations from private trial outputs.

| Claim type | Appropriate boundary | Natural contrast |
|---|---|---|
| **Authored biography** | May be spoken naturally as in-world character biography. It does not establish contact with this user. | Allowed by the supplied persona: “我小时候跟外婆学过做桂花糖藕。” Not licensed by that biography: “上次你来外婆店里，还夸过她做的糖藕。” |
| **Improvised personal episode** | Requires a product decision about whether the character can establish new off-screen history. Compatibility with the biography is not the same as authorization. | “昨晚花店关门后，我一个人循环听了她好几遍。” This could be permitted character fiction, or an unwanted false autobiographical claim. The existing agreement does not settle which. |
| **Present opinion or creative expression** | May be newly expressed without pretending it was previously held, spoken, or based on an actual listening event. | “我也挺喜欢那种不张扬的劲儿。” A metaphorical control: “你这算是给杯子换了份工作呀。” Neither requires an invented episode. |
| **Tentative inference** | May be offered as an inference, with proportionate uncertainty. A hedge must not disguise a claim of remembered evidence. | “是不是觉得还能派上用场，就留下了？” is a question about motive. “我隐约记得你是舍不得扔” still claims a memory and needs support. |
| **User history and endorsement** | Preserve content, speaker, time, uncertainty and the difference between agreement and authorship. | “那句‘不张扬的倔劲’是我当时说的，你现在也认同。” Not: “你当时就这么形容她。” |
| **Shared experience** | Conversation itself can be a real shared experience. Physical co-presence or joint activity must not be invented. | “我们之前聊过那只杯子。” Not: “上次我们一起做陶艺的时候……” |

The biography control comes directly from the `chat_linxiaotang` entry: Suzhou upbringing, learning sweets from her grandmother, visual-communication studies, flower-shop work and design work. It contains no supplied Mira listening episode. [Source: `content/personas/personas.jsonl`, `chat_linxiaotang`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/content/personas/personas.jsonl#L1).

**A warm response need not borrow authority from a fabricated past.** For the pottery example:

> 那只杯子后来被你改成装钥匙的小碟子了。没做成杯子，倒也没白忙。

That combines faithful recall with a new evaluative response. It does not need a motive, a construction method, a location, or a disclosure about databases.

Conversely:

> 要是门口有空位，可以放那儿，出门拿钥匙顺手。

is a new suggestion, not remembered placement. Those should remain legitimate creative-expression controls, not merely exceptions tolerated by a strict memory policy.

### The human choice that remains

There are two coherent products here.

**An authored character companion** can have supplied biography and spontaneous present expression, without generating unestablished past episodes.

**An improvisational fictional character** can also create solo episodes. But then the product must decide whether users should expect those episodes to remain stable across conversations, and whether later elaboration is allowed.

Neither choice requires an episode store now. The second does, however, introduce a continuity obligation. “It was only flavor text” becomes an inadequate explanation when the user later asks about that episode.

My provisional preference is the first boundary until the second is deliberately chosen—not because fiction is inherently untrustworthy, but because it avoids silently expanding what the product promises to remember.

## 2. Source findings and their smallest corrections

### A. The combined prompt supplies competing incentives, not proof of a cause

**Source observation.** The generation assembly concatenates the bound system prompt, persona and `MEMORY_CONTROL_INSTRUCTIONS`. The base template requests complete immersion and contains the literal-real-person wording. The persona asks for natural, relatively concise conversation and says it will remember preferences, emotions and recurring details. Runtime instructions separately constrain memory claims, attribution, currentness, future check-ins and faithful recollection. [Sources: `natural_context.py`, `build_natural_context`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_context.py); [`chat_v20260926.py`, `PROMPT`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/content/prompts/system/chat/chat_v20260926.py); [`context.py`, `MEMORY_CONTROL_INSTRUCTIONS`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/context.py).

These instructions are not logically impossible to satisfy together: an immersive character can still recall dialogue faithfully. But they leave “behave like this person” underspecified when the conversationally convenient move is a personal anecdote.

**Falsifiable hypothesis:** the literal-real-person sentence increases newly asserted personal episodes relative to an otherwise identical prompt without that sentence. Competing explanations are that the permission boundary is unclear regardless of that sentence, that reciprocal questions invite autobiographical completion, or that the model generally elaborates too much.

The reported one-off anecdote does not distinguish these explanations.

**Smallest correction, conditional on testing:** replace the literal identity assertion with a style instruction rather than removing the persona. Separately test a short episode boundary. Do not combine those changes and then credit the result to removing “real person.”

There are also simplification opportunities, but no evidence that prompt deduplication itself will improve quality. The template and runtime repeat memory-persistence, tool-scope and dialogue-only guidance. The persona’s broad remembering promise is less precise than the runtime’s supported behavior. A future cleanup could assign **voice and biography to the persona, operational memory authority to runtime instructions**. I would not spend a separate cycle rewriting all of it now.

### B. The reviewer cannot decide whether a new anecdote is licensed biography

**Source observation.** `natural_review_request` supplies the current user message, recent source messages, held facts/entities, candidate reply, allowed fact contracts and optional H history. It does not supply the bound persona biography or base template. [Source: `natural_memory_reviewer.py`, `natural_review_request`; `natural_memory_binding.py`, `NaturalBindingMap.packet`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py) · [packet permalink](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py).

**Counterexample:** “外婆以前教我做桂花糖藕” is supported by the authored persona. “昨天外婆陪我听了Mira的新歌” is not. With neither proposition in H history, the reviewer lacks the canonical biography needed to distinguish them on that basis.

**Smallest correction now:** describe reviewer approval accurately: it means no rejecting conflict was returned under its supplied evidence and contract—not that every sentence was historically grounded or persona-canonical.

Giving the reviewer biography and responsibility for episode licensing would be an explicit responsibility/context expansion. It is not merely another sentence explaining its existing duty. I do not recommend that expansion before the product chooses the episode policy.

### C. Two source-channel boundaries deserve tests before more prompt rules

#### Recent dialogue cannot directly ground the same conflict that H dialogue can

**Source observation.** `NaturalConflict` requires F/E references or H evidence. Recent sources have U/A handles, but those are not accepted conflict-grounding handles. [Source: `natural_memory_review.py`, `SnapshotReference`, `HistoricalConflictEvidence`, `NaturalConflict._grounding_contract`; `natural_memory_policy.py`, `_validate_conflict`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py) · [validation permalink](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py).

**Counterexample:** supply only a recent U1 listening report and A1 singer description, no held facts and no H packet. The candidate says:

> 你刚才说，她唱歌有一种不张扬的倔劲。

The false attribution is visible in recent context, but there is no legitimate U/A-grounded conflict representation. Putting the same exchange into H creates such a representation.

This is a **source-observed coverage limit**, not evidence that this failure occurred live.

**Smallest correction now:** add the matched source-channel test and state the coverage limit. Only if same-chat attribution errors are a material problem should ADE consider extending the existing conflict schema to read-only U/A grounding. That would change the current conflict schema/scope, while preserving PC-05’s model-owned interpretation and ADE-owned structural enforcement.

#### “H cannot independently authorize a write” is not identical to “H cannot support a current endorsement”

The broader product framing forbids independent historical authorization. The reviewer instruction is stricter: H is never write support, and `EndorseAssistantEvidence` accepts only A handles. [Source: `natural_memory_reviewer.py`, `HISTORY_REVIEWER_INSTRUCTION`; `natural_memory_review.py`, `EndorseAssistantEvidence`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py) · [evidence schema](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py).

**Counterexample:**

> 我也喜欢你说的那种劲儿。

A current, explicit expression of liking can still need earlier text to identify its object. The same words can refer to an eligible recent A proposition or an H proposition.

The existing endorsement fixture avoids this ambiguity by restating the preference and using `direct` evidence. It therefore does not qualify ordinary elliptical Mandarin endorsement. [Source: attribution fixture, `later_user_endorsement`; test, `test_explicit_current_endorsement_can_write_without_promoting_h_to_authority`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/fixtures/history_recall/attribution_contrasts.json) · [test permalink](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/tests/test_attribution_contract.py).

**Smallest correction now:** test this contrast and document the intended outcome. Do not quietly use a `direct` quote to conceal reliance on disallowed support. Allowing H as explicit supporting evidence for a currently authorized endorsement would amend the present H contract; it should not arrive disguised as a prompt clarification.

### D. Broad rejection would trade one error class for another

**Source observation.** `prepare_natural_memory_review` validates conflicts before preparing writes, and a valid conflict rejects the attempt. `RunFinalizer.commit_success` places memory changes and the assistant message inside the same transaction. [Sources: `natural_memory_policy.py`, `prepare_natural_memory_review`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py); [`worker_finalization.py`, `RunFinalizer.commit_success`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py).

**Counterexample:** the current user clearly endorses a music preference; the reply acknowledges it correctly but adds an unlicensed self-anecdote. A new broad rejection rule could block both the anecdote and the desired factual update for that attempt.

That does not make broader rejection wrong. It means the decision must measure **lost useful updates, blocked dialogue and recovery behavior**, not just removed embellishments.

**Smallest correction now:** retain the narrow conflict meaning. Score unsupported historical assertions separately from positive contradictions. A new unsupported-claim veto would explicitly expand ADR 0047’s reviewer mandate; it is not justified by the present sample.

## 3. What the evidence supports—and what it does not

ADR 0047 largely agrees with the implementation-level interpretation above: preserve attribution and scope; do not remove assistant history; do not fabricate contradiction citations for unsupported additions; keep generation responsible for faithful narration. [Source: ADR 0047, “Decision” and “Alternatives And Guardrails”](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/adr/0047-recalled-dialogue-attribution.md).

The **maintainer-reported** four native turns show useful behavior is possible under the bounded clarification: three relevant controls behaved appropriately, and the fourth produced the intended preference update while exposing the unresolved anecdote issue. The eight fixed-candidate reviews support the reported narrow distinction between attribution errors and unsupported additions. They do not establish comparative improvement, a failure rate, natural Mandarin reliability, or the causal role of the identity wording. [Source: final live-confirmation section](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/hands-on-feedback.md#live-attribution-confirmation-and-trial-adoption-2026-09-29).

Two limitations deserve particular attention.

First, the inspected packet test uses a generic system prompt and generic companion persona. It checks attribution instructions and identical H packets across A/A0/B; it does not exercise the combined Xiaotang template/persona incentives. The scripted empty-decision test deliberately accepts both faithful and unfaithful candidates, demonstrating the absence of an ADE semantic veto—not answer quality. [Source: `test_shared_generation_and_h_review_preserve_attributed_sources`; `test_scripted_no_change_is_not_replaced_by_an_ade_semantic_veto`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/tests/test_attribution_contract.py).

Second, the feedback memo separately reports habitual listening being saved as a preference. That is not an attribution problem and should not be absorbed into the persona-anecdote diagnosis. The reviewer currently cautions against inferring preference from a **drinking habit**; a general behavior-versus-preference contrast would be more informative than adding a singer-specific warning. [Sources: feedback memo, “Director-Run Trial”; reviewer, `NATURAL_REVIEWER_SYSTEM`](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/workflows/evals/character_memory_dev/hands-on-feedback.md) · [reviewer permalink](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py).

A citation can faithfully bind “最近一直在听” while the saved interpretation “喜欢” is wrong. More attribution rules would not solve that semantic mistake.

## 4. The smallest discriminating experiments

These are proposals, not authorization to execute them. I would stage them rather than launch a broad benchmark.

### Experiment 1: Resolve the fiction boundary without any model calls

Prepare **six matched pairs of short Mandarin replies** covering authored biography, present opinion, new solo anecdote, faithful recollection, new suggestion and invented shared activity. Keep warmth and length reasonably matched; do not compare a lively fabrication with a deliberately mechanical faithful answer.

Ask product owners or a few intended Mandarin-speaking users to judge two things separately:

- Is the statement acceptable for Xiaotang?
- Would they expect it to describe an established event and remain consistent in another chat?

**Competing explanations:** people may value solo anecdotes as expected fiction; they may interpret them as claimed personal history; or the apparent value may come from warmth that an equally natural non-episodic reply also supplies.

**What changes my conclusion:** a consistent preference for improvisational episodes, accompanied by clear expectations about their fictional status and continuity, would support permitting them. Comparable warmth without episodes would support the narrower default. Disagreement means the product decision remains unresolved; it is not a reason to add enforcement machinery.

### Experiment 2: Diagnose reviewer authority with fixed Mandarin packets

Use **12 fixed-candidate packets in six matched pairs**, without database writes. This avoids mixing generation variability with reviewer interpretation.

| Pair | Controlled contrast | Observable result and decision value |
|---|---|---|
| Speaker attribution | Faithful versus false attribution of the same H assistant opinion | Tests narrow semantic recognition while preserving an accepted control. |
| Source channel | Same H proposition versus recent A proposition, with the same elliptical current endorsement | Reveals defer, explicit support, or inappropriate `direct` handling; informs the H-support contract decision. |
| Unsupported versus contradicted past | Same claimed placement, with a source silent about placement versus a source explicitly saying it was elsewhere | Tests whether the reviewer preserves the distinction rather than manufacturing a conflict. |
| Agreement versus preference | “她确实有那股劲儿” versus “我很喜欢她那股劲儿” | Tests whether evaluative agreement is incorrectly converted into personal taste. |
| Behavior versus preference | Listening for a work task versus explicitly enjoying the music | Tests the separate semantic-write concern without a drinking-specific cue. |
| Creative expression versus episode | A faithful metaphor/new opinion versus a supported current update plus a new solo anecdote | Tests over-rejection of legitimate creativity and makes the current scope limitation visible. |

For the recent-dialogue attribution gap identified above, a **scripted schema check** is sufficient initially to demonstrate the missing U/A conflict representation. Spend model calls on whether generation actually makes that error only if needed.

Retain the exact decisions and bound quotes. Give each result two labels: **correct under the current reviewer contract** and **acceptable under the chosen product contract**. Those labels need not agree.

**What changes my conclusion:** reliable narrow attribution checks with no creative-expression false positives favor retaining the reviewer. Misuse of evidence modes or preference interpretation would justify a targeted semantic clarification. Repeated product-important errors that the schema cannot represent would justify an explicit scope decision—not merely more instructions.

### Experiment 3: Test identity wording independently of episode permission

After Experiment 1 selects a provisional boundary, use a **2×2 generation comparison**:

| Factor | Current condition | Alternative |
|---|---|---|
| Literal identity sentence | Existing literal-real-person sentence | Remove or replace only that sentence with a neutral in-character style instruction. Keep the surrounding immersion guidance. |
| Episode permission | Existing unspecified boundary | Explicitly permit authored biography and present creative expression, while disallowing newly asserted personal past episodes. |

Use four Mandarin situations, once per cell: **16 target turns**, not necessarily 16 provider requests.

The situations should include ordinary brief conversation, a question answered directly by authored biography, pottery recollection, and current music endorsement followed by “你呢？” The last deliberately invites reciprocity while allowing a present opinion instead of an anecdote.

Hold the model/settings, runtime memory instructions, source history, fact state and reviewer policy fixed. Use isolated synthetic subjects and new immutable definition bindings. Verify actual admitted packets: a prompt-length change that alters history admission is a confound, not evidence about character behavior.

**Predictions distinguish explanations:**

- A consistent identity-sentence effect would support that specific wording as a contributor.
- An episode-boundary effect with little identity effect would support underspecification as the more useful diagnosis.
- Errors concentrated after “你呢？” would implicate conversational elicitation.
- Continued embellishment of user history despite the episode rule would point toward broader source-use failure rather than autobiographical permission alone.
- Reduced warmth, excessive caveats or avoidance of canonical biography would show overcorrection.

Do not reroll misses. A mixed result should lead to a small, predeclared replication or retaining the current design—not selecting a preferred anecdotal success.

If an improvised episode is allowed or still appears, add just **two continuation probes**: one in the same chat and one in a fresh same-character chat. Ask about the episode without supplying new details. Observe whether Xiaotang reports what she previously said, invents further details, or turns solo fiction into shared participation. This examines the propagation risk directly.

### Keep four outcomes separate

| Outcome | Record |
|---|---|
| **Reply faithfulness** | Speaker, time, uncertainty, unsupported event details, current-versus-past framing, and invented participation. Separate unlicensed solo fiction from false user history. |
| **Conversational quality** | Blinded Mandarin judgments of warmth, relevance, proportionate length, comfortable pauses, unnecessary questions and conspicuous memory machinery. |
| **Reviewer behavior** | Exact decisions, evidence mode, source quote/handle, supported conflicts, false positives, deferrals and protocol failures. |
| **Complete memory delta** | Before/after facts, values, statuses, entities, revisions, evidence links and generation changes—not merely fact counts. Compare candidate and delivered reply, and retain failed attempts. |

For example, a successful recall turn can have no profile-fact changes while still appending dialogue. A successful endorsement should produce the intended scoped update and nothing unrelated. A rejected mixed candidate must not be scored simply as “safe” without recording that its useful update was also blocked.

## 5. What should remain unchanged

I would preserve **PC-03/04/05/06/09/10**: character-root and subject boundaries; continuity across ordinary immutable persona versions; model-owned semantic interpretation; ADE-owned structural checks; no keyword policy subsystem; no second reviewer, episode store or speculative service; and archive eligibility without treating historical statements as current facts. These are the current agreements, not claims of general implementation qualification. [Source: product contract, settled agreements and archived conversations](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/2e3322db32946df947f002143a964ec440628715/docs/product-contract.md).

Also retain assistant dialogue, exact attribution, current-user write authority, atomic persistence, explicit failure behavior and the distinction between unsupported and contradicted. Do not require every reply to demonstrate personalization, mention a stored fact, ask a question, or narrate how memory works.

The choices requiring human judgment are **whether new solo episodes are allowed**, **what continuity users should expect from them**, and **whether the benefit of broader rejection outweighs blocked dialogue and factual updates**. Historical support for elliptical current endorsement is a separate contract decision; it should not be bundled with persona tuning.

## Files actually inspected

All entries below were read at **`2e3322db32946df947f002143a964ec440628715`**.

For compactness, `R/` means `services/ade-api/src/ade_api/features/agent_runtime/`, and `E/` means `workflows/evals/character_memory_dev/`.

| Area | Inspected files and extent |
|---|---|
| Product and character | `docs/product-contract.md`; `content/prompts/system/chat/chat_v20260926.py`; `content/personas/personas.jsonl`—specifically the complete `chat_linxiaotang` entry, not an audit of all personas. |
| Generation and admission | `R/context.py`; `R/natural_context.py`; `R/history_admission.py`—complete files. |
| Review and binding | `R/natural_memory_reviewer.py`; `R/natural_memory_policy.py`; `R/natural_memory_review.py`; `R/natural_memory_binding.py`—complete files. |
| Execution and persistence coordination | `R/turn_execution.py` and `R/README.md`—complete files; `R/worker.py`, lines 1–180; `R/worker_finalization.py`, lines 1–260, including `commit_success`. I did not audit every underlying SQL repository. |
| Fixtures and tests | `E/fixtures/history_recall/attribution_contrasts.json`; `E/tests/test_attribution_contract.py`—complete files. |
| Comparison and evidence limits | `docs/adr/0047-recalled-dialogue-attribution.md`; `E/hands-on-feedback.md`, including the final live-confirmation/adoption section; `docs/findings/mainline-integration-2026-09-30.md`. |

**Bottom line:** the existing design is worth keeping. Clarify what fiction Xiaotang may establish, test the source-channel boundaries and native Mandarin behavior, and change only the smallest instruction or contract that a discriminating result supports. The current evidence neither demands a broader memory judge nor demonstrates that believable warmth depends on invented personal history.