# ADR 0020: Luna Subscription Calls For Local Character Experiments

- Status: Accepted
- Date: 2026-09-22

## Context

DGX Spark is shared with other projects. Character dialogue and memory-review
experiments need a development option while it is occupied. The installed Codex
CLI can request Luna using ChatGPT subscription authentication, but does not
expose ADE's native HTTP chat, tool-call, or embedding protocol.

## Decision

Keep a small host-only workflow under `workflows/evals/character_memory_dev`.
Select `luna-subscription` explicitly. Use the existing 林小棠 persona, one
ephemeral generation session per invocation, a controlled environment, bounded
captures, and explicit timeout. Validate CLI events and task schemas separately.
Never automatically retry, switch models, use API billing, or contact Spark.

Outputs are development evidence and proposals. ADE remains the authority for
persisted memories. Luna results cannot qualify Qwen or replace native runtime
acceptance. Embeddings and native tool-call protocol tests retain their own
provider requirements.

## Alternatives And Consequences

A transparent replacement base URL would hide different role/tool semantics
and introduce host authentication into container services. We reject that path.
The explicit workflow adds no production service, dependency, or API surface.
It permits work on dialogue, source-linked memory proposals, and advisory
judging, while requiring manual context input and independent semantic review.

CLI behavior and subscription availability can change. Preserve version and
raw results; reject unexpected events and requalify before reuse. Tests cover
authentication, event/schema failures, exact adapter attempts, output reuse,
and timeout cleanup. No claim is made about internal CLI network retry counts.
