# Proposed Memory Design: Worked Conversations

Revision 3: review specification, not executed evidence or accepted golden answers.
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
  The dialogue can discuss that tentative plan without a new durable plan schema.

## 2. Error Versus Change

- Earlier: "我家狗叫 Rocky。" Save pet.name against a pet entity.
- Later: "刚才打错了，它叫 Roxy。" Correct the same entity's name; Rocky is an
  erroneous predecessor, not a former pet or evidence the pet was renamed.
- Alternative later: "我们给 Rocky 改名叫 Roxy 了。" Supersede instead.
- Probe: "它以前叫什么？" Responses must distinguish those two histories.
  If chronology is ambiguous, preserve the uncertainty rather than invent history.
  This is answerable when the distinguishing exchange is supplied. If it has left
  context, do not silently require the deferred generic historical-fact tool.

## 3. Compatible Preferences

- "我早上喜欢喝咖啡。" Then "晚上我一般更喜欢花茶。"
- Save separate independently addressable scoped preferences. Do not replace coffee,
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

- "Rocky 明天要做手术，我有点担心。" Retain the ordinary dialogue; do not invent
  a permanent pet-breed fact, user diagnosis, or a currently unsupported concern row.
- Later: "手术做完了，但还得等检查结果。" The procedure is complete, but concern
  is not proven resolved. Preserve that distinction.
- Later: "结果没事，已经恢复了，我终于放心了。" The supplied dialogue now supports
  recovery and relief. No durable continuity-entry lifecycle is assumed.
- Probe: "今晚终于能睡个好觉。" An empathetic response may draw on relief without
  asking again whether surgery is still upcoming. No promised scheduled follow-up.
- Across conversations this is a source-window experiment, not a claim of implemented
  recall. Supply original statements and later updates in the fixed-evidence variant.

## 6. Interview And Unresolved Outcome

- "明天面试，我有点紧张。" Then "面试结束了，下周才知道结果。"
- The dialogue supports a completed interview, not acceptance, rejection, or the
  disappearance of all worry. "我不担心了" supplies relief evidence. No event table
  is assumed; compare a bounded source window before a durable entry representation.
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
  profile after commit. Anxiety recall across conversations requires eligible
  dialogue evidence in the proposed source-window experiment, not an assumed entry.
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

## 13. Partial Preference Removal And Mixed Revisions

- Save morning coffee and evening flower tea as separate preference records.
- "只移除保存的咖啡偏好，花茶那条保留。" Forget only coffee's record/chain.
- Separate branch: "早上现在更喜欢豆浆了；晚上那条以前说错了，我一直更喜欢红茶。"
  Supersede the first preference and correct the second in the same review, with
  different reasons and source spans. Neither operation touches another category.
- Consumption-only control: "早上现在喝豆浆；晚上以前说错了，一直喝红茶。"
  Does not require preference writes. Acknowledge the routine without inferring
  new favorites; do not weaken this control because an earlier reviewer suggested it.
- Legacy composite branch: no inferred decomposition. Ask for retained assertions
  before a supported forget-old/add-restated replacement, or offer whole removal.

## 14. Current Known, Earlier Relationship Unknown

- Earlier current residence: Beijing. Then "Actually, I live in Toronto."
- Set Toronto current with historical relationship unspecified unless more context
  explicitly establishes change or error. Do not keep a stale present to avoid
  admitting uncertainty about the past; do not invent a move.
- "Did I ever live in Beijing?" Prior reporting alone is not enough to assert yes.

## 15. Invalidate Without Replacement, End Then Remove

- "北京那条是我说错了，我不想说实际住在哪里。" Invalidate the current residence
  without a replacement; do not mark Beijing once-true or infer a deletion request.
- Separate relationship branch: save partner X, end it after an explicit breakup,
  then explicitly remove the saved relationship. The inactive record is eligible.
- Repeating the same exact targeted removal is idempotent. A later explicit
  restatement after forgetting creates fresh evidence, not a restored old chain.
