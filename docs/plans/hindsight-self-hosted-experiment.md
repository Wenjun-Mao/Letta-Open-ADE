# Self-Hosted Hindsight: Isolated First Experiment

Status: Draft for review, 2026-10-10. The user requested setup planning and
explicitly required isolation from native memory. Hosting direction and isolation
are agreed; the concrete topology, models and experiment below are recommendations,
not installation, model-call or deployment authorization.

Planning baseline: clean primary `main` at
`db52ead17fa3aa358db1d9b1847d64b1a0960562`. Follow
[PC-13](../product-contract.md#hindsight-hosting),
[ADR 0062](../adr/0062-self-hosted-hindsight.md) and the
[review synthesis](../findings/hindsight-consultation/assessment.md).
PC-02/03/04/10/11 govern identity and continuity; PC-01/06/12 govern Character;
PC-07 governs removal; PC-05/08/09 continue governing the unchanged incumbent.

## Recommendation

Run Hindsight on the **Mac in a separate Compose project**, use **DeepSeek Flash
through an isolated instance of ADE Model Router** for extraction/consolidation,
reuse **Spark's Qwen3-Embedding-0.6B endpoint**, and initially run
**BAAI/bge-reranker-v2-m3 on CPU inside Hindsight**. Keep Character on its existing
DeepSeek route with frozen, recorded settings. This is self-hosted memory with
paid hosted language-model inference, not an all-local or free experiment.

Use a **new PostgreSQL instance with pgvector and PGroonga**, not either ADE
database. Chinese lexical retrieval is part of a meaningful Xiaotang experiment;
the English defaults are not a neutral starting point. Do not translate the corpus
to English or call a vector-only smoke test full multilingual qualification.

## What We Can Reuse

Read-only inspection on 2026-10-10 established the following. These are snapshots,
not reservations or inference-performance measurements.

| Resource | Evidence now | Proposed reuse / limit |
| --- | --- | --- |
| Mac | Apple M5 Pro, 24 GiB RAM, 18 CPUs; Docker Linux ARM64 VM has 11.73 GiB RAM. ADE main and history-trial stacks are running. | Host the isolated control/data plane. Do not load another large chat model or change Docker allocation initially. |
| Spark | Reachable over configured Tailscale address; embedding container and H3/ComfyUI services running. Memory snapshot: 121 GiB total, 33 GiB available, 6.1 GiB swap used. | Reuse the existing embedding service at low concurrency. Do not restart, reconfigure or unload any Spark service. |
| Spark embeddings | Local `/v1/models` reports `Qwen/Qwen3-Embedding-0.6B`, served context 8192 tokens. | Reuse inference, not native fact vectors or their qualification. Output dimensions and request compatibility still need a permitted inference probe. |
| Spark chat | Tracked `dgx_vllm` source is disabled; no listener on its configured port 8000 was observed. | The old Qwen chat qualification is historical, not a ready local extraction service. |
| DeepSeek | Tracked route and running trial configuration use `deepseek::deepseek-flash`. | Reuse provider configuration/credential mechanism. No authenticated provider availability or new Hindsight request was tested during planning. |
| Model Router | Source supports OpenAI-compatible chat and embeddings, canonical aliases, bearer auth and one upstream attempt. | Reuse code in an experiment-owned instance; do not alter or join the running native/trial router deployment. It has no rerank route. |
| Character execution | `ConversationExecutor` accepts prepared messages and curated tools without invoking native review/finalization itself. | Reuse through a narrow feature-owned evaluation entrypoint, not workflow imports of feature internals. That entrypoint is still to be implemented. |
| PostgreSQL practice | ADE already uses Compose, pgvector, health checks and separate credentials. | Reuse operational patterns only. Hindsight owns a different database, migrations and volume. |

The `Spark` SSH alias's mDNS hostname did not resolve; its already-configured
Tailscale address worked. Keep container routing explicit rather than relying on
mDNS. No network configuration was changed. Other remote hosts and the historical
Windows llama-server route were not inventoried; they are not ready dependencies.

Relevant existing source: [router catalog](../../config/model-router/sources.json),
[profiles](../../config/model-router/model-profiles.json),
[manifest](../../config/model-router/deployment-manifest.json),
[router boundary](../../services/model-router/README.md),
[native Compose](../../compose.yaml), and
[executor](../../services/ade-api/src/ade_api/features/agent_runtime/executor.py).

## Deployment Shape

```text
Mac: ade-hindsight-probe (new Compose project and network)
  experiment runner / feature-owned Character evaluation entrypoint
      -> Hindsight 0.10.3 API + control plane + embedded worker
          -> dedicated PostgreSQL 17 + pgvector + PGroonga + new volume
          -> experiment Model Router -> DeepSeek (retain/consolidation)
          -> experiment Model Router -> existing Spark Qwen embeddings
          -> local BGE multilingual reranker (CPU)
      -> experiment Model Router -> DeepSeek (Character)

Existing ADE and history-trial projects: unchanged, no shared data/network mounts
```

Use the full Hindsight image because a local reranker needs its ML dependencies.
External embeddings do not make the slim image sufficient for this combination.
Use a single API/embedded-worker process initially, avoiding duplicate reranker
loads; no Kubernetes, Redis, separate queue, distributed workers or extra gateway.

Proposed loopback ports: API `18888`, control plane `19999`, experiment router
`18010` if needed by the host-side runner. No listeners were observed there;
recheck before startup. PostgreSQL has no published port. Use independent API/UI,
router and database credentials, with only the required provider secrets supplied
to the experiment router. Never mount the full native `.env`, database, runtime
directory or Docker socket into Hindsight. Provider sharing is compute/account
reuse, not full resource isolation; run the first probe serially.

Initial resource envelope to test, not measured requirements: up to 6 GiB for
Hindsight including BGE, 1 GiB for PostgreSQL, and 4 CPU cores for the experiment's
heavy work. Check Mac/VM pressure before startup and during recall. The upstream
small-default-model RAM figures do not establish BGE's footprint. Use one local
rerank at a time and a small batch first; an OOM/timeout is a failed readiness
check, not permission to silently drop reranking or take over Spark's GPU.

Pin Hindsight v0.10.3 / source `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`.
Public registry inspection confirmed Linux ARM64 manifests without pulling images:

| Image tag | ARM64 manifest digest |
| --- | --- |
| `ghcr.io/vectorize-io/hindsight:0.10.3` | `sha256:acf5e76bd9a5b65f9f7c540a3414007c7f874b34346587dac7e4feab7ae80cba` |
| `groonga/pgroonga:4.0.8-debian-17` | `sha256:229a259a79cdfa771fdb9e3974f60ea8ac479c57285da520daab039517b4baf3` |

The pinned upstream PGroonga recipe installs `postgresql-17-pgvector` on that
base. Its ARM64 build/package availability and extension initialization remain
unproven here; resolve them before semantic testing. Adapt the recipe into the
owned project, without its public DB binding, example passwords or fixed global
container names. Do not substitute ADE's PostgreSQL when a build fails.

### Placement Alternatives

| Option | Tradeoff / disposition |
| --- | --- |
| Mac control/data plane, existing remote inference | Recommended: closest to ADE development, no Spark service changes; requires Mac awake and access to Spark/DeepSeek. |
| Entire control/data plane on Spark | Viable later for always-on use, but adds remote deployment and shares resources with active media inference. No need for this first replay. |
| All-local extraction/chat models | Later cost/quality experiment: requires a newly provisioned or separately verified endpoint and capacity allocation. Do not conflate it with proving Hindsight's fit. |

## Model And Retrieval Configuration

| Role | First candidate | Important boundary |
| --- | --- | --- |
| Retain, extraction and observation consolidation | `deepseek::deepseek-flash` via experiment router, explicit non-thinking requests | Existing provider reuse; Chinese extraction/labels and schema fidelity are hypotheses to test. Do not inherit high-thinking defaults accidentally. |
| Character response | Same DeepSeek route, frozen existing Character settings and persona | Keep the consumer stable while inspecting memory quality; do not change persona, add a judge or evaluate two new chat models at once. |
| Embeddings | `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B` through router | Expect 1024 dimensions from the recorded deployment, verify live later. New Hindsight vector space, no reuse of ADE's native index. |
| Reranking | `BAAI/bge-reranker-v2-m3`, local CPU provider | Multilingual candidate, not an already-deployed service. Pin model revision/cache; no custom remote-code trust. Measure latency and memory. |
| Keyword retrieval | PGroonga plus pgvector in the dedicated DB | CJK-aware text search; preserve original Chinese text. PostgreSQL's `simple` dictionary is not a substitute for CJK tokenization. |
| Reflect / mental models / Iris | Not part of the first experiment | Do not introduce another generative answer stage or automatic refresh jobs. Ordinary scoped observations are tested separately from raw retained facts. |

Use Hindsight's `openai` provider with the router's `/v1` base URL; this names the
wire protocol, not an OpenAI account. Candidate settings:

```dotenv
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_BASE_URL=http://model-router:8010/v1
HINDSIGHT_API_LLM_MODEL=deepseek::deepseek-flash
HINDSIGHT_API_LLM_EXTRA_BODY={"thinking":{"type":"disabled"}}
HINDSIGHT_API_LLM_STRICT_SCHEMA=false
HINDSIGHT_API_LLM_MAX_CONCURRENT=1
HINDSIGHT_API_FAIL_ON_EXTRACTION_ERRORS=true
HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL=http://model-router:8010/v1
HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B
HINDSIGHT_API_EMBEDDINGS_QUERY_PREFIX="Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: "
HINDSIGHT_API_EMBEDDINGS_MAX_CONCURRENT_REQUESTS=1
HINDSIGHT_API_RERANKER_PROVIDER=local
HINDSIGHT_API_RERANKER_LOCAL_MODEL=BAAI/bge-reranker-v2-m3
HINDSIGHT_API_RERANKER_LOCAL_MAX_CONCURRENT=1
HINDSIGHT_API_TEXT_SEARCH_EXTENSION=pgroonga
HINDSIGHT_API_VECTOR_EXTENSION=pgvector
```

This is a configuration sketch, not a complete environment file. Independent
router credentials, database URL, authentication, cache paths, timeouts and
stable worker ID belong in the implementation. Leave Memory reasoning effort
unset; the explicit thinking override prevents the router from supplying its
high-thinking default. Preserve Hindsight's schema-in-prompt plus `json_object`
validation path; the existing DeepSeek chat adapter rejects `json_schema`.
Prove the actual serialized request with a fake upstream before a paid call.
Do not weaken router validation or silently bypass it on failure.

For remote Qwen embeddings, Hindsight must supply the query instruction; the
router only forwards input. The sketch uses the model card's retrieval example,
not ADE's typed-fact formatter. Verify that the resulting value contains an actual
newline, prefix occurs once, and stored passages are not query-prefixed. The
served Qwen limit is 8192 tokens, not the model card's theoretical maximum;
Hindsight's token counter is different. Keep fixtures short and verify untruncated
inputs. Leave requested dimensions unset initially and inspect the probe result.

Retries are another cost source: the router adds none, but Hindsight's LLM,
consolidation and embedding layers have their own retry paths. Freeze finite
values and record every attempt before running; initially propose zero additional
LLM retries and one consolidation attempt, with SDK embedding retries documented.
Do not describe this as exactly one model call per retained exchange. Keep PC-09's
observational accounting, not a new spending-control subsystem.

## First Experiment And Checkpoints

Keep future executable assets together under proposed
`workflows/evals/hindsight_memory_probe/`: Compose/build recipe, README, synthetic
fixtures, runner, checks and ignored outputs. The feature-owned Character
entrypoint belongs under `services/ade-api/.../agent_runtime/`; expose only the
bounded evaluation call needed by this workflow. No second ADE API/runtime,
generic Memory protocol or native-memory refactor is needed.

1. **Prepare offline.** Record exact image/model/source versions; create the
   isolated Compose/config and fake-upstream tests. Verify forbidden mounts,
   network attachments, native database URLs and native review/finalization calls
   are absent. Test request serialization, scope mapping and complete captures.
   Do not start Hindsight with real credentials in this stage.
2. **Check infrastructure after execution approval.** Build/pull only owned
   candidate resources, initialize only its database/extensions, then start the
   candidate. Verify API/UI auth, loopback bindings, Qwen dimension/prefix,
   structured Chinese extraction, worker completion and BGE resource use.
   A green health endpoint does not prove LLM readiness or semantic correctness.
3. **Run a small frozen Chinese corpus.** Two synthetic subjects and two character
   roots are enough to test shared profile versus private relationship behavior.
   Use attributed immutable exchanges, stable source IDs/time and committed
   assistant text for PC-11. Start with the review's one-bank-per-subject candidate:
   ADE character tags, native profile labels, nonempty strict recall scopes and
   character-local observations. This is a test layout, not adopted access control.
4. **Inspect the complete path.** Cover factual correction, a prior shared event,
   a character's solo story and uncertain missing detail, same-root new-chat/version
   continuity, other-character and other-subject exclusion, and explicit removal
   followed by source replay. Wait for retain completion and distinguish raw
   facts from consolidated observations. Async freshness is not qualified here.
5. **Hold Character fixed.** Compare Hindsight recall context with an empty-memory
   control on selected recall questions, using the same local dialogue and model
   settings without leaking the answer through recent history. Record actual
   model requests, memory/source readback, responses, usage and latency. Assess
   grounding, judgment and fidelity separately; no automated LLM judge is required.
6. **Close the bounded run.** Restart the candidate and prove a retained source is
   still readable. Record failures and qualified limits; do not reroll failed
   semantics until they look successful. Stop the experiment and its background
   work, retaining private receipts and owned volumes for review. Removing those
   volumes is a separate explicit cleanup action, never a global prune.

Before execution, freeze the actual fixtures and expected distinctions so the
corpus is reviewable. These checks diagnose fit, not statistical superiority or
production readiness. Preserve Hindsight curation state alongside source receipts;
transcript re-ingestion is not a guaranteed reconstruction of curated memory.

## Authorization, Exit Criteria And Open Risks

Planning included local Docker/host metadata, bounded read-only Spark inventory
and model-list metadata, public docs/source and registry manifests. No inference,
image pull/build, installation, database query, service change or private dialogue
export was performed. Normal publication applies only to this documentation.

**Execution approval must cover startup model probes as well as the test calls.**
Pinned source shows startup embedding dimension detection and LLM connection
verification can call providers before the first retain. The proposed run needs
model/image downloads, candidate-only DB migrations/start/restart/stop, reuse of
the existing DeepSeek credential through the experiment router, and low-concurrency
Spark inference. One approved bounded run should cover these actions together;
changing shared services, providers, real-data scope or production remains outside it.

Proceed beyond readiness only with correct request shapes, successful Chinese
extraction/recall, bounded resources, complete accounting and untouched native
services. Do not adopt until semantic scope, source attribution and removal results
are reviewed. Remaining risks are BGE CPU latency/RAM, ARM64 database build,
DeepSeek extraction quality, shared Spark contention, and one-bank derived-scope
behavior. A concrete failure should decide the next change, not a broad benchmark
or another consultation by default.

## Sources

- [Hindsight pinned installation guide](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/installation.md): platform/deployment shape; image inspection above adds current manifest evidence.
- [Pinned configuration](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/configuration.mdx): provider settings, query prefixes, retries and resource controls.
- [Pinned multilingual guide](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/multilingual.mdx) and [PGroonga recipe](https://github.com/vectorize-io/hindsight/tree/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/docker/docker-compose/pgroonga): Chinese retrieval requirements.
- [Qwen model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) and [BGE reranker card](https://huggingface.co/BAAI/bge-reranker-v2-m3): model capabilities; no ADE quality result inferred.
- [DeepSeek JSON output](https://api-docs.deepseek.com/guides/json_mode/) and [thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/): provider wire controls, checked 2026-10-10.
- Pinned source checks: `engine/providers/openai_compatible_llm.py`, `engine/embeddings.py`, `engine/memory_engine.py` under upstream `hindsight-api-slim/hindsight_api/`, and local `services/model-router/src/model_router/app.py`. Source compatibility is not a completed integration test.
