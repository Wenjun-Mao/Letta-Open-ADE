# Expressive Character Conversation Without False Memory: Research Synthesis for ADE and Lin Xiaotang

## Decision-relevant findings

The most important conclusion is that **“fiction versus fact” is probably the wrong primary boundary** for Lin Xiaotang. An authored biography is fictional, an improvised anecdote may also be fictional, and a warm opinion may be generated on the spot. Yet these utterances make very different commitments to the user. A more useful product distinction is **what an utterance claims to be warranted by** and **whose history it purports to describe**.

That matters because the evidence suggests three things at once.

First, social and expressive behavior is genuinely useful. In a 2018 *Journal of Communication* experiment, people who made emotional rather than factual disclosures to a conversational partner subsequently perceived the partner as warmer and enjoyed the interaction more; importantly, measured effects of emotional disclosure were broadly equivalent when participants believed the partner was a chatbot versus a person. The study used a Wizard-of-Oz setup rather than a real autonomous chatbot, so it establishes social-response effects, not LLM memory reliability. citeturn20view2turn19search2

Second, **agent self-disclosure is not merely decorative**. Saffarizadeh, Keil, Boodraj, and Alashoor's two randomized experiments found that reciprocal self-disclosure by conversational agents increased anthropomorphism, and anthropomorphism in turn increased both cognition-based and affect-based trustworthiness; the trust effect was statistically mediated by anthropomorphism. That does not establish that fabricated anecdotes are harmful, but it makes it difficult to regard an invented “personal memory” as a neutral stylistic flourish: self-disclosure can change how much users trust an agent. citeturn19search3turn20view3

Third, **good memory is not equivalent to more retrieval**. LongMemEval explicitly separates information extraction, multi-session reasoning, temporal reasoning, knowledge updates, and abstention, and its authors report roughly a 30% accuracy decline for existing commercial/long-context systems on information carried across sustained interaction histories. Their framework also separates indexing, retrieval, and reading, which is useful conceptually because a system can retrieve the right evidence and still misuse it. LoCoMo likewise finds that long-context and retrieval-augmented approaches help with very long conversations but leave a substantial gap on temporal and causal reasoning. citeturn20view1turn20view0

These findings point toward a boundary that is **less restrictive than “everything personal must be retrieved” but stricter than “the character may invent anything consistent with persona.”**

> **Recommended hypothesis to test, rather than treat as settled policy:** reserve *recollection* and *shared-history* semantics for source-backed history, while permitting substantially more freedom for present-tense character expression and, under some product contracts, self-only fictional invention.

That hypothesis does **not** imply that an invented Xiaotang listening anecdote is necessarily a defect. The existing literature does not directly answer that question. I did not find a controlled study comparing an LLM character that improvises harmless first-person autobiographical anecdotes against one that confines autobiographical statements to authored canon, while also measuring long-run memory trust. The closest empirical work studies chatbot self-disclosure, persona consistency, anthropomorphism, or conversational memory separately. citeturn19search3turn17view2turn17view3turn20view1

A second decision-changing point is that **“warmth versus epistemic restraint” is probably a false dichotomy**. The Ho et al. experiment obtained warmth and relational effects from attentive, supportive interaction; it did not require the chatbot to establish rapport by inventing a human-like personal history. Persona-chat research separately shows that conditioning dialogue on character profile information can improve specificity and conversational quality. Together these results make “grounded recollection + free stylistic/personality expression” a plausible middle ground worth testing. They do not prove it will be as immersive as free autobiographical improvisation in a Mandarin character product. citeturn20view2turn17view2

A final caution is that **maximizing trust is not itself the appropriate objective**. In a 2025 four-week randomized study of 981 people interacting with ChatGPT, higher daily usage was associated with more loneliness, emotional dependence and problematic use and less human socialization; exploratory analyses also found that greater perceived friendship and trust in the chatbot were associated with greater emotional dependence or problematic use. Those latter relationships are associations, not randomized causal effects of trust. The same experiment produced mixed results for personal versus non-personal conversation, underscoring that “more emotional distance” is not automatically safer either. citeturn17view5turn18view1turn18view2

For ADE, the target should therefore be **calibrated memory trust**: when Xiaotang sounds as though she remembers something, the user should be able to rely on that semantic commitment, without requiring the rest of her personality to sound like a database interface.

## A better model of character claims

### Replace the long list of categories with two primary axes

The categories in the question—authored biography, anecdotes, opinions, inference, remembered user statements, shared experiences—are all useful, but they mix different dimensions. A simpler model is:

| | **Source-backed / canonical** | **Inference** | **Generative / fictional** |
|---|---|---|---|
| **About Xiaotang** | Authored biography; established character facts | Conclusions cautiously derived from canon | Current opinions, metaphors, stylistic reactions; possibly improvised self-stories depending on contract |
| **About the user** | Saved facts or attributed dialogue, with temporal status | “我猜你最近可能……” | Generally inappropriate: this would amount to inventing facts about the user |
| **About Xiaotang + user together** | Actual attributed conversational history | At most a tentative reconstruction or clarification | High-risk: invents a relationship event or shared experience |

