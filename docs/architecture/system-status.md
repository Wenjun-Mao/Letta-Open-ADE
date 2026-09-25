# ADE System Status

## Current System

ADE Web and ADE API are the product entrypoints. PostgreSQL stores native Agent
Studio state, Model Router owns model identity and provider access, and the
runtime worker performs asynchronous Agent Studio turns. The one-shot migration
job establishes the database schema before the stack serves traffic.

| Concern | Authority |
| --- | --- |
| Browser product | ADE Web |
| Product API | ADE API |
| Agent Studio | `/api/v3`, ADE API, runtime worker, and PostgreSQL |
| Model selection and provider access | Model Router |
| Prompts, personas, and schemas | Content centers and `content/` |
| Runtime release confidence | Qualification, conformance, release ledger, and approved manifest |

Agent Studio is current product behavior, not a preview. It has no alternate
runtime, compatibility route, or per-request fallback.

## Product Spine

ADE's core loop is: configure an experience, evaluate it against a representative
scenario, inspect reply/tool/memory evidence, refine the relevant content, and
make a keep or reject decision. Agent Studio, Prompt Center, Model Catalog, and
Test Center support that loop. Comment Lab and Label Lab are router-backed labs
with their own task-specific contracts.

## Release Policy

Every released Agent Studio build is tied to a clean source revision, exact API
and worker identities, policy hashes, an approved model/agent bundle, native
three-round qualification of selected routes and deterministic conformance.
[ADR 0027](../adr/0027-provider-neutral-release-and-embedding-space.md) defines
schema-v4 evidence and selected-route compatibility, not a mandatory DGX or
llama-server provider. Historical schema-v3 evidence does not qualify the current
development branch. The release ledger records qualified evidence. Changing a governed
runtime input requires new evidence and promotion.

Recovery is deployment rollback and PostgreSQL backup/restore. The project name
remains historical; a repository-wide rename is future work and does not affect
the current runtime boundary.

## Read Next

- [Architecture overview](overview.md): service and data boundaries.
- [Request flows](request-flows.md): how requests execute.
- [Codebase map](../codebase-map.md): where to change a capability.
- [ADR 0019](../adr/0019-ade-steady-state-runtime.md): durable steady-state decision.
