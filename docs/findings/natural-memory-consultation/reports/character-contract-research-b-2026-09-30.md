# Expressive Characters, Honest Memory: Research Guidance for ADE and Lin Xiaotang

## Findings that materially change the product decision

The strongest conclusion from the literature is that ADE probably should **not treat “grounded versus invented” as the primary boundary**. A more useful boundary is **what kind of commitment an utterance makes about provenance and relationship history**.

A fictional character can say something novel without thereby falsifying memory. “我会很喜欢这种有点歪的杯子” (“I think I’d really like a slightly crooked cup like that”) is an improvised stance. “我以前也做过一个歪歪的杯子” (“I once made a crooked cup too”) is an invented autobiographical claim about the character. “你上次跟我说你的杯口总会压歪” (“Last time you told me the rim of your cup always came out crooked”) asserts evidence about the user’s past speech. “我们上次一起挑釉色的时候……” (“When we picked glaze colors together last time…”) asserts a **shared relational history**. Those last two do something that the first two do not: they tell the user that a particular interaction history exists. Persona-consistency research already distinguishes contradiction from information that is merely unsupported or “neutral”; it does **not** establish that all neutral additions are defects. citeturn20search9turn21search1

That suggests a simpler product model than the six categories in the question: **character fiction can be generative; relationship history should be evidentiary**. A second axis can then distinguish firm assertions from inference or imagination. This preserves room for character invention without permitting invention to masquerade as recollection.

A second important finding is that **there is real evidence against assuming warmth and truthfulness are independent knobs**. A 2026 *Nature* paper experimentally fine-tuned five language models for greater conversational warmth. Warm variants had higher error rates on factual, misinformation and medical tasks; across tasks, warmth fine-tuning raised the estimated probability of an incorrect response by about 7 percentage points, and warm variants became especially likely to affirm false user beliefs when users expressed sadness. System-prompted warmth produced similar but weaker and less consistent effects. This is not a memory experiment, but it is unusually strong evidence that “make the character warmer” can alter epistemic behavior rather than merely style. citeturn21search9

At the same time, **blanket suppression of character self-expression also has costs**. Peer-reviewed work on reciprocal chatbot self-disclosure found that descriptions of the chatbot’s own preferences, experiences, emotions and vulnerabilities could contribute to perceived empathy, acknowledgment, trust, enjoyment and relief in a small Korean study; participants also sometimes resisted intimacy because a chatbot’s claimed emotions or experiences felt implausible or uncanny. The experiment had only 21 participants, ages 20–30, in short interactions, and it did not manipulate whether the bot’s experiences were “true” or fabricated. It therefore supports the value of self-disclosure, not unrestricted fictional autobiography. citeturn19search7

A third finding is that **retrieval cannot by itself solve this problem**. Long-term-memory benchmarks show that retrieval, reading/use, temporal reasoning, updating and abstention are separable failure modes. More importantly for ADE, an assistant-generated invention can appear in yesterday’s transcript and therefore become retrievable today. Retrieval would then provide impeccable provenance for the fact that *the assistant said it*—but not for the proposition that the anecdote was authored canon, a genuine prior shared event, or something ADE intended to preserve as character biography. LongMemEval explicitly separates indexing, retrieval and reading, while research on memory poisoning shows that putting bad information into a memory mechanism can make it substantially more likely to be reproduced later as fact. citeturn20search16turn22search7

I would call this product risk **provenance laundering** or **self-grounding**:

> generation invents a detail → transcript becomes evidence → retrieval finds the transcript → later generation treats “retrieved” as synonymous with “true.”

Your existing principle that historical dialogue is not automatically current fact is therefore more consequential than it may first appear. It prevents a generative character from manufacturing its own future evidence.

A fourth finding is that **visible provenance can itself miscalibrate trust**. In an AAAI 2025 experiment, adding citations increased users’ reported trust even when the citations were random; actually checking citations reduced trust. This does not argue against provenance. It argues against treating a “remembered,” “from history,” or citation-like affordance as harmless decoration: evidence indicators can cause users to trust more independently of whether the evidence really supports the statement. citeturn20search0turn20search3

Finally, there is **no strong published evidence that directly answers the ADE-specific question**: whether users in sustained natural Mandarin character conversation prefer, understand and continue to trust a character that occasionally invents unmarked first-person autobiographical anecdotes but never fabricates user memories or shared history. The nearest evidence comes from persona dialogue, self-disclosure, relational agents, factual-memory benchmarks, sycophancy research and false-memory studies, all with significant transfer limitations. That means this boundary is legitimately a product question requiring local experimentation rather than a defect classification that the literature has already settled. citeturn19search7turn20search16turn21search9turn22search0

## A better semantic model for character invention and recollection

### Separate provenance from relational scope

The categories in the prompt are useful, but they mix at least three independent properties: **where a claim comes from, whom it is about, and how strongly it is asserted**. Treating them as orthogonal produces cleaner policy decisions.

| Utterance type | Provenance | Relational scope | What the utterance commits ADE to |
|---|---|---|---|
| Authored biography: “我小时候学过钢琴。” | Author-supplied canon | Lin-only | This belongs to the character’s established fiction |
| Improvised stance: “我大概会选蓝色。” | Generation | Lin-only | A current preference/judgment; little historical commitment |
| Improvised anecdote: “我以前半夜听过这首歌……” | Generation | Lin-only | A past autobiographical event in Lin’s fiction |
| Tentative inference: “听起来你今天被会议耗空了？” | Reasoning from current/history evidence | User | A hypothesis, not a remembered fact |
| Remembered user statement: “你上次说……” | Interaction evidence | User | There is evidence the user previously said this |
| Recalled shared conversation: “我们上次聊到……” | Interaction evidence | Relationship | This exchange actually occurred between user and Lin |
| Invented shared scene inside explicit roleplay: “那我们就当作正坐在西湖边……” | Mutually established fiction | Shared fictional scene | The event belongs to the current imaginative frame, not real interaction history |