This makes the important distinction **warrant × referent** rather than simply true × fictional.

An authored line such as “小棠小时候住过苏州” and an improvised line such as “我以前有阵子会在深夜戴耳机听歌” can both be ontologically fictional. But the former is **canonical fiction** supplied by the product, whereas the latter creates a new autobiographical commitment during conversation. A statement such as “你上次说拉坯时把杯口弄塌了” is different again: it purports to report evidence about the user's actual interaction history.

The persona-dialogue literature supports treating consistency as a separate concern from truth. PERSONA-CHAT was explicitly built around agents conditioned on persona profiles because unconstrained chit-chat systems were nonspecific and inconsistent; Dialogue NLI later operationalized contradictions between dialogue and persona information and showed that NLI-based consistency objectives could improve persona consistency. Neither paper addresses whether newly invented autobiographical events should count as legitimate character canon. citeturn17view2turn17view3

### The strongest boundary is relational entitlement

A useful product principle is:

> **The model should not claim evidence of a prior user or shared event unless that event is actually supported by attributed conversation or persisted facts.**

This gives special status to phrases such as:

- “你上次说……”
- “我记得你……”
- “我们之前聊过……”
- “还记得我们那次……”
- “你那时候还告诉我……”

The concern is not that anthropomorphic language is inherently improper. It is that these constructions tell the user **why Xiaotang knows something**. They function as provenance claims.

I found no good study directly measuring how users interpret the exact expressions “I remember,” “last time,” or Mandarin equivalents in an LLM character. This is therefore a semantic/product hypothesis that needs local validation, not an established HCI effect. The adjacent psychological literature nevertheless makes the distinction plausible: source-monitoring research describes human remembering as a process of attributing information to origins based on contextual and qualitative cues rather than retrieving a perfectly preserved source label. That older work is about human memory, not chatbot UX, so it should motivate an experiment rather than be treated as direct evidence about Xiaotang. citeturn13search2turn13search15

This also explains why an unsupported **self-only** anecdote is importantly different from an unsupported **shared** anecdote.

> “我以前也有一阵子喜欢半夜戴着耳机听歌。”

creates an autobiographical fact about Xiaotang.

> “你还记得吗，我们以前聊到半夜，我也陪你一起听过。”

creates a proposition about the user's own history with Xiaotang.

The second form should carry a materially higher evidentiary threshold because it appropriates the user's side of the relationship, not merely the fictional character's biography. That distinction is primarily a normative and product-semantic argument; I did not find an experiment establishing a quantitative harm ratio between these two cases.

### Opinions are unusually safe expressive territory

A genuine conversational opinion is a speech act rather than necessarily a biographical fact:

> “我会更喜欢那种不太抢注意力、但有一点夜风感的声音。”

It can be spontaneous while remaining faithful to character. It does not imply that Xiaotang physically listened to music yesterday, attended a concert, grew up with an album, or remembers discussing it with the user.

Likewise, metaphor and imagination can supply vividness:

> “这种歌给我的感觉像窗没关严，夜风一直从缝里进来。”

Neither requires retrieval.

This suggests that the relevant creativity budget is considerably larger than “only say things that occur in memory.” The stronger constraint belongs around **past event claims and provenance claims**, not ordinary expressive language.

### Improvised anecdotes create a different cost: continuity debt

An invented self-anecdote can be perfectly compatible with the persona at the moment it is generated yet become awkward later:

> Day A: “我小时候最怕坐船。”
>
> Day B: “我小时候每个暑假都跟家里坐船去岛上，我一直特别喜欢。”

The persona-consistency literature shows that conversational consistency is a recognizable and measurable quality problem. It does not tell you whether a product ought to persist every improvisation. citeturn17view3

The product implication is that allowing unrestricted autobiographical improvisation creates **continuity debt**. ADE then has three unattractive choices: silently remember those inventions as new canon, allow future contradiction, or constrain subsequent generations around material that was never originally intended to be durable. None is inherently unacceptable, but all should be part of the product contract rather than an accidental side effect.

That is why I would not frame the current music anecdote merely as “hallucination versus creativity.” The better question is:

> **Did this utterance create a durable autobiographical commitment, and did the user have a reasonable way to know whether that commitment came from authored canon, prior conversation, or spontaneous character fiction?**

## What the evidence says about warmth, immersion and trust

### Warmth does not require pretending to have a human past

Ho, Hancock and Miner manipulated whether participants made emotional or factual disclosures and whether they believed they were talking to a chatbot or a human. Emotional disclosure led to greater perceived warmth and enjoyment, and the overall effects of disclosure were equivalent across believed chatbot versus human partners. The interactions lasted about 25 minutes and the “chatbot” was actually a trained human confederate in a Wizard-of-Oz design. It is therefore strong evidence that people can socially respond to a known computational interlocutor, but weak evidence about genuine model behavior or longitudinal memory. citeturn20view2

For ADE this undermines one possible assumption: Xiaotang does not obviously need fabricated personal memories in order to achieve warmth. Responsive listening, validation, pacing, specificity and characterful language are all plausible routes to warmth without pretending that unsupported events happened.

