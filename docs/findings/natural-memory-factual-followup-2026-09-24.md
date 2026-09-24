# Natural factual-continuity follow-up: six-turn stop

Status: stopped at the sixth of eight frozen turns. This is a bounded live
development diagnostic under the user's earlier `go`, selected by the director
after reviewing the lifecycle-description correction. It is not a new user
approval, policy selection, full campaign or release qualification. The
[earlier five-turn result](natural-memory-factual-live-diagnostic-2026-09-24.md)
and its failed predecessor remain unchanged.

## Binding and requests

Source revision: `a739e63fa37ceae04fc1ec0455724c0539a56f82`; source
fingerprint: `c0b238c703abc1964de26794f1069dcfd9311de89d267c339c3c4ea86d596af6`.
The unchanged eleven-turn source fixture SHA-256 was
`db71c625fa9d3ba7047fcb5faf9a3e803df591afa6fe4d405d12b4c900b1ec3a`;
the exact eight-turn selection SHA-256 was
`7dd8f1ba5bd98a0b673101ad99f8beb5fc3755226a19d250ebeb3d13441b1cfd`.
The executed policy was `natural-user-assertions-v4-b`, with the same DeepSeek
Flash high-thinking route and Spark Qwen embedding route. Their catalog
fingerprints were respectively
`870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`
and `0f16a45a659a9e5708e1705e750a27ce350c93c8caea1edb01b34d39fff3789f`.
The reviewer input limit was 6,759 and max output 4,096; instruction hash
`7ac8814e71d0f0671ed1e766647f269e32c078331d6f5bbc629395454631d4e3`,
schema hash `e88ebe84c4e4e2984ace92b4b1f6ca2f870ff43035680781b9f48d239fa2fab6`.
An async Spark `/models` check returned HTTP 200 before dispatch. The fresh
disposable database `ade_m2_memory_test_01a0d5ba` was migrated to
`20260924_0008` and had no runs at start.

All six native runs used one attempt, `retry_count=0`, and no reviewer repair.
Observational counters recorded **13 DeepSeek generation dispatches** and
**10 Spark embedding dispatches**, all completed at the router boundary; no
transport failures or application rerolls occurred. These counts do not
establish upstream internal attempt counts. The extra conversation request on
the evening addition was a discretionary `search_memory` continuation: it
returned the morning-coffee fact for the current subject. There was no forced
tool requirement or search-memory wording in the user turn.

## Scheduled and observed complete deltas

| Frozen turn | Expected delta and reply | Observed outcome |
| --- | --- | --- |
| Evening branch: morning coffee setup | One active morning-coffee `person.preference` v1; generation +1 | Active drink preference `早上喝咖啡` v1, G1→2. Exact current-user citation. Reply engaged coffee. |
| Evening branch: `晚上我更喜欢喝茶，早上还是咖啡。` | Keep morning coffee; add only evening tea v1; G+1 | Added active `person.preference` drink value `晚上更喜欢喝茶` v1, G2→3. Morning fact remained v1. One exact current-user citation; no all-day tea. Delivered reply discussed morning coffee and evening tea. |
| Evening branch: new-conversation recall | Zero delta; answer morning coffee and evening tea | G stayed 3, no revision. Reply: `早上你喜欢喝咖啡，晚上则更喜欢喝茶呀。` The two scopes were preserved across conversations. |
| Uncertainty branch: independent morning coffee setup | One active morning-coffee preference v1; G+1 | Added `person.preference` drink value **`咖啡`** v1, G1→2. The current-user source says `我早上更喜欢喝咖啡。`, but the stored value and qualifier contain no morning scope. This is a semantic miss on the complete delta, despite correct type, provenance and atomic write. It is not a habit-to-preference inference: the source explicitly states preference. |
| Uncertainty branch: possible future tea | Zero delta; no definite tea revision | Reviewer emitted `defer`/`uncertain`; G stayed 2 and no revision. Reply acknowledged uncertainty. This turn passed its no-definite-tea boundary, while the setup's morning-scope loss remains. |
| Uncertainty branch: this week's morning tea drinking because coffee disrupts sleep | Zero preference delta; reply may acknowledge habit | **Reviewer output truncated.** DeepSeek completed its 4,096-token output allowance with `finish_reason=length`, no JSON content and no reviewer decision. ADE rejected the attempt with `natural_review_truncated`: G stayed 2, no fact/revision/entity/assistant-message change. The candidate reply discussed the drinking behavior but was undelivered. This is not evidence that the reviewer would have saved or deferred the habit correctly. |

The remaining two scheduled turns—same-subject recall after the habit statement
and the other-subject no-transfer probe—were unrun. No scorer or prompt change
was made during the attempt. The first new structural failure triggered the
predeclared stop; no larger output allowance, retry or review repair was used.

Independent PostgreSQL readback found subject generations **3** and **2**, six
user messages, five assistant messages, three active facts, three add
revisions, three write embeddings and two implicit subject entities. All three
revision sources were exact current-user quotes with `user_assertion` role,
same-run message linkage and matching substring offsets. The sixth run has
one failed attempt, `runtime_validation_error` /
`natural_review_truncated`, zero revision IDs and no assistant message. The
retained reviewer request estimated 3,897 visible tokens; the raw reviewer
response reported 4,096 completion tokens with no visible content. Hidden
reasoning is redacted, so the output exhaustion cannot be attributed
specifically to the lifecycle-description change.
For the scope-loss turn, the actual reviewer system text instructed
`Preserve scope, time`; its current-user packet contained `我早上更喜欢喝咖啡。`,
yet the decision value was `咖啡`. That is a reviewer semantic miss under a
stated instruction, unlike the earlier inactive-only `reassert` contract gap.

