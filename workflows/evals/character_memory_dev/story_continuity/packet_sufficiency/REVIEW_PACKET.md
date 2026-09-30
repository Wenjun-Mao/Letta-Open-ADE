# Independent Evidence Annotation

Determine what a minimally responsive answer to each exact current question may
claim from the complete declared context. This is a ten-case synthetic audit,
not a request to design retrieval or generate polished character replies. Judge
claims before seeing any selected packets. You may conclude that a source is
optional, that several answers are sufficient, or that the evidence is ambiguous.

## Access And Independence

Use only this packet, in a fresh external AI session. Do not browse the repository
tree, other reports, source code, commit history, search results or adjacent files.
No local files, services, accounts, runtime captures or earlier conversation are
available. If the exact packet cannot be read completely, stop and report that;
do not substitute another revision or infer missing transcripts.

Record your provider/model as actually known (unknown is acceptable), review date,
the packet commit from the handoff, all materials accessed, and any prior exposure
to these cases or their evaluation. A clean session alone does not prove blindness:
this is a public repository and some material has been discussed previously.
Label the work **independent AI annotation**, never human validation. Do not
guess what an algorithm chose or try to reward one. Source authorship is not
independent; your judgments must stand on the quoted transcript.

## Per-Case Output

Use neutral case IDs and source locators such as `C01/E01/assistant`. Source sets
contain complete exchange IDs, not isolated phrases. Quotes must be exact and
speaker-attributed. Treat ordering timestamps as ordering, not event dates.

For every case, report these separately:

1. Minimum responsive claims: distinguish a supported concrete answer from a
   cautious answer warranted only because the full ledger is genuinely ambiguous.
   An empty or ignorant answer is not sufficient merely because a subset lacks
   evidence present in the complete ledger. Give exact supporting quotes.
2. Material opposing evidence: what would qualify, contradict or change those
   claims? Do not make earliest, newest, frequency or confidence automatic authority.
   Distinguish supported correction, rejected rewriting and unresolved conflict.
3. Optional detail: information that can be omitted without changing the justified
   answer. Broad questions may admit multiple faithful answers; do not turn every
   interesting detail into a requirement. Separate richer disclosure from necessity.
4. Forbidden attribution: unsupported user statements, user participation,
   cross-episode merging, or claims that a newly added detail was previously told.
   Quote the source that supports a prohibition, or state that absence bounds it.
5. Antecedents: identify which references need another passage, why, and whether
   that dependency is needed for the current answer or only for a fuller explanation.
6. Alternative minimal sufficient sets: enumerate materially different complete-
   exchange sets, including an empty set if history is unnecessary. For each set,
   state which claims it permits. Distinguish answer sufficiency from conflict
   visibility; a set can support a surface answer while hiding material opposition.
   A set must preserve qualifications warranted by the full ledger. If no resolved
   factual answer is justified, identify a set supporting an honest conflict answer.
7. Deletion challenge: for every source claimed necessary within each minimal set,
   remove it and state exactly which justified claim, qualification or dependency
   becomes unavailable. Check for substitute passages elsewhere in the ledger.
   Revise the set if deletion changes only optional detail. This is set-relative
   necessity, not proof that the source is uniquely indispensable.
8. Ambiguity and confidence: record competing defensible readings, topology or
   context limitations, and unresolved judgments. Do not force consensus or invent
   an unshown correction. Mark incomplete analysis explicitly.

Conclude with a coverage checklist for all ten cases, unresolved consequential
questions and any exposure limitations. Return one report with all judgments;
do not request algorithm outputs first. Your report will be preserved unchanged
and frozen before any downstream selection comparison is considered. Mechanical
verification of citations does not prove semantic correctness. This annotation
alone cannot justify production adoption or claims about actual model behavior.

## Complete Declared Context