- Reassertion after ending makes a new active revision without pretending the
  relationship was continuous through the gap.
- Two invalidated preferences: morning coffee and evening tea, both null-valued
  and in the same category. "删掉早上咖啡那条，晚上那条保留。" Select only the
  coffee record using the derived withdrawn-assertion descriptors. Do not present
  either as active. After removal, coffee's descriptor is excluded from model input.
  Separate branch: explicit renewed morning-coffee preference reasserts that
  clearly identified inactive record; ambiguous identity must not guess.

## 16. Correcting Older History Without Replacing The Present

- Prior reports: Beijing, then Toronto. Current user: "北京是我姐姐住的地方，
  我来多伦多之前住渥太华。"
- Do not change current residence from Toronto to Ottawa. General retrospective
  revision correction is deferred in this design. The current reply can understand
  the clarification, but no durable historical repair is claimed.
- Operator history still shows original evidence; model-facing historical fact-chain
  lookup is not added. Mark historical-answer cases requiring that feature unsupported
  rather than converting old revisions into supposedly verified truth.

## 17. Clarification Across User Spans

- Two known dogs: Rocky and Roxy. User: "我的两只狗里有一只是哈士奇。"
  Assistant: "是 Rocky 还是 Roxy？" User: "Roxy。"
- Add Roxy's breed using both user spans. The assistant question is reference
  context, not breed evidence. Preserve name/breed entity identity.
- Negative branch: only the assistant invented Husky. A bare name answer is not
  evidence that the breed claim is true. Negative/quoted/roleplay variants must not
  import an assertion. An out-of-window claim needs clarification, not wider replay.
- Positive endorsement: assistant asks "Roxy 是哈士奇吗？" User: "对，她是。"
  The user confirms one clear proposition. Store user assent plus the role-labeled
  assistant-question reference; never pretend the user authored "哈士奇" verbatim.
- Controls: a generic "嗯" after several questions, "可能是", or assent to a
  fictional/quoted proposition cannot authorize that same factual write.
- Force the antecedent/guards beyond the shared budget: both generation and review
  lose that antecedent, dependent write is ineligible, and the reply asks naturally.
  A self-contained new statement may still be saved. No reviewer-only hidden history.
  Include a removal clarification and an intervening negation/correction; do not
  cut the latter out to make an otherwise convenient excerpt fit.
- Even with identical inputs, if the proposed reply asks which dog the user meant,
  the reviewer must not silently commit that unresolved breed assignment.

## 18. Packing, Revisions, And Entity Names

- Long persona: either full mandatory policy is included or construction fails;
  it is never silently removed.
- Oversized first profile record plus relevant Toronto record: the location can be
  packed through retrieval if omitted from profile. Manifest lists only actual
  complete evidence. Partial strings never count as included facts.
- Profile v1 versus retrieved v2: resolve which current revision is used; never
  deduplicate v2 solely because the same fact ID appeared as v1.
- Correct Rocky to Roxy, then inspect reviewer/entity context. Old unqualified Rocky
  labels must not remain canonical. After name removal use neutral identity, not
  the unversioned label. Reject unsupported new_entity_label content as evidence.
- Orphan entities remain in storage but are absent from model input unless required
  by an eligible record or the shared local exchange; no forgotten-name backdoor.

## 19. Stale Summary And Raw Narrative

- Conversation A's summary says X is the current partner. In B, explicitly end
  that relationship. Return to A with a weekend question.
- Context must supply the complete eligible lifecycle snapshot or withhold optional narrative;
  don't rely on absence from the active profile. Do not infer the user has no partner.
- Decisive sequential variant: A has never been summarized. B's breakup commits
  first; A's old partner dialogue is then compacted. The fresh summary still needs
  the independent ending guard. Recompaction cannot retire it either.
- Repeat with recent raw evidence, legacy summaries, an intervening correction,
  and a complete guard set that cannot fit. No summary creation time/generation
  certifies reconciliation. Withholding is an explicit evidence gap, not recall.
