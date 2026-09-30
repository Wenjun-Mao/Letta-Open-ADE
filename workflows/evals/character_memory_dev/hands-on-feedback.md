# Hands-on trial feedback memo

Recorded: 2026-09-29. Source: the user's first Lin Xiaotang trial and supplied
screenshot of `杰克 · 第一次聊天` (messages 1–4). These are human observations and
future tuning questions, not release findings or authorization to change prompts.

## Character Tuning: Later

Keep the current memory trial's prompt/persona unchanged while collecting these
observations. Revisit them as a separate character-tuning task.

| Observation | Direction to explore | Avoid turning this into |
| --- | --- | --- |
| Short user messages receive relatively long replies. The brief “周末就呆在家里” gets an extended response and personal anecdote. | More proportionate reply length and comfortable short acknowledgments may feel more human. | A hard sentence/word limit or a requirement that all answers be short. |
| The user reports every reply so far ending with a question in a separate paragraph; both visible examples follow that pattern. | Vary conversational rhythm. Allow a statement or natural pause rather than always eliciting another answer. | A ban on questions or phrase-specific rules. |
| Xiaotang behaves like an established friend without asking the user's name or using the entered display name. | Examine first-meeting pacing, familiarity, and how a preferred form of address becomes known. | Mandatory name collection or assuming a UI display name has been disclosed in dialogue. |

Open question: is the display name merely an operator-facing identifier, or is
it intentionally supplied as character knowledge? Inspect the actual model packet
before changing this behavior. Neither interpretation is established by the
screenshot. Friendly tone alone does not prove a fabricated shared history.

## Small Trial UI Improvement

Show an unobtrusive per-turn summary of actual provider dispatch counts and tools
used. Separate conversation generation, memory review, and embeddings rather than
presenting tool calls as additional LLM requests. Count observed requests, not
estimated cost or spending limits (PC-09). Retain failed attempts where recorded;
unavailable historical counts must not appear as zero.

This should help the user understand a turn, not restore the internal-facing
configuration boxes just removed from the chat UI.

## What the Memory Observation Does and Does Not Show

The user reports that memory appeared to work, but the visible exchange is short
and remains in one conversation. It therefore does not distinguish recent raw
context from saved profile facts or retrieved older dialogue.

For a useful hands-on check, open a separate chat with the same person and same
character. Ask about an earlier detail without repeating the answer. Inspect
whether the old information entered through saved facts or admitted history.
An episodic detail not saved as a profile fact is useful for examining history
recall; archived chats remain eligible under PC-10. A new chat rules out that
chat's own preceding turns, but does not by itself identify the retrieval source.

An admitted source establishes availability, not proof that it caused the answer.
Likewise, a `search_memory` tool call is neither necessary proof nor the only
route: saved context and automatic historical retrieval can supply information
without an explicit tool call. Keep answer quality, memory writes, and source
availability separate when recording results.

## Follow-up Status

- Character style and first-meeting behavior: captured for later; no tuning made.
- Per-turn activity summary: implemented and checked in the isolated trial.
  Complete retained traces show generation, review, and embedding requests
  separately from tools; partial or absent traces stay labeled as such.
- Cross-chat recall: continue using the [playbook](hands-on-trial.md); this memo
  does not score the user's current conversation or infer its saved state.

## Director-Run Trial: 2026-09-29

Direct built-in-browser trial, 20:49-20:54 America/Toronto. Nine new turns,
four chats, two fictional people; all nine delivered once, with one native
attempt each. No rerolls, prompt edits, restarts, or changes to the user's
existing conversations. The first newly created chat was archived deliberately.
This is exploratory AI review, not a frozen benchmark or human acceptance.
Relevant agreements: PC-01/02/03/05/09/10.

Served code: `6dacaafefe1dfb21c1b2ad32bb9feaf4bb73307f`; history recipe
`probe_local_qwen_cosine_v2`; existing `chat_v20260926` and `chat_linxiaotang`.
DeepSeek supplied generation/review; the pinned Qwen route supplied embeddings.
No deployment, default, release binding or stale-policy gate changed.

### What Happened

