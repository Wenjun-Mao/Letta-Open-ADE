# Self-Hosted Hindsight: Isolated First Experiment

Status: Revision 4 activated in Goal mode, 2026-10-11 04:49:25 UTC. The user
authorized ten hours of autonomous progress with a twelve-hour hard cap and
separate Codex tasks. Supersedes revision 3's replay limits and execution gates.

Planning baseline: clean primary `main` at
`b108a01cd3d2fc484fad249312819bff97f99c47`. Follow
[PC-13](../product-contract.md#hindsight-hosting),
[ADR 0062](../adr/0062-self-hosted-hindsight.md) and the
[review synthesis](../findings/hindsight-consultation/assessment.md).
PC-02/03/04/10/11 govern identity and continuity; PC-01/06/12 govern Character;
PC-07 governs removal; PC-05/08/09 continue governing the unchanged incumbent.

## Recommendation

Use an isolated OCI Compose project: Hindsight, dedicated PostgreSQL with
pgvector/PGroonga, experiment Model Router, existing DeepSeek Flash and Spark Qwen
embeddings, initially BGE-v2-m3 CPU reranking. This uses paid LLM inference, not
all-local/free processing. Keep Character settings fixed across comparison arms.

Target the **2-core / approximately 12 GB** host. **The upgrade is optional
headroom, not a prerequisite.** Refresh capacity before execution; the earlier
snapshot supports an attempt, not a deployment guarantee. OCI supersedes the
Mac placement to avoid workstation RAM pressure; the Mac stays client-only.
An owner-managed resize permits evidence-backed retuning, not scope expansion.
Preserve Chinese text and CJK lexical retrieval; do not substitute English
translation or call vector-only diagnostics full multilingual qualification.

## Outcome And Scope

Deliver a reproducible isolated OCI deployment, evidence-backed Chinese
memory-to-Character assessment, justified repairs/retests and safe recovery/stop
procedures. Target ten hours from activation, never exceed the twelve-hour cap.
This is not production integration or a measured winner over native memory.

Preparation and OCI deployment are one serial workstream on primary `main`.
Do not introduce native-memory refactoring, dual writes, existing-dialogue export,
a second ADE API, Studio UI work, a generic Memory protocol, Reflect/Iris,
recurring product jobs, new hosted providers, or a broad benchmark. Keep the native/trial
deployments and all pre-existing OCI/Spark services untouched (PC-05/08/09/13).

## Activation And Decision Authority

**Start only when the user explicitly starts Goal mode against this plan.** That
start authorizes the complete P0-P4 campaign below, not just offline preparation:
implementation, verification, normal commits/pushes, owned OCI staging and secret
transfer, image/model downloads and builds, candidate DB migrations, service
start/restart/stop, DeepSeek/Spark inference including startup probes, evaluation
iterations, disposable restore checks and safe cleanup. Do not seek a second
approval at each checkpoint. Planning alone does not authorize those actions.

### Routine Decisions: Proceed Without Asking

- Diagnose root causes, edit the owning code/config, add regression tests, rebuild,
  redeploy only the candidate, and repeat affected checks. Packaging, serialization,
  auth wiring, timeouts, transient failures and incomplete captures are engineering
  work, not permission blockers. Retry with finite backoff rather than busy loops.
- Tune candidate CPU/RAM allocation, DB pools, batching, concurrency and finite
  retry/deadline settings within the measured host safety envelope below. Defaults
  are starting points, not immutable per-container ceilings or an upgrade gate.
- Adjust memory-side prompts, labels, query/context composition and retrieval
  settings while preserving PC scope/grounding/removal expectations. If evidence
  warrants it, test the review's separate profile/relationship-bank alternative
  in new experiment-owned banks. Neither layout becomes product policy overnight.
- Resolve candidate dependency/ARM64 packaging defects with compatible pinned
  builds or a narrow source patch; Hindsight 0.10.x and PostgreSQL 17 remain the
  initial compatibility family. Review affected upstream contracts and requalify
  them when changing a pin; prior source review is not proof for a new version.
- If BGE cannot meet resource/latency needs, select and pin another suitably
  licensed multilingual CPU reranker, then repeat relevant quality/resource tests.
  Keep the existing DeepSeek and Spark embedding routes; no new provider/account
  or shared model-server reconfiguration. Keep Character settings fixed across
  comparisons. Diagnostic ablations are allowed, never substitutes for acceptance.
- Add small synthetic regressions and repeat the relevant subset or full suite
  after substantive changes. There is **no fixed replay or total-generation cap**.
  Each live iteration needs a concrete hypothesis, change or measurement purpose;
  keep comparable before/after evidence and observed usage. No blind rerolls or
  enlarged benchmark merely to occupy remaining time (PC-09).
- Create/reset run-owned scratch banks/databases and restore copies, preserving
  their receipts first. Retain baseline/final curation state and volumes; do not
  erase the only failed evidence. Clean only positively identified disposable
  campaign resources, never shared images/volumes or a global prune.

### Real Escalations

Ask only when progress requires touching existing ADE/OCI/Spark services or data;
public exposure or shared firewall/network changes; new accounts, top-ups,
infrastructure purchases or
provider credentials unavailable through the configured mechanism; real/private
conversation export; production adoption or changed PC requirements; a material
architecture change outside this experiment; or bypassing host safety, security,
license or native approval requirements. Respect any mandatory tool approval.
Missing optional review tools and ordinary test failures are not escalation cases.

If one branch needs owner input, stop its unsafe/dependent actions, record the
decision needed and continue independent in-scope work. Do not repeatedly ask an
absent owner, silently broaden authority, or declare the whole campaign blocked
while useful work remains. Report a genuine impasse if no safe progress remains.

### Time And Completion

Activation: `2026-10-11T04:49:25Z`; target `2026-10-11T14:49:25Z`, hard stop
`2026-10-11T16:49:25Z`. These absolute times survive resumptions; do not extend them.
Rough priorities: prepare in hours 0-3, deploy/qualify in 3-5, evaluate in 5-7,
repair/retest/recover in 7-9, then close out; reallocate freely. Reserve the last
45 minutes for safe shutdown/reporting, and finish early if the work is complete.
At deadline/impasse, provide a truthful partial handoff, not a false completion
claim. Goal mode is active; no heartbeat or agent daemon is needed. OCI-side expiry
bounds work if continuation is interrupted. Finish early when the work is complete.

## What We Can Reuse

The 2026-10-10 inventory and subsequent app-layout check are historical snapshots,
not reservations or inference-performance measurements; refresh before execution.

| Resource | Evidence now | Proposed reuse / limit |
| --- | --- | --- |
| OCI ARM host | Ubuntu 24.04.4, 2 Neoverse-N1 cores, 11.65 GiB RAM with 9.7 GiB available; no swap. CPU sampling was 97-99% idle. Docker/Compose already installed. | Selected baseline, usable for the proposed bounded attempt without a resize. Planned 4-core/24 GB upgrade remains unverified and optional. |
| OCI storage/network | 110 GiB available on `/mnt/projects`; Docker root is already on that volume. Spark model-list request returned HTTP 200 over Tailscale. Model metadata and image manifests were reachable. | Put owned deployment state on the project volume. Host reachability does not yet prove the candidate container path or inference. |
| OCI app layout | Additional read-only inspection found TeslaMate and ContentShuttle under `/mnt/projects/apps`; existing Compose labels confirm those working directories. `/mnt/projects/state/docker` holds Docker data. | Use `/mnt/projects/apps/ade-hindsight-probe`; the user permits this parent or `/mnt/projects`. Do not reuse either app's Compose project, network or PostgreSQL. |
| Spark embeddings | Running Qwen service reports `Qwen/Qwen3-Embedding-0.6B`, served context 8192 tokens; H3/ComfyUI also run there. | Low-concurrency inference only. Do not restart, reconfigure or unload shared services. Dimensions/compatibility remain to be probed. |
| DeepSeek | Tracked route and running trial configuration use `deepseek::deepseek-flash`. | Reuse provider configuration/credential mechanism. No authenticated provider availability or new Hindsight request was tested during planning. |
| Model Router | Source supports OpenAI-compatible chat and embeddings, canonical aliases, bearer auth and one upstream attempt. | Reuse code in an experiment-owned instance; do not alter or join the running native/trial router deployment. It has no rerank route. |
| Character execution | `ConversationExecutor` accepts prepared messages and curated tools without invoking native review/finalization itself. | Reuse through a narrow feature-owned evaluation entrypoint, not workflow imports of feature internals. That entrypoint is still to be implemented. |
| PostgreSQL practice | ADE already uses Compose, pgvector, health checks and separate credentials. | Reuse operational patterns only. Hindsight owns a different database, migrations and volume. |

Use Spark's configured Tailscale address, not its unresolved mDNS name. OCI's
unauthenticated DeepSeek HTTPS response proved reachability, not model access.
No planning probe made inference calls or changed remote files/services.

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
The parent was owned by SSH user `ubuntu` at inspection; verify before creating it.
Deploy a clean committed source bundle, not the Mac's working tree or full `.env`.

Give database and pinned model cache project-owned named volumes, resolved under
the existing Docker root. No mount of `/mnt/projects/state/postgres`, shared
backup directories or other apps' state is permitted. Record actual volume names
and mounts before startup; never use `external: true`, a global container name,
host networking or a Docker-socket mount. No new persistent host service is needed.

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

Refresh actual capacity and existing-service health before deployment/after any
owner resize. Reallocate candidate limits autonomously from measured peaks while
leaving at least 1.5 GiB beyond the combined prospective RAM ceilings and at least
0.5 CPU core outside the candidate quotas, with more allowance when incumbent
load requires it. The initial table needs 9.25 GiB available; earlier 9.7 GiB met
that check. If it no longer fits, revise the candidate allocation rather than
automatically wait for an upgrade. Record every allocation and its evidence.
During build/start/run, sample host memory, CPU/IO pressure, candidate cgroup peaks,
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

Do not add swap, resize OCI, hide limit changes, drop required retrieval capability
to claim success, or take over Spark's GPU. Stop unsafe work, diagnose, then resume
within the envelope without renewed approval; the upgrade is not mandatory.

Start with Hindsight v0.10.3 / source `eb6df499d35300e5b2f3f029b2e6adda04ed90f8`;
pin every evaluated revision, including justified compatibility repairs.
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

This sketch still needs credentials, DB URL, auth, cache paths, deadlines and a
stable worker ID. Resolve an immutable BGE snapshot and load its local path.
Leave Memory reasoning effort unset initially; explicit thinking-disabled avoids
the router's high-thinking default. Verify Hindsight's schema-in-prompt plus
`json_object` path with a fake upstream; DeepSeek's adapter rejects `json_schema`.
Do not weaken/bypass validation. For Qwen, verify one query prefix with an actual
newline, no prefix on stored passages, dimensions and untruncated inputs under
the served 8192-token limit, not the model card's theoretical maximum.

Use finite request/token/time limits and explicit retry/backoff settings, initially
zero extra LLM retries and one consolidation attempt. Account for embedding SDK,
worker, split/reschedule and startup calls too; one retained exchange is not one
model call. Tune these mechanics when justified, retaining observational usage
under PC-09 rather than a new runtime spending-control subsystem.

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

Start with roughly 12 synthetic source units, eight paired questions (memory
versus empty memory), two adequate-memory controls and a separate readiness case.
This is a small comparison anchor, not a cap on retries, cases or generations.
Version fixtures and expected distinctions before observing each iteration;
preserve the original suite and add regressions rather than rewriting failures
away. Freeze ordered lifecycle calls per iteration; no extra LLM judge is needed.

Fake-upstream tests cover actual DeepSeek payloads, Qwen prefix/dimensions,
scope filters, invalid/missing scope rejection, immutable retry payload identity,
unavailable versus empty recall, oversized context and complete request captures.
Embedding response capture accepts validated numeric arrays and base64 float32
vectors while retaining dimensions only; it preserves the SDK request format and
fails qualification on malformed successful replies. Capture failure must fail
experiment qualification despite the executor's best-effort observer. Static
Compose checks reject shared DB URLs, mounts,
networks, missing auth, unbounded worker reservations and unintended providers.
Run focused workflow/evaluation-entrypoint/executor/router tests with
`uv run --locked python -m pytest`, Ruff with `uv run --locked ruff check`, and
`docker compose config` with dummy credentials. Tests needing the pinned Hindsight
image run at P1, before live credentials are supplied; never substitute a
hand-reconstructed request for verification of its actual provider serialization.
No real-credential startup, model/image downloads or OCI changes occur at P0.

**P0 offline checkpoint, 2026-10-11:** the frozen synthetic corpus and query
distinctions, immutable reference-context/payload freezer, public-HTTP workflow
for readiness/retain/consolidation/curation/readback/replay, feature-owned
pre-generation full-rerank qualification and correlated phase protocol are
implemented and covered by offline fake-upstream checks. This status does not
claim P1 image/provider qualification, P2 candidate infrastructure/readiness, or
P3 semantic replay; those remain unrun. The archived design proposed eight
paired cases and two adequate controls; q07 is frozen with a historical-context
clarification to distinguish recall of the prior hypothetical from PC-11's
permitted new compatible solo fiction.

### P1: OCI Preflight And Staging

After the user's Goal-mode start, record actual capacity, disks, ports and existing
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
network without real provider credentials. Download only the selected pinned reranker
into its owned cache. Record resolved image IDs/digests, package/model manifests
and actual disk use. Bind build results back to the committed release manifest.

Before supplying live credentials, implement and test a bounded OCI-side campaign
supervisor/expiry using a dummy owned workload. It must survive SSH disconnect,
stop only an explicit allowlist of campaign processes/Compose projects at the
absolute deadline or on safety failure, and preserve evidence/volumes. Verify
loss-of-controller recovery and recorded state before resuming; no duplicate run.
This is temporary workload supervision, not an agent scheduler or permanent host
daemon. If it cannot be proven, keep live work stopped and continue offline work.

### P2: Candidate Startup And Infrastructure Acceptance

Start dedicated DB first, create/verify `vector` and `pgroonga` with errors fatal,
then the experiment router, then Hindsight with one stable-ID worker. Keep runtime
restart policy `no` to avoid crash/restart model-call loops. Explicit diagnosed
restarts are allowed and accounted for. There is no always-on/boot activation.

Verify container-to-Spark Tailscale routing and DeepSeek TLS without changing host
network rules. Verify effective resource limits, DB mounts/extensions, API/UI auth,
loopback-only published sockets, and absence of a published DB port. Test the
documented Mac SSH tunnel and UI login without additional generation.

Account for automatic startup LLM/embedding checks. In a disposable readiness bank,
run the one Chinese exchange/recall: verify dimensions, one query prefix, complete
extraction, terminal operation state and full selected-reranker execution within recorded
deadlines/ceilings. Capture peak memory and latency. A healthy API, partial rerank
or merely accepted async operation is insufficient. Failed readiness prevents P3,
not repair work: diagnose, test and repeat readiness autonomously until safe,
qualified, genuinely blocked or out of time.

### P3: Frozen Semantic Replay

Use two subjects and two character roots, with one bank per workspace/subject as
the first hypothesis. ADE supplies character identity; narrow extraction labels
identify shared profile facts. Use nonempty strict character-OR-profile scopes,
character-local consolidation and shared raw profile facts, not shared observations.
An evidence-driven alternative uses separate profile/relationship banks in a new
candidate, with the same sharing/exclusion expectations and source attribution.
Do not mark entire private source documents as profile-visible. Initially exclude
raw chunks/source bundles from Character context. Test before/after consolidation.

**Candidate04 q01 negative evidence, 2026-10-11:** the completed Hindsight arm
answered with the superseded jasmine/hot/half-sugar preference and referred to
the source conversation. Readback showed the s03 correction and sugar change
were extracted but had only `character:root_xiaotang`, so `root_other` recall
could not retrieve them through `kind:profile`. The initial attempt's capture
failure was before Character dispatch; this later completion supplies the
observed negative answer. The likely cause is extraction-time optional label
omission, not reranking. Candidate05 therefore changes only the versioned Memory
bank mission and label description. It directs fact-level separation of
portable subject properties/preferences—including safe, clearly time-bounded
history and corrections—from private source/interaction narrative. Source
character tags and observation root gates stay intact; speaker/time attribution,
hypothetical/unverified status, solo/shared participation, uncertainty and
correction-versus-change distinction remain explicit retain obligations.
Re-ingest the unchanged frozen corpus only into a fresh candidate and preserve
q01 private-origin exclusions. The offline checks bind exact
JSON/config/readback and do not prove model semantics; candidate04 remains
negative pending fresh-candidate evidence.

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
For a failure, first record what failed, its causal layer, supporting evidence
and why the proposed repair belongs there. Fix the contract/configuration/code,
run offline regressions, then the smallest useful live comparison. Keep previous
receipts immutable. Repeating an unchanged failure requires an explicit transient
or variability hypothesis; do not loop indefinitely or lower the success criteria.

### P4: Persistence, Stop And Review

After jobs drain, restart only the candidate with the same volumes and stable
worker identity; account for every startup probe. Independently read back a
retained source and curated state, without re-ingesting the corpus. This proves
bounded restart persistence, not crash-recovery qualification.

If time permits, stop inference, dump only the candidate DB and restore into a
new disposable PostgreSQL volume/project. Reuse the same resource envelope by
stopping the main candidate when necessary. Compare source, fact, curation and
scope readback without re-ingesting the corpus; API startup probes, if needed,
remain part of the accounted campaign. Never restore over baseline/final state.
Preserve the dump and receipt before removing an explicitly disposable restore
copy. Unperformed or failed restoration remains visible in the handoff.

Stop runner and Hindsight/worker first, preserve receipts and a candidate-only
logical DB dump, then stop router and DB. Retain owned volumes/cache; do not use
`down -v` on retained state or any global prune. Recheck existing-service
identity/health and host headroom. Remove the temporary expiry only after all
owned live work has stopped; no recurring automation is left behind.
Record infrastructure results separately from semantic pass/fail and remaining
questions. Redact private receipts into a concise finding; update tracker/roadmap
without declaring adoption, integration or release qualification.

The runbook must give exact commands for preflight, stage, start, inspect, run,
restart and stop, binding the selected release and explicit owned project name:
`ade-hindsight-probe` for the candidate, recorded unique names for restore copies.
On failure, stop unsafe owned work and preserve evidence; continue diagnosis and
covered repairs without owner input. Do not roll an older image onto a newer
schema, auto-reingest to repair curation or repair shared services. Evaluate new
schema/bank candidates in owned scratch state, not by damaging retained evidence.

## Acceptance And Morning Handoff

Provide the exact clean source/image/model/configuration identities, deployment
and restart commands, test results, resource peaks/latencies, observed model usage,
immutable run locations and a clear account of what remains stopped or running.
Separate built, deployed, infrastructure-qualified and semantically demonstrated
status. A useful campaign may identify a reproducible Hindsight limitation;
never claim the product requirement is met merely because the investigation ended.

Acceptance requires correct wire requests, authenticated/private deployment,
Chinese extraction and complete retrieval, identity/attribution/removal findings,
inspectable Character comparisons, retained restart readback, verified shutdown
and unaffected existing services. State any failed/unrun item and restoration
limits explicitly. Leave native adoption and any unresolved product decision to
the owner; a successful experiment does not authorize cutover.

Main risks remain ARM64 packaging, local-reranker resource use, DeepSeek extraction
quality, shared Spark contention and derived-memory scope. Diagnose them rather
than commission broad research or substitute a weaker acceptance test. Planning
performed only read-only inventories and source/documentation checks: no
installation, deployment, model inference or private dialogue export has occurred.

## Sources

- [Hindsight pinned installation guide](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/installation.md): platform/deployment shape; image inspection above adds current manifest evidence.
- [Pinned configuration](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/configuration.mdx): provider settings, query prefixes, retries and resource controls.
- [Pinned multilingual guide](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-docs/docs/developer/multilingual.mdx) and [PGroonga recipe](https://github.com/vectorize-io/hindsight/tree/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/docker/docker-compose/pgroonga): Chinese retrieval requirements.
- [Qwen model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B) and [BGE reranker card](https://huggingface.co/BAAI/bge-reranker-v2-m3): model capabilities; no ADE quality result inferred.
- [DeepSeek JSON output](https://api-docs.deepseek.com/guides/json_mode/) and [thinking mode](https://api-docs.deepseek.com/guides/thinking_mode/): provider wire controls, checked 2026-10-10.
- Pinned source checks: `engine/providers/openai_compatible_llm.py`, `engine/embeddings.py`, `engine/memory_engine.py` under upstream `hindsight-api-slim/hindsight_api/`, and local `services/model-router/src/model_router/app.py`. Source compatibility is not a completed integration test.