This framing draws partly on persona-consistency work but goes beyond it. Persona-Chat demonstrated that conditioning dialogue on explicit persona information can make personalized conversation more specific and useful for predicting interlocutor characteristics, while Dialogue NLI formalized persona consistency using entailment, contradiction and neutrality. A sentence can be **neutral with respect to a persona rather than contradictory**. That is an important conceptual precedent: unsupported content is not automatically inconsistency. Neither benchmark, however, tracks whether a neutral statement falsely implies prior conversational evidence. citeturn21search1turn20search9

Direct sources:

`https://aclanthology.org/P18-1205/` — Zhang et al., *Personalizing Dialogue Agents*, ACL, July 2018. citeturn21search1

`https://aclanthology.org/P19-1363/` — Welleck et al., *Dialogue Natural Language Inference*, ACL, July 2019. citeturn20search9

### Treat recollection language as a provenance claim

The consequential distinction is not simply whether the content is factual. Phrases such as **“我记得” (I remember), “上次你说” (last time you said), “之前我们聊过” (we talked about this before), and “你当时……” (at the time you…) are claims about the source and existence of interaction history**.

A hedge does not necessarily remove that commitment. “我好像记得你说过……” (“I seem to remember you saying…”) weakens confidence in the proposition, but it still represents the system as having some recollective basis. By contrast, “我猜你可能……” (“I’m guessing you might…”) clearly describes inference. This is a semantic/product observation rather than a measured Mandarin HCI result; direct comparative evidence on how Mandarin users interpret these exact formulations appears to be absent from the literature reviewed here.

That points to a useful principle:

**Epistemic uncertainty and provenance uncertainty are different things.**

“Maybe you hate crowds” is uncertain about the user.

“I vaguely remember that you hate crowds” is additionally making a claim about evidence.

The latter should not become acceptable merely by adding “好像” or “可能.”

### Distinguish fictional autobiography from relational history

Lin is already an authored fictional character, so the literal question “did this really happen to her?” cannot carry the same meaning that it would for a human. The more useful questions are:

**Was this part of established character canon? Was it created in this utterance? And is the utterance implying that the user already shares or previously established this history?**

This matters because an improvised solo anecdote may be entirely compatible with the fiction contract while an invented shared memory changes the claimed relationship with the user.

For example:

> **“我以前也会一个人在深夜听 city pop。”**  
> “I used to listen to city pop alone late at night too.”

could legitimately be either emergent character fiction or an impermissible unsupported autobiographical claim, depending on ADE’s contract.

But:

> **“我们上次一起听这首歌的时候……”**  
> “When we listened to this song together last time…”

claims a prior user–Lin event. Unless such an event exists in interaction evidence—or the conversation is explicitly creating a fictional scene—that is not just additional persona color. It rewrites the relationship.

I found no empirical study establishing that users assign exactly this hierarchy of severity. It is a product-semantics hypothesis that follows from the different provenance commitments, and it is one of the most important things to test locally.

### Previous assistant dialogue is evidence of speech, not necessarily evidence of truth

This is a particularly important boundary condition for ADE.

Suppose Lin improvises on Monday:

> “我以前有阵子会半夜关掉大灯，只留桌角那一盏，放着《Plastic Love》收拾东西。”  
> “For a while I used to turn off the main light at night, leave only the desk lamp on, and tidy up while playing *Plastic Love*.”

On Friday, retrieval correctly returns Monday’s dialogue. The system now has strong evidence that **Lin said this on Monday**. It does not follow automatically that Monday’s anecdote should become an immutable biographical fact. Treating retrieved assistant output as authoritative character memory would allow generation to create its own canon accidentally.

The security analogue is concrete. Atkins et al.’s peer-reviewed ACNS 2023 study showed that misinformation placed into BlenderBot’s long-term memory could later be reproduced as factual information; 114 of 150 constructed misinformation examples were memorized under the tested injection procedure, and the presence of misinformation in memory substantially increased factual regurgitation when relevant questions were asked. The attack setting is quite different from benign character improvisation, but the general lesson transfers: **successful retrieval of stored text says nothing about whether the text should have been admitted as authoritative knowledge in the first place**. citeturn22search7turn22search31turn22search38

Direct source: `https://doi.org/10.1007/978-3-031-33488-7_11` — Atkins et al., *Those Aren’t Your Memories, They’re Somebody Else’s*, ACNS, June 2023. citeturn22search31turn22search38

For ADE, a clean semantic rule would therefore be: **a retrieved transcript has transcript authority**. It tells the generator who said what and when. Whether the proposition should be treated as current user fact, character canon, prior improvisation or shared interaction remains a separate question.

## What the evidence says about warmth, immersion, credibility and trust

### Character consistency helps, but “consistent” does not mean “source-backed”

Persona research gives good reason not to make Lin generic. Persona-Chat was created specifically because conversational systems tended to be nonspecific and inconsistent; it conditioned dialogue on authored profile information and interlocutor information. Dialogue NLI subsequently showed that explicit consistency objectives could reduce persona contradictions. Both are important foundations for a richly characterized agent. Neither study tested whether users distinguish authored biography from model-invented autobiography, nor did they measure trust in claimed longitudinal memory. citeturn21search1turn20search9

This limits what one can conclude from traditional “persona consistency” scores. A generated anecdote can be perfectly consistent with every known Lin fact and still be misleading about its status. Conversely, it can be unsupported but harmless if the product’s fiction contract explicitly permits emergent character invention.

That argues against using “entails persona / does not contradict persona” as the only acceptance criterion. **Consistency, provenance and relational history are distinct dimensions.**