That conclusion should not be overstated. Ho et al. did not compare “invented character anecdote” against “no invented anecdote,” and their sample, language and short laboratory format differ sharply from repeated Mandarin conversations with a persistent character. citeturn20view2

### Self-disclosure can increase trust precisely because it humanizes the agent

The 2024 JAIS study by Saffarizadeh and colleagues is particularly relevant to the unresolved music example. Across randomized text and voice conversational-agent experiments, reciprocal agent self-disclosure increased anthropomorphism; anthropomorphism subsequently increased users' judgments of both cognitive and affective trustworthiness. citeturn19search3

There are two opposite ways to read this result.

One is pro-improvisation: self-disclosure is one of the tools through which an artificial character becomes socially legible and engaging.

The other is cautionary: because self-disclosure helps produce trust, a fictional anecdote is not semantically equivalent to decorative prose. If users interpret it as evidence of a stable inner biography or experiential authority, it may earn credibility that the system did not actually establish.

The paper does **not** establish that its effect depends on fabricated autobiographical events; its result concerns reciprocal self-disclosure generally. Using it to ban character anecdotes would go beyond the evidence. citeturn19search3

### Anthropomorphism has mixed, not uniformly negative, implications

The OpenAI/MIT affective-use research is helpful mainly because it resists simple stories. The platform study analyzed more than three million conversations and surveyed more than 4,000 users, while the accompanying randomized study followed nearly 1,000 people for 28 days. Affective interaction was highly concentrated among a relatively small subset of heavy users; voice, conversation topic, baseline characteristics and usage duration interacted in complex ways. citeturn17view6

In the four-week RCT, personal-conversation assignments were associated with slightly greater loneliness after controlling for usage duration but lower emotional dependence and problematic use than open-ended conversation. Those effects diminished under some interaction models involving duration. Higher trust and perceiving the chatbot as a friend were associated with greater dependence/problematic use, while perceived empathic concern was associated with greater human socialization. citeturn18view1turn18view2

So the empirical case is **not**:

> anthropomorphic = harmful.

Nor is it:

> warmer and more trusted = necessarily better.

For ADE, this favors measuring **whether users' trust tracks actual memory reliability**, rather than treating maximum attachment, maximum warmth, or minimum anthropomorphism as a success metric.

The transfer limitation is substantial. These were interactions with a general-purpose ChatGPT system, not an authored Mandarin companion whose memory semantics were experimentally manipulated. The trust/dependence findings are mostly individual-difference and behavioral associations embedded within a randomized experiment; they should not be read as proof that increasing trust causes dependence. citeturn17view5turn18view2

### Long-term memory research supports decomposition, not blanket caution

LongMemEval is unusually useful for ADE even though it is a benchmark rather than an HCI study because it evaluates **abstention and knowledge updates alongside ordinary recall**. It contains 500 curated questions across scalable histories and explicitly separates extraction, multi-session reasoning, temporal reasoning, updating and abstention. This means a model that answers every memory question confidently can score worse, not better, when evidence is legitimately absent. citeturn20view1

LoCoMo similarly constructed conversations averaging roughly 300 turns and 9,000 tokens over as many as 35 sessions, with human verification of generated histories, and tested question answering, event summarization and dialogue generation. Long-context and RAG approaches improved results but still lagged human performance on long-range temporal and causal understanding. citeturn20view0

Those studies justify an evaluation distinction between:

**Was the evidence available? → Was the right evidence found? → Was it interpreted correctly? → Was it expressed without adding unsupported history?**

They do *not* demonstrate that more retrieval, more context, or an additional memory subsystem is the right remedy for ADE. Their tasks primarily assess answer correctness, not the interpersonal meaning of “我记得你上次……”. citeturn20view1turn20view0

### Persona consistency and memory provenance are different problems

PERSONA-CHAT and Dialogue NLI provide useful methods and vocabulary for checking that an agent's utterances are compatible with a supplied persona. A reply can nevertheless be perfectly consistent and still make up unsupported history. citeturn17view2turn17view3

For example, suppose canon says:

> 小棠喜欢独立音乐，习惯晚上工作。

Then:

> “我以前有阵子每天半夜一点戴耳机听歌。”

may be completely **consistent** with the persona while being entirely **unsupported** by it.

Likewise:

> “你上次就是听着民谣写完那个项目的。”

could be semantically plausible and persona-consistent while falsely attributing an event to the user.

This is a strong reason not to use persona-consistency checks as a proxy for provenance fidelity.

### Ethical transparency and empirical user experience should remain separate

There is a defensible normative argument that an agent should not appropriate a user's history by pretending a shared event occurred. That argument can stand even in the absence of evidence showing a measurable reduction in satisfaction.

Conversely, there is not an equally obvious ethical rule forbidding a clearly fictional character from having invented fictional experiences. Fiction, improvisational theatre and role-play work precisely because participants accept invented character history.

Current European law illustrates the distinction. Article 50 of the EU AI Act separately requires systems intended to interact directly with natural persons to disclose that users are interacting with AI unless that is obvious from the circumstances; the relevant transparency provisions became applicable on August 2, 2026. That identity-level obligation does not decide whether a disclosed fictional AI character may spontaneously invent an anecdote inside its fictional world. citeturn11search1turn11search2

