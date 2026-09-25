# ADR 0020: Luna Subscription Calls For Local Character Experiments

- Status: Retained development workflow; no longer the primary provider lane.

> [ADR 0025](0025-deepseek-development-lane.md) establishes DeepSeek development;
> [ADR 0024](0024-local-luna-agent-backend-feasibility.md) keeps the Luna backend
> investigation on hold. Historical Luna evidence is not native-runtime qualification.
- Date: 2026-09-22

## Context

### Structured Output Follow-Up (2026-09-22)

The first GPT-6 call returned plain text despite JSON prompt instructions. The
transport succeeded; task validation correctly rejected it. New workflow calls
therefore supply a task-specific JSON Schema using the supported CLI
`--output-schema` flag, saving the schema and contract identifier with captures.
Prompt-only enforcement and wrapping plain text after generation are rejected:
neither establishes the requested structured-output contract. Existing semantic
and event validators stay authoritative. Synthetic command tests pass separately
from live qualification, which is still pending. Frozen runs are not rewritten.
See [CLI documentation](https://learn.chatgpt.com/docs/non-interactive-mode).

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

## 2026-09-22 GPT-6 Luna configuration clarification

Future development calls request `gpt-6-luna` through the existing strict
subscription-CLI transport. The configuration retains medium reasoning effort,
the default service tier, the 180-second timeout, and no retry or fallback
behavior. It does not establish account entitlement or a qualified GPT-6
generation run; that requires a separately agreed live-call budget.

Existing M1/M2 GPT-5.6 Luna matrices, raw captures, manifests, results, and
historical validators remain frozen. They are not relabeled as GPT-6 evidence
and must not be compared with a future GPT-6 batch until that batch is
separately qualified.