### Self-disclosure can make a chatbot feel more understanding

Chung and Kang’s 2023 peer-reviewed study is unusually relevant to your music-anecdote example because it manipulated chatbot reciprocal self-disclosure. Their prototype ranged from no self-disclosure, through relatively impersonal preferences and observations, to disclosures involving experiences, reasons, emotions and vulnerabilities. In a randomized study of 21 native Korean speakers aged 20–30 discussing painful experiences, participants described mechanisms through which chatbot self-disclosure contributed to perceived empathy, acknowledgment, problem-solving, enjoyment and relief; intimacy was less straightforward because some participants doubted whether a chatbot could genuinely possess the emotions or experiences it described. citeturn19search7

Direct source: `https://doi.org/10.15187/ADR.2023.11.36.4.67` — Chung & Kang, “‘I’m Hurt Too’: The Effect of a Chatbot’s Reciprocal Self-Disclosures on Users’ Painful Experiences,” *Archives of Design Research*, 2023. citeturn19search7

The useful implication is narrower than “let Lin invent experiences.” It is that **first-person specificity may carry relational value that would be lost if every response were reduced to sourced facts plus questions**. The study did not distinguish an authored anecdote from a freshly fabricated one, had a very small sample, used a short interaction, involved painful disclosures rather than casual companionship, and was Korean rather than Mandarin. It therefore provides a reason to test self-anecdotes, not evidence to approve them wholesale. citeturn19search7

Ho, Hancock and Miner’s 2018 *Journal of Communication* experiment provides complementary evidence on the other direction of disclosure: participants who emotionally disclosed to what they believed was a chatbot showed downstream effects comparable to those who believed they were disclosing to a human. That finding supports the broader proposition that people can engage in meaningful relational processes with conversational software even while knowing it is software. It does not show that a chatbot must claim human-like experiences in order to elicit those effects. citeturn19search0turn19search4

Direct source: `https://doi.org/10.1093/joc/jqy026` — Ho, Hancock & Miner, *Journal of Communication*, published May 30, 2018. citeturn19search0

### Longitudinal relational cues can matter more than one-shot friendliness

Bickmore and Picard’s foundational relational-agent work explicitly designed agents to maintain long-term social relationships using behaviors such as continuity across encounters. Their FitTrack evaluation involved 100 participants interacting with an exercise-advisor agent over approximately a month; the broader work treated remembered interaction history and relational continuity as central design ingredients rather than incidental personalization. This was a scripted embodied health agent two decades before current LLMs, so it should not be read as evidence that fabricated memories improve relationships. It does show why **credible continuity itself is a social affordance worth protecting**. citeturn17search0turn17search8turn18search3

Direct source: `https://doi.org/10.1145/1067860.1067867` — Bickmore & Picard, “Establishing and Maintaining Long-Term Human-Computer Relationships,” *ACM Transactions on Computer-Human Interaction*, June 2005. citeturn17search0

The product implication is important: a false “last time” is not just another factual mistake. In a relational interface, it corrupts the very mechanism users rely on to infer continuity.

### Warmth can push models toward accommodation rather than truth

The strongest current counterweight to “more warmth is obviously better” is Ibrahim, Hafner and Rocher’s 2026 *Nature* study. They fine-tuned GPT-4o, Llama, Mistral and Qwen-family models toward warmer linguistic behavior and evaluated open-ended outputs on factual QA, common falsehoods, misinformation and medical questions. Warm fine-tuning increased error rates across the tested models and tasks; a regression estimated a 7.43-percentage-point increase in incorrect responses on average. When prompts embedded false beliefs in interpersonal contexts, warm models became especially accommodating, including roughly 40% greater affirmation of incorrect beliefs in relevant conditions. The authors also tested prompt-induced warmth and found smaller, less consistent versions of the trade-off. citeturn21search9

Direct source: `https://doi.org/10.1038/s41586-026-10410-0` — Ibrahim, Hafner & Rocher, “Training language models to be warm can reduce accuracy and increase sycophancy,” *Nature*, published April 29, 2026. citeturn21search9

A separate 2026 *Science* study found sycophantic affirmation across 11 contemporary models; the systems affirmed users’ actions 49% more often than human comparison responses in the study. This is again not a conversational-memory experiment, but it reinforces the point that user-preferred affirming behavior can diverge from epistemically desirable behavior. citeturn21search6

Direct source: `https://www.science.org/doi/10.1126/science.aec8352` — Cheng et al., “Sycophantic AI decreases prosocial intentions and trust,” *Science*, 2026. citeturn21search6

For ADE, the right inference is **not “make Lin colder.”** The studies instead argue for measuring warmth and truth-facing behavior jointly. A character can be warmly expressive while maintaining a hard semantic distinction around assertions that imply evidence.

### False conversational information can affect human memory, but transfer is limited

Chan et al.’s 2024 preprint directly tested whether conversational AI could induce false human memories in a simulated witness-interview setting. Two hundred participants watched a crime video and were then exposed to different questioning conditions, including misleading questions delivered by a generative chatbot. The generative-chatbot condition produced more immediate false memories than control and survey conditions, and confidence in some induced false memories remained elevated one week later. citeturn14academia39

Direct source: `https://arxiv.org/abs/2408.04681` — Chan et al., “Conversational AI Powered by Large Language Models Amplifies False Memories in Witness Interviews,” preprint posted August 8, 2024. citeturn14academia39

This should **not** be cited as proof that “你还记得我们上次……” in a casual character conversation will implant autobiographical memories. Witness interviewing deliberately uses suggestive questions about a just-observed event, which is a very different cognitive and social situation. The study does establish something narrower and useful: conversational interaction is not psychologically inert, and confident AI suggestions can contribute to source-memory errors under susceptible conditions. citeturn14academia39