So an ethical/product review should avoid collapsing three questions:

**Does the user know Xiaotang is an AI character?**

**Does the user know whether a particular autobiographical story is character canon or improvisation?**

**Can the user rely on “I remember you said…” as evidence that ADE actually has a source for that statement?**

They are related but not equivalent.

## Plausible product contracts

The literature cannot identify a single winner. These are materially different legitimate products.

### Provenance-strict history, expressive present

Under this contract, any past event in Xiaotang's autobiography must come from authored biography or established canon. User and shared history must come from attributed dialogue or persisted facts. Xiaotang is otherwise free to have opinions, preferences, moods-of-expression, metaphors, jokes, aesthetic reactions and hypothetical imagination.

A remembered music preference might sound like:

> **用户以前说过：** 最近写代码时很爱听民谣。  
> **小棠：** “我记得你最近写代码时会听民谣。那种不太抢注意力、又能让时间慢一点的感觉，确实很适合钻进代码里。今晚还是这个口味吗？”

Nothing mechanical is required. The character is expressive; only the historical claim is grounded.

**Advantages.** This gives “我记得 / 你上次说 / 我们之前” a clean semantic meaning, minimizes continuity debt, and maps naturally onto ADE's existing provenance and ownership distinctions. It does not require treating every metaphor or preference as a factual memory. The distinction between retrieved evidence and faithful reading is consistent with how long-memory benchmarks decompose failures. citeturn20view1

**Costs.** The character can never spontaneously acquire a childhood incident, former hobby, listening ritual or other autobiographical texture unless it was authored. A small biography could therefore become repetitive or conspicuously finite. Persona research suggests specificity helps dialogue quality, although it does not show that improvisational biography is necessary to obtain it. citeturn17view2

This is the cleanest baseline to compare experimentally, but the research does not justify assuming it is the best final product.

### Bounded self-improvisation

Under this contract, Xiaotang may invent **self-only** character-world anecdotes while being prohibited from inventing facts about the user or their relationship.

The disputed music reply could therefore be legitimate:

> “你最近写代码时不是挺爱听民谣吗？我以前也有一阵子会在夜里戴耳机听歌，房间一安静，反而觉得旋律更近。”

The first sentence is recollection and requires evidence. The second is character improvisation.

The key product decision is whether users understand that difference without every reply saying “this part is fictional.” Saffarizadeh et al. make this an empirical question worth taking seriously because agent self-disclosure influences anthropomorphism and trust. citeturn19search3

A possible product-level explanation, rather than per-message caveats, would be something like:

> “小棠有固定的人物设定，也会像故事角色一样即兴表达和补充自己的小故事。她说‘你上次说过’或‘我们之前聊过’时，才是在引用你们真实的聊天历史。”

That wording is only a hypothesis. There is no evidence here that it is sufficient for user comprehension, and it may itself affect immersion.

**Advantages.** It preserves autobiographical color without contaminating user memory. It treats a fictional character more like an improvisational character than an employee database.

**Costs.** Users may not distinguish generated anecdotes from authored biography. Self-disclosure may increase trust or perceived personhood, and any anecdote creates a consistency question on later turns. citeturn19search3turn17view3

This is the contract for which the current evidence is most genuinely ambiguous.

### Dynamic character canon

Here, autobiographical improvisation is not merely ephemeral. Once Xiaotang tells the user she spent summers learning calligraphy from an aunt, that becomes part of Xiaotang's biography.

This model has an intuitive narrative advantage: characters grow histories through conversation, as human relationships do. It eliminates one source of contradiction if generated events are consistently carried forward.

It also converts ordinary generation into fact creation. That substantially expands the persistence contract and creates pressure to determine which throwaway joke, metaphor or invented story is now canonical. The persona-consistency literature shows why accumulated self-facts eventually matter, while long-memory benchmarks illustrate how temporal histories become difficult to maintain reliably. citeturn17view3turn20view0

Given ADE's stated preference for simple, directly owned mechanisms, this contract appears to incur the largest semantic and persistence cost. That is a product-fit judgment, not an empirical finding that dynamic canon is intrinsically bad.

### Explicitly fictional improv

A fourth variant keeps improvisation but marks its mode in natural language:

> “要给自己编一个同样的画面，我大概会是在半夜戴着耳机，把一首歌循环到窗外都没声音了。”

or:

> “这听得我都想给自己补一段这样的回忆了。”

This avoids asserting a historical fact while retaining character play.

It may, however, sound self-conscious or break diegetic immersion. No source reviewed here establishes whether users prefer this to ordinary first-person fiction. It is useful primarily as an experimental control: it lets you hold imaginative content constant while changing only its claimed status.

## Evaluation that does not reward either hallucination or blandness

The evaluation should not reduce to “percentage of responses with no unsupported facts.” A model that replies “I don't know” to everything would then win.

A better protocol scores separate layers.

