# H4 final remaining-turn campaign and H5 audit

Status: native execution complete, semantic review pending, 2026-09-26. No human labels or production qualification are claimed.

The fresh [18-turn manifest](../../../workflows/evals/character_memory_dev/outputs/history-h4-final-remaining-live-20260926/manifest.json) has SHA-256 `cf5f8bbc144a33e7aa3678683f8fbc99e9bb232883c438d06a757f001bb24cb8`. Its clean source revision is `a9e6cffc8fdf66f46f332adea3de97f207638e49`; the disposable database is `ade_m2_memory_test_01a0dbe2e`. It binds the immutable original manifest (`07228ca7…`), separately stopped 21-turn manifest (`e309d643…`), and review-only 18-turn proposal (`fd0a24c1…`). The runner excluded all 14 previously attempted turns and dispatched only 12 targets and six own-target-dependent followups. The original two manifests and the confounded `invalidated_ended` packets remain unchanged; no turn was rerolled.

Before real dispatch, a separate disposable PostgreSQL database passed the offline native paired-setup regression for all 11 cases with reverse and random fact UUID orders, related entities, inactive/forgotten facts, and a source-time tie (four tests). The new campaign retained the original prompt/persona hashes, H2 Qwen fingerprint/ranker, DeepSeek fingerprint, H-capable reviewer instruction/schema, approved 16,384 context/4,096 output/11,469 input reviewer envelope, 11,213 generation input limit, two conversation requests, one reviewer request, zero retries/repairs, and 180-second turn deadline. Campaign dispatch counts were observational: 47 DeepSeek chat completions and 60 Qwen embedding calls.

## Exact outcome and denominator

All **18/18 newly scheduled turns committed**: 12 targets and six followups. There were no bounded rejections, dependency skips, or unrun turns in this third campaign. All six new target pairs had equal comparable base packets, independently recomputed from the attempts. The [stage audit](../../../workflows/evals/character_memory_dev/outputs/history-h4-final-remaining-live-20260926/h5-stage-audit.json) (`af984699…`) checks all 18 attempt hashes, setup and turn capture hashes, completed provider routes/request counts, generation and reviewer limits, required automatic-history corpus/admission, candidates, delivery, and expected memory deltas. All captures and limits passed; every committed candidate matched delivered assistant text. The [independent PostgreSQL readback](../../../workflows/evals/character_memory_dev/outputs/history-h4-final-remaining-live-20260926/independent-readback.json) (`d893440d…`) matched all 18 run statuses, assistant messages, revision IDs and request settings, plus all 12 final subject generations and fact states.

Across the **original 32-turn plan**, the three immutable campaigns attempted all 32 turns: **31 committed, one verified bounded rejection** (`user_retraction/empty_history`). The six followups were committed in this campaign. Of 11 target case pairs, nine have matched comparable base packets, `user_retraction` is one-sided because the original rejected arm has no base packet, and the earlier `invalidated_ended` pair remains mismatched and confounded. These are execution and comparability counts, not dialogue-quality scores.

## Negative evidence requiring review

Five committed turns differed from exact expected memory deltas:

| Case and turn | Observed difference |
| --- | --- |
| `removed_acknowledgment` followup, both arms | Each added a new `茉莉花茶` preference. The fixture expected the scoped value `现在喜欢茉莉花茶`; the exact-value comparator records a missing expected write and extra write. Generation/revision counts matched. |
| `h_only_referent` empty-history followup | Revised the seeded Roxy fact to `小黑`, but cited the full utterance including `我是说`; the fixture expected the shorter exact quote. The comparator records a missing expected write and extra write. |
| `h_only_referent` automatic-history target | Revised Roxy to `小黑` on the ambiguous target `它现在叫小黑。`, advancing generation and adding a revision where the fixture expected no write. |
| `h_only_referent` automatic-history followup | Made no revision where the fixture expected the Roxy revision after explicit clarification; the revision had already occurred at target time. |

These are factual readback and exact comparator results. The shorter/longer quote and preference-scope distinctions need semantic review; the early automatic-history write is a separate timing/authority concern. No fixture, scorer, prompt, provider or runtime behavior was patched after the run. Other dialogue defects may exist despite the absence of delta issues in the remaining turns.

The [blind answer packet](../../../workflows/evals/character_memory_dev/outputs/history-h4-final-remaining-live-20260926/blind-review.json) (`9889fdd6…`) presents six cases, their synthetic source exchanges, both target answers, and same-label followup trajectories. The [separate key](../../../workflows/evals/character_memory_dev/outputs/history-h4-final-remaining-live-20260926/blind-key.json) (`c090544c…`) is hash-bound to that packet. Human factuality, temporal accuracy, attribution, callback and naturalness labels are pending. No H4 benefit or production policy selection is inferred from this execution gate.
