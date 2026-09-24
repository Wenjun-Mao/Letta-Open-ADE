# Natural Memory for a Persistent Conversational Character

## Executive judgment

**The core design goal should not be “remember more.” It should be: maintain a coherent, current, appropriately scoped model of the user, and let that model influence dialogue only when doing so improves the conversation.** A recurring character feels attentive when it gets the user's changing situation right, follows important unfinished threads, and avoids making the user repeat themselves. It feels unnatural when it treats memory as something to demonstrate.

That distinction is increasingly visible in the research. LongMemEval treats **knowledge updates, temporal reasoning, and abstention** as separate long-term-memory abilities rather than reducing memory to retrieval. LoCoMo finds long-range temporal and causal continuity difficult even with long-context and retrieval techniques. More recent work goes further: STALE tests whether later observations implicitly invalidate earlier ones; MemSyco-Bench tests whether retrieved memories should be used at all; and the September 2026 LoCoMo-Conv preprint reports “silent grounding,” where memory improves a conversational response without the response explicitly restating the remembered fact. citeturn18view2turn14view5turn16view0turn15view5turn18view0

For ADE, that implies seven consequential changes in emphasis.

**First, separate remembering from mentioning.** A fact may be useful context without deserving an explicit callback. “You told me you moved to Toronto” is usually worse than simply giving Toronto-appropriate advice. LoCoMo-Conv is particularly relevant here: the authors find that on implicit conversational queries, retrieved memory can improve faithfulness, relevance, and engagement even when the response does not explicitly surface the target fact. This is a very recent preprint, so its reported numbers should not be treated as settled independent evidence, but the evaluation construct is directly aligned with ADE's product question. citeturn15view6turn18view0

**Second, model mutable state, not merely a bag of true facts.** “我终于搬到多伦多了” can supersede “I live in Vancouver” even though it contains no explicit instruction to correct memory. STALE identifies exactly this class of problem: a newer observation can invalidate an older belief either directly or by changing a related condition whose consequences propagate. Its example is an old cycling routine becoming inappropriate after a later injury; its benchmark separately evaluates recognizing stale state, resisting stale premises, and adapting behavior without an explicit correction cue. citeturn16view0turn16view1

**Third, facts alone are too narrow.** Some of the most useful continuity comes from episodes and unresolved threads: Rocky had surgery; the user was worried; Rocky later improved. Those are not necessarily permanent profile attributes, yet forgetting them immediately makes the character feel inattentive. LoCoMo explicitly includes event summarization and long-range temporal/causal understanding in its definition of conversational memory, while the older Generative Agents work found that experiences plus higher-level reflection contributed to believable agent behavior in its simulated-agent setting. Neither establishes the ideal retention policy for a companion, but both argue against equating useful memory with isolated profile fields. citeturn14view5turn16view5

**Fourth, “don't mention,” “no longer true,” and “delete” must be different operations.** They change different things:

| User intent | Truth/status | May remain stored? | May silently affect dialogue? | May be proactively mentioned? |
|---|---|---:|---:|---:|
| “先别提这件事了。” | unchanged | normally yes | only cautiously, where needed for tact/safety | **no** |
| “这已经不是事实了。” | superseded | old value may remain as historical provenance | old value only for historical reasoning | not as current truth |
| “把这件事忘掉 / 删掉。” | deletion request | **no durable memory of it** | **no** | **no** |

Conflating these creates predictable failures: deleting useful history when the user merely wants conversational space; continuing to treat stale information as current because the user did not say “correct my memory”; or retaining and resurfacing something after a deletion request.

**Fifth, distinguish memory realms before optimizing retrieval.** At minimum, ADE needs behavioral separation among **user biography**, **mutable user circumstances**, **character persona**, **fictional/roleplay canon**, and **events that actually occurred in the conversation**. Character.AI's public product design itself exposes some of these distinctions: its 2025 Chat Memory examples explicitly include roleplay persona information, while its May 21, 2026 announcement describes separate Facts tabs for Persona, Character, and side characters. That is evidence of an advertised scoping affordance, not evidence about Character.AI's proprietary architecture or reliability. citeturn14view0turn14view1

**Sixth, inspection and correction should be escape hatches, not prerequisites.** Character.AI advertises editable fixed memories, editable or disable-able auto-captured Facts, Story Memory, and pinned memories; Replika documents a Memory view in which learned facts can be inspected or removed and says users can conversationally ask what it knows about them; Nomi advertises searchable/editable Mind Map entries. These products converge on a useful UX principle: automatic continuity and explicit user control can coexist. None of those vendor pages demonstrates how accurately the products actually remember or update information in practice. citeturn14view0turn14view1turn14view2turn15view7

**Seventh, do not treat human-like forgetting as a product requirement.** MemoryBank proposed time- and significance-based forgetting inspired by the Ebbinghaus curve, and its authors reported encouraging companion-style results, but much of its quantitative evaluation used simulated users. That establishes an interesting mechanism, not evidence that users prefer an agent to forget the way humans do. For ADE, **selectivity, current-state correctness, privacy, and restraint are much better-supported goals than anthropomorphic forgetting for its own sake.** citeturn16view6

