# ADE System Status Map

Use this page to explain ADE's present authority and direction in a few
minutes. It is a status map, not a replacement for the ADRs that define durable
runtime decisions.

## One-Sentence Model

ADE is a local-first operator workspace for improving agent behavior with
evidence: ADE Web presents the workflow, ADE API owns product orchestration,
Model Router owns provider access, and Letta currently owns the supported
Agent Studio runtime.

## Current Authority

| Concern | Current authority | Status |
| --- | --- | --- |
| Product UI and browser contract | ADE Web and `/api/v2` | Supported product path |
| Persistent Agent Studio execution and current agent state | Letta `0.16.8` | Supported product path |
| Provider discovery, capability policy, and generation routing | Model Router | Supported shared boundary |
| Prompts, personas, schemas, and custom-tool content | `content/` through its owning center | Reviewed product material |
| Product behavior evidence | Test Center and feature-owned evaluation workflows | Delivered evaluation-loop baseline |
| ADE-native agent runtime | isolated `ade-native-api`, ADE PostgreSQL, and `ade-runtime-worker` | Accepted candidate with a separate implemented pilot; navigation disabled and deployments unqualified |

The native candidate is deliberately separate. It neither imports Letta agents
nor dual-writes state. Its `/native-runtime-preview` product slice is build-gated,
uses a dedicated native proxy, and never appears as an Agent Studio mode. Do not
describe it as a replacement or a supported runtime until its qualification and a
later cutover ADR are complete.

```mermaid
flowchart LR
    O[Operator] --> W[ADE Web]
    W --> A[ADE API /api/v2]
    A --> L[Letta\ncurrent Agent Studio authority]
    A --> R[Model Router\nprovider boundary]
    L --> R
    A --> C[Content centers\nprompts, personas, schemas, tools]
    T[Test Center] --> A
    T --> E[Behavior evidence\nand workflow artifacts]
    W -. gated /api/v3 preview .-> NAPI[ade-native-api\nnative surface only]
    NAPI --> N[ADE-native runtime\nPostgreSQL + worker]
    N --> R
```

## Product Spine

The core operator outcome is the **Agent Behavior Evaluation Loop**:

1. Build or configure an agent experience.
2. Select the relevant model, prompt, persona, embedding, and fixture.
3. Evaluate the behavior and inspect reply, tool, and memory evidence.
4. Refine the content that explains the outcome.
5. Compare with a baseline and decide to keep, promote, or reject the change.

Agent Studio, Prompt Center, Model Catalog, and Test Center serve this loop.
Comment Lab and Label Lab should receive their own evaluation flows only when a
task-specific contract makes the result meaningful. Stack health, provider
probes, diagnostics, and native-runtime qualification remain Operations work:
they support confidence in the loop but do not measure product behavior.

## Direction And Gates

| Horizon | Outcome | Decision gate |
| --- | --- | --- |
| Delivered | Initial evaluation loop works from configured chat through deterministic evidence and refinement. | Baseline is available; ongoing work improves trust and usability rather than recreating it. |
| Now | Evaluation becomes the primary product journey, with verified content-addressed input provenance and readable baseline/candidate decisions. | An operator can make a keep/promote/reject decision without reconstructing raw artifacts, and quality evaluation is distinct from operations. |
| Next | The native runtime becomes a qualified candidate for a narrow product pilot. | Exact role fingerprints pass ADR 0010's three complete rounds and reviewed promotion; the curated-tool scope and native-only operations are proven. |
| Later | A fresh-start v3 cutover removes the dual-runtime system. | A later cutover ADR is accepted after product-pilot evidence; only then can new Agent Studio traffic move and Letta/Redis removal begin. |

## Read Next

- [Product Roadmap](../product-roadmap.md) for outcome priorities and the full
  milestone wording.
- [Architecture Overview](overview.md) for service boundaries and repository
  structure.
- [Codebase Map](../codebase-map.md) to locate the owner of a change.
- [ADR 0009](../adr/0009-ade-owned-agent-runtime.md),
  [ADR 0010](../adr/0010-production-path-runtime-qualification.md), and
  [ADR 0011](../adr/0011-agent-runtime-operational-readiness.md), and
  [ADR 0013](../adr/0013-narrow-native-runtime-product-pilot.md) before
  changing or describing the native runtime.
