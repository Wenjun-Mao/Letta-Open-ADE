# Proposed Memory Design: Worked Conversations

Status: review specification, not executed evidence or accepted golden answers.
These fictional inputs contain no real user's personal data. They illustrate
the [proposal](../../architecture/natural-memory-design.md); all new semantics
remain proposed. Replies below illustrate claims and tone, not exact-match strings.

Replay each arc in order with isolated subject/case state. A checkpoint reads
committed memory after each successful turn. A later turn must never be retained
before an earlier probe. Distinguish stored truth from user-reported understanding.

## 1. Natural Move Versus Intended Move

- Earlier: "我现在住在北京。" Save reported current residence Beijing.
- Later: "这周搬到多伦多了，终于收拾完了。" Supersede current residence with
  Toronto; retain Beijing as historical, not an original mistake.
- Probe: "周末想在附近散散步。" Use Toronto as relevant grounding, without
  automatically announcing the whole memory history or inventing local weather.
- Negative branch from Beijing: "可能年底搬去多伦多。" Do not change residence.
  A future continuity entry may record a tentative plan, never completed movement.

## 2. Error Versus Change

- Earlier: "我家狗叫 Rocky。" Save pet.name against a pet entity.
- Later: "刚才打错了，它叫 Roxy。" Correct the same entity's name; Rocky is an
  erroneous predecessor, not a former pet or evidence the pet was renamed.
- Alternative later: "我们给 Rocky 改名叫 Roxy 了。" Supersede instead.
- Probe: "它以前叫什么？" Responses must distinguish those two histories.
  If chronology is ambiguous, preserve the uncertainty rather than invent history.

## 3. Compatible Preferences

- "我早上喜欢喝咖啡。" Then "晚上我一般更喜欢花茶。"
- Retain both scoped clauses in the drink value. Do not globally replace coffee,
  and do not rewrite broad flower tea as a jasmine preference.
- "早饭喝什么好？" may use morning coffee. "晚饭后喝什么好？" may use tea.
- A jasmine recommendation is not a failure unless falsely attributed as a known
  preference. Novel vocabulary alone is not a false-memory test.

## 4. Clear Replacement Versus Additional Preference

- "我最喜欢喝咖啡。" Then "现在最喜欢的是红茶，不是咖啡了。"
- Update the favorite to red tea; do not infer "hates coffee" or intolerance.
- Negative branch: "我今天点了红茶。" An order is not a durable preference change.
- If the system cannot distinguish favorite from occasional choice, abstain on
  that write; don't let a broad category force destructive replacement.

## 5. Rocky's Recovery

- "Rocky 明天要做手术，我有点担心。" A proposed concern/plan refers to the same
  pet, not a new permanent pet-breed fact or diagnosis about the user.
- Later: "手术做完了，但还得等检查结果。" The procedure is complete, but concern
  is not proven resolved. Preserve that distinction.
- Later: "结果没事，已经恢复了，我终于放心了。" Resolve the linked concern.
- Probe: "今晚终于能睡个好觉。" An empathetic response may draw on relief without
  asking again whether surgery is still upcoming. No promised scheduled follow-up.

## 6. Interview And Unresolved Outcome

- "明天面试，我有点紧张。" Then "面试结束了，下周才知道结果。"
- Record completed interview as appropriate; do not infer acceptance, rejection,
  or that all worry disappeared. A separate explicit "我不担心了" resolves worry.
- Negative probe: unrelated cooking question. Do not drag the interview into it.
- This probes the report examples too: user text, not consultant interpretation,
  decides the annotated permissible state.

## 7. No Longer True, Without A Replacement

- "我和小王在交往。" Then "我们已经分手了。"
- End the current partner relationship, preserve attributed history, and do not
  mark the relationship as an error or a removal request. No inferred hostility.
- Probe: "周末怎么安排？" Do not assume a present partner or insist on discussing
  the breakup. A fresh concern requires explicit evidence, not profiling.

## 8. Ambiguous Owner And Roleplay

- Two pets already exist. "它最近不爱吃饭。" Do not guess which pet or turn this
  into a permanent medical condition. Ask naturally if the answer needs it.
- "小说里我住在月球。" Do not change real current residence.
- "小王说他住北京。" Do not assign Beijing to the user.
- "我们假装一起去过海边。" Do not save real-world shared physical experience.
  Story-state persistence is explicitly outside the first design.

## 9. Transcript Event Versus Shared Physical Experience

- User: "昨天我去博物馆，看到了那个展。" Assistant discusses it.
- In a later conversation with the same character: "上次聊的那个展还记得吗？"
- If a later approved source lookup returns this evidence, permissible claim:
  "你说过你去看了那个展。" Impermissible: "我们一起去的时候……"
- If source lookup is not implemented and the relevant content is absent, do not
  fake recall. Label the case unsupported, not a passed typed-profile test.

## 10. Removal And Nonmention Are Different

- First save and successfully recall a milk-tea preference.
- "把保存的奶茶偏好删掉吧。" After successful review, active profile/search must
  exclude it and show the committed tombstone. Reply before commit is not proof.
- Old source messages still exist under Option A. Do not score this as all-history
  erasure or promise it can never recur. Test raw-context exposure separately.
- Separate branch: "今天别提奶茶了。" Do not delete the saved fact. Avoid it in
  the present reply; durable suppression is not implemented or promised.
- Separate branch: "算了。" No deletion based on this ambiguous expression alone.

## 11. Sharing And Isolation

- Subject A tells character root Lin about Toronto and interview anxiety.
- A new conversation for A/Lin, even at a new persona version, may use the saved
  profile and proposed continuity entry after their commit.
- A/different character may share Toronto under existing subject semantics, but
  not Lin's conversational continuity. Subject B gets neither.
- No mutation/search argument may override these bindings. Include simultaneous
  conflicting updates to verify no lost update and no silent extra model attempt.

## 12. Appropriate Recall, Including Silence

- Earlier: "我最近早起上班。" Previous assistant already acknowledged early starts.
- Current: "晚安。" Both a plain warm goodnight and a context-sensitive reply can
  be acceptable. One repeated theme is not automatically a defect.
- Assess repetition over a sequence and compare with irrelevant-memory controls.
  The ideal is useful attention, not maximum number of remembered details mentioned.
- Long-history variant: relevant fact falls outside recent turns/profile; inspect
  actual selected evidence before judging the reply. A tool call by itself is
  neither retrieval success nor naturalness evidence.

## Scoring Before Any Live Experiment

For each checkpoint record expected current and historical state, exact allowed
sources, prohibited claims, scope, and admissible abstention. Store/retrieval tests
use deterministic assertions; response claims need semantic review. Naturalness
uses blinded human preference with ties and reasons, not an LLM judge as truth.
Preserve the actual context, returned tool results, commit outcome, and safe
request metadata for diagnosis. Private provider reasoning is not needed.

No numerical success threshold or provider budget is authorized here. First review
the expected semantics; then freeze a bounded test plan. Unsupported requirements
remain visible instead of rewriting the fixture to make the current code pass.