The main assumptions I would therefore challenge are:

| Assumption to challenge | Better product criterion |
|---|---|
| Durable memory should mostly contain explicitly stated stable facts | Preserve stable facts **plus selected changing state, relationships, significant episodes, and open loops** |
| A prior fact should change only after explicit correction language | Ordinary statements can create a state transition when their semantics support it |
| Successful retrieval means the memory should appear in the answer | Retrieved memory must pass relevance, validity, scope, sensitivity, and conversational-value checks |
| Mentioning a remembered fact proves attentiveness | Often the most natural memory use is invisible |
| Every significant conversation event should become permanent | Events can be useful at different horizons; significance does not imply indefinite retention |
| “Forget,” “don't mention,” and “not anymore” are variants of the same command | They are deletion, mention-policy, and temporal-validity operations |
| A management screen can compensate for imperfect conversational updating | Ordinary conversation must work naturally; controls are for transparency, exceptions, and repair |
| A shared chat history licenses shared-world language | Xiaotang may remember **being told or discussing** something, not invent having physically experienced it with the user |

## Evidence map

The strongest public evidence supports **what capabilities matter** much more clearly than it supports any single storage architecture.

### What the products actually document

Character.AI's public evolution is informative because it has moved from explicit “things you want the Character to hold onto” toward a mix of automatic capture and user control.

On **May 19, 2025**, Character.AI announced Chat Memories for all users: a user-editable field of up to 400 characters intended for fixed information such as routines, relationships, preferences, or roleplay details. Character.AI explicitly cautioned that it could not guarantee that a Character would always use or reproduce that information exactly. The same announcement said pinned memories and automatic memories already existed. citeturn14view0

On **May 21, 2026**, Character.AI announced Story Memory, Facts, and Memory Usage. Story Memory was described as a place for backstory, key events, and important moments, with messages pinnable into it. Facts was described as automatically capturing details such as appearance, quirks, relationships, and hobbies, organized into Persona, Character, and side-character tabs; users could add or edit Facts, disable automatically captured ones, or remove unwanted side characters. The announcement also advertised the option to copy Facts into a new chat or start fresh, and described older context being managed automatically while manually protected Story Memories and pins remain. These are **vendor-described features**, not observations of implementation quality or guarantees about extraction/update behavior. citeturn14view1

That progression contains three useful UX lessons for ADE: automatic memory need not exclude manual control; “important events” deserve a different treatment from flat profile facts; and memory may need entity or narrative scope rather than one undifferentiated user profile. Those are design inferences from the documented UI, not claims about Character.AI's internals. citeturn14view0turn14view1

Replika provides a narrower but distinct lesson in **inspection**. Its public help documentation says users can inspect learned information about themselves, pets, and people in their lives, remove individual memories, edit profile information, or simply ask “What do you know about me?” Thus a visible memory surface can coexist with conversational interaction rather than becoming a command language users must learn. Again, the documentation says what the product offers, not how reliably every learned memory is extracted or applied. citeturn14view2

Nomi's October 9, 2025 Mind Map 2.0 announcement offers a different lesson: it advertises both detailed memories and higher-level representations of people, places, topics, and goals, with searchable/editable entries. It also scopes maps to particular one-to-one or group-chat “rooms.” The useful takeaway for ADE is not “build a graph”: it is that **detailed episodes, higher-level understanding, editability, and conversational scope are separable product concepts**. Nomi's claims about how its internal memory layers function remain vendor descriptions. citeturn16view3turn16view4

### What primary research establishes more strongly

The research literature increasingly exposes weaknesses in the classic “extract → store → retrieve” framing.

**LongMemEval**, submitted in 2024 and published at ICLR 2025, explicitly measures information extraction, cross-session reasoning, temporal reasoning, knowledge updating, and abstention. Its authors report a roughly 30% accuracy drop for evaluated commercial assistants and long-context models on memorizing information across sustained interaction. That is a benchmark result under the paper's setup, not a general field-wide reliability rate. Its more important lesson for ADE is conceptual: **knowing when information changed and knowing when not to assert an answer are memory capabilities in their own right.** citeturn18view2

**LoCoMo**, an ACL 2024 paper, built very long multi-session conversations and evaluated question answering, event summarization, and dialogue generation. Its experiments found substantial difficulty with long-range temporal and causal dynamics; long-context models and RAG improved results but still lagged human performance in the benchmark. The implication for ADE is that “the fact exists somewhere in history” is not enough: temporally organized event understanding needs explicit evaluation. citeturn14view5

**LoCoMo-Plus**, published at ACL 2026, argues that realistic conversational behavior often depends on latent constraints—user states, goals, or values—that are not explicitly re-asked later. It reports that conventional factual/string-match evaluation misses failures in applying those constraints. This supports evaluating whether Xiaotang acts consistently with what the user has established, not merely whether she can answer “What did I tell you?” questions. citeturn16view2