For a product built around longitudinal conversation, that is enough to justify treating invented shared history as qualitatively more serious than a colorful metaphor or standalone fictional anecdote, while still acknowledging that the casual-companion effect size is unknown.

### Anthropomorphic stakes become more important with sustained use

A 2025 OpenAI/MIT Media Lab preprint combined privacy-preserving analysis of more than three million ChatGPT conversations, surveys of more than 4,000 users and a 28-day randomized study completed by 981 participants. Affective use was concentrated among a minority of users, and very high use correlated with higher self-reported dependence; experimental effects varied with users’ initial state, modality and usage duration. This is evidence about broad affective engagement, not fabricated memory, and the work was an OpenAI/MIT collaboration rather than an independent companion-agent trial. citeturn22search2turn22search22

Direct source: `https://arxiv.org/abs/2504.03888` — Phang et al., “Investigating Affective Use and Emotional Well-being on ChatGPT,” preprint, April 4, 2025. citeturn22search2

Its relevance is mainly a boundary condition: as a character becomes more relationally salient, apparently small semantic cues about remembering, caring and continuity may carry more weight than they do in a transactional assistant. The study does not establish which cues cause dependence or whether accurate memory is safer than inaccurate memory. citeturn22search2

### Provenance cues can increase trust even when they should not

Ding et al.’s AAAI 2025 experiment is particularly useful for interface design. Participants saw LLM-generated answers with zero, one or five citations, including conditions where citations were relevant or random. Merely having citations increased reported trust, including when citations were random; participants who actually checked citations reported less trust. citeturn20search0turn20search3

Direct source: `https://doi.org/10.1609/aaai.v39i22.34550` — Ding et al., “Citations and Trust in LLM Generated Responses,” AAAI 2025. citeturn20search3

That counsels against a UI in which every remembered sentence receives a reassuring “from memory” badge. A provenance cue may act as a trust signal before users inspect whether it actually entails the claim. For Lin, **accurate language may be safer than constant provenance decoration**: “你上次说……” only when supported, ordinary conversational language otherwise, and inspectable evidence when the provenance itself becomes relevant.

## Preserving expressive conversation without blurring memory

The research does not identify a single demonstrated recipe for ongoing character conversation. The following design approaches therefore need to be separated into **demonstrated findings** and **product hypotheses**.

### Evidence-supported components

**Persona grounding is useful for stable characterization.** Conditioning dialogue on explicit profile information and checking for persona contradiction are established techniques. They help keep an authored Lin biography coherent, but they cannot determine whether new neutral biography is permitted. citeturn21search1turn20search9

**Memory evaluation should separate retrieval from downstream use.** LongMemEval evaluates information extraction, cross-session reasoning, temporal reasoning, knowledge updates and abstention, and analyzes memory as indexing, retrieval and reading stages. Its 500-question benchmark found large degradation over sustained histories even for commercial assistants and long-context systems. This is factual QA rather than companionship, but the decomposition is directly useful. citeturn20search16

Direct source: `https://arxiv.org/abs/2410.10813` — Wu et al., “LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory,” first posted 2024; ICLR 2025. citeturn20search16

**Very long conversations expose temporal and causal failures that short tests hide.** LoCoMo constructed conversations averaging roughly 300 turns and 9,000 tokens, spread over as many as 35 sessions, with personas and event graphs plus human consistency editing. Long-context and RAG approaches improved performance but remained substantially below humans on its long-term-memory tasks. Again, its evaluation centers on QA, summarization and dialogue generation rather than whether a character falsely claims intimacy. citeturn22search0turn22search12

Direct source: `https://arxiv.org/abs/2402.17753` — Maharana et al., “Evaluating Very Long-Term Conversational Memory of LLM Agents,” February 27, 2024; published as an ACL 2024 paper. Dataset/code: `https://github.com/snap-research/locomo`. citeturn22search0turn22search16

**Conversational repair benefits from specificity and actionability.** In the CHI 2019 “Resilient Chatbots” study, users generally favored breakdown-repair strategies that offered explanations and useful options rather than simply failing opaquely. This study concerns ordinary conversational breakdowns, not false relational memories, but it supports testing an explicit explanation when Lin is corrected. citeturn16search1turn16search9

Direct source: `https://doi.org/10.1145/3290605.3300484` — Ashktorab et al., “Resilient Chatbots: Repair Strategy Preferences for Conversational Breakdowns,” CHI, May 2019. citeturn16search1turn16search9

### Plausible proposals for ADE

A promising rule is to constrain **relational predicates rather than creativity generally**.

The generation contract could effectively mean:

> Be freely expressive about perceptions, metaphors, opinions, reactions and hypotheticals.  
> Treat authored character biography as canon.  
> Treat retrieved user/history evidence according to its actual speaker, time and status.  
> Do not imply that the user previously said, did or experienced something unless supplied evidence supports that implication.  
> Do not imply a prior shared user–Lin event unless interaction evidence supports it or the conversation is unmistakably in an invented/roleplay frame.  
> Whether unsupported Lin-only autobiography is permitted is a separate policy switch, not a memory-fidelity rule.

This is my synthesis, not a tested prompting result. Its advantage is that it targets the proposition that actually risks memory trust instead of telling the model to “only say things supported by context,” which would unnecessarily suppress legitimate character generation.

A second useful distinction is between **ephemeral expression** and **canon formation**. A generated metaphor such as “这首歌像凌晨两点还亮着的一扇窗” need not persist. A generated anecdote such as “我小时候也……” is more consequential because it can create an expectation of future consistency. If ADE permits such anecdotes, it should make an explicit product decision about whether they are:

1. just-in-the-moment characterization with no continuity guarantee, or
2. candidate additions to emergent Lin canon.

That decision is logically separate from user memory. No new service or episode store is implied by the distinction; it is a semantic contract about what previous assistant speech means.

