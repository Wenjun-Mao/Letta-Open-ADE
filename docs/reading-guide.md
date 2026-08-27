# ADE Maintainer Reading Guide

This guide is for maintainers and contributors learning the current
architecture. Start with the [Codebase Map](codebase-map.md) to find the
owner of a change, then use this guide to understand the system boundaries.

For the active product outcome, read the [Product Roadmap](product-roadmap.md).
The [Maintenance Roadmap](maintenance-roadmap.md) is retained only as a
historical cleanup record and must not be used to select current work.

## Five-Minute System Model

Read [Architecture Overview](architecture/overview.md), then remember these
six ideas:

1. `ade-web` is the browser product, not the business-logic owner.
2. `ade-api` owns ADE workflows, feature contracts, and orchestration.
3. `model-router` owns provider-facing model access and model intelligence.
4. Letta owns persistent agent execution; Agent Studio owns ADE's Letta use.
5. `content/` is reviewed product material; `workflows/` is executable operator work.
6. A product feature has one home, including its UI, API, tests, and README.

## Thirty-Minute Tour

| Time | Read | Learn |
| --- | --- | --- |
| 0-4 min | [Product Roadmap](product-roadmap.md) | The current Agent Behavior Evaluation Loop outcome and its boundaries. |
| 4-8 min | [ADR 0006](adr/0006-comprehension-first-service-and-feature-architecture.md) | Why the architecture exists and its breaking-change rules. |
| 8-13 min | [Architecture Overview](architecture/overview.md) | Services, repository shape, dependency rules, and exposure boundary. |
| 13-20 min | [Request Flows](architecture/request-flows.md) | How Agent Studio, generation labs, content centers, and workflows execute. |
| 20-26 min | One feature's `README.md` | Its user value, endpoints, storage, integrations, and tests. |
| 26-30 min | [Feature README Template](feature-readme-template.md) and [Glossary](glossary.md) | How to add work without recreating cross-cutting ambiguity. |

For the proposed, not-yet-implemented Agent Studio runtime direction, read the
[replacement study](architecture/agent-runtime-replacement-study.md) and then
[ADR 0009](adr/0009-ade-owned-agent-runtime.md). Do not use them as descriptions of
current production behavior while the ADR remains Proposed.

## Find The Right Home

| You need to change... | Start here |
| --- | --- |
| Browser interaction or feature state | `apps/ade-web/src/features/<feature>/` |
| ADE endpoint, contract, or business behavior | `services/ade-api/src/ade_api/features/<feature>/` |
| FastAPI setup, auth, shared settings, or dependency wiring | `services/ade-api/src/ade_api/platform/` |
| Letta or Model Router protocol code | `services/ade-api/src/ade_api/integrations/` |
| Provider source, profile, discovery, or forwarding | `services/model-router/` and `config/model-router/` |
| Prompts, personas, schemas, tools, or reviewed model artifacts | `content/` |
| Eval, probe, smoke check, input, or generated run artifact | `workflows/<workflow>/` |
| Local infrastructure support | `infra/` or root `compose.yaml` |
| A durable architectural decision | `docs/adr/` |

## Contribution Checklist

Before opening a change, identify the feature owner and update its local tests
and README. Prefer a single feature slice over scattering edits across generic
directories. Keep external protocol details in an integration adapter, keep
provider behavior in Model Router, and use public API contracts from workflows.

When a concern looks reusable, first ask whether it belongs to one feature,
`platform/`, an integration, or a workflow. Create a shared package only when
two services need the same stable, versioned contract.

## Structure Compass

Long-lived work belongs in the service-first layout: `apps/ade-web/`,
`services/ade-api/`, `services/model-router/`, `content/`, and `workflows/`.
Keep a complete vertical change with its owner, and do not create compatibility
aliases or duplicate feature implementations.