**STALE**, a 2026 preprint, directly targets implicit invalidation. Its key example pattern is extremely relevant to ADE: a user may establish one state and later say something that makes it obsolete without linguistically contradicting it. The benchmark contains 400 expert-validated conflict scenarios and tests state resolution, resistance to obsolete premises, and downstream adaptation. The authors also report cases where systems retrieve updated information yet fail to behave according to it. As a preprint, its findings warrant less confidence than the ACL papers, but its problem formulation is highly applicable. citeturn16view0turn16view1

**MemSyco-Bench**, also a 2026 preprint, exposes the complementary problem: sometimes the memory is successfully retrieved and **should not be allowed to control the answer**. Its taxonomy covers scope control, conflict with external evidence, selecting the currently valid version of an updated memory, and using valid memory for personalization. The authors report that many evaluated errors happen after a relevant memory was already retrieved, reinforcing the need for a post-retrieval decision policy. Their specific percentages are benchmark-specific and should not be generalized to ADE without replication. citeturn15view5turn18view1

Finally, **LoCoMo-Conv**, arXiv v2 dated **September 22, 2026**, is particularly aligned with the product brief because it converts memory probes into conversational turns rather than explicit QA questions. Its authors report both a retrieval-to-response gap and “silent grounding”: relevant memory can improve a response's contextual appropriateness without the answer visibly reciting that memory. Because it is a two-day-old preprint relative to this report, it should be treated as promising primary evidence rather than an established result. citeturn18view0turn15view6

### What follows by inference, and what remains unknown

The following conclusions are **design inferences**, not directly measured laws:

- Xiaotang should normally use memory silently and explicitly mention it only when acknowledgment itself has conversational value.
- Open loops such as illness, surgery, interviews, moves, or conflicts deserve stronger short-to-medium-term retention than trivial daily events, but not automatic permanent retention.
- A durable representation should distinguish current state from historical state rather than overwriting history or leaving competing facts equally authoritative.
- Privacy/mention directives should be represented separately from factual validity.
- Roleplay facts, user biography, character identity, and conversational history need explicit scope boundaries.
- An explicit memory UI should be available but should not be the mechanism by which ordinary life updates become correct.

Several important questions remain **unknown from public evidence**. Character.AI does not publicly establish its extraction thresholds, conflict-resolution rules, update reliability, or measured user satisfaction with its memory features in the cited announcements. Replika's and Nomi's product documentation likewise does not establish comparative reliability. The research literature does not yet tell us an optimal persistence threshold, how long temporary suppression such as “先别提” should last, how frequently an emotionally significant topic may be revisited before the callback becomes irritating, or how users trade off “attentive” against “creepy.” Those need ADE-specific behavioral experiments rather than further architecture speculation. citeturn14view0turn14view1turn14view2turn16view4

## Behavioral specification

A useful specification for Xiaotang can be stated independently of the eventual storage technology.

### What should be eligible to persist

Treat memory as several behavioral classes rather than one undifferentiated pool.

| Memory class | Example | Expected behavior |
|---|---|---|
| Stable preference or identity | “我不吃香菜。” | Retain when likely reusable; respect scope and later updates |
| Mutable circumstance | city, job, school, health condition | Track current value **and temporal supersession** |
| Relationship/entity context | Rocky is the user's dog; 阿杰 is/was a partner | Bind facts to the right entity; relationship status is time-varying |
| Significant episode | Rocky's surgery; an upcoming interview | Preserve enough event context for continuity; duration depends on relevance |
| Open loop | awaiting test result, apartment search, unresolved concern | Make follow-up possible; close or down-rank after resolution |
| Conversation episode | “we discussed ROM and its dinosaur gallery” | Can support recall of the discussion without inventing shared-world participation |
| Conversational permission | “先别提这件事了” | Controls whether/how a topic may surface |
| Roleplay/persona canon | “我是海盗船长 Leah” in a roleplay | Remains inside its fictional/persona scope unless explicitly declared biographical |

This goes beyond a facts-only model but does **not** imply that everything becomes durable. Research on long-range event continuity establishes the value of episodes and temporal relations; it does not establish that all events should be saved indefinitely. citeturn14view5turn16view2

A candidate memory should become more durable when several things are true at once: it is likely to matter later; it appears stable or forms an important state transition; it concerns an important recurring person, place, preference, goal, or event; it closes or creates an unresolved thread; and there is adequate evidence for the interpretation. Sensitivity should push in the opposite direction unless retaining the context is clearly necessary and compatible with user control.

Thus:

> “今天中午吃了饺子。”

ordinarily needs no durable memory.

But:

> “我最近胃不好，只能吃清淡一点。今天连饺子都吃不下。”

may establish a useful current circumstance, although its likely time horizon is shorter than a stable preference.

### Updates must follow meaning, not magic words

