# Agent Studio

Agent Studio is the current ADE-native workspace for reusable definitions,
explicit memory subjects, persistent conversations, and inspectable runs.

- Entry route: `/agent-studio`
- `api.ts` owns typed browser calls to `/api/v3`.
- `use-agent-studio.ts` owns URL-backed selection, session lifecycle, event
  monitoring, cancellation, and state refresh.
- `agent-studio-view.tsx` presents definitions, subjects, conversations, typed
  memory lineage, summaries, and run evidence.
- `selection.ts` contains pure resource-selection rules with colocated tests.

A conversation binds exactly one immutable definition version to one memory
subject. Selecting an existing subject deliberately shares its durable memory;
creating a new subject creates an isolated boundary. The UI shows the evidence
for those choices rather than hiding them behind mutable prompt blocks.

The feature sends no provider request directly. It receives canonical options
and runtime state from ADE API, while Model Router remains behind the backend.
