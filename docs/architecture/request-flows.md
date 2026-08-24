# ADE Request Flows

These flows describe the implemented architecture defined by
[ADR 0006](../adr/0006-comprehension-first-service-and-feature-architecture.md).
Use the owning feature README for feature-specific contracts and operational
notes.

## Shared Web Request Path

```mermaid
sequenceDiagram
    participant B as Browser
    participant W as ADE Web
    participant A as ADE API
    B->>W: Same-origin feature request
    W->>A: Server-side proxy with ADE API credential
    A-->>W: Feature response
    W-->>B: UI result
```

The browser knows the ADE Web origin only. ADE Web owns user-facing routing and
the server-side API credential. API contracts and feature behavior belong to
ADE API.

## Agent Studio

```mermaid
sequenceDiagram
    participant B as Browser
    participant W as ADE Web / agent-studio
    participant A as ADE API / agent_studio
    participant L as Letta
    participant R as Model Router
    participant M as Selected model
    B->>W: Create agent or send message
    W->>A: /api/v2/agent-studio/...
    A->>L: Create or continue persistent agent
    L->>R: Model completion or tool loop
    R->>M: One provider request
    M-->>R: Completion
    R-->>L: Normalized response
    L-->>A: Agent reply and persistent state
    A-->>W: Agent Studio response
    W-->>B: Chat, memory, tool, and lifecycle view
```

`agent_studio` is the sole ADE feature that owns agent lifecycle, persistent
state, and Letta orchestration. It requests a resolved model capability from the
Model Router integration; it does not inspect provider files or call providers.

## Comment Lab And Label Lab

```mermaid
sequenceDiagram
    participant B as Browser
    participant W as ADE Web feature
    participant A as ADE API feature
    participant C as Model Catalog
    participant R as Model Router
    participant M as Selected model
    B->>W: Generate comment or labels
    W->>A: /api/v2/comment-lab or /label-lab
    A->>C: Resolve model handle and capabilities
    A->>R: OpenAI-compatible completion request
    R->>M: One provider request
    M-->>R: Completion
    R-->>A: Normalized response
    A-->>W: Feature result and diagnostics
    W-->>B: Generated output
```

Both features own their prompts, request mapping, response mapping, timeout,
and retry policy. Model Router owns upstream provider behavior. Retry ownership
must remain singular: a user-requested feature retry never combines with a
hidden router retry.

## Content Centers

```mermaid
flowchart LR
    U[Prompt, Schema, or Tool Center] --> W[ADE Web feature]
    W --> A[ADE API feature]
    A --> V[Feature validation]
    V --> S[content/]
    S --> R[Runtime consumer]
    R --> A
```

Prompt Center owns prompt and persona editing, Schema Center owns label-schema
editing, and Tool Center owns custom-tool editing and invocation. Each uses a
feature-specific adapter to validate and operate on `content/`; no generic
registry is allowed to hide the owner.

## Test Center And Workflows

```mermaid
sequenceDiagram
    participant U as Operator or ADE Web
    participant T as Test Center / workflow
    participant A as ADE API
    participant R as Model Router
    participant O as Local artifacts
    U->>T: Launch named check, eval, or probe
    T->>A: Public ADE API contract
    A->>R: Model operation when required
    R-->>A: Model result
    A-->>T: Run result
    T->>O: CSV, JSONL, summary, and logs
    O-->>U: Inspectable artifacts
```

Test Center owns interactive run launch and artifact viewing. `workflows/` owns
CLI-oriented evals, probes, and smoke checks. Both consume public boundaries;
neither imports arbitrary ADE API internals. Provider probes that must call
providers run within Model Router's service boundary.

## Model Catalog

The Model Catalog feature is the one ADE-facing interpretation boundary for
model availability and capabilities. It reads Model Router's normalized catalog
and returns selection-ready options to other ADE features. No lab, agent, or UI
feature parses source files, model profiles, provider endpoints, or probe report
formats directly.