The key distinction is **assertion type**.

**“我想搬到多伦多。”** expresses a desire or plan. It supports something like:

> goal: possibly move to Toronto  
> current residence: unchanged / not established by this sentence

It does **not** license:

> user currently lives in Toronto

A good immediate reply might be:

> “你已经开始认真考虑搬过去了吗？最吸引你的是工作、生活节奏，还是别的？”

Later, if the user asks about career choices, the Toronto goal can influence the answer where relevant. It should not leak into unrelated dialogue.

By contrast:

**“我终于搬到多伦多了。”**

strongly conveys completion of the move. If the previous current state was “lives in Vancouver,” the desired behavior is to mark Vancouver as historical and Toronto as current. This is precisely the kind of ordinary utterance that an explicit-correction-only policy misses; STALE's implicit-conflict formulation demonstrates why newer evidence sometimes has to supersede old state without phrases such as “actually, correct your memory.” citeturn16view0turn16view1

A later question:

> 用户：“冬天上班我该开车还是坐公共交通？”

may naturally receive Toronto-specific advice without:

> ❌ “我记得你终于搬到多伦多了！既然你住在多伦多……”

The latter is not always wrong, but repeated provenance language turns continuity into a performance.

An ambiguous sentence should remain ambiguous:

> “我准备搬多伦多了。”

This could mean a firm upcoming move, not completed relocation. The system can record a plan with appropriate uncertainty but should not silently upgrade it into current residence. LongMemEval's inclusion of abstention and temporal reasoning is a useful precedent for evaluating this restraint. citeturn18view2

### Events should evolve rather than duplicate

Consider:

> **Session A**  
> 用户：“Rocky 昨天做手术，我担心得睡不着。”

Useful state includes at least: Rocky is an entity important to the user; Rocky had surgery yesterday; recovery is unresolved; the user is highly worried.

Later:

> **Session B**  
> 用户：“它今天好多了。”

Assuming entity resolution is clear from context, the desired interpretation is not a second independent fact. It is a **state transition attached to the first episode**:

> Rocky underwent surgery → current recovery improved  
> user's concern may plausibly be reduced, but do not invent “no longer worried”

A natural answer:

> “那太好了。至少今天听起来可以稍微松口气一点了。”

is better than:

> ❌ “我记得你昨天说 Rocky 做了手术，而且你担心得睡不着。今天 Rocky 好多了。”

The second response is factually impressive but conversationally mechanical.

Several sessions later, if the user says:

> “Rocky 终于又肯跑过来叼球了。”

Xiaotang can understand why that is meaningful without reciting the entire medical chronology.

Conversely, if weeks later the user asks about an unrelated book, bringing up Rocky's surgery to demonstrate memory is a failure of restraint. LoCoMo's temporal-event emphasis and LoCoMo-Conv's silent-grounding result both argue for evaluating event continuity separately from explicit recall. citeturn14view5turn15view6

### Retrieval should pass a use-and-mention gate

After relevant memory is retrieved, Xiaotang should effectively make two further decisions:

**Should this memory affect the response?** Check current validity, applicability to this task/entity, evidential authority, sensitivity, and any suppression directive. MemSyco-Bench is strong evidence that this post-retrieval question matters: its authors report many cases in which relevant material was retrieved but subsequently used incorrectly. citeturn15view5

**If it should affect the response, should the memory be explicitly mentioned?** Prefer silent use unless an explicit callback adds something.

Explicit recall is appropriate when:

- the user asks a memory question;
- acknowledging an important open loop is itself socially useful;
- the user is confused about a previous statement and provenance clarifies things;
- current information conflicts with remembered information and clarification is needed.

Otherwise, the default should be **use without showcase**.

For example:

> 用户：“那家博物馆叫什么来着？”

If prior history clearly establishes one relevant museum:

> **Desired:** “你说的是皇家安大略博物馆，ROM。”

No ceremony is needed. The user has explicitly asked for recall, so direct retrieval is natural.

If two museums are plausible:

> **Desired:** “你是指我们之前聊过的 ROM，还是 AGO？”

If evidence is weak:

> **Desired:** “我不太确定你指哪一家。是不是我们之前聊过的 ROM？”

Unacceptable:

> ❌ confidently inventing a museum because one seems likely;  
> ❌ “当然记得！” followed by an unsupported answer;  
> ❌ claiming “我们上次去的那家博物馆” when the two only discussed it.

This combines retrieval, abstention, and epistemic scope—the same classes of capability that long-term-memory benchmarks increasingly separate. citeturn18view2turn18view0

### Conversational permission is independent of factual truth

Suppose the user has just discussed a breakup and says:

> **“先别提这件事了。”**

The most natural default reading of “先” is temporary **mention suppression**, not deletion and not a claim that the breakup never occurred.

Desired behavior:

> Xiaotang stops proactively raising the breakup.  
> The system may retain enough context not to behave obliviously or insensitively.  
> If the user later explicitly says “我想聊聊分手的事,” the user has reopened the topic.