- Historical correction without a fact mutation: A reports past Beijing; B says
  that was a sister's city. If B is absent from allowed context, A's narrative only
  proves an old report, not the user's true history. No counter detects all such edits.
- Over-withholding control: short complete interview dialogue plus unrelated fact
  pressure. Annotate answerability independently; count lost useful context, even
  if the reply safely abstains. Compare with the same-budget no-summary baseline.

## 20. Shared Knowledge Beside Private Dialogue

- A source message to Lin contains Toronto plus a private conversation detail.
- Another root can receive the shared residence with compact source attribution,
  not the full message or a claim "you told me when we discussed that detail."
- Archived source conversations are excluded from the experimental model source
  pool; operator citations and already committed facts have separate eligibility.
- Same subject/other root is not the same as other subject. Assert both boundaries.

## 21. Capacity And One Mutation Snapshot

- Full reviewer packet cannot fit: normal extraction fails explicitly, without
  sending costly generation first where this can be preflighted.
- Exact-target operator removal still works without model/embedding calls. It
  checks scope/version, persists action provenance, and does not invent a user quote.
- Select two targets; change one before execution. Neither may be removed. Successful
  action result and both tombstones commit together; same-request idempotent replay
  returns the original result without changing newer state. Another subject's target
  is rejected. An origin label alone is never authorization.
- A large current message or persona may still block chat after successful removal.
  Record the actual capacity cause, not a universal "memory full" diagnosis.
- Concurrent conversations both add the same apparent pet or scoped preference:
  accept both at generation G; commit one and advance G. The other's nonempty
  proposal conflicts, without a hidden rerun or partial assistant/memory commit.
- Supporting identity race: A selects a pet by name for a breed revision. B corrects
  name-to-entity assignments while the breed version remains unchanged. Reject A's
  stale proposal via the changed generation, not just target-version checks.
- Empty-again race: A is accepted with no preference; B adds it; an operator forgets
  it. A must conflict even though eligible records are empty again. Capturing a new
  generation only after model work would incorrectly allow this pre-removal turn.
  A genuinely new explicit restatement accepted afterwards can create a new record.
- Also change memory between acceptance and packet construction: do not silently
  rebase. Verify generation/effects roll back together on failed finalization;
  no-op and replay do not advance the counter. It is not subject-name metadata version.
- Two genuinely different pets with the same name must not be merged by a name rule.
- A concurrent no-op reply based on the old snapshot remains possible under the
  deliberately weaker contract; record it, don't call it a prevented lost update.

## 22. Residence And Temporary Whereabouts

- Current residence Toronto; "这个周末在巴黎玩。" Do not change residence to Paris.
- Next: "附近有什么适合散步的地方？" Use the supplied Paris visit for current
  surroundings while keeping Toronto as home. Do not invent live opening/weather
  data. If the visit's time is no longer clear, clarify rather than assume it persists.
- "已经搬到巴黎，之后住这里了。" Supersede residence with Paris.
- Legacy current_location value with ambiguous source remains meaning-unspecified,
  not automatically reclassified. No location pin may silently equate it with home.

## Scoring Before Any Live Experiment

For each checkpoint record expected current and historical state, exact allowed
sources, prohibited claims, scope, and admissible abstention. Store/retrieval tests
use deterministic assertions; response claims need semantic review. Naturalness
uses blinded human preference with ties and reasons, not an LLM judge as truth.
Annotate required evidence/answerability independently of what the assembler keeps.
Distinguish necessary withholding, avoidable evidence loss, and unjustified abstention;
an always-abstaining system does not pass continuity. Preserve the actual context,
shared-bundle membership, returned tool results, commit outcome, and safe
request metadata for diagnosis. Private provider reasoning is not needed.

No numerical success threshold or provider budget is authorized here. First review
the expected semantics; then freeze a bounded test plan. Unsupported requirements
remain visible instead of rewriting the fixture to make the current code pass.
