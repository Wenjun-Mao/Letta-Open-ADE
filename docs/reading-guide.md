# ADE Maintainer Reading Guide

This guide is for maintainers and contributors learning the current
architecture. Start with the [Codebase Map](codebase-map.md) to find the
owner of a change, then use this guide to understand the system boundaries.

For the active product outcome, read the [Product Roadmap](product-roadmap.md).
For a concise statement of current authority and direction, read the
[ADE System Status Map](architecture/system-status.md). The
[Maintenance Roadmap](maintenance-roadmap.md) is retained only as a historical
cleanup record and must not be used to select current work.

## Five-Minute System Model

Read [Architecture Overview](architecture/overview.md), then remember these
six ideas:

1. `ade-web` is the browser product, not the business-logic owner.
2. `ade-api` owns ADE workflows, feature contracts, and orchestration.
3. `model-router` owns provider-facing model access and model intelligence.
4. Agent Studio uses the separately deployed ADE-native v3 API and worker; Letta v2
   remains only as the Phase 5 release-level rollback lane.
5. `content/` is reviewed product material; `workflows/` is executable operator work.
6. A product feature has one home, including its UI, API, tests, and README.

## Thirty-Minute Tour

| Time | Read | Learn |
| --- | --- | --- |
| 0-3 min | [ADE System Status Map](architecture/system-status.md) | Current product authority, native-runtime status, and decision gates. |
| 3-7 min | [Product Roadmap](product-roadmap.md) | The behavior-improvement outcome and Now/Next/Later milestones. |
| 7-11 min | [ADR 0006](adr/0006-comprehension-first-service-and-feature-architecture.md) | Why the architecture exists and its breaking-change rules. |
| 11-16 min | [Architecture Overview](architecture/overview.md) | Services, repository shape, dependency rules, and exposure boundary. |
| 16-23 min | [Request Flows](architecture/request-flows.md) | How Agent Studio, generation labs, content centers, and workflows execute. |
| 23-27 min | One feature's `README.md` | Its user value, endpoints, storage, integrations, and tests. |
| 27-30 min | [Feature README Template](feature-readme-template.md) and [Glossary](glossary.md) | How to add work without recreating cross-cutting ambiguity. |

For the Agent Studio runtime design and evidence-gated release contract, read the
[replacement study](architecture/agent-runtime-replacement-study.md), then
[ADR 0009](adr/0009-ade-owned-agent-runtime.md),
[ADR 0010](adr/0010-production-path-runtime-qualification.md), and
[ADR 0011](adr/0011-agent-runtime-operational-readiness.md), and
[ADR 0013](adr/0013-narrow-native-runtime-product-pilot.md), then the
[`agent_runtime_v3` guide](../services/ade-api/src/ade_api/features/agent_runtime_v3/README.md).
The implementation and cutover design are accepted. Effective product activation is
authorized only by the reviewed release ledger described in ADR 0016 and the
[cutover runbook](operations/agent-studio-cutover.md).

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