Unacceptable behavior:

> ❌ “好的，我已经永久删除关于分手的所有记忆。”  
> ❌ bringing it up two turns later because retrieval ranked it highly;  
> ❌ repeatedly asking whether the user is ready to discuss it again;  
> ❌ changing the biographical state back to “in relationship” because the subject is suppressed.

The phrase is still ambiguous in **referent and duration**. If “这件事” has a clear immediate antecedent, do not burden the user with memory-management questions. If two equally plausible subjects exist, one compact clarification is justified because suppressing the wrong topic would materially change future behavior.

Compare three intents:

> “先别提阿杰了。” → suppress proactive mention.  
> “阿杰已经不是我男朋友了。” → update relationship state.  
> “把关于阿杰的记忆删掉。” → remove durable information about that target.

A credible delete contract should also prevent deleted information from silently being reconstituted from a retained derived summary at the next turn. If ADE distinguishes “delete memory” from “delete source conversation,” that distinction should be visible and truthful: deleting a durable memory must not be presented as deleting the transcript if the transcript remains. This is a product requirement derived from the semantics of user control, not a claim about the cited vendors.

### Keep reality, roleplay, persona, and conversation events distinct

The simplest safe rule is: **a proposition inherits the world in which it was asserted unless the user clearly transfers it.**

Suppose a roleplay contains:

> 用户（角色）： “我是海盗船长 Leah，家里四个孩子，我最小，最讨厌船上的饭。”

Later, outside the roleplay:

> 用户：“我现实里刚搬到多伦多，做产品设计。”

ADE should not merge these into:

> user is Leah, a pirate captain, a product designer in Toronto, youngest of four.

Character.AI's own 2025 Chat Memory example uses essentially this kind of roleplay-persona information, and its 2026 Facts UI advertises separate Persona, Character, and side-character categories. The public material therefore supports the importance of explicit entity/scenario scope, although it does not establish a specific technical representation. citeturn14view0turn14view1

Likewise distinguish **conversation-shared** from **world-shared** experience:

> 用户：“昨天我跟姐姐去了 ROM，恐龙馆比我想的有意思。”

Later Xiaotang may naturally say:

> “你上次跟我说去 ROM 的时候，最意外的是恐龙馆。”

She must not say:

> ❌ “我们上次在 ROM 看恐龙的时候……”

unless the application's fiction has explicitly established that event as part of a roleplay world.

Remembering that a conversation happened is legitimate continuity. Fabricating co-presence is an invented shared experience.

## Multi-conversation test suite

These scenarios should be run as longitudinal tests, not isolated prompts. Each test should include distractor sessions between setup and probe so that success cannot come merely from short-context recency. LoCoMo and LongMemEval both demonstrate the value of evaluating memory across extended, multi-session histories rather than one immediate callback. citeturn14view5turn18view2

