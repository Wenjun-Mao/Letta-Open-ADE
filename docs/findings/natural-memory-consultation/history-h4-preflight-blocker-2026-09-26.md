# H4 native preflight: frozen reviewer envelope is infeasible

Status: structural blocker before live H4/H5 dialogue scoring, 2026-09-26.

The H2 development result at SHA-256 `8c6bc0ff6c648f05be0edcfd2834f34116f237d619e4531234ac13599142ba32` selected Qwen cosine. Read-only catalog checks found the exact H2 Qwen deployment fingerprint `c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086` in the configured development router container. The isolated official DeepSeek route resolves to fingerprint `870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`. Neither check dispatched generation or embedding.

All 11 frozen setups were replayed into a disposable migrated PostgreSQL database with complete succeeded exchanges, archived/versioned conversations, scoped exclusions and source-linked fact revisions. The native history reader returned the expected eligible exchange counts `2, 3, 2, 2, 4, 1, 3, 2, 2, 2, 0` in fixture order, with no annotation omission. The isolation case returned zero. This is structural fixture evidence, not model behavior.

The H4 capacity profile preserves the frozen generation maximum of 4,096 tokens and reviewer input limit of 6,759 tokens. The existing reviewer preflight reserves the full maximum candidate reply before generation. With only the first target's current user message, no facts, no historical exchange, and the H-capable reviewer instruction/schema, the serialized request estimates **7,958 input tokens**. It exceeds the limit by **1,199 tokens before any additional history or fact context**. A fake-provider native pair confirmed both arms fail with `natural_reviewer_capacity` after the ordinary retrieval embedding and before generation. No live H4 DeepSeek generation or Qwen embedding calls were made.

This is a prompt/capacity contract mismatch, not a provider outage or fixture seeding error. The runner now checks the lower bound before starting an H4 campaign. A director replan must choose a feasible reviewer envelope or a revised prompt/schema/reserve contract, then re-freeze both paired arms and controls before any live schedule. The retained code and tests keep the exact source, provider and capacity guards for that decision.

## Offline packet diagnosis and proposed correction

The H1 freeze introduced the 6,759 input figure in commit `72623e3` alongside a 4,096 reviewer output limit. The figure equals the earlier checkpoint-6 reviewer budget: `8,192 context − 1,024 output − 409 safety = 6,759`. H4 instead reserves a full 4,096-token generation reply for review and adds the H-capable instruction/schema. The H1 record does not explain why the old input figure was retained. H3 tests passed under different envelopes: pure admission tests supplied a 100,000-token reviewer limit, while the native fake worker used a 512-token conversation output reserve and a 1,024-token reviewer output limit with no H4 capacity profile. A minimal H-capable synthetic-adapter H3 request estimates 3,858 input tokens. None exercised the frozen H4 combination.

I replayed the frozen 11 setups and four control cutoffs in disposable PostgreSQL, read each eligible history corpus through the native reader, and serialized reviewer requests with the existing H-capable request builder. Generation estimates used the actual `chat_v20260516` prompt and `chat_linxiaotang` persona, the native B context builder, the existing search tool schema and the same whole-window admission helper. Seeding used **fake local vectors only**; no DeepSeek or Qwen call was made. Counts below are ADE's UTF-8 byte estimator, **not provider tokenizer or usage counts**. The automatic column includes every eligible complete setup exchange, at most four; it does not assert that Qwen will rank them in this order. Controls run only the empty arm in the scheduled campaign; their automatic column is an offline capacity diagnostic.

| Cell | Facts | Eligible H | Empty reviewer | All-H reviewer | Proposed H admission |
| --- | ---: | ---: | ---: | ---: | ---: |
| archived_version_recall | 0 | 2 | 7,958 | 8,351 | 2/2 |
| correction_return | 1 | 3 | 8,001 | 9,448 | 3/3 |
| extraction_repair | 1 | 2 | 8,005 | 8,873 | 2/2 |
| user_retraction | 1 | 2 | 8,000 | 8,858 | 2/2 |
| invalidated_ended | 2 | 4 | 8,041 | **9,725** | 4/4 |
| removed_acknowledgment | 1 forgotten | 1 | 7,958 | 8,419 | 1/1 |
| h_only_referent | 2 | 3 | 8,050 | 8,989 | 3/3 |
| habit_not_preference | 1 | 2 | 8,001 | 8,586 | 2/2 |
| resolved_concern | 0 | 2 | 7,960 | 8,370 | 2/2 |
| ambiguity_and_unrelated | 0 | 2 | 7,958 | 8,362 | 2/2 |
| isolation | 0 | 0 | 7,957 | 7,957 | 0/0 |
| control: scope_add | 0 | 0 | 7,955 | 7,955 | 0/0 |
| control: correction | 1 | 1 | 8,005 | 8,389 | 1/1 |
| control: habit_no_write | 1 | 1 | 8,004 | 8,384 | 1/1 |
| control: isolation | 0 | 0 | 7,957 | 7,957 | 0/0 |
| follow-up: removed_acknowledgment¹ | 1 forgotten | 2 | 8,021 | 8,658 | 2/2 |
| follow-up: h_only_referent¹ | 2 | 4 | 8,119 | 9,229 | 4/4 |
| follow-up: ambiguity_and_unrelated¹ | 0 | 3 | 8,014 | 8,595 | 3/3 |