| Check | Observation and limit |
| --- | --- |
| Introduction | The user explicitly said their name, Ottawa location and folk-music preference. All three were saved; Xiaotang used the disclosed name. This does not test knowledge of a UI-only display name. |
| One-off story | A failed pottery cup became a key dish. No pottery profile fact was created. The separate statement `最近常听陈粒` did become a music-preference fact: its citation is valid, but habitual listening is not an explicit preference assertion. This is a semantic concern, not a citation failure. |
| Unrelated question | The answer correctly calculated 18:35 + 40 minutes as 19:15. It did not end with a question, so the earlier question-ending pattern is not universal. |
| Archived continuity | After chat 1 was archived, the first reply in chat 2 spontaneously mentioned the dish. Activity showed all three archived exchanges admitted and no earlier messages in chat 2. This brought the answer back into local context before the later deliberate recall question. |
| Factual correction | Ottawa became Halifax, version 2, with the new user statement cited and the original revision retained. Attending heavy metal did not replace the explicitly reaffirmed folk preference. |
| Recall after distraction | After city and music turns, the model correctly recalled the dish. The original archived story ranked into admitted history, but the current chat also already contained the answer; this is not history-only causal evidence. |
| Fresh-chat recall | Chat 3 began with a pottery question without the answer. The reply recalled the cup, collapsed wall, dish and keys. Activity showed no prior chat messages, zero retrieved profile-fact IDs and four admitted older exchanges, including the archived original. No saved pottery fact exists. This rules out this chat's earlier turns as the explanation, not every alternative causal mechanism. |
| Unsupported embellishment | That same fresh-chat answer added `你舍不得扔`, pressing the clay into shape, and putting the dish `在门口`. None appeared in preceding source messages. The correct central outcome does not make these details supported. No new facts/revisions were committed by this reply. |
| Speaker attribution | The next reply correctly recalled Halifax and folk, then said `你说过她唱歌有一种很轻的倔强`. The phrase originated in Xiaotang's own chat-1 reply, not the user's statement. The original exchange was admitted. This is a delivered source-attribution error; it caused no new fact/revision. |
| Separate person | The fresh second person asked about their city/music. Two successful `search_memory` calls returned zero results; no prior history or profile-fact IDs were supplied. The reply said it did not know, and the subject retained no facts. This one case is not general isolation/security qualification. |

### Readback And Retained Evidence

- First fictional subject: `1e63a728-d550-56df-a2cb-a2fb81f9ec8e`
  (`陈雨 · DIRECT0929`). Second: `569ca82c-3b98-520a-9ae9-c2211b63a82d`
  (`许宁 · DIRECT0929`). Same immutable character version throughout.
- Chat 1: `0ba850ce-34fb-5eae-848a-848b46ca9ac5` (archived).
  Chat 2: `fd43b2a3-5c1c-56a3-b352-814b08a96296`.
  Chat 3: `3324bdb9-4b94-59c0-940e-72b83025e81d`.
  Chat 4: `bbb3f46f-2645-5b24-b633-54f74c9882ff`.
- Fresh recall run: `721fdedf-f9a5-4fa1-a787-465138fbceef`.
  Speaker-attribution run: `73cb3366-9c79-4995-aaba-e5facab071cd`.
  Their admitted original story is `342851e0-9a84-471b-a1be-352540902ba1`.
- Complete per-turn activity reports **10 generation, 9 reviewer and 28 embedding
  requests**, with two successful memory-search tools in the second-person turn
  only. Counts exclude catalog reads. All nine run-completion records show one
  native attempt; no turn was resent.
- Independent PostgreSQL readback matches four facts and five revisions for
  Chen, and zero for Xu. The five revisions comprise three introduction adds,
  the Chen Li preference add, and the city correction. Later recall replies
  created none. Saved-state correctness and spoken correctness differ here.
- Ignored evidence directory: `outputs/direct-hands-on-20260929/` beside this
  memo. It retains four chat-state exports, four activity exports, nine complete
  event logs, both memory exports, SQL memory readback, served worker identity,
  and the fresh-recall screenshot. These are retained readbacks, not complete
  provider wire captures. `SHA256SUMS` records artifact integrity.

### Next Investigation, Not A Fix Authorization

Prioritize source attribution and unsupported answer elaboration over another
retrieval adjustment: the needed exchanges were admitted in these failing
answers. Inspect the generation/reviewer role and authority contract before
proposing a general correction; do not add phrase-specific rules or infer model
rationale from the reply. Assess habit-to-preference storage separately. The
sample supports useful cross-chat continuity, not broad recall reliability.
Character verbosity, repeated questions and unsolicited callbacks remain later
tuning work; this trial changed none of them.