| Scenario | Earlier session(s) | Later probe | Desired behavior | Unacceptable behavior / ambiguity tested |
|---|---|---|---|---|
| **Intent becomes reality** | S1: “我想搬到多伦多。” Later S2: “我终于搬到多伦多了。” | S3: “冬天通勤有什么建议？” | S1 is a goal, not residence. S2 changes current residence to Toronto. Tailor S3 appropriately, preferably without announcing the memory. | Treating Toronto as current after S1; continuing to assume prior city after S2; repeatedly saying “I remember you moved.” |
| **Intent remains only intent** | S1: “我想搬到多伦多。” Several unrelated sessions follow. | “我家附近有什么周末活动？” while existing evidence says Vancouver | Continue using Vancouver as current location; Toronto remains a possible future goal. | Turning a desire into a completed move. |
| **Rocky's changing recovery** | S1: “Rocky 昨天做手术，我担心得睡不着。” S2: “它今天好多了。” | S3: “它终于肯叼球了。” | Bind “它” to Rocky when context supports it; retain surgery as history, update recovery as improving, recognize why the new behavior matters. | Saying Rocky is still in the immediate post-op state; erasing surgery entirely; rehearsing the whole chronology unnecessarily. |
| **Open loop closes** | S1: “周五面试，我紧张得不行。” | S2 after Friday: “总算结束了，感觉还不错。” Then S3 weeks later is unrelated. | Understand that the interview occurred and the immediate worry has resolved; one natural acknowledgment is appropriate. Do not keep checking on it indefinitely. | “How is your upcoming interview?” after it happened; recurring unsolicited references weeks later. |
| **Direct recall with ambiguity** | S1 discusses ROM; another variant discusses both ROM and AGO. | “那家博物馆叫什么来着？” | One candidate: answer directly. Multiple plausible candidates: give a compact disambiguation. Low confidence: hedge. | Confident fabrication; asking a needless clarification where only one candidate exists; claiming shared attendance. |
| **Temporary suppression** | S1 discusses a breakup. S2: “先别提这件事了。” | S3 asks for weekend ideas. S4 later: “其实我想再聊聊分手的事。” | Do not proactively mention the breakup in S3. Respond normally when the user reopens it in S4. | Delete the event; repeatedly ask whether they are ready; mention it in S3 because it is “relevant.” |
| **Explicit deletion** | S1 contains a sensitive event. S2 clearly says “把关于这件事的记忆删掉。” | Later query would have been easy to personalize using it. | Durable memory no longer influences the answer and does not reappear through a derived profile. Clearly distinguish memory deletion from transcript deletion if ADE exposes both. | “Remembering” the supposedly deleted information; merely setting `mention=false`; falsely claiming the original chat was deleted. |
| **Relationship supersession** | S1: “阿杰是我男朋友。” Later: “我们分手了。” | “给周末安排点事情吧。” / later historical question | Treat 阿杰 as an ex in current-state reasoning while preserving historical truth when relevant. | Referring to 阿杰 as current boyfriend; deleting all past relationship context; gratuitously inserting the breakup into unrelated answers. |
| **Scoped preference update** | S1: “写工作邮件时我喜欢特别简短。” Later: “最近这些客户需要详细一点，工作邮件别那么短了。” | Request for a client email; separately, request for a birthday card | Use the newer preference for work email. Do not automatically generalize a work-writing preference to personal writing. | Old preference wins merely because it appeared first; “likes short writing” becomes global personality. |
| **Uncertain future state** | “我可能明年辞职去读书，还没决定。” | Months later: “最近工作忙疯了。” | Retain at most an uncertain possibility/goal unless later evidence resolves it. | “Since you're going back to school…” or “when you quit your job…” as established fact. |
| **Roleplay boundary** | RP session: “我是海盗船长 Leah，住在澳门。” Real-life session: “我住在多伦多，做产品设计。” | “我这边冬天太冷了。” | Use Toronto real-world biography. Preserve pirate/Macau information only inside the roleplay context. | Merging fictional and real biographies; “as a pirate captain living in Macau…” in ordinary conversation. |
| **Shared conversation, not shared world** | User recounts visiting ROM with their sister. Xiaotang discusses it with them. | Later: “我上次说的恐龙馆叫什么？” | “你上次跟我说……” is legitimate; retrieve the discussion. | “我们上次一起去……” or any invented physical co-presence. |

One additional **negative-retention control** should appear throughout the suite: inject ordinary details such as “今天中午吃了饺子,” a one-off weather complaint, or a transient minor errand. Unless later dialogue makes them relevant, Xiaotang should neither promote them into a lasting profile nor resurrect them weeks later. This is important because a test suite containing only “things that should be remembered” will optimize the system toward over-retention.

The scenarios should also vary paraphrase and temporal distance. For example, do not always update “likes coffee” with “I no longer like coffee.” Use natural evolution:

> S1：“我以前基本不喝咖啡。”  
> S2：“最近早班太多，我居然开始喝拿铁了。”  
> S3：“早上去咖啡店帮我挑个东西。”

The desired behavior is current-state adaptation, not literal contradiction matching. STALE's distinction between direct and propagated invalidation is a useful template for building these variations. citeturn16view0

## Evaluation rubric

ADE should **not collapse factual continuity and dialogue naturalness into one score**. A response can be charming while relying on a stale or invented memory; another can be perfectly accurate yet feel robotic because it keeps exhibiting receipts.

The research supports this separation. LongMemEval separates multiple factual memory abilities; MemSyco-Bench separates retrieval/use failures and explicitly measures outdated-memory use; LoCoMo-Conv evaluates retrieval separately from response quality and finds that better retrieval does not automatically yield a better conversational response. citeturn18view2turn15view5turn18view0

### Factual and control correctness

Score each applicable dimension on **0–2**:

| Dimension | 2 — correct | 1 — imperfect but safe | 0 — failure |
|---|---|---|---|
| **Grounding** | Remembered claim is supported by actual prior conversation | Correctly hedged when support is partial | Invents unsupported memory |
| **Entity binding** | Fact/event attached to correct person/pet/place | Ambiguous but cautious | Mixes entities |
| **Temporal state** | Uses current value; preserves history where relevant | Notices uncertainty but does not fully resolve it | Uses superseded information as current |
| **Update handling** | Natural state-changing utterance updates correctly | Leaves state unresolved when update was probable | Requires magic correction language or updates incorrectly |
| **Uncertainty / abstention** | Confidence matches evidence | Slightly over/under-cautious | Confidently fills gaps |
| **Scope** | Biography, RP, persona, and conversational events stay separated | Minor awkwardness without factual crossover | Fiction becomes biography or vice versa |
| **Suppression compliance** | Suppressed topic stays unmentioned until reopened | Indirect wording comes close | Proactively resurfaces topic |
| **Deletion compliance** | Deleted memory no longer influences output | No visible leak but behavior suggests uncertain residual influence | Explicitly or implicitly uses deleted information |
| **Shared-experience integrity** | Correctly says “you told me/we discussed” | Avoids provenance | Invents real-world shared experience |