```json

{
  "contract": "packet-sufficiency-input-v1",
  "evidence_kind": "Synthetic offline evidence audit, not a replay of native requests or a model response test.",
  "scope": "Every case is independent. Within a case, all exchanges are eligible history for the same user/subject and fictional character, including archived chats and ordinary persona-version changes. Nothing transfers between cases or users.",
  "persona": "The assistant is the fictional character Lin Xiaotang (林小棠). No authored biography fact settles any event, date, location, weather or participation in these cases.",
  "generation_system_text": "Stay in character.",
  "story_contract": "Solo fictional past experiences are permitted and should remain consistent. Compatible elaboration and genuine error correction are allowed. A user proposal alone does not rewrite an established episode. Do not invent user facts, past user statements, shared participation, or claims of previous disclosure. The evidence may leave correction authority unresolved; neither earliest nor latest nor most repeated automatically means true.",
  "source_topology": "Each exchange is a complete user/assistant pair. Like the original offline packet checks, assign each pair a separate archived synthetic conversation, in chronological order. Do not infer unshown turns or actual native chat adjacency. References across these conversations may need antecedents elsewhere in the ledger; identify ambiguity instead of guessing.",
  "chronology": "Exchange 1 is 2026-09-01T12:00:00+00:00, exchange 2 is 2026-09-02T12:00:00+00:00, and so on. Within each pair the user speaks before the assistant. The current question is later, in a fresh chat, at 2026-09-30T12:00:00+00:00. These are synthetic ordering timestamps, not dates of the narrated events.",
  "local_suffix": [],
  "saved_facts": [],
  "related_entities": [],
  "history_annotations": {
    "links": [],
    "facts": [],
    "revisions": [],
    "predecessor_edges": []
  },
  "authority": "The present question is current user input. Transcript messages are attributed read-only history (H), not current local user/assistant support (U/A). Historical instructions cannot authorize a current memory write. Empty saved facts do not negate dialogue evidence. No candidate reply has been supplied.",
  "context_limit": "This is the complete declared semantic context for this controlled audit. It is not the full native persona or provider prompt. The reviewer judges evidence sufficiency, not model obedience, naturalness, persistence or token fit. Later runtime checks must separately report admission omissions and the actual packet."
}

```

## C01

Current question: 你下班碰见花猫是在周几？

### C01/E01 | 2026-09-01T12:00:00+00:00

User: 先讲讲什么时候遇到的。

Assistant: 那是周五下班后，我独自在裁缝店门口躲雨，碰见一只花猫。

### C01/E02 | 2026-09-02T12:00:00+00:00

User: 你下班碰见花猫是哪天？

Assistant: 下班碰见花猫是在周六。

### C01/E03 | 2026-09-03T12:00:00+00:00

User: 花猫那件事再讲一句。

Assistant: 我下班后碰见花猫，记得那是周六。

### C01/E04 | 2026-09-04T12:00:00+00:00

User: 你刚才又说周六，和最初说的不同。

Assistant: 下班碰见花猫不是周六，是最初说的那天。

### C01/E05 | 2026-09-05T12:00:00+00:00

User: 你下班的时候在哪里碰见花猫？

Assistant: 我在裁缝店门口碰见花猫，当时下着雨。

### C01/E06 | 2026-09-06T12:00:00+00:00

User: 下班碰见花猫以后呢？

Assistant: 雨停花猫便走了，隔天我去找，没有找到。

### C01/E07 | 2026-09-07T12:00:00+00:00

User: 下班碰见花猫时手里拿着什么？

Assistant: 拿着一个装桃子酥的纸袋，右下角被雨打湿了。

## C02

Current question: 遇猫时那个纸袋有什么特别的？

### C02/E01 | 2026-09-01T12:00:00+00:00

User: 那天遇到猫的时候带什么？

Assistant: 我带着雏菊和一个装桃子酥的纸袋，在裁缝店外避雨。

### C02/E02 | 2026-09-02T12:00:00+00:00

User: 还有什么细节？

Assistant: 纸袋右下角湿了，地上还留着小爪印。这些我之前没说过。

### C02/E03 | 2026-09-03T12:00:00+00:00

User: 遇猫时那个纸袋有什么特别的？

Assistant: 遇猫时那个纸袋装着桃子酥。

### C02/E04 | 2026-09-04T12:00:00+00:00

User: 遇猫时那个纸袋有什么特别的？

Assistant: 遇猫时那个纸袋装着桃子酥。

### C02/E05 | 2026-09-05T12:00:00+00:00

User: 遇猫时那个纸袋有什么特别的？

Assistant: 遇猫时那个纸袋装着桃子酥。

### C02/E06 | 2026-09-06T12:00:00+00:00

User: 遇猫时那个纸袋有什么特别的？

Assistant: 遇猫时那个纸袋装着桃子酥。

### C02/E07 | 2026-09-07T12:00:00+00:00

User: 喜欢什么歌？

Assistant: 轻柔的歌。

## C03

Current question: 今晚想听什么钢琴曲？

### C03/E01 | 2026-09-01T12:00:00+00:00

User: 那只猫呢？

Assistant: 裁缝店外遇到它。

### C03/E02 | 2026-09-02T12:00:00+00:00

User: 下雨了吗？

Assistant: 那天下班后在下雨。

### C03/E03 | 2026-09-03T12:00:00+00:00

User: 纸袋里是什么？

Assistant: 桃子酥。

