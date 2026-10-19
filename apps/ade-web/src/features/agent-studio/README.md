# Agent Studio

Agent Studio is the current ADE-native workspace for reusable definitions,
explicit memory subjects, persistent conversations, and inspectable runs.

- Entry route: `/agent-studio`
- `api.ts` owns typed browser calls to `/api/v3`.
- `use-agent-studio.ts` owns URL-backed selection, session lifecycle, event
  monitoring, cancellation, and state refresh.
- `agent-studio-view.tsx` presents authored versions, saved conversations,
  summaries, pause/Retry and run evidence.
- `use-relationship-memory.ts` and `relationship-memory-view.tsx` independently
  load relationship-scoped learned memories, original sources, delivery queue and
  native processing. Late selection responses cannot replace the selected scope.
- `turn-activity-view.tsx` separates ADE generation/compaction counts from tool
  calls and supplied Hindsight memory IDs. It does not count native Hindsight
  extraction/consolidation calls or infer why Character answered a certain way.
- `selection.ts` contains pure resource-selection rules with colocated tests.

A conversation binds exactly one immutable definition version to one memory
subject. Learned Memory belongs to the same subject and character root, not to
the subject alone. New chats, ordinary persona versions and archive state preserve
that relationship. Another character or person does not inherit it.

Memory errors do not prevent saved chat/run loading and are not empty results.
Delivery acceptance, retention completion and semantic correctness are distinct.
The queue remains readable when Hindsight is down. Failed/uncertain delivery Retry
preserves its original source; paused reply Retry preserves the saved user input
and performs fresh recall. Both are different from sending a new message.

The current client has no manual fact removal/reset or historical-trial redirect.
See [ADR 0074](../../../../../docs/adr/0074-relationship-memory-inspection.md).

The feature sends no provider request directly. It receives canonical options
and runtime state from ADE API, while Model Router remains behind the backend.