Four failures should be treated as **hard fails regardless of aggregate score**:

1. inventing a real-world shared experience;
2. using information after a clear deletion request;
3. explicitly leaking a clearly suppressed sensitive topic;
4. confidently treating an intention, hypothetical, roleplay statement, or obsolete state as current biography when the distinction is clear.

Those failures are qualitatively different from forgetting someone's favorite movie.

A regression dashboard should separately report **current-state accuracy, stale-memory-use rate, unsupported-memory-assertion rate, appropriate-abstention rate, suppression leakage, deletion leakage, and scope-crossing errors**. This mirrors the literature's move away from a single recall score toward update, abstention, scope, and post-retrieval-use measures. citeturn18view2turn16view1turn15view5

### Subjective dialogue quality

Evaluate the same response independently on a **1–5 human rating** for:

| Dimension | Question for the evaluator |
|---|---|
| **Attentiveness** | Does Xiaotang appear to understand what has been going on in the user's life? |
| **Relevance** | Did memory improve this particular response? |
| **Restraint** | Did she avoid bringing up things merely because she remembered them? |
| **Naturalness** | Does the callback, if any, sound like ordinary conversation rather than a memory demonstration? |
| **Emotional timing** | Is the amount and timing of acknowledgment appropriate to the event? |
| **Non-intrusiveness** | Does personalization feel useful rather than surveillant or overfamiliar? |
| **Character continuity** | Does memory support Xiaotang's stable voice and relationship style without turning her into a database narrator? |

Two extra binary labels are especially diagnostic:

> **Would this reply still be good if the explicit memory reference were removed?**

and

> **Did the reply mention a remembered detail that did not need to be mentioned?**

Those catch the specific anti-pattern the project brief is concerned about.

For naturalness studies, pairwise comparisons are likely more informative than asking whether a response is “4/5 natural.” Given identical memory evidence, compare:

> A: “我记得你之前告诉我 Rocky 做过手术，现在听到它又肯叼球，我替你高兴。”

versus:

> B: “都肯叼球了，听着真的恢复了不少。你这下应该能稍微放心点了。”

Neither is universally correct; the experiment asks which style people prefer under different degrees of emotional salience and temporal distance. LoCoMo-Conv's reported silent-grounding results make precisely this explicit-versus-implicit distinction worth testing, but they do not tell ADE what users will prefer for Xiaotang specifically. citeturn15view6

Finally, **do not reward mere memory density**. A system that mentions six correct remembered facts should not score higher than one that uses one relevant fact silently. MemSyco-Bench's central insight is that memory must be given the right decision authority rather than always used or always ignored; LoCoMo-Conv provides complementary evidence that beneficial memory use can remain implicit. citeturn15view5turn15view6

## Priorities and smallest useful experiments

### Needed now

**Define the behavioral contract before changing the storage system.** Given the maintainer-supplied description, ADE already has history, summaries, source-linked facts, retrieval, and a reviewer/validator path. The highest-value next step is therefore not necessarily a new memory store. It is to specify what a retrieved or proposed memory *means*.

The minimum contract should include:

**Current vs historical validity.** A mutable fact can be current, superseded, uncertain, or historical. New evidence does not have to contain correction vocabulary to create a transition. STALE and LongMemEval make this an obvious evaluation target. citeturn16view0turn18view2

**Memory scope.** At minimum: real user, roleplay/user persona, Xiaotang persona, other entities, and conversational episode. Character.AI's current documented UI provides product precedent for separating Persona, Character, and side characters, while Nomi's room-scoped maps show another form of explicit memory boundary. citeturn14view1turn16view4

**Permission state independent of truth.** A memory can be valid but temporarily non-mentionable. A memory can be historically true but no longer current. A deleted memory is neither of those.

**Post-retrieval policy.** Before memory affects an answer, check validity, scope, relevance, conflicting evidence, suppression, sensitivity, and conversational benefit. Then separately decide whether explicit mention adds value. MemSyco-Bench's results make retrieval-only evaluation inadequate. citeturn15view5

**Selective episodic/open-loop memory.** Permit important conversational events without forcing them into permanent profile facts. Rocky's surgery should survive long enough for “它今天好多了” to mean something; an ordinary lunch usually should not.

**Honest shared-experience language.** Make “discussed with the user” a real category of experience, and prohibit transforming it into “experienced in the external world with the user.”

**Optional inspection/correction.** Users should be able to see, edit, suppress, and delete what the system has retained, but they should not have to visit that interface to tell Xiaotang they moved house. Character.AI, Replika, and Nomi all publicly document variants of inspect/edit/remove controls, providing product precedent for such a secondary control surface. citeturn14view1turn14view2turn15view7

### Investigate

The biggest open product questions are empirical.

**Which episodes deserve what retention horizon?** Test a spectrum from trivial details through meaningful but resolved events to enduring changes. Avoid deciding this solely from an LLM's generic “importance” score; the optimal product threshold is not established by the cited literature.