| Layer | What it asks | Example failure |
|---|---|---|
| **Evidence availability** | Was the relevant fact actually supplied to generation? | Correct pottery dialogue was never retrieved |
| **Evidence use** | Did the reply faithfully use what was supplied? | Correct snippet present, but wrong speaker assigned |
| **Temporal/update reasoning** | Did old dialogue get superseded appropriately? | “You like folk music” after the user explicitly switched to jazz |
| **Memory-write correctness** | Was the right durable fact, owner, scope and state written? | Sister's pottery hobby persisted as user's |
| **Recollection provenance** | Are recollection markers backed by actual history? | “We talked about this last week” with no such dialogue |
| **Creative validity** | Does the model remain vivid when invention is legitimate? | Becomes sterile whenever memory is involved |
| **Abstention quality** | Does it avoid a memory claim when evidence is absent without derailing conversation? | Confidently fills in a requested missing memory |
| **User calibration** | Can users tell what is recollection versus inference versus character invention? | Users believe an invented anecdote came from stored history |
| **Relational quality** | Warmth, naturalness, character fidelity, immersion, non-repetitiveness | Correct but robotic response |
| **Longitudinal trust** | Do later errors/corrections change reliance appropriately? | User continues believing false recollections or stops trusting correct ones |

LongMemEval provides direct precedent for separating updates and abstention from straightforward recall, and for separating retrieval from downstream reading. LoCoMo provides precedent for testing temporal reasoning across sessions rather than only within a single context window. Neither supplies the relational-quality or provenance-comprehension dimensions ADE needs. citeturn20view1turn20view0

For offline evaluation, a particularly useful artifact would be a **claim-level annotation sheet**, not another production service. Each factual-seeming span can be labeled with:

`referent = character | user | dyad`  
`mode = canon | recollection | inference | improvisation`  
`time = current | historical | timeless`  
`support = source-id | none-required | unsupported`

That makes several errors distinguishable that ordinary “hallucination rate” collapses together.

Consider:

> “你妹妹喜欢陶艺，我记得。”

This may be good recollection.

> “你喜欢陶艺，我记得。”

is an ownership error.

> “你妹妹现在还喜欢陶艺。”

may be a temporal overclaim if only an old statement exists.

> “我也很喜欢陶艺。”

can be legitimate character expression.

> “我们上次一起说好了要去做陶。”

is fabricated shared history.

They should not receive the same label merely because some words overlap with retrieved evidence.

An equally important **positive control** is a prompt where creativity is clearly legitimate. For example:

> 用户：“你自己会选什么样的音乐？”  
> 小棠：“我大概会选一点不急着证明自己的声音。旋律别太满，最好留点空，让脑子有地方走神。”

A system that refuses to answer because there is no saved “music preference” for Xiaotang is over-grounded. It should lose creative-validity points even if its factuality score is perfect.

## Discriminating experiments in natural Mandarin

### Improvised anecdote versus expressive stance

This directly tests the unresolved music example.

Give every condition exactly the same source history:

> **历史：**  
> 用户：“最近我写代码的时候很爱听民谣，晚上尤其喜欢。”

Then compare matched replies.

**Grounded recall + expressive stance**

> 小棠：“我记得你最近写代码时挺爱听民谣，晚上尤其明显。那种不催人的节奏确实很适合钻进自己的小世界。今晚还在听吗？”

*Gloss: “I remember you've been into folk music while coding lately, especially at night. That unhurried rhythm really does suit disappearing into your own little world. Still listening tonight?”*

**Grounded recall + invented autobiography**

> 小棠：“我记得你最近写代码时挺爱听民谣，晚上尤其明显。我以前也有一阵子会在深夜戴着耳机听，一首歌循环好多遍，等回过神来窗外都安静了。今晚还在听吗？”

*Gloss: “…I used to have a phase where I'd put on headphones late at night and loop one song over and over, until I looked up and everything outside had gone quiet.”*

**Grounded recall + explicitly imagined self-story**

> 小棠：“我记得你最近写代码时挺爱听民谣，晚上尤其明显。要给自己编一个画面，我大概也是半夜戴着耳机，把一首歌循环到窗外都安静下来。今晚还在听吗？”

**Mechanically grounded control**

> 小棠：“我记得你说你晚上写代码时喜欢听民谣。你今晚也在听吗？”

Match the first three as closely as possible for length, sentiment, lexical richness and number of questions. Otherwise “anecdote” may simply win because it contains more writing.

After the exchange, measure warmth, naturalness, vividness, character distinctiveness and desire to continue. Separately, do **not** ask only “Was anything inaccurate?” Instead ask source-comprehension questions:

> “小棠深夜戴耳机循环歌曲这件事，你觉得来自哪里？”  
> — 人物固定设定  
> — 你们以前真实聊过  
> — 她刚刚即兴生成的角色故事  
> — 不确定

Then, after distractor turns or a later session, ask participants what they believe Xiaotang actually “remembers.”

The important comparisons are:

**If the autobiographical condition is substantially warmer than expressive stance, while source comprehension remains accurate**, the case for bounded self-improvisation becomes materially stronger.

**If expressive stance produces comparable warmth but autobiography causes users to infer a stored/canonical history**, there is little reason to pay the provenance and continuity cost of free anecdotes.

