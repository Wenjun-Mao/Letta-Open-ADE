# ADE-Native Agent Runtime Study

This workflow is the reproducible architecture-study harness for a possible
ADE-owned Agent Studio runtime. It does not serve production traffic, modify the
current API, migrate Letta data, or change Compose. Generated evidence is written
under `outputs/`, which is intentionally ignored.

Read the full conclusions in
[`docs/architecture/agent-runtime-replacement-study.md`](../../../docs/architecture/agent-runtime-replacement-study.md)
and the unaccepted decision proposal in
[`docs/adr/0009-ade-owned-agent-runtime.md`](../../../docs/adr/0009-ade-owned-agent-runtime.md).

## What It Measures

- A shared `AgentRuntime.run_turn(...) -> TurnResult` product contract.
- Typed, subject-bound `add`, `correct`, `merge`, and `forget` memory proposals.
- Immutable messages, versioned facts/revisions/summaries, optional episodes, and
  normalized run events.
- Context ordering and bounded token construction.
- Exact ADE-owned timeout, cancellation, idempotency, and retry behavior.
- A minimal OpenAI-compatible tool loop against a PydanticAI `2.35.1` adapter.
- Fact-only retrieval against fact-plus-episode retrieval.
- Product-faithful live fixtures through Model Router.
- Current Letta behavior through disposable ADE API agents only.

The study tool schema deliberately accepts a free-form fact key so live model
behavior remains observable. It is not the proposed production contract: the report
requires ADE-owned, versioned fact types and cardinality/entity rules after live DGX
produced semantically duplicate keys for the same pet-name evidence.

Static scripted tests establish executor semantics. Live runs establish model and
provider compatibility. The Letta probe establishes current externally observable
behavior. These evidence classes are deliberately reported separately.

## Layout

```text
agent_runtime_study/
  run.py                    # CLI entrypoint
  config.toml               # Non-secret defaults
  contracts.py              # Shared domain/runtime contracts
  repository.py             # Deterministic transactional study store
  memory.py                 # Memory policy and retrieval
  context.py                # Context assembly and budgeting
  tools.py                  # Three curated study tools
  runtime.py                # ADE-owned orchestration
  adapters/                 # Custom-loop and PydanticAI executors
  fixtures/study_cases.json # Product and isolation fixtures
  tests/                    # Deterministic contract coverage
```

## Setup

Install the established workspace environment:

```bash
uv sync --all-packages --frozen --group dev
```

The PydanticAI candidate intentionally uses the official slim OpenAI extra rather
than the full meta package:

```text
pydantic-ai-slim[openai]==2.35.1
```

## Static Study

Run deterministic adapter contracts, retrieval comparison, source/dependency
metrics, and provenance capture:

```bash
uv run python workflows/evals/agent_runtime_study/run.py
```

The static candidate result is not a live-model qualification. In particular,
framework validation retries and SDK retries are set to zero for both candidates;
`retry_count` means additional ADE-owned attempts after the first.

## Current Letta Probe

With Compose running, black-box the pinned Letta behavior through ADE API. The
probe creates a disposable agent and always attempts archive/purge cleanup:

```bash
AGENT_RUNTIME_STUDY_ADE_API_BASE_URL=http://127.0.0.1:${ADE_API_PORT:-8000} \
uv run python workflows/evals/agent_runtime_study/run.py --letta-baseline
```

The probe records creation, chat/tool traces, memory snapshots, persisted-history
growth, raw-prompt growth, manual memory editing, a zero-retry failure, archive
blocking, and purge. It does not claim to prove hidden internal retry counts or
long-history compaction.

## Live Model Study

Model Router is internal-only by design. Run from a network location that can
reach it, or supply a temporary operator-side address without changing Compose:

```bash
AGENT_RUNTIME_STUDY_ROUTER_V1_BASE_URL=http://MODEL_ROUTER_HOST:8010/v1 \
uv run python workflows/evals/agent_runtime_study/run.py --live
```

Focused examples:

```bash
uv run python workflows/evals/agent_runtime_study/run.py \
  --live \
  --adapter custom_loop \
  --model 'dgx_vllm::qwen3.6-35b-a3b-fp8' \
  --case chat_memory_baseline \
  --timeout-seconds 180 \
  --max-output-tokens 4096
```

DGX Qwen is the primary model. `local_llama_server::gemma4` is the compatibility
model. The default 16,384-token study window reserves 4,096 output tokens because
DGX thinking is intentionally enabled by its Model Router profile.

## Fixtures

The suite covers the restored Chinese chat-memory baseline, corrections,
forgetting, cross-agent subject sharing, cross-subject isolation, old-memory deep
search, long-history summaries, false-memory prevention, weather selection, and
weather failure. Synthetic source messages make raw model evidence safe to retain.

## Artifacts

Each run creates:

- `summary.json`: scores, facts, revisions, and candidate evidence.
- `turns.jsonl`: per-turn context, raw model messages, normalized events, tools,
  memory revisions, usage, and latency.
- `provenance.json`: repository state, source/fixture/lock hashes, exact Letta image
  digest and runtime version, PydanticAI version, effective non-secret config, Model
  Router catalog, and upstream references.

Do not commit generated outputs. Preserve a durable conclusion in the architecture
study or ADR instead.

## Verification

```bash
uv run python -m pytest workflows/evals/agent_runtime_study/tests -q
uv run ruff check workflows/evals/agent_runtime_study
```
