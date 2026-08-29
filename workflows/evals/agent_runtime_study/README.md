# ADE-Native Agent Runtime Study

This directory is a reproducible architecture-study harness for a possible
ADE-owned Agent Studio runtime. It does not serve production traffic, modify the
current API, migrate Letta data, or change Compose. Generated evidence is written
under `outputs/`, which is intentionally ignored.

Read the conclusions in
[`docs/architecture/agent-runtime-replacement-study.md`](../../../docs/architecture/agent-runtime-replacement-study.md)
and the accepted implementation decision in
[`docs/adr/0009-ade-owned-agent-runtime.md`](../../../docs/adr/0009-ade-owned-agent-runtime.md).
Production-path qualification is separate and is governed by
[`docs/adr/0010-production-path-runtime-qualification.md`](../../../docs/adr/0010-production-path-runtime-qualification.md).

## What It Measures

- A shared `AgentRuntime.run_turn(...) -> TurnResult` product contract.
- Reusable agent definitions, explicit memory subjects, immutable messages,
  versioned summaries, and normalized run events.
- A closed fact-type registry with stable entities and typed `add`, `correct`,
  `merge`, and `forget` proposals.
- A dedicated post-response memory reviewer, independent of the conversation model
  loop and unable to select a subject ID.
- Atomic assistant-plus-memory commit: an invalid or failed review commits neither.
- Bounded context assembly and multilingual subject-bound retrieval.
- Exact ADE-owned timeout, cancellation, idempotency, and retry behavior.
- A minimal OpenAI-compatible tool loop compared with PydanticAI `2.35.1` under the
  same contracts.
- Exact deployment fingerprinting and role-specific qualification for conversation,
  reviewer, and retriever deployments.
- Current Letta behavior through disposable ADE API agents only.

Static scripted tests establish executor semantics. Live runs establish model and
deployment compatibility. The Letta probe establishes current externally observable
behavior. These evidence classes are reported separately.

## Runtime Boundary

The conversation model receives only two curated tools: subject-bound
`search_memory` and the deterministic `get_weather` fixture. It cannot write memory.
After a user-visible response, the required reviewer receives the current user
message, prior user messages, and an ADE-built inventory of active facts/entities.
It never receives assistant text or a selectable subject ID.

Reviewer output is parsed against a closed schema, checked against exact source
spans and the product-owned fact registry, then staged transactionally. Corrections
must be `correct`; forgetting requires explicit forgetting intent. ADE assigns all
durable entity IDs. A failed review leaves the accepted user message immutable but
commits no assistant message and no memory revision.

The study compiles the production chat prompt into an ADE-native variant by removing
Letta-owned memory-tool and inner-monologue instructions. Production prompt files are
not changed.

## Layout

```text
agent_runtime_study/
  run.py                         # CLI entrypoint
  config.toml                    # Non-secret defaults
  contracts.py                   # Study-only runtime execution contracts
  fact_registry.py               # Closed fact and entity rules
  memory_review.py               # Dedicated reviewer protocol
  repository.py                  # Transactional deterministic study store
  memory.py                      # Proposal validation and projections
  semantic_retrieval.py          # Direct zero-retry embedding client/retriever
  context.py                     # Context assembly and budgeting
  product_material.py            # Study-only prompt compiler
  tools.py                       # Search and weather tools
  runtime.py                     # ADE-owned orchestration
  adapters/                      # Custom-loop and PydanticAI executors
  tests/                         # Deterministic contract coverage
```

Canonical fixtures, runtime-neutral observations, deterministic scoring, and
qualification primitives live in the buildable
`packages/agent-runtime-eval-contracts/` package. Exact deployment metadata has
one checked-in authority: `config/model-router/deployment-manifest.json`.

## Setup And Static Study

Install the established workspace environment, then run the deterministic adapter
contracts, source metrics, and provenance capture:

```bash
uv sync --all-packages --frozen --group dev
uv run python workflows/evals/agent_runtime_study/run.py
```

The PydanticAI candidate uses `pydantic-ai-slim[openai]==2.35.1`. Framework and SDK
retries are zero for both candidates. `retry_count` always means additional
ADE-owned attempts after the first.