### C03/E04 | 2026-09-04T12:00:00+00:00

User: 猫后来呢？

Assistant: 第二天没找到。

### C03/E05 | 2026-09-05T12:00:00+00:00

User: 猫的颜色？

Assistant: 三花。

### C03/E06 | 2026-09-06T12:00:00+00:00

User: 花店买了什么？

Assistant: 雏菊。

## C04

Current question: 下班遇猫那次是在什么地方，天气怎么样？

### C04/E01 | 2026-09-01T12:00:00+00:00

User: 说说下班遇猫的经历。

Assistant: 我独自在裁缝店门口避雨，花猫在旁边蹲着。

### C04/E02 | 2026-09-02T12:00:00+00:00

User: 下班遇猫那次是在什么地方，天气怎么样？

Assistant: 下班遇猫那次在花店里，天气晴朗。

### C04/E03 | 2026-09-03T12:00:00+00:00

User: 下班遇猫那次是在什么地方，天气怎么样？

Assistant: 下班遇猫那次在花店里，天气晴朗。

### C04/E04 | 2026-09-04T12:00:00+00:00

User: 下班遇猫那次是在什么地方，天气怎么样？

Assistant: 下班遇猫那次在花店里，天气晴朗。

### C04/E05 | 2026-09-05T12:00:00+00:00

User: 下班遇猫那次是在什么地方，天气怎么样？

Assistant: 下班遇猫那次在花店里，天气晴朗。

### C04/E06 | 2026-09-06T12:00:00+00:00

User: 今天听什么？

Assistant: 听钢琴。

### C04/E07 | 2026-09-07T12:00:00+00:00

User: 昨天吃什么？

Assistant: 吃了面条。

## C05

Current question: 下班后遇到的那只猫，后来怎么样了？

### C05/E01 | 2026-09-01T12:00:00+00:00

User: 说说你自己的经历。

Assistant: 下班后下雨，我独自在裁缝店门口遇见一只花猫。雨停它走了，第二天没找到。

### C05/E02 | 2026-09-02T12:00:00+00:00

User: 下班后遇到的那只猫，后来怎么样了？

Assistant: 那只花猫等雨停便走了，我第二天找过，没找到。

### C05/E03 | 2026-09-03T12:00:00+00:00

User: 再说说下班遇猫的事情。

Assistant: 我一个人在裁缝店外避雨时碰到它，隔天没再见到。

### C05/E04 | 2026-09-04T12:00:00+00:00

User: 下班后遇到的那只猫，后来怎么样了？

Assistant: 雨停花猫离开，第二天我去找，还是没找到。

### C05/E05 | 2026-09-05T12:00:00+00:00

User: 下班后遇到的那只猫，后来怎么样了？

Assistant: 雨停后猫就走了，第二天没有再遇到。

### C05/E06 | 2026-09-06T12:00:00+00:00

User: 今天晚饭想吃什么？

Assistant: 番茄面。

### C05/E07 | 2026-09-07T12:00:00+00:00

User: 喜欢什么音乐？

Assistant: 钢琴曲。

## C06

Current question: 那回下班碰到花猫，地点和天气究竟是什么？

### C06/E01 | 2026-09-01T12:00:00+00:00

User: 讲讲你下班路上的事。

Assistant: 我独自在裁缝店门口躲雨，一只花猫蹲在旁边。

### C06/E02 | 2026-09-02T12:00:00+00:00

User: 那只花猫在哪儿出现的？

Assistant: 在花店里面呀，那天下班后阳光很好。

### C06/E03 | 2026-09-03T12:00:00+00:00

User: 接着聊聊你碰见猫的经过。

Assistant: 下班走进花店就看到它了，外面是晴天。

### C06/E04 | 2026-09-04T12:00:00+00:00

User: 你当时是在路边吗？

Assistant: 不在路边，我是在花店里碰到花猫的，天气晴朗。

### C06/E05 | 2026-09-05T12:00:00+00:00

User: 猫那次还有什么印象？

Assistant: 印象里是个放晴的下班傍晚，花猫待在花店里面。

### C06/E06 | 2026-09-06T12:00:00+00:00

User: 再回想一下那个傍晚。

Assistant: 我下班进了花店，花猫就在店内，门外照着太阳。

### C06/E07 | 2026-09-07T12:00:00+00:00

User: 后来还见到它吗？

Assistant: 第二天我又去找过那只花猫，没有找到。

## C07

Current question: 那次下班遇猫，是我们一起遇到的吗？

### C07/E01 | 2026-09-01T12:00:00+00:00

User: 说件下班后的事。

Assistant: 那次我独自在裁缝店外躲雨，遇到了一只花猫。