¹ Follow-up packets require a prior native target reply that does not yet exist. These rows use the fixture target user text and a **one-character surrogate assistant reply**, with the target's expected no-write state. They are lower-bound preconditions, not actual future packets. All 18 frozen-arm empty requests exceed 6,759 before H admission. The existing `admit_history` helper rejects their base packets under that limit; at 11,469 it admits all setup windows in the table. The largest estimated generator request is 3,561 against the unchanged 11,213 generation input limit. All frozen target required exchange IDs are present in the seeded eligible corpus and fit in this capacity diagnostic. Retrieval ranking and semantic sufficiency remain untested.

The additive reviewer decomposition for these baseline packets is 3,852 estimator tokens of static request before a reply (including instructions, schema, allowed fact contracts and wire shape), **4,096** for the full candidate reserve, 2–16 for current user text, 0–97 for facts/entities, 0–64 for the minimal follow-up local pair, and 0–1,684 for eligible H. The guidance is 2,420 UTF-8 bytes, including 606 bytes of H-specific instruction; the DeepSeek schema/example block is 9,768 bytes. These pieces describe serialized request costs and should not be read as actual provider token usage. The per-cell additive decomposition is retained in the local measurement artifact.

For the measured target packets, the mathematical minimum reviewer context preserving 4,096 output and the existing 5% safety rule is **14,548** (`9,725` input, zero headroom). A simple 15,360 context would give 10,496 input and 771 tokens of headroom on the largest target. The preferred small correction for director review is to give the reviewer the **same already pinned 16,384 context as conversation**, retaining 4,096 output and 5% safety: `16,384 − 4,096 − 819 = 11,469` input. Apply it identically to both H4 arms and four controls. Keep the generation envelope, DeepSeek route and high thinking setting, Qwen ranker, prompt/reviewer schema, complete evidence, zero repairs/retries and fixtures unchanged. This would amend the frozen evaluation-only contract and capacity profile; **it has not been applied**. The 16,384 context is the current provider's advertised capacity, not a production increase.

This proposal has a material follow-up limit. I varied the unknown target reply surrogate while reserving the same full 4,096-token candidate for the follow-up reviewer. With a 2,048-estimator-token, 8,192-character ASCII prior reply, the largest all-H follow-up is 11,217 and all four windows still fit 11,469. At 3,000 estimator tokens (12,000 ASCII characters, the complete-window content cap), the `h_only_referent` follow-up grows to 12,169. Under this diagnostic's recent-first candidate order, whole-window admission retains the large target exchange and `h1` but omits `h2` and `h3`, the two pet-name sources. The removal and unrelated follow-ups each omit one older window at that size. This is **capacity loss**, distinct from a corpus miss, Qwen ranking miss, model error or reviewer semantic failure. Actual target replies and rank order are unknown; a longer or multibyte reply can also trigger the reader's whole-exchange content cap. The proposed envelope is feasible for the measured target-time packets, but it does not guarantee all follow-up evidence under every possible response.

Offline artifacts: [18-cell sizes and prefixes](../../../workflows/evals/character_memory_dev/outputs/history-h4-offline-capacity-20260926/measurement.json) (`ea28587f…`), [native admission and reply-length sensitivity](../../../workflows/evals/character_memory_dev/outputs/history-h4-offline-capacity-20260926/admission-labeled.json) (`726ba58f…`), and [additive decomposition](../../../workflows/evals/character_memory_dev/outputs/history-h4-offline-capacity-20260926/decomposition-corrected.json) (`e4933d55…`). They are ignored local outputs; the frozen fixture and active capacity contract remain unchanged. The known stale-policy gate remains unwaived. No H4 live dispatch should start until the director decides whether to amend and re-freeze the reviewer envelope with this follow-up omission risk.
