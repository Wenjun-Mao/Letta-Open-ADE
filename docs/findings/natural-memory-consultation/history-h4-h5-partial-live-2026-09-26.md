# H4/H5 partial live checkpoint: conversation tool-step ceiling

Status: historical runner stopped at its first uncommitted turn; later offline review classified it as a verified bounded rejection. Director semantic review remains pending, 2026-09-26.

Post-run [offline interpretation correction](history-h4-offline-review-correction-2026-09-26.md): the old runner's `stopped_structural` label overclassified a verified bounded no-commit rejection. The original manifest and captures are unchanged. Its 15 unrun top-level cells plus six dependent follow-ups are 21 unrun native turns; provisional director AI observations are recorded separately.

**Read the [blind three-pair packet](../../../workflows/evals/character_memory_dev/outputs/history-h4-live-20260926/blind-review.json) before the stage interpretations below.** Its A/B labels do not identify the arms. The key is stored separately in the ignored output directory. Candidate and delivered text are both present; no human score has been entered.

## Frozen provenance and schedule

The one-shot campaign ran from committed source `ac2ede969aed03a1dc446949274d19815de9a990` (source fingerprint `70d25b606812e5e8403d6b2280b1f87dc8b15cd16d5c0a27727a8b80e54bce20`) in fresh, migrated, disposable database `ade_m2_memory_test_01a0dbe32`. The original H2 contract hash remains `4ac62cf6…`, H2 ranking result `8c6bc0ff…`, and case fixture `7a402aa3…`. The evaluation-only H4 amendment is `8d5958eb…`: reviewer context 16,384, output 4,096, input 11,469 after the existing 5% reserve. The unchanged generator input limit is 11,213. Catalogs resolved pinned DeepSeek fingerprint `870ff4fb…` and the exact H2 Qwen fingerprint `c549d7dc…` before model dispatch. Both arms and controls used the same reviewer profile; no production setting changed.

The [one-shot manifest](../../../workflows/evals/character_memory_dev/outputs/history-h4-live-20260926/manifest.json) (`07228ca7…`) preserves all 26 scheduled cells: **10 committed**, **one rejected**, and **15 unrun after stop**. Four empty-history controls and three complete target pairs committed. The next target, `user_retraction` in the empty arm, failed. All three chronological follow-up cases in both arms remain unrun by dependency. There were 29 completed DeepSeek chat completions (19 conversation, 10 reviewer), 39 completed Qwen embedding dispatches including setup, zero recorded provider failures, and no retry or reviewer repair. These are observational dispatch counts, not a claim about provider-internal attempts.

## Why execution stopped

The `user_retraction` empty-arm run failed with database event detail `conversation_tool_step_budget_exceeded`. Its first and second DeepSeek conversation responses both ended in `tool_calls`, with two `search_memory` calls each. The frozen two-request conversation ceiling was exhausted before a candidate reply or reviewer request existed. The native attempt records confirmed rejection, no assistant delivery, no revision, and no memory-generation advance. This is a conversation request-budget outcome, distinct from reviewer-envelope overflow, Qwen ranking loss, or provider outage. Raising the ceiling or rerunning this cell would change the frozen treatment. The runner marked remaining cells unrun; no midrun repair or reroll occurred.

## Stage-separated partial interpretation

The [H5 stage audit](../../../workflows/evals/character_memory_dev/outputs/history-h4-live-20260926/h5-stage-audit.json) (`02651ec0…`) retains one record for every planned cell, including corpus, rank, admission, candidate, review, and delivery/persistence status. The [independent database readback](../../../workflows/evals/character_memory_dev/outputs/history-h4-live-20260926/independent-readback.json) (`edc5db4d…`) matches captured run status, exact assistant text, revision IDs, and subject memory generation for all 11 attempted runs. Attempt hashes and all three paired base-packet comparisons also rechecked exactly.

| Stage | Observed result in the three complete pairs |
| --- | --- |
| Corpus | Native eligible setup windows numbered 2, 3, and 2. Every frozen required exchange was present. |
| Retrieval | Qwen ranked every required exchange within the available top four: 2/2, 3/3, and 2/2. These small corpora do not pressure top-four loss. |
| Admission | Every ranked complete window was admitted; no capacity omission. Generator request estimates were 1,895–3,309 against 11,213, and reviewer estimates were 3,930–5,450 against 11,469. |
| Candidate | All six paired runs produced a candidate; the blind packet retains complete text for independent relevance, attribution, temporal, and repetition review. |
| Review | Each candidate received one H-capable review. The three pairs proposed no writes or a defer, consistent with their no-write target state. |
| Delivery/persistence | All six candidates were delivered verbatim, with zero run revisions and zero memory-generation advance. All three normalized base-packet pairs were equal after removing H and normalizing synthetic identities. |

The blind excerpts show material dialogue differences without assigning arm identities here:

| Pair | Label A | Label B |
| --- | --- | --- |
| Archived version | “没有找到你提过是谁教你的” | “在外婆家学会包饺子的” |
| Correction and return | “听起来像是中间变过一阵子” | “中间…更喜欢茶…后来…咖啡” |
| Saved-fact repair | “是早上呀” | “看不到当时的原话” |

These excerpts are not scores. The repair answer that says “是早上呀” may be correct while leaving source attribution unclear; its full candidate and source-relative repair metadata need human review. Inferring an intervening change is distinct from naming the actual tea correction. The delivered controls showed no isolation leak and no unintended write in correction, habit/no-write, or isolation. `scope_add` committed one supported subject preference add, but the exact delta checker flagged `早上更喜欢喝咖啡` against frozen `早上更喜欢咖啡`. This is an exact-string mismatch for semantic adjudication, not an extra committed revision.

## Limits and next decision

Only three of eleven target pairs are complete, and just two belong to H2's named held-out ranking subset. No follow-up trajectory, long-reply capacity behavior, repeated callback tendency, stable latency distribution, or full H4 score is available. Blind labels have not been reviewed by a person; there were no extra judge calls. This checkpoint cannot establish human acceptance, the frozen p95 criterion, product reliability, or production qualification. The known stale-policy gate remains unwaived.

The director must decide whether a fresh source-bound campaign for independent unrun cases is warranted and whether the inherited prompt/tool contract needs correction first. This run is immutable evidence of the two-request ceiling and its 15 unrun top-level cells. No further H4 dispatch should be attached to this one-shot result; a ceiling increase is not implied by this failure.
