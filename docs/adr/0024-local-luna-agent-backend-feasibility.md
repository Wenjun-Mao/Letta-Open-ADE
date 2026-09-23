# ADR 0024: Do Not Bind Subscription Luna As An ADE Agent Backend Yet

- Status: Proposed; backend integration deferred pending contract qualification
- Date: 2026-09-22
- Scope: private, single-operator ADE on this Mac only; no public or multi-user claim

## Problem and finding

ADE's steady-state runtime is not a generic text-generation caller. An immutable
agent definition binds three Router deployments (`conversation`, `reviewer`,
`retriever`) to catalog fingerprints. The worker assembles subject-bound context,
executes curated native function calls, embeds queries and committed facts, reviews
typed memory, optionally compacts history, and commits the result transactionally.
Router transport and tracing are the current provider boundary. See ADR 0019 and
`agent_runtime/{deployments,turn_execution,executor,reviewer,embeddings,worker_finalization}.py`.

The installed `codex-cli 0.155.0-alpha.9.2` reports ChatGPT login. Its supported
`exec` command and the existing `workflows/evals/character_memory_dev/luna.py`
prove a *different*, narrower local development contract: one fresh ephemeral
Codex turn, schema-constrained final text, captured events, bounded subprocess,
and no adapter retry/fallback. The workflow's 61 passing synthetic tests and
three prior schema smoke calls establish task-shape feasibility, not native ADE
backend compatibility or future account entitlement. No model call was made for
this assessment. [Codex authentication](https://learn.chatgpt.com/docs/auth),
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).

## Decision

Keep the existing subscription workflow as a host-only, explicitly selected
character-development prototype. Do not register Luna as a Router alias, replace
`RouterTransport`, alter immutable definition/deployment snapshots, or wire the
CLI into the Agent Studio worker yet. Do not fall back to Spark, another model,
or API-key billing. This is a contract-level deferral, not a conclusion that
Luna cannot generate useful dialogue.

| ADE contract | Current local subscription evidence | Integration gap |
|---|---|---|
| Catalog-qualified conversation/reviewer/retriever identities | CLI model name and observed events | No Router-style immutable deployment/fingerprint or embedding identity |
| Role-separated chat messages and native `tool_calls` | One Codex task prompt and final agent message | Role-labelled text is not equivalent to message-role precedence; final JSON proposals are not native calls |
| Subject-bound `search_memory` and required-tool enforcement | Development prompt prohibits tools and rejects tool events | No proven mapping from ADE's curated function schema to CLI `exec` |
| Qwen query/fact embeddings with versioned vector policy | No subscription embedding endpoint | Retrieval and memory commit cannot use the existing fingerprint/policy contract |
| ADE-owned attempts, timeout, cancellation, and retries | One bounded process, no adapter retry/fallback | CLI internal request retries and partial-turn cancellation/usage remain unqualified |
| Curated tool-only authority | Empty cwd, read-only sandbox, prompt prohibition | Read-only still permits reads; rejecting a tool event afterward does not prevent it |

The [Codex App Server](https://learn.chatgpt.com/docs/app-server) offers a
documented stdio JSON-RPC transport, turn interruption, and *experimental*
`dynamicTools`; the [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) wraps
that CLI/app-server protocol. Neither is an OpenAI-compatible chat/embeddings
endpoint. Dynamic tools may be a future ADE-owned bridge, but their event and
approval semantics must be qualified before a turn is allowed to affect memory.
The current app-server schema and CLI help do not establish a complete built-in
tool denylist, a no-read process boundary, or zero internal network retries.
Official configuration documents provider retry defaults, but not a verified
subscription-builtin override for this lane. Therefore the adapter's zero
*application* retries must not be described as zero network attempts.
[Codex sample configuration](https://learn.chatgpt.com/docs/config-file/config-sample).

## Rejected shortcuts

- Wrapping Codex final text in a `/chat/completions`-shaped response would hide
  tool and role semantics, and could make memory-search policy look satisfied
  without a native authorized call.
- Inventing a local retriever alias or mixing a different embedding model into
  existing vectors would break deployment identity and retrieval-policy meaning.
- Treating `read-only`, `--ignore-user-config`, `--ignore-rules`, or a prompt ban
  as a tool-free security boundary would misstate what those controls guarantee.
- Calling the existing development workflow a passed backend prototype would
  conflate task-shape validation with ADE's transaction and release contracts.

## Reopen gates for a bounded local-only implementation

1. Define an explicit local-subscription deployment kind and provenance model,
   separate from Router-backed snapshots, including observed-versus-requested
   runtime identity. Preserve release rejection until independently qualified.
2. Prove an ADE-owned tool bridge with exactly the curated tool set, required
   calls, subject binding, and native call/result validation. If app-server
   dynamic tools are used, pin and test the experimental protocol and reject
   unknown items before any ADE side effect.
3. Provide an independently versioned local embedding service/model, measured
   dimensions and retrieval threshold, or redesign the memory/retrieval contract
   with a new policy version. Never reuse existing Qwen vector fingerprints for
   another model.
4. Qualify process isolation and operation ownership: no inherited project
   context or unapproved built-in tools, bounded stdout/stderr, process-tree
   cleanup, cancellation, timeout, uncertain outcomes, explicit ADE retry
   budget, and no provider/model fallback.
5. Add fake-protocol tests first, then isolated database tests for add/correct/
   forget, required search, compaction, cancellation, and stale fingerprints.
   Only then consider live calls or a development-only feature flag.

## Proposed live-call budget (not authorized or run here)

After gates 1-4 have a testable prototype, ask the operator to approve **at
most six serial calls**, each through ChatGPT login, `gpt-6-luna`, medium effort,
default tier, fresh ephemeral session, 180-second limit, and no adapter reroll:

1. One dialogue turn: supplied synthetic persona/context, user asks for the
   stated favorite drink; verify role attribution and exact final-event shape.
2. One required `search_memory` turn: synthetic older fact absent from profile;
   verify one native call, validated arguments, current-subject-only result, and
   final answer after the tool result.
3. One add-only memory review: current synthetic user message states a new pet
   name; verify schema, source quote, entity/type, and no write before ADE review.
4. One explicit forget review: current synthetic user asks to forget a supplied
   active preference; verify `forget`, fact ID/version, JSON null, no add.
5. One compaction turn: synthetic prior messages and summary boundary; verify
   structured output and ADE token/sequence limits.
6. One deliberately interrupted turn: verify process/turn termination, uncertain
   usage classification, no retry, and no commit.

Capture exact inputs, CLI version, requested settings, raw events, timing,
validation, and missing/observed usage without credentials or private user
transcripts. Stop on the first unqualified behavior; do not spend the remaining
budget automatically. This budget is a proposal only, not permission to call.

## Consequences

ADE product and release paths remain unchanged. The development workflow can
inform prompt and memory-policy work with synthetic data, but it must continue
to label results as non-native evidence. A future backend implementation needs
a separate decision and requalification of the changed runtime contract.
