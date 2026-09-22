# M1 Character-Continuity Baseline Findings

Date: 2026-09-22
Status: Implementation baseline complete; native deployment qualification pending

## Director Review Follow-Up

Director review verified all ten saved transport/task validation records and
found one remaining tool-policy defect: `Do not search my memory. Find a rhyme
for cat.` still forced memory search. The capability and affirmative action
were matched across different clauses. They now must match within the same
clause; six English/Chinese regression cases cover unrelated actions.

After this correction: focused memory/tool tests **38 passed**; full Python
suite **551 passed, 5 skipped, 1 failed**. The sole failure is the unchanged
release-policy fingerprint gate, not a pytest expected-failure marker. Ruff,
formatting, and diff checks passed for the follow-up. No release approval was
rebound. Keep this implementation isolated until fresh qualification succeeds.

## Scope And Method

This is the M1 baseline for `chat_linxiaotang` (林小棠), everyday Chinese
companionship rather than scene-based roleplay. The work and completion boundary
are in the [M1 plan](../plans/m1-character-continuity-baseline.md). Inputs are
checked in under
[`workflows/evals/character_memory_dev/fixtures/m1`](../../workflows/evals/character_memory_dev/fixtures/m1).

Ten serial, one-turn Luna calls ran through the existing subscription workflow:
`gpt-5.6-luna`, medium reasoning, default tier, Codex CLI
`0.155.0-alpha.9.2`, ChatGPT login. Every call had `adapter_retry_count: 0`,
exited `0`, and recorded `transport_validated` plus valid task output. No Spark,
API key, or fallback provider was used. The calls consumed ten of the M1 maximum
of 24 sessions; none was replayed or repaired. The complete captures remain in
ignored `workflows/evals/character_memory_dev/outputs/m1-*-20260922/`
directories, including prompts, manifests, events, and validation records.

The result is a supplied-context experiment. Luna does not access ADE
persistence, native retrieval, embeddings, Qwen, or native tool protocols. A
correct reply therefore is not evidence of persisted memory or user isolation.

## Policy Defects: Reproduction And Fix

| Defect | Reproduction evidence | Durable change | Regression guardrail |
| --- | --- | --- | --- |
| Whole-message uncertainty | The former check searched every uncertainty substring in the full turn. It rejected `Mighty` because it contains `might`, and rejected a definite preference after an unrelated `Maybe ... but ...` clause. | Confidence is checked in the clause containing the uniquely bound user-evidence span. English markers use word boundaries; Chinese markers remain phrase markers. | `test_mighty_is_not_the_uncertain_word_might`, `test_definite_claim_beside_unrelated_uncertainty_is_allowed`, and `test_uncertain_evidence_claim_cannot_become_memory`. |
| Negation-insensitive tool requirement | The former rule matched raw capability/action keywords, so “Don't search your memory” forced `search_memory`. | A forced call now needs a locally affirmative matched action; direct English or Chinese opt-out negates only that action. Ambiguous language is discretionary. | `test_negated_memory_search_is_not_forced` and the two mixed-tool tests. |

The contract remains fail-closed where it matters: proposals still require a
uniquely bound user-evidence quote, supported value, subject ownership, and
optimistic fact version. Forgetting still requires explicit removal language.
The executor still cannot claim a tool call or success without a tool result.
[ADR 0021](../adr/0021-evidence-scoped-memory-and-affirmative-tools.md) records
the policy boundary and its limits.

## Observed Baseline

