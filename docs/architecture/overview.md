# ADE Architecture

This document describes the implemented architecture defined by
[ADR 0006](../adr/0006-comprehension-first-service-and-feature-architecture.md).
The repository tree and each feature's README are the current source for local
ownership and operational details.

Letta Open ADE has one simple system story: **ADE Web** presents the product,
**ADE API** owns the retained v2 product workflows, **ADE Native API** and its
worker own Agent Studio, and **Model Router** owns model access. Letta and Redis
remain temporarily for v2 capabilities during the cutover window; they are not
Agent Studio's memory or execution authority.

```mermaid
flowchart LR
    B[Browser] --> W[ADE Web\napps/ade-web\n:3000]
    W --> A[ADE API\nservices/ade-api\n:8000]
    W --> N[ADE Native API\nade-native-api\n:8002]
    A --> L[Letta\nretained v2 capabilities]
    A --> R[Model Router\nprovider access]
    L --> R
    R --> P[Local and cloud\nmodel providers]
    A --> C[content/\nprompts, personas, schemas, tools]
    L --> S[(PostgreSQL / Redis\nlegacy state)]
    N --> D[(PostgreSQL\nADE v3 state)]
    N -. accepted runs .-> V[ade-runtime-worker]
    V --> D
    V --> R
```

## Repository Shape

```text
apps/
  ade-web/                         # Next.js product UI
    src/app/                       # Thin routes and proxy only
    src/features/                  # Product feature UI, state, API client, tests
    src/shared/                    # UI primitives and HTTP transport

services/
  ade-api/                         # FastAPI product API
    migrations/                    # Alembic authority for ADE-owned PostgreSQL
    src/ade_api/
      platform/                    # App composition, settings, auth, DI
      integrations/                # Letta and Model Router adapters
      features/                    # Feature-owned API/application/storage/tests
  model-router/                    # OpenAI-compatible provider router

content/                           # Reviewed, human-edited product assets
  prompts/ personas/ label-schemas/ custom-tools/ model-catalog/
workflows/                         # Evals, probes, smoke checks, local artifacts
config/                            # Runtime configuration, especially router sources
infra/                             # Non-application container support assets
docs/                              # Architecture, ADRs, and contributor guides
compose.yaml                       # Primary local operator entrypoint
```

`packages/model-catalog-contracts/` contains the small, stable catalog and probe
contracts shared across services. `packages/agent-runtime-eval-contracts/` contains
only runtime-neutral fixtures, observations, scoring, and qualification contracts
shared by the two agent-runtime evals. A generic `core` package is not allowed.

## Architecture Invariants

- Every product capability has one feature home in ADE Web and ADE API.
- A vertical change keeps its UI, API, tests, documentation, and operations in
  the owning feature or workflow, then removes replaced code.
- A current concern has one name and one home. Compatibility aliases and
  duplicate implementations are not retained.
- `content/` holds reviewed product material; `data/runtime/` and workflow
  `outputs/` hold generated local state.

## Feature Ownership

Each feature has one discoverable home in both applications:

```text
features/<feature>/
  README.md                        # Purpose, flow, dependencies, storage, tests
  api.py / contracts.py             # ADE API boundary, when applicable
  service.py                        # Feature application behavior, when applicable
  storage.py                        # Feature persistence adapter, when applicable
  ui/ hooks/ client.ts              # ADE Web behavior, when applicable
  tests/                            # Feature unit and API/UI tests
```

The feature set is: `agent-studio`, `comment-lab`, `label-lab`, `prompt-center`,
`schema-center`, `tool-center`, `test-center`, and `model-catalog`. Agent Studio is
the native v3 product surface; the former separate preview route has been removed.

Feature code may depend on `platform/` contracts and `integrations/`; it must
not import another feature's internal modules. If two features need to interact,
one publishes a narrow application-facing interface or the concern is promoted
to `platform/` only when it is genuinely cross-feature.

```mermaid
flowchart TD
    F[Feature] --> P[platform\ncomposition and shared API concerns]
    F --> I[integrations\nexternal protocol adapters]
    F --> X[feature-owned content or storage adapter]
    P --> F
    I --> L[Letta or Model Router]
    F -. no internal imports .-> O[Other Feature]
```

## Runtime And Network Boundaries

| Component | Owner | Exposure | Canonical name |
| --- | --- | --- | --- |
| ADE Web | Product interface | Host port `3000` | `ade-web`, `ADE_WEB_*` |
| ADE API | Product workflows | Host port `8000` | `ade-api`, `ADE_API_*` |
| Model Router | Provider access | Compose network only | `model-router`, `MODEL_ROUTER_*` |
| Letta | Retained v2 capabilities | Compose network only | `letta`, `LETTA_*` |
| Native runtime worker | Agent Studio run execution | Compose network only | `ade-runtime-worker`, `ADE_API_AGENT_RUNTIME_V3_*` |
| ADE Native API | Agent Studio v3 API | Loopback `8002` and same-origin web proxy | `ade-native-api`, `ADE_NATIVE_API_*` |
| PostgreSQL | Letta and separate ADE v3 databases | Compose network only | `postgres`, `LETTA_PG_*`, `ADE_PG_*` |
| Redis | Retained Letta runtime storage | Compose network only | `redis`, `LETTA_REDIS_*` |

All browser calls use ADE Web's same-origin proxy. The proxy is the only web
component that receives the server-side ADE API credential. It routes `/api/v2`
to `ade-api` and `/api/v3` only to `ade-native-api`; there is no runtime toggle or
fallback. Backend services call Letta or Model Router only across the Compose
network, so browser code never sees those credentials or provider base URLs.

## Content And Workflow Boundaries

`content/` is versioned product material and contains no application imports.
Prompt Center, Schema Center, and Tool Center own the adapters that validate,
read, edit, and activate their respective content. Runtime projections such as
SQLite state and evaluation outputs remain ignored under `data/` or a workflow's
local `outputs/` directory.

`workflows/` owns executable operational work. A workflow has a runner,
configuration, inputs, outputs, documentation, and tests together. Workflows
use public ADE API or Model Router contracts rather than importing ADE API
feature internals.

## Public Contract Direction

ADE API version 2 is organized by the product capability a caller is using:

```text
/api/v2/agent-studio/...
/api/v2/comment-lab/generations
/api/v2/label-lab/generations
/api/v2/prompt-center/prompts and /personas
/api/v2/schema-center/label-schemas
/api/v2/tool-center/tools and /invocations
/api/v2/test-center/runs
/api/v2/model-catalog/options, /models, and /capabilities
/api/v2/health
```

ADE API version 2 remains the supported contract for Comment Lab, Label Lab,
Prompt Center, Schema Center, Tool Center, Test Center, Model Catalog, health, and
the rollback-only legacy Agent Studio endpoints. Model Router retains its
OpenAI-compatible `/v1` API.

Agent Studio uses the breaking `/api/v3` resource model for reusable definitions,
memory subjects, atomic sessions, conversations, turns, runs/events, and typed
memory lineage. The v3 proxy never falls back to v2. See
[ADR 0016](../adr/0016-ade-native-agent-studio-cutover.md) and
[ADR 0017](../adr/0017-incumbent-baseline-does-not-veto-native-cutover.md). Any
future public contract change requires an ADR and regenerated OpenAPI artifacts.