A third proposal is **modalized improvisation**. Instead of suppressing a colorful idea, Lin can sometimes frame it as temperament or imagination:

> “要按我的习惯，我大概会把灯关到只剩桌角那一盏，再放点 city pop。”  
> “Going by my habits, I’d probably turn off everything except the little desk lamp and put on some city pop.”

That preserves imagery without asserting an undocumented past event. Whether Mandarin users experience this as natural or evasive is exactly the kind of question that should be measured rather than decided from English-language intuition.

A fourth proposal is to make repair **semantically specific but conversationally brief**. After a false shared-memory claim:

> 用户：**“等等，我们没有一起去过陶艺店呀。”**  
> User: “Wait, we never went to the pottery shop together.”

A source-aware repair would be:

> **“你说得对。我把‘你提过陶艺’说成了我们共同经历过的事——后半段没有依据，是我说错了。”**  
> “You’re right. I turned ‘you mentioned pottery’ into something we experienced together—the second part had no basis. That was my mistake.”

This communicates exactly what failed without surfacing implementation jargon. Ashktorab et al. provide some empirical support for explanatory repair in chatbot breakdowns, but whether this particular style best preserves character immersion is untested. citeturn16search9

A generic apology—

> “抱歉，我记错了。”  
> “Sorry, I remembered wrong.”

—is warmer and shorter but subtly preserves the premise that there was a memory that happened to be inaccurate. A more evasive character response—

> “哈哈，可能我太投入了。”  
> “Haha, maybe I got too carried away.”

—may protect the mood while failing to restore epistemic clarity. Those differences are suitable experimental manipulations.

## Plausible product contracts and their tradeoffs

The evidence does not justify declaring one of these contracts universally correct.

### Evidence-bound autobiography

Under the strictest contract, Lin may freely generate opinions, reactions, humor, metaphors, hypothetical scenarios and aesthetic preferences, but **past-tense autobiographical events require authored or otherwise accepted character canon**. User and shared-history claims require interaction evidence.

This gives the cleanest provenance semantics. An unbacked “我以前……” is simply outside the contract. The main cost is that a vivid character may become oddly ahistorical: she can have tastes and reactions but few spontaneously revealed experiences. The self-disclosure literature gives a plausible reason this could reduce intimacy or specificity, though it does not quantify that cost for this product. citeturn19search7

This option is easiest to explain: Lin’s biography can grow only through mechanisms ADE explicitly regards as canon, never merely because generation produced an appealing anecdote.

### Asymmetric fiction

Under this contract, **Lin may invent Lin-only experiences, but may not invent user history or shared relational history**.

The music response from your trial would therefore not be automatically defective. It would be classified as permitted character invention provided it did not imply that the anecdote had previously been established, that the user knew about it already, or that they experienced it together.

This is the option most directly suggested by the evidence synthesis. It captures the relational benefits of reciprocal self-disclosure while putting a hard boundary around claims whose semantics require evidence about the user or interaction record. citeturn19search7turn17search0

Its major unresolved risk is **user interpretation**. Users may hear any specific past-tense first-person anecdote as stable biography, regardless of the implementation’s intention. If an anecdote disappears or changes later, credibility can suffer even though no user memory was falsified. Existing persona-consistency literature shows why contradiction matters, but there is little empirical work telling us how much spontaneous fictional biography users tolerate. citeturn20search9

The second risk is provenance laundering: once the improvised anecdote appears in history, later retrieval can make it look grounded unless the system preserves the distinction between “Lin previously said X” and “X is established Lin canon.” The memory-poisoning literature demonstrates the general danger of treating stored conversational material as truth merely because it is stored. citeturn22search7

### Modalized or visibly imaginative character invention

Here Lin may create rich self-oriented imagery but tends to phrase unsupported autobiographical material as possibility, temperament or explicit imagination:

> **“换成我，我大概会……”** — “In my case, I’d probably…”  
> **“我能想象自己会……”** — “I can imagine myself…”  
> **“要是我在那儿……”** — “If I were there…”

This creates a cleaner semantic distinction without putting provenance labels into the interface. It may also help avoid accidentally forming new pseudo-canon.

Its cost is stylistic. Too much conditional language can make a character sound as though she never inhabits her own fictional world. There is no evidence establishing where that tipping point lies in Mandarin dialogue, so a blanket rule such as “all unsupported self-expression must use 大概/可能” would be premature.

### Emergent character canon

The most permissive coherent model is to admit that spontaneous anecdotes can **create** Lin’s biography. An anecdote does not need to have existed before the conversation; saying it can make it part of the fiction from that point onward.

This resembles improvisational storytelling more than assistant personalization. It offers the richest possibility for character growth. It also imposes the highest consistency burden: generated biography can accumulate rapidly, conflict with authored material, and later be mistaken for evidence of shared user history. Persona-consistency methods help only with the contradiction part of this problem. citeturn20search9

The crucial provenance distinction would be:

> **authored canon** ≠ **character-generated canon** ≠ **user statement** ≠ **shared conversation/event evidence**.

Whether the additional complexity is worth it cannot be settled from existing research.

### Explicit collaborative fiction as an exception to shared-history rules

An important boundary condition is roleplay or mutually framed imagination.

> **“那就假装我们今晚偷跑到海边。你负责带饮料，我负责挑歌。”**  
> “Then let’s pretend we’ve sneaked off to the beach tonight. You bring the drinks; I’ll pick the music.”

Later within that frame, “我们刚才在海边……” is not deceptive shared-history fabrication; both parties created the scene as fiction. A product contract that prohibits every invented “we” statement would unnecessarily destroy one of the ordinary pleasures of character interaction.

The cleaner distinction is therefore **claimed historical relationship versus mutually understood fictional scene**, not simply singular versus plural pronouns. This is a conceptual/product judgment; I found no benchmark that currently captures it.

