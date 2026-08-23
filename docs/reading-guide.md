# ADE Maintainer Reading Guide

This guide is for maintainers and contributors learning the **target**
architecture. Start with the current [Codebase Map](codebase-map.md) while the
migration is in progress; use this guide to understand where the project is
going and how to place new work.

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
| 0-5 min | [ADR 0006](adr/0006-comprehension-first-service-and-feature-architecture.md) | Why the target exists and the breaking-change rules. |
| 5-10 min | [Architecture Overview](architecture/overview.md) | Services, repository shape, dependency rules, and exposure boundary. |
| 10-18 min | [Request Flows](architecture/request-flows.md) | How Agent Studio, generation labs, content centers, and workflows execute. |
| 18-25 min | One feature's `README.md` | Its user value, endpoints, storage, integrations, and tests. |
| 25-30 min | [Feature README Template](feature-readme-template.md) and [Glossary](glossary.md) | How to add work without recreating cross-cutting ambiguity. |

## Find The Right Home

| You need to change... | Start in the target layout |
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

## Migration Compass

During the transition, a legacy location and its target replacement can coexist
only while one vertical slice is being moved. New long-lived work belongs in the
service-first layout: `apps/ade-web/`, `services/ade-api/`,
`services/model-router/`, `content/`, and `workflows/`. A completed slice deletes
its replaced paths; do not create compatibility aliases or duplicate feature
implementations.
