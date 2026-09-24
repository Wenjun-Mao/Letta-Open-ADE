# ADR 0033: Separate Reviewer Output-Envelope Diagnostic

- Status: Accepted for development diagnostic iteration 2 on 2026-09-24
- Scope: isolated natural-memory evaluation sessions using the native B policy

## Problem

Iteration 1 committed the previously failing morning preference, then stopped
on scoped addition. The second DeepSeek reviewer response used exactly 1,024
completion tokens, ended with `finish_reason=length`, and had no visible JSON.
Its request used the frozen 1,024-token reviewer output reserve with thinking
enabled at high effort. [DeepSeek's Chat Completions documentation](https://api-docs.deepseek.com/api/create-chat-completion/)
defines `max_tokens` as the generated-completion cap and `length` as cap or
context exhaustion; [thinking-mode documentation](https://api-docs.deepseek.com/guides/thinking_mode/)
states that reasoning precedes the final answer. The captured prompt and
completion usage support output exhaustion here; private reasoning was not
inspected.

## Decision

Run one separately identified diagnostic with the same pinned DeepSeek route,
high-thinking request fields, prompt/schema, 6,759-token reviewer input limit,
source selection, one reviewer call, and zero repair. A named evaluation-only
snapshot binding permits `max_tokens: 4096` for the natural reviewer request.
The provider's pinned fingerprint advertises at least 4,096 output tokens and
16,384 total context tokens; the diagnostic checks both before execution.
Normal product requests and frozen checkpoint-6 comparison requests retain
1,024. The native request builder and exact preflight receive the same explicit
cap; no router mutation or retry path is used.

## Consequences and alternatives

This changes the completion envelope and therefore cannot qualify as an
unchanged frozen A/B comparison. A successful diagnostic would identify a
necessary future envelope amendment for review, not authorize one. Disabling
thinking, changing effort, raising the frozen matrix silently, retrying a
truncated response, or parsing incomplete JSON would confound the diagnosis or
weaken evidence. Wire-shape and real-worker tests must show the only request
change is `max_tokens`, while the reviewer input limit and pinned identity stay
fixed.
