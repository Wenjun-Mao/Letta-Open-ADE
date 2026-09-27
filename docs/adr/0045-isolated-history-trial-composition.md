# ADR 0045: Isolated Development History Trial

Status: Accepted for the authorized hands-on development trial on 2026-09-27.
This does not select production historical retrieval, switch a default, or qualify
a release. Relevant product contracts: PC-01/02/03/04/05/08/09/10.

## Problem

The existing Agent Studio browser binds `agent_studio` resources to its typed
memory default. The automatic H4 historical probe requires an `evaluation`
conversation, an evaluation-only policy and capacity snapshot, and a worker
constructed with the pinned probe. Changing the chat prompt alone cannot meet
those conditions. The user requested a real browser trial of that exact
development behavior without touching the production stack.

## Decision

Expose a separate `/api/v3/history-trial` resource surface only when
`ADE_API_HISTORY_TRIAL_ENABLED=true` and the API is in development mode. It
retains the existing reader/operator roles and delegates to the established
purpose-owned session and resource services. Trial definition preparation
enforces the candidate prompt, persona, DeepSeek/Qwen routes and fingerprints,
history policy, and H4 capacity before immutable persistence. Reused versions
are checked again. The isolated worker explicitly binds automatic historical
retrieval with the pinned Qwen recipe. The ordinary Studio endpoints, default
worker construction and production release checks keep their existing meaning.

The isolated web build reuses the Studio view and selects the trial resource
URLs with a visible experimental label. Controls without a trial endpoint are
hidden. A workflow-local Compose override supplies distinct loopback ports,
database and content/runtime directories; its stop command retains trial data.

## Alternatives and guardrails

A copied Studio application or generic experiment framework would duplicate
resource ownership. Reinterpreting ordinary Studio URLs or allowing the probe
under `agent_studio` purpose would weaken the purpose boundary. A script-only
runner would not satisfy the interactive request. The trial is therefore an
intentional, explicitly configured development divergence.

Focused route/auth, policy/capacity and purpose checks, a web build, and live
API/worker/PostgreSQL/browser readback guard the composition. Any provider
fingerprint drift fails closed until reviewed. No migration, row rewrite,
production rebind, or automatic promotion follows from trial observations.