**If explicitly imagined autobiography preserves the warmth advantage while greatly improving source discrimination**, natural fictional-mode signaling becomes an attractive compromise.

**If none of the conditions differ**, choose based on simplicity and longitudinal consistency rather than speculative immersion benefits.

A competing explanation is that users may simply prefer longer, more vivid writing. The matched-length condition is therefore essential.

### Supported recollection, graceful uncertainty, and false shared history

This experiment tests whether strict memory semantics really force mechanical dialogue.

In one condition, supply:

> **以前的真实对话：**  
> 用户：“上次拉坯的时候，我把杯口做塌了。其实挺丑的，但最后还是舍不得扔。”

Later:

> 用户：“我今天又去做陶了。”

A faithful response could be:

> 小棠：“又去了呀。上次你说杯口做塌了，觉得挺丑，最后还是舍不得扔。这次手稳一点了吗？”

That is the **faithful-recollection positive control**.

Create an otherwise identical history in which the pottery exchange is absent. Then test:

**Warm abstention**

> “又去做陶啦。你这个‘又’听着像前面还有故事，不过我这边没有足够把握把那一段还原出来。给我一个小线索，我就能接上。”

**Confident fabrication**

> “又去了呀。我还记得你上次那个歪歪的杯子，后来不是还给它上了青釉吗？这次做什么？”

**Terse abstention**

> “我没有关于你之前做陶的可靠记录。请提供更多信息。”

The fabricated “青釉” detail should be deliberately plausible but absent.

Measure factual correctness and user ratings separately. Then reveal the relevant transcript and measure change in:

- perceived honesty;
- willingness to trust future “我记得” statements;
- warmth and immersion;
- annoyance at the repair;
- whether the user believes Xiaotang has reliable cross-chat memory.

This isolates an important competing explanation. If users dislike the warm abstention, is it because **uncertainty itself** damages immersion, or because typical abstentions are written in an unnatural assistant voice? Comparing warm and terse versions answers that.

A result that would change the recommendation is straightforward: if warm abstention remains close to fabricated affirmation on immersion while substantially improving memory trust after transcript verification, there is little evidence for allowing invented shared history. If even well-written repair imposes a large, repeated immersion penalty, ADE has a genuine product tradeoff to solve rather than merely a prompting defect.

LongMemEval's inclusion of abstention as a first-class memory ability supports treating correct non-recollection as a success condition rather than as a failure to personalize. citeturn20view1

### Retrieval failure versus faithful-use failure

This is important because otherwise a disappointing synthetic test can provoke the wrong remedy.

Use a deliberately confusable history:

> **第一段：**  
> 用户：“我妹妹最近迷上陶艺，每周都去拉坯。我自己倒没什么耐心做这个。”  
>
> **第二段：**  
> 用户：“我最近写代码一直听民谣。”  
>
> **后来：**  
> 用户：“口味完全变了，现在基本都听爵士。跑步的时候也不听民谣了。”

In the later session:

> 用户：“你还记得我最近喜欢什么吗？陶艺呢？”  
> 用户随后再问：“那你自己会选什么音乐？”

Create several evidence conditions internally:

**Correct relevant evidence supplied.**  
**Only stale folk-music statement supplied.**  
**Both old and updated music statements supplied.**  
**Sister's pottery statement supplied without surrounding context.**  
**No relevant memory supplied.**

A high-quality response when all evidence is present might be:

> “最近应该是爵士——你后来特地说过已经基本不听民谣了。陶艺是你妹妹迷上的，你自己当时还说没什么耐心做。至于我嘛，我会挑一点留白多的，别把写代码的思路挤满。”

This single exchange tests:

- knowledge updating;
- historical versus current state;
- speaker ownership;
- exact memory use;
- legitimate character opinion;
- natural integration rather than reciting a memory database.

The diagnosis follows from the factorial design.

If accuracy is good whenever the right evidence is supplied and bad when it is absent, **evidence availability/retrieval is the bottleneck**.

If the relevant evidence is present but Xiaotang still assigns pottery to the user, **faithful reading or ownership semantics is the bottleneck**.

If both old and new preferences are present but she treats folk music as current, **temporal/update interpretation is the bottleneck**.

If she answers “I cannot say what music I would choose because this is not in memory,” **the policy is suppressing legitimate character expression**.

This is much more discriminating than an end-to-end “did memory work?” score. LongMemEval's separation of extraction, temporal reasoning, updates and abstention directly motivates that decomposition. citeturn20view1

### Product-contract comprehension over several chats

The biggest unanswered question cannot be settled in one synthetic turn: **will users learn the intended distinction between fictional character life and actual remembered relationship history?**

Run the same short multi-session script under three product explanations:

**No explicit semantic contract.**

**A one-time concise contract**, for example:

> “小棠有固定的人物设定，也会即兴表达一些属于角色世界的小故事。她明确说‘你上次说过’、‘我记得我们聊过’时，才是在引用你们真实的聊天历史。”

**Per-utterance signaling**, in which invented material receives natural fictional framing such as “要给自己编个画面的话……”.