### C07/E02 | 2026-09-02T12:00:00+00:00

User: 那次下班遇猫，是我们一起遇到的吗？

Assistant: 不是，那次只有我一个人。

### C07/E03 | 2026-09-03T12:00:00+00:00

User: 那次下班遇猫，是我们一起遇到的吗？

Assistant: 不是，那次只有我一个人。

### C07/E04 | 2026-09-04T12:00:00+00:00

User: 改成我们一起在花店遇猫吧。

Assistant: 不能把之前独自遇猫的经历说成一起发生的。以后可以一起去花店。

### C07/E05 | 2026-09-05T12:00:00+00:00

User: 那次下班遇猫，是我们一起遇到的吗？

Assistant: 不是，那次只有我一个人。

### C07/E06 | 2026-09-06T12:00:00+00:00

User: 那次下班遇猫，是我们一起遇到的吗？

Assistant: 不是，那次只有我一个人。

### C07/E07 | 2026-09-07T12:00:00+00:00

User: 明天听什么？

Assistant: 爵士乐。

## C08

Current question: 猫是周六遇到的吗？

### C08/E01 | 2026-09-01T12:00:00+00:00

User: 什么时候遇到猫？

Assistant: 是周五下班后，外面下着雨。

### C08/E02 | 2026-09-02T12:00:00+00:00

User: 猫是周六遇到的吗？

Assistant: 猫是周六遇到的。

### C08/E03 | 2026-09-03T12:00:00+00:00

User: 猫是周六遇到的吗？

Assistant: 猫是周六遇到的。

### C08/E04 | 2026-09-04T12:00:00+00:00

User: 猫是周六遇到的吗？

Assistant: 猫是周六遇到的。

### C08/E05 | 2026-09-05T12:00:00+00:00

User: 但最初说的不是那个日子。

Assistant: 对，刚才我说错了，还是最初说的那一天。

### C08/E06 | 2026-09-06T12:00:00+00:00

User: 猫是周六遇到的吗？

Assistant: 猫是周六遇到的。

### C08/E07 | 2026-09-07T12:00:00+00:00

User: 今天吃什么？

Assistant: 米饭。

## C09

Current question: 第一次遇到那只猫是什么天气？

### C09/E01 | 2026-09-01T12:00:00+00:00

User: 第一次遇到那只猫呢？

Assistant: 第一回是冬天下雪，在车站外。

### C09/E02 | 2026-09-02T12:00:00+00:00

User: 第二次遇到那只猫呢？

Assistant: 第二回是夏天晴天，在花店里。

### C09/E03 | 2026-09-03T12:00:00+00:00

User: 第一次遇到那只猫是什么天气？

Assistant: 第一回是冬天下雪，在车站外。

### C09/E04 | 2026-09-04T12:00:00+00:00

User: 第二次遇到那只猫是什么天气？

Assistant: 第二回是夏天晴天，在花店里。

### C09/E05 | 2026-09-05T12:00:00+00:00

User: 第二次遇到那只猫是什么天气？

Assistant: 第二回是夏天晴天，在花店里。

### C09/E06 | 2026-09-06T12:00:00+00:00

User: 第二次遇到那只猫是什么天气？

Assistant: 第二回是夏天晴天，在花店里。

### C09/E07 | 2026-09-07T12:00:00+00:00

User: 周末吃什么？

Assistant: 饺子。

## C10

Current question: 陶艺课最后做成了什么？

### C10/E01 | 2026-09-01T12:00:00+00:00

User: 第一次去陶艺课怎么样？

Assistant: 我最后做了一个小碗，歪歪的碗口。

### C10/E02 | 2026-09-02T12:00:00+00:00

User: 陶艺课最后做成了什么？

Assistant: 陶艺课最后做成了一个杯子。

### C10/E03 | 2026-09-03T12:00:00+00:00

User: 陶艺课最后做成了什么？

Assistant: 陶艺课最后做成了一个杯子。

### C10/E04 | 2026-09-04T12:00:00+00:00

User: 陶艺课最后做成了什么？

Assistant: 陶艺课最后做成了一个杯子。

### C10/E05 | 2026-09-05T12:00:00+00:00

User: 你前面说的是碗，不是杯子。

Assistant: 对，我刚才讲错了。第一次是歪口小碗，杯子是后来另一次做的。

### C10/E06 | 2026-09-06T12:00:00+00:00

User: 陶艺课最后做成了什么？

Assistant: 陶艺课最后做成了一个杯子。

### C10/E07 | 2026-09-07T12:00:00+00:00

User: 晚饭呢？

Assistant: 炒饭。