## Current Letta Probe

With Compose running, black-box pinned Letta behavior through ADE API. The probe
creates a disposable agent and always attempts archive/purge cleanup:

```bash
AGENT_RUNTIME_STUDY_ADE_API_BASE_URL=http://127.0.0.1:${ADE_API_PORT:-8000} \
uv run python workflows/evals/agent_runtime_study/run.py --letta-baseline
```

The probe records creation, chat/tool traces, memory snapshots, persisted-history
growth, raw-prompt growth, manual memory editing, a zero-retry failure, archive
blocking, and purge. It does not claim to prove hidden internal retry counts or
long-history compaction.

## Live Model Study

Model Router is internal-only by design. Run from a location that can reach it or
supply a temporary operator-side address without changing Compose:

```bash
AGENT_RUNTIME_STUDY_ROUTER_V1_BASE_URL=http://MODEL_ROUTER_HOST:8010/v1 \
uv run python workflows/evals/agent_runtime_study/run.py \
  --live \
  --adapter custom_loop \
  --model 'dgx_vllm::qwen3.6-35b-a3b-fp8' \
  --timeout-seconds 180 \
  --retry-count 0 \
  --max-output-tokens 4096
```

DGX Qwen is the primary conversation and required reviewer deployment.
`local_llama_server::gemma4` is a route alias for the compatibility deployment, not
its identity. The exact served artifact, revision/digest, runtime, hardware, context,
sampling, and policy hashes are declared in the deployment manifest and copied into
each run's qualification artifact.

Multilingual retrieval uses a direct OpenAI-compatible Qwen3-Embedding-0.6B sidecar
on the DGX Spark. The workflow client sets provider retries to zero. Automatic
retrieval applies the calibrated similarity threshold; an explicit
`search_memory` call returns top subject-bound candidates without that automatic
precision cutoff.

## Deployment Qualification

A route alias is never treated as a durable model identity. Every deployment is
qualified independently for one or more roles using its exact fingerprint and four
policy-bundle hashes. Any fingerprint or policy change makes prior rounds stale.

This study records historical research evidence only. Release qualification now
requires three consecutive passing rounds through the real `/api/v3` API, worker,
and PostgreSQL path. Direct `custom_loop` rounds and focused `--case` diagnostics
cannot advance or repair production qualification history. Use
`workflows/evals/agent_runtime_v3_acceptance/` for that gate.

Conversation and reviewer outcomes are scored independently. A valid candidate
response is not failed merely because memory review is rejected, and a successful
reviewer is not failed by a conversation-only tool-selection error. A role that was
not observed across the complete matrix receives no round.

Unqualified deployments are blocked by default. This study uses an explicit
development override so candidates can be measured; the override is recorded in
`qualification.json` and must not be interpreted as release approval. There is no
reviewer fallback: reviewer failure fails the turn atomically.

## Fixtures And Artifacts

The runtime suite covers the restored Chinese chat-memory baseline, corrections,
forgetting, cross-agent subject sharing, cross-subject isolation, old-memory deep
search, long-history summaries, false-memory prevention, weather selection, and
weather failure. The retrieval suite includes multilingual positives, hard
negatives, and subject-isolation cases over a larger synthetic corpus.

Each run creates:

- `summary.json`: case scores, facts, revisions, qualification assessment, and
  coverage evidence.
- `turns.jsonl`: per-turn context, reviewer evidence, normalized events, tools,
  memory revisions, usage, and latency.
- `retrieval.json`: strategy, held-out metrics, thresholds, and acceptance checks.
- `qualification.json`: exact fingerprints, policy hashes, role rounds, lifecycle,
  and study-override decisions.
- `provenance.json`: repository/source/fixture/lock hashes, effective non-secret
  config, dependency versions, and upstream references.

Do not commit generated outputs. Promote stable conclusions into the architecture
study or ADR instead.

## Verification

```bash
uv run python -m pytest workflows/evals/agent_runtime_study/tests -q
uv run ruff check workflows/evals/agent_runtime_study
```
