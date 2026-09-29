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

The shared Studio presentation uses person and character names for setup.
Client-generated, opaque keys are created once per new draft and kept across
failed submissions with the same idempotency key; a successful chat selects its
existing person and character for the next chat, then prepares fresh keys for
another new draft. Equal display names remain separate people. The trial uses
its pinned character without editable definition internals. Ordinary Studio
retains version creation and persona previews in an expandable management
section. Hashes, deployment receipts and run events are available in collapsed
technical details; saved facts, citations and failures remain visible. Visible
field captions are selectable text connected with `aria-labelledby`; a plain
caption click still focuses its control, while dragging preserves the selection.
The original wrapping `<label>` caused browser label activation to take the
selection into the input; an explicit `htmlFor` label still did so in a drag
check. No CSS rule had disabled selection. The caption interaction belongs in
the shared view because the form structure caused it in both Studio modes.

Per-turn activity is read from retained run events and attempt receipts in one
conversation-scoped readback. Provider attempts are deduplicated by ADE request
ID and grouped as generation, review, embedding, or other dispatch; tool calls
remain separate. A completed final-attempt trace establishes a real zero only
when its retained dispatch starts match the terminal receipt. Missing or partial
old traces are unavailable or observed lower bounds. Source details name current
chat context, selected fact IDs, and admitted older run IDs when retained;
admission shows availability and cannot establish what caused an answer. This
readback is shared Studio presentation and does not alter trial bindings.

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