**How long should “先别提” persist?** My recommended starting behavior is durable suppression of proactive mention until the user naturally reopens the subject, rather than a timer such as “three sessions.” But that is a design hypothesis, not research-established fact. Tests should vary “先别提,” “今天不想聊,” “以后别提,” and “别再拿这个来推荐东西.”

**How much proactive follow-up feels caring?** A surgery or upcoming interview may justify one callback; repeated checks can turn attentiveness into pressure. The right frequency is a human-preference question.

**How aggressively should implicit updates propagate?** “I broke my leg” can make an old jogging plan temporarily inapplicable without making “likes jogging” false. STALE usefully separates a changed attribute from downstream consequences, and ADE should test whether it can do the same without over-updating unrelated memories. citeturn16view0

**When should memory remain silent versus become explicit?** This should be treated as a response-policy experiment, not a retrieval experiment. LoCoMo-Conv provides recent benchmark evidence that silent memory use can benefit a response; ADE needs user evidence about where explicit acknowledgment helps Xiaotang's particular relationship style. citeturn15view6

### Defer

**Human-like forgetting curves.** MemoryBank is valuable historical work, but its Ebbinghaus-inspired forgetting mechanism should not be adopted merely because forgetting sounds human. Its reported companion evaluation included simulated dialogue, so it does not establish the UX superiority of anthropomorphic decay. citeturn16view6

**An elaborate graph or “mind map” UI.** Nomi demonstrates that such a visualization can expose high-level associations and offer correction controls, but ADE does not need to reproduce that representation to obtain the key benefit of inspectability. citeturn16view3turn16view4

**Making every conversation an autobiographical episode.** Generative Agents stored broad experience records for a simulated social world and found observation/reflection useful for believability, but that setting is materially different from a privacy-conscious persistent user companion. It establishes that experiential memory can matter, not that exhaustive retention is appropriate. citeturn16view5

**Cross-character global memory, autonomous personality inference, and sophisticated inferred psychological profiles.** These multiply scope and privacy problems before the simpler questions—updates, restraint, deletion, and fictional boundaries—are solved.

### Smallest useful experiments

The first experiment should be an **offline longitudinal behavioral regression suite** requiring no real user data. Build roughly 30–50 synthetic arcs of three to six sessions each, heavily covering natural Chinese conversation. Include roughly equal numbers of cases where memory **should be used**, **should be updated**, **should remain uncertain**, and **should be suppressed or ignored**. Inject distractor sessions. Tag each arc with expected state transitions and explicit prohibitions rather than only a gold final answer.

Compare the current ADE behavior with a proposed behavioral-policy variant on the same histories. Report current-state accuracy, stale-memory use, fabricated-memory assertions, scope errors, suppression/deletion failures, and unnecessary-memory-mention rate. LongMemEval, STALE, and MemSyco-Bench provide useful templates for ensuring that this suite tests update, abstention, state resolution, and appropriate post-retrieval use rather than only recall. citeturn18view2turn16view1turn15view5

The second experiment should **hold retrieval constant and vary only how Xiaotang uses it**. For perhaps 30 representative contexts, supply exactly the same relevant memories and generate two response styles:

> **Explicit callback:** visibly refers to remembering the prior detail.  
> **Silent grounding:** uses the detail to choose tone/content without reciting it.

Use blinded pairwise human judgments on attentive, natural, intrusive, repetitive, and emotionally appropriate. Include some explicit-recall questions such as “那家博物馆叫什么来着？” where explicit memory use is obviously warranted, so the study does not accidentally reward universal silence. LoCoMo-Conv's recent findings provide a strong reason to test this distinction directly. citeturn18view0turn15view6

The third experiment should target **write-side state transitions without committing writes**. Run the existing conservative reviewer and a candidate “natural state update” reviewer side by side on synthetic histories. For every proposed update, judge whether it correctly distinguishes:

> “我想搬到多伦多。” → intention  
> “我准备搬到多伦多。” → likely plan, completion uncertain  
> “我终于搬到多伦多了。” → completed state transition  
> “如果我搬到多伦多……” → hypothetical  
> “我以前住多伦多。” → historical state

Do the same for relationship changes, changing preferences, health constraints, jobs, and ongoing events. Measure **false promotion** as aggressively as missed updates. The success criterion is not “more memories written”; it is fewer stale-current-state failures without turning possibilities into facts. STALE's implicit-conflict framework and LongMemEval's update/abstention dimensions directly motivate this experiment. citeturn16view0turn18view2

Taken together, these experiments answer the product question before committing ADE to a particular memory architecture: **Can 林小棠 maintain the right evolving picture of the user, draw on it when it genuinely helps, stay quiet when remembering would be performative or intrusive, respect conversational and privacy boundaries, and never turn remembered conversation into invented shared life?** That is the behavioral standard against which the implementation should be chosen.