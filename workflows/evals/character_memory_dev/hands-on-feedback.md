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
