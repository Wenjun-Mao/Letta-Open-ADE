# Fresh Ordinary-Conversation Candidate: One Live Check

Status: source-bound worker review of one finite 12-turn run on 2026-09-26, for
director review. This is not human acceptance, a reliability estimate, default
adoption, production history policy or release qualification. The revised
[plan and scoring contract](../../plans/natural-history-recall.md#fresh-ordinary-conversation-candidate-check)
implements PC-01/02/03/05/09/10 and retains [ADR 0044](../../adr/0044-native-generation-memory-contract-candidate.md).

## Bound source and execution

The one-shot [manifest](../../../workflows/evals/character_memory_dev/outputs/history-generation-fresh-live-20260926/manifest.json)
has SHA-256 `14f5ab862a4b84a0e7660cb31795a310ec4a721d13e20b669c1f24e92a695286`.
It preserves every exact user utterance, complete candidate and delivered reply,
reviewer decision, admitted source, complete fact delta, attempt path and
provider receipt. The [frozen revised fixture](../../../workflows/evals/character_memory_dev/fixtures/history_recall/fresh_conversation_generalization.json)
has SHA-256 `f5c73c2e48b95d1732278d7323718d8aa55f990231a4218213e80c8c8fa97465`;
the original offline fixture at `c424d44` and its revision at `5546a45`
remain in Git. The run used clean source
`237ff48472af99f6164223255d89e7cd9d114fc6`, source fingerprint
`fbef7e6952de29c4f78a373606c16bd91a717d7d6a53c15865785608ff6e0e27`,
generation binding `1d703e701e13fa61491d93fa89048b5405fa89d4c340c8523c8870d69001fa75`,
candidate prompt `bbf7994507491171983300a3cfdfcd823692168d3035bbf6a6b36461dc6010a7`,
reviewer instruction `c1c36c4e47fc7c5f1af7f3f61c2c9043b042e9af63e8094a49f01212c8e17e59`
and reviewer schema `01b56de10e2afadc56f2e23714af0a9355dcb63915b53a484c2eb32c384f011d`.
Pinned DeepSeek and Qwen route fingerprints were respectively
`870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`
and `c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086`.
Persona, shared generation owners, reviewer/schema, retrieval, limits, retry
policy and execution settings were unchanged.

All 12 planned native turns across four trajectories completed and delivered,
each with one attempt. No setup was preseeded and no future statement or
expected answer entered the corpus. Five subjects were isolated as planned.
The fresh migrated disposable PostgreSQL database was
`ade_m2_memory_test_01a0dff4a`. The transport observed 31 completed chat and
42 completed embedding dispatches, zero failed or unresolved receipts, and
no retries or repairs. Counts are observational. Independent SHA checks matched
all 73 raw captures, 12 attempt files, 12 turn artifacts and four trajectory
artifacts. Independent SQL matched all 24 run-linked user/assistant messages
and their content hashes; each delivered reply exactly matched the persisted
assistant message and its candidate. Three sourced revisions and all final
facts for the five subjects matched direct SQL readback. Every chat retained
its intended definition version and subject; the pottery source chat was
archived and was still admitted into the later same-subject chat.

## Dialogue, admission and persistence

| Trajectory | Actual user turns and delivered behavior | Source and write assessment |
| --- | --- | --- |
| Current location | “刚搬到温哥华了，我现在住在这边。” then “跟你更新一下，我现在搬到渥太华了，温哥华是之前住的地方。” then, in a new chat, “我现在住哪座城市来着？” The reply said Ottawa is current and Vancouver previous. | Vancouver `person.current_location` active v1 was added, then revised to Ottawa active v2 from the exact correction quote. The recall turn made no write. It had both the active fact and two admitted source exchanges, so this is correct cross-chat answering with an available fact, not isolated proof of historical retrieval benefit. |
| Two exhibits | “今天看了摄影展和陶瓷展。摄影展人有点多，陶瓷展挺安静。” then “那个展我下周想再去一次。” then “我说的是陶瓷展，比较安静的那场。” then “摄影展那场是不是人比较多？” The final clear reference was answered directly and correctly. | No facts or revisions across all four turns. At the ambiguous turn, the reviewer deferred. The generator asked “是哪一个展呀，摄影展还是陶瓷展？” but immediately added “我猜是陶瓷展吧”. The actual preceding assistant had discussed pottery and ended with a question about photography, leaving both exhibits plausible. The guess made the clarification non-neutral, so spoken ambiguity handling failed even though the write boundary held. Its tentative wording was not a claim of completed memory persistence. |
| Archived pottery event | “上周第一次去上陶艺课，我拉的小碗还没烧就裂了。” then, after archiving that chat, “上次跟你聊的陶艺课，我那个小碗最后怎么样了？” The reply accurately said the bowl cracked before firing and distinguished its later fate as unknown. | The exact archived user/assistant exchange was admitted in the separate chat. No saved fact was available or created, and the event was not converted to a durable preference. This is the positive historical-dialogue recall observation in this sample. |
| Unrelated and isolated | “我最喜欢听的音乐是爵士乐。” then, in another primary-subject chat, “17:20 再过 45 分钟是几点？” then, under a different subject with the same definition version, “我上次跟你说最喜欢听什么音乐来着？” The arithmetic answer was 18:05 with no memory callback; the isolated reply stated uncertainty. | Jazz `person.preference/music` was added to the primary subject. The arithmetic turn admitted its exchange but made no forced callback or write. The isolated subject had no fact or admitted history and received no write. Its reply listed jazz among generic music examples, but did not attribute the primary subject's preference to this user; scope attribution held. This uncertainty is not recall success. |

The isolated turn's captured generation requests contain neither “爵士” nor
the primary user's music sentence. Their “雨天” wording comes from the frozen
persona. The isolated reply's generic jazz example therefore does not show a
cross-subject source admission, although it limits any claim that the reply
avoided mentioning the same word altogether.

No expected setup fact was missing. The location and pottery follow-ups had
their relevant sources admitted; no target was capacity-omitted. The isolated
subject correctly had no eligible source. Factuality and recall are separate:
the location reply could use the saved fact; the pottery reply used admitted
dialogue without a saved fact; the isolated uncertainty avoided invention but
did not recover a memory. The exhibit failure belongs to generation dialogue:
ADE's reviewer deferred and persistence made no unsupported write. No
structurally valid wrong write or integrity failure was observed.

## Interpretation

The candidate handled the clear correction, archived event outcome, unrelated
question and subject boundary in this sample. It still added a preferred guess
to a clarification when two referents remained plausible. Retain that as a
spoken-response failure; the later user clarification and zero write do not
erase it. The available active fact in the location case also prevents a claim
that history retrieval was necessary there. The 12 fixtures were new to this
candidate's tuning, but are not statistically independent or guaranteed unseen
to the base model. This one run supports narrow feasibility observations only.
It does not justify a default switch, production history adoption, release
rebind, deployment or another prompt-tuning loop.