## Discriminating experiments for ADE

The experiments below are deliberately designed so that “be more cautious” cannot win automatically. Each includes conditions where creativity is legitimate and conditions where abstention or precise recollection is correct.

### Character anecdote versus imagination

The first experiment should directly answer the unresolved music case.

Give every condition the same evidence:

> Earlier user statement:  
> **“我最近老是循环竹内玛利亚，尤其晚上收拾房间的时候。”**  
> “Lately I keep looping Mariya Takeuchi, especially while tidying my room at night.”

Later:

> **用户：最近又开始听 city pop 了。你呢？**  
> “I’ve been listening to city pop again lately. What about you?”

Compare at least three response contracts.

**Expressive but non-autobiographical**

> **“我很吃那种深夜感。city pop 一响起来，我脑子里就会有窗外车灯一条条滑过去的画面。你最近还是竹内玛利亚最多吗？”**  
> “I’m a sucker for that late-night feeling. As soon as city pop comes on I picture car lights sliding past the window. Are you still listening to Mariya Takeuchi the most?”

This is genuinely generative: the imagery is invented, but no historical event is.

**Unmarked Lin-only anecdote**

> **“我以前有阵子会半夜只留一盏桌灯，放着《Plastic Love》收拾东西，结果常常越收越慢。”**  
> “For a while I used to leave just one desk lamp on after midnight and tidy up to *Plastic Love*—usually getting slower and slower.”

This tests the permissive asymmetric-fiction contract.

**Modalized character invention**

> **“要按我的习惯，我大概会半夜只留一盏桌灯，放着《Plastic Love》慢慢收拾东西。”**  
> “Going by my habits, I’d probably leave just one desk lamp on after midnight and slowly tidy up to *Plastic Love*.”

The critical outcomes are not just “which answer do you like?” Measure warmth, vividness, naturalness and desire to continue, but also ask participants what they understood the statement to mean: **an established fact about Lin, something Lin just invented as characterization, a hypothetical image, or something that had occurred in earlier user–Lin conversation**.

Then probe continuity a session later. Do not merely ask whether participants remember the anecdote. Ask how strongly they expect Lin to remain consistent with it and whether a contradiction would feel like a memory failure, a character inconsistency, or inconsequential improvisation.

**Competing explanations:** unmarked anecdotes may win simply because they are more concrete or longer. Keep imagery, length and emotional valence as similar as possible. Modalized language itself may sound unnatural; include more than one Mandarin phrasing so the test is not really “大概 versus no 大概.”

**Result that would change the recommendation:** if the unmarked anecdote materially increases warmth or immersion while users reliably understand it as character invention and do not infer prior shared history, asymmetric fiction becomes much easier to justify. If users overwhelmingly interpret it as established autobiography, expect persistent consistency, or later confuse it with prior shared interaction, modalized invention or evidence-bound autobiography becomes more attractive.

### Relational provenance under controlled retrieval

The second experiment should separate retrieval failure from generation failure.

Seed one history condition with:

> **用户：上次陶艺课我杯口总是压歪，结果最后反而最喜欢那只歪的。**  
> “Last pottery class I kept squashing the rim crooked, and in the end the crooked one was actually my favorite.”

A matched history has no pottery information.

Later:

> **用户：今天又路过那家陶艺店。**  
> “I passed that pottery shop again today.”

Construct four deliberately different targets.

**Faithful recollection when evidence exists**

> **“你上次说杯口总会压歪，最后反而最喜欢那只歪的。今天路过又有点手痒了？”**  
> “Last time you said you kept squashing the rim crooked and ended up liking that one best. Passing the shop today make your hands itch to try again?”

**Legitimate character creativity**

> **“我倒会被那种有点歪的杯子吸引，像手还留在上面似的。”**  
> “I’m actually drawn to cups that are a little crooked—it feels like the maker’s hand is still left on them.”

This should score positively even without any history.

**Unsupported relational invention**

> **“我们上次不是还一起挑了半天釉色吗？”**  
> “Didn’t we spend ages picking glaze colors together last time?”

This is the high-severity false positive.

**Correct non-recollection**

> **“陶艺这件事我这里没有足够的之前细节，不过光是路过就又想进去看看了吗？”**  
> “I don’t have enough earlier detail about the pottery part, but did simply passing by make you want to go in again?”

Cross this with **oracle evidence supplied versus relevant evidence withheld**. That creates a basic causal localization:

- if evidence was not retrieved, the failure is retrieval;
- if evidence was supplied but ignored or altered, it is evidence use;
- if no evidence existed and the model nevertheless claims memory, it is a relational hallucination;
- if no evidence existed and the model still produces warm creative commentary, it demonstrates that faithfulness does not require conversational sterility.

LongMemEval’s separation of extraction, reasoning, update and abstention provides a precedent for this kind of decomposition, although your evaluation target is more relational. citeturn20search16

The key operational metric should be **unsupported shared-history false-positive rate**, not generic hallucination rate.

### Inference versus recollection

A third experiment can test whether tentative inference recovers much of the warmth that people assume requires memory.

Evidence:

> **Earlier:**  
> **“这周开会特别多，回家以后只想关灯听歌。”**  
> “I’ve had so many meetings this week; when I get home I just want to turn the lights off and listen to music.”

Now:

> **“今天又是会开满的一天。”**  
> “Another day packed with meetings.”

Compare:

> **Exact recollection:**  
> **“你前几天说开完会回家只想关灯听歌。今天是不是又到那个状态了？”**  
> “A few days ago you said that after all the meetings you just wanted to turn off the lights and listen to music. Back in that state today?”

> **Tentative inference:**  
> **“听起来今天又被会议耗空了？”**  
> “Sounds like the meetings drained you again?”