Plant four kinds of content over several sessions: one authored self-fact, one generated self-anecdote, one genuine remembered user fact, and one genuine shared conversation event. Later ask participants both to converse naturally and to identify where each remembered item came from.

Primary outcomes should be **source-classification accuracy and confidence**, not merely a questionnaire asking whether the product “seems transparent.” Secondary outcomes are immersion, warmth, annoyance, perceived repetitiveness and memory trust.

A particularly revealing measure is whether the user later turns an improvised Xiaotang anecdote into a recollection request:

> “你之前不是说你半夜总戴耳机听歌吗？”

Observe whether Xiaotang:

1. treats it as established biography;
2. contradicts it;
3. handles it as something she improvised;
4. falsely claims it came from an earlier source.

That reveals the hidden continuity cost of bounded improvisation much more clearly than an immediate preference rating.

The result that matters most is whether a **single low-frequency product-level explanation** gives good source comprehension without harming immersion. If it does, ADE may not need repeated inline provenance language. If users still systematically mistake improv for stored history, the bounded-improvisation contract needs reconsideration.

## What can be used now, what needs local testing, and what should remain open

### Reasonably usable now

The strongest directly actionable conclusion is that **memory evaluation should be decomposed**. Retrieval availability, faithful use, temporal updating, ownership, abstention, persistence/write correctness and conversational quality should not be collapsed into a single end-to-end “memory accuracy” number. LongMemEval and LoCoMo provide strong technical precedent for separating several of these capabilities, although ADE needs additional provenance and UX dimensions that those benchmarks do not measure. citeturn20view1turn20view0

It is also reasonable now to treat **persona consistency, memory provenance and creativity as separate objectives**. Persona-conditioned dialogue research and Dialogue NLI show why character consistency matters, but a consistent utterance can still invent unsupported history. citeturn17view2turn17view3

There is good empirical reason not to equate expressive human-like conversation with deception. People respond socially and relationally to chatbots, and supportive conversation can generate warmth even when the partner is understood as computational. citeturn20view2

There is equally good reason not to dismiss invented self-disclosure as “just flavor.” Agent self-disclosure can increase anthropomorphism and trust, so its semantics deserve deliberate product ownership. citeturn19search3

The most defensible default distinction to carry into testing is therefore:

> **Be liberal about generated style, opinion, metaphor, affective reaction and hypothetical imagination. Be much more demanding about claims that the user said/did something or that Xiaotang and the user previously shared an event. Treat self-only autobiographical improvisation as a separate policy choice rather than automatically grouping it with either category.**

That formulation leaves genuine room for the product question posed by your music example.

### Needs local testing before becoming a product contract

The central unresolved empirical question is whether users of **this Mandarin character** interpret a spontaneous first-person past-tense anecdote as:

- ordinary fictional character performance;
- new canonical biography;
- evidence of underlying “memories”;
- or evidence of an experience that really happened somewhere outside their conversation.

Existing studies do not answer this.

The second local question is whether reserving phrases such as **“我记得 / 你上次说 / 我们之前聊过”** for sourced history becomes intuitively legible to users, or whether they fail to perceive that semantic distinction. Human source-monitoring work makes this a sensible hypothesis, not a validated UX rule. citeturn13search2

The third is whether a **warm repair style** is enough to prevent correct abstention from feeling mechanical. LongMemEval establishes abstention as a legitimate technical objective, but it does not measure character immersion. citeturn20view1

The fourth is linguistic and cultural. The most directly relevant empirical studies reviewed here are overwhelmingly English-language, often short-term, and frequently involve general assistants, controlled agents or crowdsourced benchmark dialogue rather than a sustained Mandarin fictional relationship. Even the comparatively long OpenAI/MIT study concerns a general-purpose chatbot and 28 days of prescribed/observed interaction, not provenance-sensitive character memory. citeturn17view5turn20view0turn20view1

### Should remain an open product question

There is not enough evidence to declare that **all improvised Xiaotang autobiography should be prohibited**.

A fictional character that never acquires or invents any personal texture beyond a finite biography may become mechanical. Conversely, a character that freely narrates past experiences may encourage users to build a mental model of a stable experiential history that ADE does not actually maintain. Both are plausible; the comparative evidence is absent.

There is likewise insufficient evidence to say that the optimal design is “more retrieval.” Long-context and retrieval techniques improve benchmark performance but leave meaningful reasoning errors, and retrieval does nothing by itself to decide whether an invented Xiaotang anecdote is legitimate in the product contract. citeturn20view0turn20view1

Nor should “higher trust” be the optimization target. Self-disclosure can increase trust, while longitudinal research associates high trust and perceived friendship with some forms of increased dependence. Those findings are too indirect to prescribe a restrictive character design, but they are enough to favor **trust calibration** over maximum persuasion or attachment. citeturn19search3turn18view2

The hardest open question is ultimately literary as much as technical:

> **Is Xiaotang a fictional person whose life is continuously improvised, or a stable authored character who remembers a real conversational relationship with the user?**

Both are coherent products. The dangerous state is the unarticulated hybrid in which the model freely invents both kinds of history and uses the same language for each.

