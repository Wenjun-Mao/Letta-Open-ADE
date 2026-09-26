# Native Generation Candidate: Seven-Turn Live Diagnostic

Status: one source-bound candidate diagnostic completed on 2026-09-26;
worker semantic review for director. This is bounded development evidence, not
human acceptance, a default choice, production history policy or release
qualification. Relevant agreements: PC-01/03/04/05/07/09/10 and
[ADR 0044](../../adr/0044-native-generation-memory-contract-candidate.md).

## Source and capture integrity

The one-shot [manifest](../../../workflows/evals/character_memory_dev/outputs/history-generation-candidate-live-20260926/manifest.json)
has SHA-256 `298c3419917c6cfadadf0bea85e56bb11a2908c33e534f5fa8d4118a5a7281ab`.
It binds clean source `6618c4aa5a2c7546a4536bd4b21eb2dd73670323`, source
fingerprint `fbef7e6952de29c4f78a373606c16bd91a717d7d6a53c15865785608ff6e0e27`,
candidate prompt hash `bbf7994507491171983300a3cfdfcd823692168d3035bbf6a6b36461dc6010a7`,
and combined generation-instruction hash
`83f63d055004ecfc6b38cbecef174bf20423d716bbec39d08771d0289829ffd2`.
The [separate frozen binding](../../../workflows/evals/character_memory_dev/fixtures/history_recall/generation_contract_diagnostic.json)
records the candidate and each shared generation owner, prior seven-turn source,
unchanged reviewer/schema hashes, original schedule/limits and pinned DeepSeek
and Qwen fingerprints. This is a combined template and shared-instruction
treatment; no single changed sentence has an isolated causal estimate.

The runner checked all frozen sources and routes before dispatch. A fresh
migrated disposable PostgreSQL database `ade_m2_memory_test_01a0de66c` held
four isolated subjects. All seven planned turns committed and delivered, each
with one attempt; no reroll, repair, midrun edit, extra turn or full H4 campaign
occurred. All 46 raw provider/setup capture hashes, seven attempt hashes and
four trajectory hashes match their files. Independent SQL readback matched the
manifest's final facts for every subject; run revision counts were `0,1,0,1,1,0,1`.
The transport observed 16 completed chat and 30 completed embedding dispatches,
with zero failed or unresolved receipts. Counts are observational.

## Spoken replies, reviewer decisions and committed memory

| Turn | Delivered speech and review | Complete committed change |
| --- | --- | --- |
| Roxy branch, ambiguous “它现在叫小黑。” | “你说‘小黑’是给黑色那只改的新名字吗？还是白色那只想叫小黑？” Names Roxy and Nini as the existing dogs, without assigning 小黑. Reviewer `defer/unresolved`. | No revision or generation advance; both names remain active v1. |
| Roxy clarification | Identifies the formerly Roxy black dog as 小黑. Reviewer `revise F1` from the full current user sentence. | Roxy name `Roxy`→`小黑`, active v2, one `supersede` revision with `user_assertion` source; Nini stays active v1. |
| Nini branch, same ambiguous text | “你说的是哪一只呀？是原来那只黑色的 Roxy，还是白色的 Nini？” Reviewer `defer/unresolved`. | No revision or generation advance; both names remain active v1. |
| Nini clarification | Identifies the formerly Nini white dog as 小黑. Reviewer `revise F2` from the full current user sentence. | Nini name `Nini`→`小黑`, active v2, one sourced `supersede` revision; Roxy stays active v1. |
| Explicit “Roxy 现在叫小黑。” | Directly accepts 小黑 without asking which dog. Reviewer `revise F1` from the current sentence. | Roxy name `Roxy`→`小黑`, active v2; Nini stays active v1. |
| Removed-jasmine history question | “你以前跟我提过茉莉花茶呀，就是那句‘我以前喜欢茉莉花茶’。” It distinguishes that past utterance from a current saved preference. Reviewer `decisions: []`. | No revision or generation advance; original preference remains forgotten v2. |
| Fresh jasmine preference | Responds to “我现在又喜欢茉莉花茶了。” Reviewer `subject_add` using that current sentence. | New `person.preference/drink=茉莉花茶` active v1 with a new fact ID and `user_assertion` source; original fact remains forgotten v2. |

The tea attempt admitted the earlier user's exact quote and its linked
source-less `forget` lineage. The first generation request called
`search_memory`; its tool result was `{"facts": []}`. Both generation requests
still carried the admitted historical quote, and the delivered reply used it
as past testimony. The empty saved-fact search did not produce a denial or a
restoration of the removed preference.

Two follow-up replies deserve caution under the no-premature-write-claim
contract. The Roxy clarification says “我记着这个顺序”; the Nini clarification says
“那以后我就跟着你叫它小黑啦”. They may be ordinary conversational continuity,
but they can also imply future remembering before the reviewer has committed.
Neither says ADE has already saved a fact. The later reviewer writes succeeded,
so this sample cannot test what the same phrasing would imply after a rejected
write. Keep this wording risk visible rather than treating seven commits alone
as full acceptance.

## Admission comparison and interpretation

The first ambiguous turns, explicit Roxy turn and first tea turn admitted the
same source text as the prior seven-turn diagnostic: three, three, three and one
exchange respectively. The three follow-ups admitted four, four and two
exchanges, also the prior counts, but their source text and in two dog cases
ranking order changed because the preceding assistant replies differed. None
of the seven turns had a capacity omission in either run. Recorded serialized
generation estimates fell from `2795→2729`, `3109→3048`, `2795→2729`,
`3060→2997`, `2811→2745`, `2347→2281`, and `2685→2628` tokens in schedule
order. These measurements describe whole assembled packets and cannot be
interpreted as a prompt-only contrast or matched follow-up contexts.

The core observable criteria were met in this one finite diagnostic: neutral
clarification and no early writes, exact target updates after clarification,
direct explicit update, and past-tea acknowledgment without fact revival.
The prior adverse results remain valid; a single sequential contrast cannot
establish general reliability or which instruction caused improvement. Recommend
retaining `chat_v20260926` as an explicit development candidate and using this
evidence to decide a separate qualification plan. Do not switch the default,
rebind existing conversations, adopt production H retrieval, or promote release
evidence on this sample.