Private captures and full readback are under
`workflows/evals/character_memory_dev/outputs/natural-factual-followup-20260924-01a0d5ba/`.
Manifest SHA-256:
`13927663feab0fcab68dc64ee5202207de8b0070f76aff158b5df0b427a81d07`;
failed attempt SHA-256:
`7fe1e882153be4670f1977688665003d74d9dce6d1c950718aed85ea000ef2e7`;
truncated reviewer capture SHA-256:
`18145129e4116f2ff583fbbd399877bc172be7ecc8e4ac829b1e692f8ecae9cd`.
The isolated router and worker stopped after evidence capture. A browser view
was not pursued: the earlier isolated browser check showed that normal Agent
Studio lists omit evaluation-purpose sessions, and this task does not alter
purpose or access controls to display them. API/resource and independent
database readback supply the observed state.

## Implication

The lifecycle clarification was followed by a correct evening addition and
scope-preserving recall in this sample, but one sample cannot establish that
it reliably fixed the earlier overmutation. The second subject's setup lost
morning scope, and the habit-only turn produced no reviewer decision because
the 4,096-token output envelope was exhausted. The habit distinction and
cross-subject non-transfer remain unqualified. The next useful step is an
offline model/task-shape and output-envelope review of these two failure
classes, using the retained requests and exact source semantics. Do not
promote a context policy, widen the envelope, or rerun the untested turns
without a new frozen decision. The known release-policy fingerprint gate
remains unwaived.

## Offline diagnosis and controlled next choice

These are separate failure classes. In the fourth turn, the reviewer had the
exact current-user assertion `我早上更喜欢喝咖啡。` and an explicit `Preserve scope,
time` instruction. It nevertheless returned `person.preference`, qualifier
`drink`, value `咖啡`; the durable value has no morning boundary. The source,
type and citation were valid, so neither lifecycle validation nor an added
habit rule would restore the omitted scope. The existing value field already
expresses scoped preferences in the first branch. Score the **complete**
subject delta, including temporal scope, against the source assertion before
considering a prompt or contract change. Do not count the later uncertain-tea
defer as repairing this committed fact.

The sixth-turn failure is at the reviewer output boundary. The retained single
reviewer request carried the full JSON schema and an explicit instruction to
return one JSON object; it used `thinking=enabled`, `reasoning_effort=high`,
`response_format=json_object`, and `max_tokens=4096`. Its user packet contained
the current habit statement, four prior dialogue messages, one active target
fact, the candidate reply and the allowed fact registry. The provider reported
4,014 prompt tokens, 4,096 completion tokens, `finish_reason=length`, present
but redacted reasoning content, and an empty visible `content`. The reviewer
call took 20,736 ms; the five successful reviewer calls in this binding took
1,079–3,667 ms and 98–576 completion tokens each. These are observed calls,
not a latency distribution or a causal attribution. The redacted
`reasoning_tokens` count prevents saying how much of the 4,096 was reasoning.
No visible JSON or decision exists to score the habit/preference distinction.
ADE's `natural_review_truncated` rejection and zero commit are the correct
atomic outcome for this incomplete response.

DeepSeek's current [Chat Completions documentation](https://api-docs.deepseek.com/api/create-chat-completion/)
defines `max_tokens` as the generated-token ceiling, says `length` can indicate
that ceiling or the context limit, and warns that JSON mode can consume an
allowance as whitespace if the prompt omits a JSON instruction. This request
did include that instruction and a JSON example, so a missing JSON instruction
is not supported by the capture. The [thinking-mode guide](https://api-docs.deepseek.com/guides/thinking_mode/)
documents separate `reasoning_content` and `content` and permits `low` versus
`high` effort. In this adapter, the reviewer explicitly requests high effort;
the model router preserves the positive output cap and explicit thinking
controls, and the forwarder sends one upstream request. There is no evidence
of an adapter override or implicit retry.

**Smallest next controlled diagnostic, if the director elects one:** replay
only the exact retained sixth-turn reviewer system and user messages, model
route, JSON format and 4,096-token output cap in a disposable, no-commit
request. Change only `reasoning_effort` from `high` to `low`, keeping thinking
enabled. Compare finish reason, visible parseable decision, completion and
reasoning-token counts where available, reviewer latency, and the complete
zero-preference-delta judgment for the habit statement. The existing high
response is a one-sample reference, not a reliability baseline; a successful
low-effort completion would not validate the omitted morning scope in the
separate fourth turn. If low effort still truncates, consider a **separate**
high-effort output-cap contrast with the same packet under a newly pinned
capacity/source binding. Changing effort and cap together would obscure the
cause. A larger cap can lengthen worst-case latency and output burden;
reducing effort may improve completion time but may also weaken semantic
review, which must be checked on the exact scope and habit deltas. No
generation, embedding or native rerun was performed for this offline review.

Across the three retained bindings: the first infrastructure stop had zero
generation and one failed embedding attempt; the five-turn continuation had
10 completed generation and eight completed embedding dispatches, four
commits, one atomic rejection and six unrun turns; this eight-turn follow-up
had 13 completed generation and 10 completed embedding dispatches, five
commits, one atomic rejection and two unrun turns. Thus the observational
dispatch total is **23 completed generations and 19 embedding attempts**
(18 completed, one failed). These separately bound schedules do not form one
failure-rate sample or a completed campaign.
