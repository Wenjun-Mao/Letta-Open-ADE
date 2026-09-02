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
    participant N as ADE Native API
    participant D as ADE PostgreSQL
    participant K as Runtime Worker
    participant R as Model Router
    participant M as Selected model
    B->>W: Create definition, subject, and conversation
    W->>N: POST /api/v3/agent-studio/sessions
    N->>D: Atomic product resource creation
    B->>W: Send a turn
    W->>N: POST /api/v3/conversations/.../turns
    N->>D: Persist accepted run
    K->>D: Claim the exact conversation run
    K->>R: Conversation, retrieval, and reviewer requests
    R->>M: One provider request
    M-->>R: Completion
    R-->>K: Normalized response
    K->>D: Atomic messages, typed memory, summary, and events
    N-->>W: SSE events and persisted read models
    W-->>B: Chat, memory lineage, summary, and run trace
```

The native runtime is the sole Agent Studio lifecycle, memory, retry, and event
authority. Definitions are reusable behavior snapshots, subjects own durable
facts, conversations own immutable history, and runs explain execution. The v3
web proxy routes only to `ade-native-api`; it never falls back to Letta. The
retained v2 Agent Studio API exists only as a release rollback boundary during
Phase 5.

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
    participant U as Operator
    participant W as ADE Web
    participant T as Test Center API
    participant E as Evaluation workflow
    participant A as ADE API
    participant R as Model Router
    participant O as Local artifacts
    U->>W: Open evaluation from Agent Studio or Test Center
    W->>T: Launch named check, eval, or probe
    T->>E: Start run with persisted options
    E->>A: Public ADE API contract
    A->>R: Model operation when required
    R-->>A: Model result
    A-->>E: Run result
    E->>O: CSV, JSONL, summary, and logs
    U->>W: Compare runs or inspect a turn
    W->>T: Request typed evaluation evidence
    T->>O: Read run-owned artifacts
    T-->>W: Metrics, rounds, turns, tools, and memory layers
```

Test Center owns interactive run launch, persisted launch options, and typed
read models projected from run-owned artifacts. Agent Studio may prefill a Test
Center evaluation but does not execute it or mutate the selected agent. Raw
artifacts remain secondary diagnostics. `workflows/` owns CLI-oriented evals,
probes, and smoke checks. Both consume public boundaries; neither imports
arbitrary ADE API internals. Provider probes that must call providers run within
Model Router's service boundary. See
[ADR 0008](../adr/0008-test-center-evaluation-read-models.md) for this ownership
contract.

Native-runtime qualification is a stricter form of this flow: the workflow calls
the authenticated worker-health endpoint first, then calls the real `/api/v3`
asynchronous API and worker only after preflight passes, captures normalized events and
PostgreSQL-backed memory evidence, and then purges only its run-owned resources.
Only complete production-path rounds may emit a promotion proposal, and applying
that proposal is a separate reviewed operator action under
[ADR 0010](../adr/0010-production-path-runtime-qualification.md). Request-level
provider failures and process-readiness evidence follow
[ADR 0011](../adr/0011-agent-runtime-operational-readiness.md).

## Model Catalog

The Model Catalog feature is the one ADE-facing interpretation boundary for
model availability and capabilities. It reads Model Router's normalized catalog
and returns selection-ready options to other ADE features. No lab, agent, or UI
feature parses source files, model profiles, provider endpoints, or probe report
formats directly.