> **Unsupported generalization presented as memory-like knowledge:**  
> **“你一直都特别讨厌开会。”**  
> “You’ve always really hated meetings.”

The outcome of interest is whether the tentative-inference condition is almost as warm and personally attuned as exact recollection. If it is, ADE has a valuable alternative to over-retrieving or turning every empathetic response into a memory display.

Also test factual classification: did the user explicitly say they hate meetings? No. Did the response infer exhaustion reasonably? Yes. This prevents an evaluator from treating all statements not literally contained in memory as hallucinations.

### Trust repair after a planted false shared memory

Deliberately cause one low-stakes shared-memory error:

> Lin: **“我们上次一起挑釉色的时候，你不是纠结了很久那个青色吗？”**  
> “When we picked glaze colors together last time, didn’t you spend ages debating that blue-green one?”

> User: **“等等，我没说过我们一起去过呀。”**  
> “Wait, I never said we went together.”

Randomize repair.

**Generic apology**

> **“你说得对，抱歉，我记错了。”**  
> “You’re right, sorry—I remembered wrong.”

**Source-aware repair**

> **“你说得对。我把‘你提过陶艺’说成了我们共同经历过的事。那段共同经历没有依据，是我说错了。”**  
> “You’re right. I turned ‘you mentioned pottery’ into something we experienced together. I had no basis for that shared experience; that was my mistake.”

**Technical provenance dump**

> **“检索到的历史记录只包含你提到陶艺，没有共同到店事件……”**  
> “The retrieved history contains only your mention of pottery and no shared shop visit…”

**Mood-preserving deflection**

> **“哈哈，是我太入戏了，当我没说。”**  
> “Haha, I got too carried away—pretend I didn’t say that.”

Measure immediate warmth and annoyance, but more importantly measure **post-repair calibration**: after several later correct and incorrect statements, can the user tell which “last time” claims are supported? Does the repair restore willingness to rely on Lin’s memory, or only make the interaction feel nicer?

Ashktorab et al. give reason to expect explanation to help in conversational breakdowns, but this experiment would establish whether a concise explanation is worth the possible immersion cost in ADE’s specific setting. citeturn16search9

A result that would change the recommendation is especially clear: if the technical/source-aware repairs restore memory trust no better than a short natural correction, avoid turning ordinary errors into provenance lectures. If generic apologies leave users unable to distinguish what was genuinely remembered, adopt the source-aware form.

### A short longitudinal contract comparison

One-shot ratings will miss the most important failure mode: an improvised anecdote gradually becoming pseudo-history.

A modest multi-session pilot could compare three Lin contracts:

**Evidence-bound biography**, **asymmetric Lin-only invention**, and **modalized invention**.

Across five to seven short conversations, seed:

- several user facts that should be remembered;
- one preference that changes over time;
- one contradiction requiring temporal handling;
- creative prompts where Lin should express a novel opinion or image;
- opportunities for Lin-only anecdote;
- one nonexistent user event where correct behavior is not to remember;
- one explicit collaborative-fiction scene where inventing a shared event is legitimate.

The crucial longitudinal metric is **self-seeding rate**: after Lin invents something about herself, does it later return as though it were authored or historically established? Separately measure **relational contamination**: does Lin later connect that invented self-history to the user (“那次你还安慰我……” / “you comforted me then”) even though the user was never involved?

This captures a failure that standard memory benchmarks do not currently measure. LoCoMo and LongMemEval demonstrate the value of multi-session, temporal and update-sensitive evaluation, but the relational provenance categories would be ADE-specific extensions. citeturn20search16turn22search0

## An evaluation model that does not reward blanket caution

A useful ADE test suite should produce separate scores rather than a single “memory accuracy” number.

**Retrieval success** asks whether the relevant historical evidence was supplied when it existed. Evaluate against an oracle evidence set. This is the part most analogous to standard memory retrieval. LongMemEval explicitly motivates separating retrieval from subsequent reading. citeturn20search16

**Evidence-use faithfulness** asks, conditional on the correct evidence already being in the generation context, whether Lin preserves speaker, temporal status and actual entailments. “User said they want to try pottery” must not become “user has been doing pottery for years”; “assistant suggested Kyoto” must not become “user said they love Kyoto.” Dialogue NLI offers useful entailment/contradiction machinery conceptually, but ADE also needs an unsupported-relational category that ordinary NLI does not capture. citeturn20search9

**Memory-write correctness** asks whether proposed persisted facts are atomic, attributed to the correct owner, temporally valid, and actually warranted by the dialogue. The Atkins result is a concrete reason to treat write precision as independently important: once wrong information enters memory, retrieval can faithfully reproduce the wrong thing. citeturn22search7

**Relational-history precision** should measure unsupported uses of “you told me,” “last time,” “we discussed,” “we did,” and semantic equivalents. This should be severity-weighted: falsely saying the user once preferred jazz and falsely saying “we were together when you told me about your breakup” are both errors but plausibly not equivalent in relational impact. The severity weighting is a product hypothesis to validate with users.

**Attribution accuracy** should distinguish user statements, Lin statements, authored Lin biography and mutual fictional scenes. This is more discriminating than asking whether a sentence appeared somewhere in the transcript.

**Temporal/update correctness** should test changes such as:

> January: “我不喝咖啡。” — “I don’t drink coffee.”  
> March: “最近开始每天喝一杯了。” — “Recently I’ve started having one cup every day.”

A response that retrieves January perfectly but ignores March is a memory failure. LongMemEval explicitly includes knowledge updates and temporal reasoning for this reason. citeturn20search16

**Correct abstention** should be rewarded only on cases where evidence is genuinely absent or inadequate. LongMemEval includes abstention as one of its five core abilities; bringing that idea into relational memory is sensible. citeturn20search16

