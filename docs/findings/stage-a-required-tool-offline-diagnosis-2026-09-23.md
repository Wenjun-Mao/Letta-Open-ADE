# Stage A Required-Tool Failure: Offline Diagnosis

Status: diagnosis for the [failed one-shot Stage A attempt](stage-a-provider-neutral-preflight-2026-09-23.md), **not a repair or authorization to rerun**. Stage B/C remain blocked. No provider, embedding, or production request was made during this review.

## What the retained evidence proves

The scored `old_memory_deep_search` run
`aa44465b-adc1-447d-a5cf-518dc6bfe096` completed one DeepSeek conversation
transport request in about 971 ms. Its safe trace records one choice, content
and reasoning fields present, `finish_reason=stop`, and zero tool calls
(`tool_calls_state=missing_or_null`). ADE had resolved
`memory.deep_search`/`search_memory` as an explicit required action, then
emitted `tool.requirement.unmet` and failed the run with
`conversation_required_tool_missing`. The Qwen `retrieval_query` embedding
completed beforehand; that automatic retrieval is **not** a `search_memory`
tool execution. There was no reviewer call or assistant commit for this scored
turn, no retry, and no second Stage A attempt. See the retained
`diagnostic-round-001/events.jsonl` and `round.json` under the run directory
linked in the Stage A finding.

The trace deliberately saves response *shape*, not the response content,
reasoning body, or raw provider request. The failed evaluation session was
purged after artifact capture. We can reconstruct the request **construction
rules** from the frozen source, but cannot claim an exact captured wire body,
what the model said, why it made its choice, or whether the museum fact was
visible in the actual built context.

## Contract gap at the provider boundary

1. [`turn_execution.py`](../../services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py)
   builds context and resolves a `ToolRequirement` from the user's message,
   then passes it to `ConversationExecutor`. The action detector sees the
   message's explicit search instruction and records the requirement.
2. [`executor.py`](../../services/ade-api/src/ade_api/features/agent_runtime/executor.py)
   computes a named `search_memory` choice, but **always substitutes
   `tool_choice="auto"` for `deepseek_openai`**. The request still includes the
   `search_memory` function schema and a generic system rule to call selected
   tools for explicit actions. ADE checks the required call *after* the
   provider response and correctly rejects final text without it.
3. [`model-router/app.py`](../../services/model-router/src/model_router/app.py)
   supplies the selected model's default `thinking=enabled` and
   `reasoning_effort=high`; it does not strengthen `auto` into a forced choice.
   Its validation intentionally rejects a named/`required` choice in thinking
   mode. This matches the current [official DeepSeek Chat Completions
   reference](https://api-docs.deepseek.com/api/create-chat-completion/):
   forced choices return HTTP 400 in thinking mode, while `auto` lets the
   model answer without calling a tool. DeepSeek's [thinking-mode
   guide](https://api-docs.deepseek.com/guides/thinking_mode/) confirms that
   thinking mode *can* call tools; it does not guarantee one under `auto`.

This is a real **enforcement mismatch**: ADE represents the action as
mandatory at its validation boundary but can only express it as
discretionary through the current thinking-mode Chat Completions request.
The provider returned a valid response to that discretionary request; the
runtime correctly failed its stronger contract. An earlier [development
smoke](deepseek-development-smoke.md) succeeded with `search_memory` under
`auto`, but it had an explicit one-purpose system instruction and synthetic
tea query. It proves capability, not reliability or equivalence to this
native context. Focused executor/router/runner tests (57 passed) reproduce
the current construction and fail-closed behavior without any live calls.

## Fixture/context ambiguity to resolve separately

The canonical fixture asks, in effect, “If the current material does not have
it, search memory,” yet also requires an observed `search_memory` call. Its
`profile_token_override=48` is parsed by the shared fixture loader but is not
consumed by the native acceptance runner or runtime. The runtime instead
uses its normal profile budget and the 12 most recently updated active facts,
plus automatic Qwen retrieval. The museum fact was committed during setup,
but the failed run lacks a `context.built` event or raw prompt capture; whether
that fact was actually shown in the profile or retrieved section is not
proven. The generic memory prompt says to use `search_memory` only when older
relevant details are absent from the profile. Thus the fixture's conditional
wording, its unconditional tool assertion, and ADE's unconditional resolved
requirement are not yet a single explicit semantic contract. This ambiguity
may have influenced the response, but is **not** proven to have caused it.

## Recommendation and decision gate

Before any new live budget, name one source-owned `ToolRequirement` contract
that aligns (a) the user/fixture semantics, (b) what context proves about
answer availability, (c) the provider request's enforceable choice, and (d)
the runtime assertion. For this Chat Completions route, the smallest plausible
deterministic implementation is a **per-required-action** non-thinking
request with a named `search_memory` choice, followed by strict validation
and a zero-repair continuation. DeepSeek documents named choice as supported
when thinking is disabled. This is a material, explicit exception to the
candidate's thinking/high default and must be reviewed, fingerprinted,
tested offline end-to-end with fake transport, and freshly qualified. Do not
silently disable thinking globally or convert a successful automatic query
into a fabricated tool result.

The alternatives are to retain thinking/`auto` as best-effort and accept
fail-closed, non-guaranteed tool use (which does **not** satisfy a deterministic
required-action claim), or to assess a different DeepSeek API format such as
the [Responses API](https://api-docs.deepseek.com/guides/responses_api/) for
forced choice; that is a larger adapter contract and has not been validated
here. Independently, decide whether the canonical case should require an
unconditional deep search or whether the runtime should make its obligation
conditional on actual available context. Do not edit the fixture merely to
turn this failed attempt green. A new bounded live experiment would require
that decision, a new clean source/build fingerprint and ledger, and separate
approval; the remaining 25/25 Stage A slots are not a reroll budget.
