# ADE Request Flows

## Shared Web Path

```mermaid
sequenceDiagram
    participant B as Browser
    participant W as ADE Web
    participant A as ADE API
    B->>W: Same-origin feature request
    W->>A: Server-side proxy with ADE credential
    A-->>W: Feature response
    W-->>B: UI result
```

ADE Web is the only browser-facing component. It proxies both `/api/v2` and
`/api/v3` to the single ADE API and keeps the API credential server-side.

## Agent Studio

```mermaid
sequenceDiagram
    participant B as Browser
    participant W as ADE Web
    participant A as ADE API
    participant P as PostgreSQL
    participant K as Runtime Worker
    participant R as Model Router
    participant M as Selected model
    B->>W: Create or select a session
    W->>A: /api/v3/agent-studio/sessions
    A->>P: Bind definition, subject, and conversation
    B->>W: Send a turn
    W->>A: /api/v3/conversations/{id}/turns
    A->>P: Persist run and immutable input
    K->>P: Claim conversation lease
    K->>R: Model, retrieval, and reviewer requests
    R->>M: One provider request
    K->>P: Commit messages, memory, summary, and events
    A-->>W: Run state and event stream
```

An agent definition is a reusable behavior snapshot. A memory subject owns
durable facts. A conversation binds one definition to one subject and retains
immutable messages. The runtime validates typed memory proposals against the
bound subject and sources them to messages; model arguments cannot select another
subject.

## Labs And Content Centers

```mermaid
flowchart LR
    W[ADE Web feature] --> A[ADE API feature]
    A --> C[Model Catalog or content adapter]
    C --> R[Model Router or content/]
    R --> O[Provider result or reviewed record]
    O --> A
```

Comment Lab and Label Lab resolve a canonical model key through Model Catalog,
then send one router-backed request. Prompt Center and Schema Center validate
and manage reviewed content; neither invokes a provider.

## Test Center

Test Center launches only three named workflows:

1. Behavior evaluation: chat-memory evidence and deterministic scoring.
2. Agent runtime qualification: release-eligible native runtime evidence.
3. Current-stack smoke: service-level operational checks.

The orchestrator writes run manifests and artifacts inside the allocated run
directory. Artifact access is rooted to that directory and exposed through a
`TestRunDescriptor`; raw artifacts remain diagnostics rather than an alternate
product contract.