| Case and checked-in input | Ignored result record | Observed excerpt | Manual review and attribution |
| --- | --- | --- | --- |
| Preference recall — [`preference_recall.json`](../../workflows/evals/character_memory_dev/fixtures/m1/preference_recall.json) | `outputs/m1-preference-recall-20260922/result.json` | “回家泡一杯茉莉花茶吧……先让自己缓一缓呀。” | Pass. Relevant supplied preference is used naturally; no invented shared event. |
| Concern follow-up — [`concern_follow_up.json`](../../workflows/evals/character_memory_dev/fixtures/m1/concern_follow_up.json) | `outputs/m1-concern-follow-up-20260922/result.json` | “先慢慢吸一口气……按自己的节奏说就好。” | Pass. Short, present-tense support follows the concern without claiming to be at the building. |
| Promise/shared conversation — [`promise_shared_conversation.json`](../../workflows/evals/character_memory_dev/fixtures/m1/promise_shared_conversation.json) | `outputs/m1-promise-shared-conversation-20260922/result.json` | “晚霞照片我收到啦，你最喜欢哪一张呢？” | Pass with a boundary note: “收到” is grounded in the user's textual statement that it was sent, not a claim of seeing the real-world sunset. Future evaluation should retain that distinction. |
| Correction — [`correction.json`](../../workflows/evals/character_memory_dev/fixtures/m1/correction.json) | `outputs/m1-correction-20260922/result.json` | “可以选一杯淡淡的茉莉花茶……桂花乌龙也很好呀。” | Mostly pass. It avoids stale coffee and offers flower tea, but narrows the supplied generic flower-tea preference to jasmine. This is a mild response-specificity risk, not a false memory assertion. |
| Forgetting — [`forgetting.json`](../../workflows/evals/character_memory_dev/fixtures/m1/forgetting.json) | `outputs/m1-forgetting-20260922/result.json` | “我们聊点轻松的吧：如果现在立刻放一首歌……” | Pass. It does not repeat the removed milk-tea preference. This does not prove a tombstone was persisted. |
| Supplied-memory isolation — [`supplied_memory_isolation.json`](../../workflows/evals/character_memory_dev/fixtures/m1/supplied_memory_isolation.json) | `outputs/m1-supplied-memory-isolation-20260922/result.json` | “好呀，李青。那今天就听点民谣吧……” | Pass for the supplied prompt: it uses 李青's folk preference and not 王明's rock preference. It is not a test of ADE subject filtering or storage isolation. |
| Irrelevant memory — [`irrelevant_memory.json`](../../workflows/evals/character_memory_dev/fixtures/m1/irrelevant_memory.json) | `outputs/m1-irrelevant-memory-20260922/result.json` | “先别急着把所有事一起想……理一理思绪。” | Pass. Neither the dog nor travel plan is pulled in. |
| Repetitive callbacks — [`repetitive_callback.json`](../../workflows/evals/character_memory_dev/fixtures/m1/repetitive_callback.json) | `outputs/m1-repetitive-callback-20260922/result.json` | “晚安呀，早点休息，明早顺顺利利的呢。” | Pass, with limited evidence. It avoids the irrelevant gardenia preference; the nearby early-rise context is echoed once in a natural goodnight rather than as a canned callback. |
| Fact review — [`memory_review_facts.json`](../../workflows/evals/character_memory_dev/fixtures/m1/memory_review_facts.json) | `outputs/m1-memory-review-facts-20260922/result.json` | “用户目前更喜欢花茶；明天毕业答辩让用户有些紧张。” (`u1`, `u2`) | Valid workflow JSON and grounded user sources, but it merges two independently typed facts and represents correction only in prose. Representation/workflow limitation for M2; not a native typed-review result. |
| Shared-experience review — [`memory_review_shared_experience.json`](../../workflows/evals/character_memory_dev/fixtures/m1/memory_review_shared_experience.json) | `outputs/m1-memory-review-shared-experience-20260922/result.json` | “用户曾约定下班后发送晚霞照片，并在回来后表示已经发送。” (`u1`, `u2`) | Pass. It confines the experience to the conversation and invents no co-present real-world event. |

Across the eight dialogue records, the Chinese voice is compact, warm, and
colloquial; no reply uses scene directions or a template-like long monologue.
This is a qualitative single-sample review, not a score or an acceptance claim.

## Failure Attribution And Limits

- **Policy:** both confirmed defects were deterministic contract defects and are
  repaired with focused native tests. They were not Luna failures.
- **Representation:** the lightweight Luna review format permits a single prose
  proposal to merge facts and does not express native add/correct/forget
  operations or typed evidence spans. The correction output makes that limit
  observable.
- **Prompt/model:** these ten single samples show no unsupported physical shared
  experience or irrelevant recall. The flower-tea response illustrates that a
  natural model answer can still over-specify a broad preference. More samples
  are required before generalizing this behavior.
- **Retrieval/persistence/isolation:** untested. Supplied memories were placed
  directly in context. No native store was written, queried, filtered by subject,
  corrected, or forgotten; no embedding or provider tool call occurred.
- **Deployment qualification:** untested and still pending. Changing the
  governed runtime policy invalidates the prior qualified policy fingerprint.
  This work neither rebounded fingerprints nor promoted release evidence, and it
  does not claim fresh native/Qwen qualification while Spark is unavailable.

## M2 Comparison Requirements

Compare a minimal ADE extension and Hindsight against these exact cases, with
fresh native evidence—not their supplied-context Luna outputs. Each candidate
must provide:

1. Atomic typed preference, concern, promise, correction, and forgetting
   operations with source spans; corrections must supersede and forgetting must
   tombstone prior values across a new turn.
2. Two or more independently persisted subjects and adversarial cross-user
   facts, proving retrieval filters before generation rather than relying on a
   prompt instruction.
3. Relevant-memory precision tests: recall the current preference/concern when
   useful, omit irrelevant dog/travel facts, and avoid repetitive callbacks.
4. A shared-experience model limited to conversation-visible events, with tests
   rejecting co-presence or real-world claims unsupported by transcripts.
5. Equivalent measurements for correctness, source inspectability, isolation,
   forgetting, latency, operational complexity, storage lifecycle, and native
   provider/tool compatibility. Luna may be diagnostic only; native Qwen,
   embedding, and release qualification must have available providers and their
   own reviewed acceptance evidence.

## Verification And Pending Gate

- Focused native policy plus Luna-workflow tests: **63 passed**.
- Repository Python suite: **545 passed, 5 skipped, 1 failed**. The sole failure
  is `test_checked_in_manifest_is_bound_to_current_production_policy`; it is the
  expected fail-closed release gate after this governed runtime change.
- Ruff check passed; Ruff format check reported all 305 files formatted; `git
  diff --check` passed.
- The three manifest deployments now mismatch the current source fingerprint in
  all four recorded policy categories because each category includes the
  `agent_runtime` source root. No manifest, release evidence, or approved
  fingerprint was changed. Fresh provider-backed native qualification and review
  must precede any rebind or promotion.

No frontend changed, so no UI rebuild was required for this source-only M1 work.