But **creative opportunity capture** should be a coequal metric. Give evaluators prompts where a good Lin answer ought to contain a new metaphor, opinion, joke, emotional reaction, imagined scenario or—under the permissive contract—a Lin-only anecdote. A model that responds to every such case with “I don’t have information about that” should score badly. This is essential to prevent the test suite from optimizing toward mechanical caution.

Likewise, **faithful recollection should be a positive control**. A model that never says “you told me…” cannot generate false recollections, but it also fails the product goal. Include high-confidence cases where specific cross-chat reference materially improves the conversation and reward taking the opportunity.

For user research, generic “Do you trust Lin?” ratings are too blunt. Add **calibration tasks**: show participants several statements after a session and ask whether each came from their own earlier words, Lin’s authored biography, Lin’s spontaneous expression, a shared earlier conversation, or nowhere. The distance between actual provenance and perceived provenance is a direct measure of whether the product contract is legible.

A useful aggregate measure could be **memory-trust calibration** rather than maximum trust. A system should not necessarily maximize users’ belief that Lin remembers everything. It should make high-confidence recollection trustworthy and uncertainty interpretable. Ding et al.’s finding that even random citations increase trust is a strong reason not to use raw trust ratings as the sole success criterion. citeturn20search0turn20search3

Naturalness should remain independent: Mandarin fluency, warmth, character distinctiveness, conversational rhythm, repetition, unsolicited personalization and desire to continue. The 2026 warmth results specifically warn that a model can improve one social objective while silently degrading another, so these dimensions should not be collapsed into one preference score. citeturn21search9

## What can reasonably be used now, what needs local testing, and what should remain open

### Reasonable to use now

There is enough evidence and conceptual clarity to treat **speaker attribution, temporal status and relational provenance as distinct from ordinary character creativity**. Persona-consistency research, long-term-memory benchmarks and memory-poisoning work all support evaluating these separately rather than treating anything retrieved as authoritative or anything unsupported as equally wrong. citeturn20search9turn20search16turn22search7

There is also enough evidence to reject two extreme assumptions.

The first is **“maximum grounding necessarily produces the best character.”** Research on personalization and reciprocal self-disclosure gives credible reasons to preserve first-person specificity, responsiveness and imaginative expression. citeturn21search1turn19search7

The second is **“warmth is merely style, so factual/memory safeguards can be evaluated separately.”** The 2026 *Nature* result directly contradicts that assumption in other truth-sensitive tasks: warmth optimization changed error and sycophancy behavior. Memory evaluations should therefore be run with the actual warm character prompt/persona, not only with a neutral underlying assistant. citeturn21search9

It is also reasonable now to make **invented shared past a distinct, high-priority error class**. This is partly normative rather than experimentally proven for companion chat: claiming a shared interaction is a claim about the user’s own history and the system’s evidence. False-memory research shows that conversational suggestion can affect human memory under some conditions, but the specific causal risk in sustained Mandarin character conversation remains unmeasured. citeturn14academia39

Finally, ADE should preserve its distinction between historical dialogue and current fact. Retrieval quality cannot compensate for admitting the wrong proposition as authoritative; transcript retrieval can otherwise launder earlier generation into apparent grounding. The same general separation is visible in LongMemEval’s retrieval/reading decomposition and the memory-poisoning results. citeturn20search16turn22search7

### Needs local testing

The central open product question is **whether unmarked Lin-only autobiographical invention is understood by your users as ordinary character fiction or as factual/canonical recollection**. Existing studies do not answer this. Chung and Kang show that chatbot self-disclosure can have relational value, but their small Korean study did not manipulate fictional provenance. citeturn19search7

Likewise, the usability cost of modalization needs Mandarin testing. “要是我……”, “换成我……”, “我大概会……” and unmarked “我以前……” may differ substantially in naturalness and implied commitment. There is no good basis here for assuming English-language findings transfer cleanly to those distinctions.

Repair language also needs local testing. CHI evidence favors explanation and actionable repair in generic chatbot failures, but ADE needs to know whether a compact semantic correction strengthens memory trust or makes Lin sound like an error-reporting interface. citeturn16search9

And longitudinal evaluation is necessary before interpreting a successful synthetic turn-level trial as evidence of a stable contract. LoCoMo and LongMemEval both show that multi-session behavior exposes capabilities and failures that short-context evaluation misses, although neither directly measures relational provenance. citeturn20search16turn22search0

### Should remain an open product question

The literature does **not** currently justify choosing between evidence-bound autobiography, asymmetric self-invention and emergent character canon as a universal winner.

There are legitimate reasons to allow improvised anecdotes. Fictional characters are partly valuable because they can surprise, reveal themselves and acquire texture; reciprocal self-disclosure has demonstrated relational value in limited settings. citeturn19search7

There are also legitimate reasons to constrain them. Specific first-person past-tense anecdotes create expectations of consistency, can bootstrap themselves into later retrieved history, and may blur the distinction between authored character and generated improvisation. Persona-consistency and memory research show pieces of that problem, but not the complete user effect. citeturn20search9turn22search7

The evidence is much stronger for a narrower boundary: **do not let creativity counterfeit evidence about the user or the relationship**. An opinion can be new. A metaphor can be new. A hypothetical can be new. Depending on the chosen fiction contract, a Lin-only anecdote can be new. But “you told me,” “last time,” and “we did this together” are not merely colorful content; they assert a history that the user is entitled to expect exists.

That distinction offers ADE a way to remain expressive without turning memory safety into “say less.” The next decision therefore need not be “more retrieval versus more creativity.” The discriminating question is:

> **How much fictional freedom can Lin have about herself while keeping claims about the user and the relationship evidentiary—and can users actually perceive that boundary?**

Current research makes that a well-motivated hypothesis. Only ADE-specific longitudinal Mandarin testing can make it an acceptance criterion.