## Attribution Investigation: 2026-09-29

Offline follow-up to the two delivered errors above. No additional provider
calls, trial-data writes, runtime/prompt changes or deployment occurred. A
read-only GPT-6.1 Sol / Medium subagent independently inspected contract scope;
the director inspected persisted evidence and performed the reconstruction.

### What The Trace Establishes

The served runtime matches the relevant source on the retained branch. For both
runs, memory generation remains 4, matching the accepted generation. Using
`load_turn_state`, the persisted admitted-run order, and the actual
`build_natural_binding_map`, `_context_with_history`, and
`natural_review_request` functions reconstructed identical H sections for
generation and review. All selected source messages preceded the target turn.
The disputed singer description is **H4, role `assistant`**, not user, in both
reconstructed packets. The pottery source is H3, role `user`.

The generation/review path in
`services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py` passes
the same admitted exchanges and the candidate reply to the reviewer. Both
requests completed normally in the original traces, and both replies committed
without a new memory revision. There was no tool search in either failed answer.

These are source-backed reconstructions, **not retained original requests**.
The trial did not retain full request packets or the exact reviewer decision
JSON. Zero writes does not prove an empty decisions array, and the available
evidence does not reveal the model's internal reason for allowing the replies.

### Root-Cause Boundary

- **No evidence of a retrieval or role-serialization defect in these cases.**
  The needed exchange was admitted; the serializer preserves speaker roles and
  content hashes. Do not change ranking, erase assistant history, or label all
  history as user testimony to address the failure.
- **Generation failed source-faithful narration.** H instructions already say
  not to invent unavailable history. The shared I/you rule is phrased around
  profile/search facts, while the history wording is more general. Neither is
  a guarantee against model elaboration or misattribution. A claim that the
  runtime lost the speaker, or that a completely absent instruction explains
  everything, would be too strong.
- **Reviewer coverage is narrower than general answer verification.** The
  instruction explicitly checks memory writes and replies that contradict held
  facts; H evidence can ground such a conflict. It does not explicitly require
  checking every narrative addition for support. The existing contract can
  represent a source-speaker mismatch using the assistant H quote, but does not
  expressly call out that check. This is the appropriate narrow review target.
- **Unsupported is not necessarily contradicted.** A key-dish source does not
  establish a doorstep location or motive, but it does not explicitly disprove
  either. Using that source as a fabricated contradiction would misuse the
  contract. A new general unsupported-claim veto would need a separate design
  decision, not a silent expansion of `conflict`.

A manually injected, exact H4-grounded speaker-mismatch conflict was rejected
by the served `_validate_conflict` function with
`natural_memory_reply_conflict`. That establishes rejection mechanics only,
not reliable model detection. No database mutation or model call was involved.

### Smallest Proposed Follow-up

1. At the existing shared generation-instruction owner, clarify speaker and
   assertion fidelity: assistant opinions are not user testimony; do not add
   motives, actions or locations while presenting a recollection. Natural
   suggestions and explicitly tentative inferences remain allowed. Do not
   special-case the singer, pottery, keywords or observed Chinese phrases.
2. Clarify the existing H-capable review instruction for a positively grounded
   source-speaker mismatch. Keep the current schema and atomic rejection; do
   not turn missing evidence alone into a contradiction or add another reviewer.
3. Before live execution, prepare small contrasts: correctly attributed assistant
   opinion versus false user attribution; supported recollection versus invented
   remembered detail; an ordinary suggestion versus an asserted past event;
   and explicit later user endorsement as a positive control. Measure both
   delivered answers and complete memory deltas. Preserve these original errors.

This is a proposed bounded correction, not an implemented or qualified fix.
The habit-to-preference concern remains separate; character tuning is deferred.

### Verification

The existing policy, history-admission and generation-contract suites passed
**28 tests**. The two reconstructions and injected conflict check passed using
the served API code. Original `SHA256SUMS` is unchanged; ignored
`attribution-reconstruction.json` and `reconstruct_attribution.py` beside the
original captures have a separate `ATTRIBUTION-SHA256SUMS` receipt. The script
runs read-only inside the API container and writes only a `/tmp` artifact.
These checks support the layer diagnosis, not a claim of improved live behavior.
