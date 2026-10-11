# Self-Hosted Hindsight: Isolated First Experiment

Status: Revision 3, 2026-10-10. End-to-end implementation/deployment plan for review.
Self-hosting, OCI placement and isolation from native memory are agreed; the user
explicitly requires planning for the current host without waiting for its upgrade.
Implementation, service/model configuration and execution remain proposed.

Planning baseline: clean primary `main` at
`aaae3f1b5472673941be0bbaf46bb1fac5c0e113`. Follow
[PC-13](../product-contract.md#hindsight-hosting),
[ADR 0062](../adr/0062-self-hosted-hindsight.md) and the
[review synthesis](../findings/hindsight-consultation/assessment.md).
PC-02/03/04/10/11 govern identity and continuity; PC-01/06/12 govern Character;
PC-07 governs removal; PC-05/08/09 continue governing the unchanged incumbent.

## Recommendation

Run Hindsight on the **selected OCI ARM host in a separate Compose project**.
Use **DeepSeek Flash through an isolated instance of ADE Model Router** for extraction/consolidation,
reuse **Spark's Qwen3-Embedding-0.6B endpoint**, and initially run
**BAAI/bge-reranker-v2-m3 on CPU inside Hindsight**. Keep Character on its existing
DeepSeek route with frozen, recorded settings. This is self-hosted memory with
paid hosted language-model inference, not an all-local or free experiment.

OCI placement supersedes the original Mac-hosted recommendation after the user
raised Mac memory/swap concerns and a read-only OCI inspection confirmed capacity
and connectivity. The user announced an intended **4 CPU core / 24 GB RAM**
upgrade. **The upgrade is optional headroom, not a prerequisite.** Target
the measured **2-core / approximately 12 GB** host; its earlier available-memory
snapshot supports attempting the bounded workload, not a deployment guarantee.
Refresh actual capacity before execution. The Mac is only a development/browser
client, not the Hindsight server or reranker host. Keep the same conservative
configuration if the owner upgrades before deployment; do not expand the run.

Use a **new PostgreSQL instance with pgvector and PGroonga**, not either ADE
database. Chinese lexical retrieval is part of a meaningful Xiaotang experiment;
the English defaults are not a neutral starting point. Do not translate the corpus
to English or call a vector-only smoke test full multilingual qualification.

## Outcome And Scope

Deliver one reproducible, isolated OCI deployment and one bounded synthetic
Hindsight-to-Character replay, with inspectable results and a tested stop path.
This is not production integration or a measured winner over native memory.

Preparation and OCI deployment are one serial workstream on primary `main`.
Do not introduce native-memory refactoring, dual writes, existing-dialogue export,
a second ADE API, Studio UI work, a generic Memory protocol, Reflect/Iris,
scheduled jobs, new hosted providers, or a broad benchmark. Keep the native/trial
deployments and all pre-existing OCI/Spark services untouched (PC-05/08/09/13).

## What We Can Reuse

Read-only inspection on 2026-10-10 established the following. These are snapshots,
not reservations or inference-performance measurements.

| Resource | Evidence now | Proposed reuse / limit |
| --- | --- | --- |
| OCI ARM host | Ubuntu 24.04.4, 2 Neoverse-N1 cores, 11.65 GiB RAM with 9.7 GiB available; no swap. CPU sampling was 97-99% idle. Docker/Compose already installed. | Selected baseline, usable for the proposed bounded attempt without a resize. Planned 4-core/24 GB upgrade remains unverified and optional. |
| OCI storage/network | 110 GiB available on `/mnt/projects`; Docker root is already on that volume. Spark model-list request returned HTTP 200 over Tailscale. Model metadata and image manifests were reachable. | Put owned deployment state on the project volume. Host reachability does not yet prove the candidate container path or inference. |
| OCI app layout | Additional read-only inspection found TeslaMate and ContentShuttle under `/mnt/projects/apps`; existing Compose labels confirm those working directories. `/mnt/projects/state/docker` holds Docker data. | Use `/mnt/projects/apps/ade-hindsight-probe`; the user permits this parent or `/mnt/projects`. Do not reuse either app's Compose project, network or PostgreSQL. |
| Mac | Apple M5 Pro, 24 GiB RAM; later snapshot showed about 9.1 GiB swap and 5.3 GiB compressor occupancy, with no new swap-outs during 30 seconds. | Keep server/model RAM off the Mac. The snapshot supports caution, not a claim of current thrashing or measured SSD wear. |
| Spark | Reachable over configured Tailscale address; embedding container and H3/ComfyUI services running. Memory snapshot: 121 GiB total, 33 GiB available, 6.1 GiB swap used. | Reuse the existing embedding service at low concurrency. Do not restart, reconfigure or unload any Spark service. |
| Spark embeddings | Local `/v1/models` reports `Qwen/Qwen3-Embedding-0.6B`, served context 8192 tokens. | Reuse inference, not native fact vectors or their qualification. Output dimensions and request compatibility still need a permitted inference probe. |
| Spark chat | Tracked `dgx_vllm` source is disabled; no listener on its configured port 8000 was observed. | The old Qwen chat qualification is historical, not a ready local extraction service. |
| DeepSeek | Tracked route and running trial configuration use `deepseek::deepseek-flash`. | Reuse provider configuration/credential mechanism. No authenticated provider availability or new Hindsight request was tested during planning. |
| Model Router | Source supports OpenAI-compatible chat and embeddings, canonical aliases, bearer auth and one upstream attempt. | Reuse code in an experiment-owned instance; do not alter or join the running native/trial router deployment. It has no rerank route. |
| Character execution | `ConversationExecutor` accepts prepared messages and curated tools without invoking native review/finalization itself. | Reuse through a narrow feature-owned evaluation entrypoint, not workflow imports of feature internals. That entrypoint is still to be implemented. |
| PostgreSQL practice | ADE already uses Compose, pgvector, health checks and separate credentials. | Reuse operational patterns only. Hindsight owns a different database, migrations and volume. |

The `Spark` SSH alias's mDNS hostname did not resolve; its already-configured
Tailscale address worked. Keep container routing explicit rather than relying on
mDNS. No network configuration was changed. OCI reached DeepSeek over HTTPS with
an unauthenticated 401; authenticated model access remains untested. Other remote
hosts and the historical Windows llama-server route were not inventoried.

Relevant existing source: [router catalog](../../config/model-router/sources.json),
[profiles](../../config/model-router/model-profiles.json),
[manifest](../../config/model-router/deployment-manifest.json),
[router boundary](../../services/model-router/README.md),
[native Compose](../../compose.yaml), and
[executor](../../services/ade-api/src/ade_api/features/agent_runtime/executor.py).

## Deployment Shape

```text
OCI ARM, current 2-core host: ade-hindsight-probe (new project/network)
  one-shot experiment runner / feature-owned Character evaluation entrypoint
      -> Hindsight 0.10.3 API + control plane + embedded worker
          -> dedicated PostgreSQL 17 + pgvector + PGroonga + new volume
          -> experiment Model Router -> DeepSeek (retain/consolidation)
          -> experiment Model Router -> existing Spark Qwen embeddings
          -> local BGE multilingual reranker (OCI CPU)
      -> experiment Model Router -> DeepSeek (Character)

Mac browser/development client -> SSH tunnel -> OCI loopback API/UI
Existing ADE/trial and OCI services: unchanged, no shared data/network mounts
```

Use the full Hindsight image because a local reranker needs its ML dependencies.
External embeddings do not make the slim image sufficient for this combination.
Use a single API/embedded-worker process initially, avoiding duplicate reranker
loads; no Kubernetes, Redis, separate queue, distributed workers or extra gateway.
The runner is a one-shot CLI container, not an ADE API/worker or always-on service.

### Owned Files And Storage

Use `/mnt/projects/apps/ade-hindsight-probe/releases/<ADE_SHA>/` for immutable
source/config releases, with an explicit selected release recorded by the runbook.
Keep secrets, receipts and candidate-only dumps under the sibling `private/`
directory (directory mode `0700`, secret files `0600`), outside source releases.
The parent is currently owned by the SSH user `ubuntu`; verify before creating it.
Deploy a clean committed source bundle, not the Mac's working tree or full `.env`.

Give database and pinned model cache project-owned named volumes, resolved under
the existing Docker root. No mount of `/mnt/projects/state/postgres`, shared
backup directories or other apps' state is permitted. Record actual volume names
and mounts before startup; never use `external: true`, a global container name,
host networking or a Docker-socket mount. No new host package/daemon is needed.

Proposed loopback ports: API `18888`, control plane `19999`, experiment router
`18010` only if needed for operator diagnostics. The container runner uses internal
service DNS. No listeners were observed there;
recheck on OCI before startup. Use SSH forwarding for Mac access; do not publish
new public ports or change OCI ingress rules. PostgreSQL has no published port.
Use separate API and UI access keys, router and database credentials, with only
the required provider secrets supplied to the experiment router. Never mount
the full native `.env`, database, runtime
directory or Docker socket into Hindsight. Provider sharing is compute/account
reuse, not full resource isolation; run the first probe serially.

Use the built-in `ApiKeyTenantExtension` with `HINDSIGHT_API_TENANT_API_KEY`;
configure `HINDSIGHT_CP_DATAPLANE_API_KEY` for its API access and a separate
`HINDSIGHT_CP_ACCESS_KEY` for browser login. Verify unauthorized data requests fail
and authenticated UI/API requests work. Loopback and SSH are not substitutes for
application authentication. Disable unused MCP exposure or verify its separate
authentication; no public port, reverse proxy or OCI ingress change is included.

### Current-Host Resource Budget

Working-memory estimate, not measured on OCI: roughly 4-6 GiB for the whole
candidate, with possible 6-8 GiB startup/processing peaks. Initial proposed
container ceilings below are not reservations or proof that every component fits.
The [pinned installation guide](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/installation.md#hardware)
supports two-vCPU basic workloads, but its small
default-model RAM figures do not establish BGE's footprint or latency here.

| Component | RAM ceiling | CPU quota on the two-core host |
| --- | --- | --- |
| Hindsight API, UI, one embedded worker and BGE | 6 GiB | 1.0 core |
| Dedicated PostgreSQL | 1 GiB | 0.25 core |
| Experiment Model Router | 256 MiB | 0.125 core |
| One-shot runner, only while executing | 512 MiB | 0.125 core |
| Combined maximum | 7.75 GiB | 1.5 cores |

Re-read CPU/RAM, service health and available memory before deployment and after
any owner-managed resize. Require at least 9.25 GiB available before starting the
whole candidate, leaving a proposed 1.5 GiB host margin beyond these ceilings;
the earlier 9.7 GiB snapshot meets that check, but is not a reservation. During
build/start/run, sample host memory, CPU/IO pressure, candidate cgroup peaks,
OOM/restart counters and existing-service health. Stop candidate work on an OOM,
new existing-service failure, or available memory below 1.5 GiB for 30 seconds.

Build/download serially before inference; Compose runtime limits do not constrain
Docker image builds. Use low build concurrency, observe host headroom, and stop
the owned build if it threatens other services. Require at least 25 GiB free on
the project volume before staging and stop new work below 15 GiB free. Verify
runtime quotas with Docker inspection, not just a rendered Compose file.

Use one worker slot, one request/rerank at a time, initial rerank batch size 1,
one native ML thread and a small DB pool. Set consolidation reserved slots to 0:
its default of 2 conflicts with a one-slot worker. Drain retain/consolidation
before recall. Keep finite, recorded deadlines; CPU latency is measured rather
than promised. Partial reranking can still return HTTP 200 upstream: require
complete rerank evidence, not merely a successful response status.

Do not add swap, resize OCI, raise ceilings silently, drop reranking or take over
Spark's GPU to pass. A failed resource check calls for a reported configuration
revision, not an assumption that the upgrade has become mandatory.

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
| OCI control/data plane, existing remote inference | Selected. Plan for today's two-core host; no upgrade dependency. Avoids Mac server RAM; CPU reranker latency remains unmeasured. |
| Mac control/data plane, existing remote inference | Original recommendation superseded because the user wants to avoid extra Mac memory/swap pressure. |
| Entire control/data plane on Spark | Viable later for always-on use, but adds remote deployment and shares resources with active media inference. No need for this first replay. |
| All-local extraction/chat models | Later cost/quality experiment: requires a newly provisioned or separately verified endpoint and capacity allocation. Do not conflate it with proving Hindsight's fit. |

## Model And Retrieval Configuration

| Role | First candidate | Important boundary |
| --- | --- | --- |
| Retain, extraction and observation consolidation | `deepseek::deepseek-flash` via experiment router, explicit non-thinking requests | Existing provider reuse; Chinese extraction/labels and schema fidelity are hypotheses to test. Do not inherit high-thinking defaults accidentally. |
| Character response | Same DeepSeek route, frozen existing Character settings and persona | Keep the consumer stable while inspecting memory quality; do not change persona, add a judge or evaluate two new chat models at once. |
| Embeddings | `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B` through router | Expect 1024 dimensions from the recorded deployment, verify live later. New Hindsight vector space, no reuse of ADE's native index. |
| Reranking | `BAAI/bge-reranker-v2-m3`, local CPU provider on OCI | Multilingual candidate, not an already-deployed service. Pin model revision/cache; no custom remote-code trust. Measure latency and memory. |
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
HINDSIGHT_API_RERANKER_LOCAL_BATCH_SIZE=1
HINDSIGHT_API_WORKER_MAX_SLOTS=1
HINDSIGHT_API_WORKER_CONSOLIDATION_RESERVED_SLOTS=0
HINDSIGHT_API_DB_POOL_MIN_SIZE=1
HINDSIGHT_API_DB_POOL_MAX_SIZE=10
HINDSIGHT_API_DB_MAX_PARALLEL_WORKERS_PER_GATHER=0
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
HINDSIGHT_API_TEXT_SEARCH_EXTENSION=pgroonga
HINDSIGHT_API_VECTOR_EXTENSION=pgvector
```

This is a configuration sketch, not a complete environment file. Independent
router credentials, database URL, authentication, cache paths, timeouts and
stable worker ID belong in the implementation. Download BGE at a resolved
immutable model revision during authorized staging, record its manifest, and
point the local-model setting to that snapshot rather than a mutable Hub branch.
Leave Memory reasoning effort unset; the explicit thinking override prevents the
router from supplying its high-thinking default. Preserve Hindsight's schema-in-prompt plus `json_object`
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
Also freeze worker retries and consolidation split/reschedule behavior: disabling
LLM retries does not prevent a failed job or batch from issuing further requests.
Do not describe this as exactly one model call per retained exchange. Keep PC-09's
observational accounting, not a new spending-control subsystem.

## First Experiment And Checkpoints

### P0: Offline Package And Experiment Contract

Keep assets under `workflows/evals/hindsight_memory_probe/`: `README.md`,
`compose.yaml`, `docker/`, `config/`, `fixtures/`, `tests/`, a runner and ignored
`outputs/`. Add a narrow feature-owned evaluation CLI in
`services/ade-api/src/ade_api/features/agent_runtime/`, documented in its README
with tests under `services/ade-api/tests/agent_runtime/`. Workflows call that
entrypoint; they do not import the executor's internals. Record this evaluation
boundary in an ADR during implementation; no generic public API is needed.

The workflow owns immutable source delivery, curation and readback. The feature
entrypoint owns scoped recall and final Character request composition/execution.
For this first live path, inject recalled context before one tool-free Character
generation, rather than adding a new discretionary tool. Hold persona and model
settings fixed across arms; do not relabel character stories as native user facts.
No native database, reviewer, run service or finalizer is constructed by the CLI.

Create an experiment-only router catalog containing DeepSeek and Qwen, preserving
their existing aliases/adapters and explicitly frozen profiles; do not copy all
enabled sources or modify shared router config. Bind source revision, Hindsight
image, database build inputs, BGE revision, fixtures and configuration hashes in a
run manifest. Record finite timeouts/retry semantics and all anticipated startup,
retain, consolidation, recall and Character call categories, not a fabricated
exact total of upstream calls. Never include secrets or private reasoning.

Freeze at most 12 original synthetic source units, eight paired Character questions
(memory versus empty memory), and two preselected adequate-memory control calls:
at most 18 Character generations, plus one separate readiness exchange/recall.
The lifecycle checks below may redeliver sources, but their exact ordered calls
must be listed before execution. No open-ended loops, extra judge or rerolls.
Fixture wording and case assignment are implementation work within these bounds.

Fake-upstream tests cover actual DeepSeek payloads, Qwen prefix/dimensions,
scope filters, invalid/missing scope rejection, immutable retry payload identity,
unavailable versus empty recall, oversized context and complete request captures.
Capture failure must fail experiment qualification despite the executor's
best-effort observer. Static Compose checks reject shared DB URLs, mounts,
networks, missing auth, unbounded worker reservations and unintended providers.
Run focused workflow/evaluation-entrypoint/executor/router tests with
`uv run --locked python -m pytest`, Ruff with `uv run --locked ruff check`, and
`docker compose config` with dummy credentials. Tests needing the pinned Hindsight
image run at P1, before live credentials are supplied; never substitute a
hand-reconstructed request for verification of its actual provider serialization.
No real-credential startup, model/image downloads or OCI changes occur at P0.

### P1: OCI Preflight And Staging

After execution approval, record actual capacity, disks, ports and existing
containers' IDs, image IDs, start times and health. Inventory includes TeslaMate,
Grafana, Mosquitto, its private DB and the separate shared PostgreSQL. No queries
or backups of those databases are needed. Verify the owned path is unused or
belongs to this experiment; stop on conflicting contents rather than overwrite.

Stage the clean, committed release and private secrets into the owned app directory.
Render and inspect resolved configuration without publishing secret-bearing output.
Pull/build only pinned ARM64 candidate images, serially; test the PGroonga recipe's
exact pgvector package availability and both extensions before dependent work.
Resolve a packaging failure at the candidate image layer, not by using a shared
database. Run the pinned-image fake-upstream serialization checks on the owned
network without real provider credentials. Download only the pinned BGE snapshot
into its owned cache. Record resolved image IDs/digests, package/model manifests
and actual disk use. Bind build results back to the committed release manifest.

### P2: Candidate Startup And Infrastructure Acceptance

Start dedicated DB first, create/verify `vector` and `pgroonga` with errors fatal,
then the experiment router, then Hindsight with one stable-ID worker. Keep runtime
restart policy `no` for this attended experiment to avoid crash/restart model-call
loops. There is no always-on/boot activation in this plan.

Verify container-to-Spark Tailscale routing and DeepSeek TLS without changing host
network rules. Verify effective resource limits, DB mounts/extensions, API/UI auth,
loopback-only published sockets, and absence of a published DB port. Test the
documented Mac SSH tunnel and UI login without additional generation.

Account for automatic startup LLM/embedding checks. In a disposable readiness bank,
run the one Chinese exchange/recall: verify dimensions, one query prefix, complete
extraction, terminal operation state and full BGE reranking within recorded
deadlines/ceilings. Capture peak memory and latency. A healthy API, partial rerank
or merely accepted async operation is insufficient. Stop on failure before P3.

### P3: Frozen Semantic Replay

Use two subjects and two character roots, with one bank per workspace/subject as
the first hypothesis. ADE supplies character identity; narrow extraction labels
identify shared profile facts. Use nonempty strict character-OR-profile scopes,
character-local consolidation and shared raw profile facts, not shared observations.
Do not mark entire private source documents as profile-visible. Initially exclude
raw chunks/source bundles from Character context. Test before/after consolidation.

| Case | Required observation |
| --- | --- |
| Shared profile plus private origin in one sentence | Other character sees only the profile fact, not the private conversation/event. |
| Referential update and factual correction | Attribution and current meaning survive; old source text is not rewritten. |
| Shared event and committed solo story | Speaker/participation stay distinct; hypothetical or unsupported user claims do not become shared history. |
| Missing detail | Character does not invent the unstated remembered detail (PC-11). |
| New chat, ordinary version edit and archive | Same subject/root stays eligible; another root or subject stays excluded (PC-02/03/04/10). |
| Operator invalidation | Check unrelated ingestion, same-source retry and repeated old context in a new source separately; distinguish correction from removal (PC-07). |

Use attributed immutable exchanges, source IDs/times and committed assistant text.
Wait separately for retain and consolidation, then compare the frozen Character
arms with identical local dialogue, without leaking answers through recent history.
Retain requests, operation/fact/observation/source readback, final serialized model
inputs, replies, usage and latency. Assess grounding, judgment and fidelity
separately (PC-12); no claim of statistical superiority or async freshness.

### P4: Persistence, Stop And Review

After jobs drain, restart only the candidate once with the same volumes and stable
worker identity; account for repeated startup probes. Independently read back a
retained source and curated state, without re-ingesting the corpus. This proves
bounded restart persistence, not backup/restore or crash-recovery qualification.

Stop runner and Hindsight/worker first, preserve receipts and a candidate-only
logical DB dump, then stop router and DB. Retain owned volumes/cache; do not use
`down -v` or any prune. Recheck existing-service identity/health and host headroom.
Record infrastructure results separately from semantic pass/fail and remaining
questions. Redact private receipts into a concise finding; update tracker/roadmap
without declaring adoption, integration or release qualification.

The runbook must give exact commands for preflight, stage, start, inspect, run,
restart and stop, always using the selected release and `-p ade-hindsight-probe`.
On any stage failure, stop only owned work, preserve failed evidence/volumes and
report the cause. Do not roll an older image onto a newer schema, auto-reingest
to repair curation, retry semantic failures or repair shared services. Mechanical
preparation fixes within the approved architecture, pins and resource limits can
proceed with renewed offline checks. Changing providers/semantics/limits or adding
a live campaign requires a new scope decision, not a silent reroll.

## Authorization, Exit Criteria And Open Risks

Planning included local Docker/host metadata, bounded read-only Spark and OCI
inventory, app-directory/Compose-label inspection, model-list/connectivity
metadata, public docs/source and registry manifests. OCI host selection is
accepted; its upgrade remains owner-managed and
pending verification, not a dependency. The user permits an app directory under
`/mnt/projects` or `/mnt/projects/apps`; directory creation is part of later
execution, not this read-only inspection. No inference,
image pull/build, installation, database query, service change or private dialogue
export was performed. Normal publication applies only to this documentation.

**One end-to-end execution approval should cover P0-P4, including OCI deployment
and startup model probes, not just offline implementation.**
Pinned source shows startup embedding dimension detection and LLM connection
verification can call providers before the first retain. The proposed run needs
model/image downloads and deployment to OCI, candidate-only DB migrations and
start/restart/stop, reuse of the existing DeepSeek credential through the
experiment router, and low-concurrency Spark inference. One approved bounded run
should cover these actions together;
changing shared services, providers, real-data scope or production remains outside it.
It also covers the clean source transfer, private credential staging, pinned
downloads, candidate-only dump, planned restart and final stop. Continue covered
steps without repeated milestone permission requests; stop for failed acceptance
checks or uncovered scope/risk changes. Existing commit/push approval covers
scoped verified source/docs only. Planning approval is not execution approval.

Proceed beyond readiness only with correct request shapes, successful Chinese
extraction/recall, bounded resources, complete accounting and untouched native
services. Do not adopt until semantic scope, source attribution and removal results
are reviewed. Remaining risks are capacity drift, BGE CPU latency/RAM,
ARM64 database build and CPU quota sufficiency,
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
