# ADR 0026: Memory Replies Must Respect Review and Capability Boundaries

- Status: Accepted for the M3 development slice; behavioral acceptance remains open
- Date: 2026-09-23

## Problem

The isolated M3 removal turn committed a valid `forget` revision and removed the
fact from active memory, but the conversation model replied as though it had
already forgotten the detail and would never mention it again. That promise
exceeds Option A: the reviewer runs after generation, and old messages,
summaries, and revision evidence remain. The runtime system context previously
said only not to claim a memory write; it did not state these removal limits.
Later, an unsupported concern produced no memory revision, yet the model
promised to remember it and proactively ask in a later conversation. ADE has
neither a concern fact type nor scheduled outreach.

## Decision

Keep review and persistence authority unchanged. The runtime-owned memory
instructions now describe removal as pending while the reply is generated and
prohibit claims of completed removal, historical erasure, or permanent future
suppression. They also prohibit promises to remember unsupported concerns or
initiate future check-ins, while allowing an immediate empathetic reply. This
applies to every conversation provider, not a DeepSeek-only exception. The
Agent Studio UI continues to confirm success only after a matching committed
revision. Regression tests assert that these boundaries reach the built
system context.

## Rejected Alternatives and Consequences

- Do not delete or rewrite old conversation messages, summaries, or revisions.
- Do not post-process model text with a list of forbidden phrases; that would
  be brittle across languages and could hide a model-quality failure.
- Do not rerun the failed removal to erase its evidence. Its response remains
  in the disposable conversation and the finding. Likewise, do not rerun the
  concern request or add a concern schema to make its promise appear true.

The prompt contract reduces misleading replies but does not prove provider
compliance. A future model response may still violate it; that requires its
own observed failure and quality or fail-closed design decision. The changed
runtime policy receives a new unqualified DeepSeek fingerprint. Existing
conversation snapshots remain immutable and cannot be executed against the
new policy; subsequent synthetic turns use a freshly bound definition.