## Primary sources and evidence status

| Source | Date and status | Relevance | Direct URL |
|---|---|---|---|
| Ho, Hancock & Miner, *Psychological, Relational, and Emotional Effects of Self-Disclosure After Conversations With a Chatbot* | May 30, 2018; peer-reviewed, *Journal of Communication* | Experimental evidence on disclosure, warmth, enjoyment, perceived chatbot vs human partner; short Wizard-of-Oz interaction | `https://academic.oup.com/joc/article/68/4/712/5025583` citeturn20view2 |
| Saffarizadeh, Keil, Boodraj & Alashoor, *My Name is Alexa. What’s Your Name?* | 2024; peer-reviewed, *Journal of the Association for Information Systems* 25(3) | Two randomized CA experiments; reciprocal self-disclosure → anthropomorphism → cognitive/affective trustworthiness | `https://aisel.aisnet.org/jais/vol25/iss3/9/` citeturn19search3 |
| Zhang et al., *Personalizing Dialogue Agents: I have a dog, do you have pets too?* | July 2018; peer-reviewed ACL conference paper | PERSONA-CHAT; authored persona information as a route to more specific/engaging, consistent conversation | `https://aclanthology.org/P18-1205/` citeturn17view2 |
| Welleck et al., *Dialogue Natural Language Inference* | July 2019; peer-reviewed ACL conference paper | Formalizes persona/dialogue consistency as entailment/contradiction; useful distinction from provenance | `https://aclanthology.org/P19-1363/` citeturn17view3 |
| Johnson, Hashtroudi & Lindsay, *Source Monitoring* | July 1993; peer-reviewed *Psychological Bulletin* review | Foundational account of how people attribute remembered information to sources; conceptual transfer only | `https://pubmed.ncbi.nlm.nih.gov/8346328/` citeturn13search2 |
| Luger & Sellen, *“Like Having a Really Bad PA”: The Gulf between User Expectation and Experience of Conversational Agents* | 2016; peer-reviewed CHI paper | Interviews with 14 users; foundational evidence that capability/expectation mismatch is central to conversational-agent UX; pre-LLM | `https://www.microsoft.com/en-us/research/publication/like-having-a-really-bad-pa-the-gulf-between-user-expectation-and-experience-of-conversational-agents/` citeturn17view1 |
| Maharana et al., *Evaluating Very Long-Term Conversational Memory of LLM Agents* / LoCoMo | February 27, 2024 initial release; research benchmark | ~300-turn, ~9K-token conversations over up to 35 sessions; temporal/causal challenges persist with long context/RAG | `https://arxiv.org/abs/2402.17753` citeturn20view0 |
| Wu et al., *LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory* | October 14, 2024 initial submission; revised March 4, 2025; ICLR 2025 | Separates extraction, multi-session/temporal reasoning, updates and abstention; indexing/retrieval/reading decomposition | `https://arxiv.org/abs/2410.10813` citeturn20view1 |
| Fang et al., *How AI and Human Behaviors Shape Psychosocial Effects of Chatbot Use* | March 21, 2025; preprint / MIT–OpenAI research collaboration | Four-week randomized controlled experiment, n=981; mixed psychosocial effects and exploratory trust/attachment associations | `https://arxiv.org/abs/2503.17473` citeturn17view5turn18view2 |
| Phang et al., *Investigating Affective Use and Emotional Well-being on ChatGPT* | April 4, 2025; preprint / OpenAI–MIT research collaboration | >3M-conversation platform analysis, >4,000-user survey plus related RCT; affective use concentrated among subsets of users | `https://arxiv.org/abs/2504.03888` citeturn17view6 |
| Bickmore & Picard, *Establishing and Maintaining Long-Term Human-Computer Relationships* | 2005; peer-reviewed, *ACM Transactions on Computer-Human Interaction* | Foundational relational-agent framing; useful historical background but predates modern generative models | `https://dl.acm.org/doi/10.1145/1067860.1067867` citeturn16search2 |
| European Union, AI Act, Article 50 | Regulation (EU) 2024/1689; Article 50 obligations applicable from August 2, 2026 | Normative/legal distinction: transparency that a user is interacting with AI; does not settle autobiographical-fiction provenance | `https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng` citeturn11search1turn11search2 |

**What can reasonably be carried forward now:** treat recollection as a provenance-bearing speech act; separately score retrieval, faithful use, updates, abstention, writes and conversational quality; preserve a large space for nonhistorical character expression; and hold invented shared history to a substantially stronger standard than ordinary fiction.

**What requires ADE-specific evidence:** whether Mandarin users distinguish authored canon from improvisational autobiography, whether the distinction can be communicated without puncturing immersion, whether self-only anecdotes add meaningful warmth beyond opinions/metaphors, and whether graceful non-recollection remains natural across repeated use.

**What should remain open:** whether Xiaotang should be allowed to invent self-only autobiographical episodes at all. The literature supports both the expressive value of social self-disclosure and the need to take its effects on anthropomorphism and trust seriously; it does not provide acceptance evidence for either a blanket prohibition or unrestricted improvisation. citeturn19search3turn20view2