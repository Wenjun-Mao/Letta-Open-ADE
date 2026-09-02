# Agent Studio

Agent Studio is the ADE-native v3 workspace. It does not edit Letta agents, free-text memory blocks, prompts, models, or arbitrary tool attachments.

- Entry route: `/agent-studio`
- `api.ts` owns the typed browser calls to `/api/v3/agent-studio` and the asynchronous v3 run endpoints.
- `use-agent-studio.ts` owns URL-backed conversation selection, resource lifecycle, event-stream monitoring, polling fallback, cancellation, and state refresh.
- `agent-studio-view.tsx` presents the product model: immutable definition versions, explicit memory subjects, conversations, typed fact lineage, summaries, and run evidence.
- `selection.ts` contains the pure URL and resource-selection rules with colocated tests.

## Product Boundaries

Creating a conversation binds exactly one immutable definition version to exactly one memory subject. Selecting an existing subject deliberately shares that subject's durable memory across conversations; creating a new subject creates an isolated memory boundary.

Definitions are created from a qualified release bundle. The UI displays frozen prompt, persona, deployment, policy, and curated-tool snapshots, but never mutates them in place. It supports archive and restore actions where the API exposes them. The operator-only fresh-start reset is intentionally absent from the browser UI.

Turns are asynchronous. The browser opens an SSE event stream, continues status/event-log polling if it reconnects, exposes timeout and additional retry controls, and allows cancellation. Immutable messages, typed memory revisions with evidence, versioned summaries, and normalized run events remain inspectable after the run finishes.
