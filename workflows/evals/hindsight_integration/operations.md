# Isolated Integration Operations

Authority: M0-M6/A1-A6 in the [implementation plan](../../../docs/plans/hindsight-integration.md).
Use only the candidate Compose project and registered resources on OCI. These
commands do not dispatch GitHub Actions. Source publication remains manual-CI only.

## Release And Activation

Stage a clean committed source archive beneath
`/mnt/projects/apps/ade-hindsight-integration/releases/<commit>/`. Keep private
configuration outside releases, and never copy the root repository `.env` or
historical banks into the candidate. Record the exact commit and archive hash.
Use `/mnt/projects/apps/ade-hindsight-integration/private/activations/<activation>/`
for the immutable lease, checks, private HTTP evidence and owned resource receipts.

Run the standard-library host controller from the staged release:

```sh
python3 -m workflows.evals.hindsight_integration.operations_cli prepare \
  --root "$INTEGRATION_ACTIVATION" --revision "$INTEGRATION_REVISION"
python3 -m workflows.evals.hindsight_integration.operations_cli check \
  --root "$INTEGRATION_ACTIVATION"
```

Preparation inventories baseline identities/health/mounts without exporting
their environments or data. It refuses an overlapping running candidate owner.
Persistent services are exact baseline identities. Explicit auto-removing Compose
one-offs are inventoried separately because successful completion removes them;
an unclassified missing service still closes the activation.
The maximum lease is twelve hours, with a one-hour shutdown margin. A fresh
lease is a new immutable activation, with reconciliation before any new startup.

Before inference, start `operations_cli supervise` as an owned systemd service
with the staged release as its working directory and a runtime bounded by the
lease. Install a separate one-shot systemd timer for `operations_cli stop` at
hard expiry. On this OCI host user lingering is disabled: use system-level units
with `User=ubuntu`, not a user timer that disappears after logout. Record the
exact unit names and verify both are active. Scope their names to the activation.
The supervisor writes a source-bound heartbeat every fifteen seconds. Router
requires a healthy heartbeat at most sixty seconds old for each inference call.

The host supervisor closes admission and stops only matching project/activation
containers if resources, baseline, source binding or candidate health fail.
It writes `closed.json` before Docker operations. Closure is permanent for that
activation, including when Docker is temporarily unavailable or a service restarts.
The independent expiry timer remains necessary if the supervisor dies.

## Private Configuration And Images

Build the native PostgreSQL recipe in `docker/postgres.Dockerfile` and inspect
its immutable image ID. Use that ID, not a floating image, when preparing config:

```sh
python3 -m workflows.evals.hindsight_integration.provision \
  --activation-root "$INTEGRATION_ACTIVATION" \
  --environment "$INTEGRATION_ENV" \
  --existing-credentials /mnt/projects/apps/ade-hindsight-probe/private/secrets.env \
  --database-image "$INTEGRATION_DATABASE_IMAGE" \
  --source-fingerprint "$INTEGRATION_SOURCE_FINGERPRINT"
docker compose --env-file "$INTEGRATION_ENV" \
  -f workflows/evals/hindsight_integration/compose.yaml config --quiet
python3 -m workflows.evals.hindsight_integration.build_images \
  --root "$INTEGRATION_ACTIVATION" --environment "$INTEGRATION_ENV"
```

`INTEGRATION_ENV` must be outside the mounted activation directory. Provisioning
copies only the existing DeepSeek/embedding credentials into new private secret
files and generates separate candidate database/Router/Hindsight keys. It prints
paths/identity only. The runner never mounts provider credentials. Do not print
resolved Compose configuration or container environments.

Provisioning also copies only the staged source's authored `content` tree into a
new private runtime tree and hashes every source asset. The non-root API gets that
copy read/write at `/app/content`; worker gets it read-only. Do not mount incumbent
assets or chmod the release/image to fix authoring startup. The frozen product
startup rechecks the seed receipt. See
[ADR 0078](../../../docs/adr/0078-candidate-authoring-asset-seed.md).

The build helper requires the staged directory name to equal the lease's full
commit. It builds serially under three-CPU/3-GiB limits with CPU 3 excluded, checks
actual cgroup enforcement in an uncached budget build first, and records immutable
image IDs/private logs. It temporarily selects the legacy builder in its child
environment only because this host's installed Buildx lacks per-build limits.
Do not replace a failed budget assertion with an unrestricted build. This is a
candidate-only mitigation with a Stage 3 replacement requirement in
[ADR 0076](../../../docs/adr/0076-isolated-product-actor-and-provenance.md).
Complete image/model preparation **before** starting the inference supervisor;
build load must not invalidate or postpone its heartbeat.

Create the candidate model-cache volume with the Compose project/volume labels
and activation/source ownership recorded before use. Run `model_cache.py` in the
pinned Hindsight image, with no credentials, one CPU and bounded RAM. Mount only
that new volume and the helper source, explicitly as `--user 0:0` for new-volume
ownership preparation only. A prior owned public model-artifact volume may be
mounted read-only solely to copy the same pinned files into this new cache;
never reuse a database/bank or alter the source volume. The helper verifies the
actual complete weight hash and metadata after copying. Otherwise it downloads
the exact public BGE snapshot
and verifies the weight hash and metadata before the Hindsight server starts.
Preserve partial failures; repeated provisioning may resume the same pinned
download but cannot accept an unverified or silently substituted model.

Then recheck lease/headroom and start only the owned native services:

```sh
python3 -m workflows.evals.hindsight_integration.operations_cli start \
  --root "$INTEGRATION_ACTIVATION" --environment "$INTEGRATION_ENV"
```

The startup command refuses closed/expired leases, changed configuration or stale
supervision before invoking Compose, and stops newly created containers if the
activation closes during startup. Do not bypass it with a direct Compose `up`.
Use an activation-specific project name when rearming, so retained candidate
database volumes cannot silently become a fresh activation's database.

Verify native health, installed database extensions, actual image/model identities,
Chinese reranking and safe request observations. The API binds to OCI loopback
ports 18889 (Hindsight) and 18019 (Router). Use private tunnels when needed;
do not expose either service publicly or reuse baseline database/network mounts.

## Native Source Gate

The native gate tests the public concrete Hindsight integration. It does not
send a Character request or establish source history through the ADE product.
Its actor-only fixtures and controlled source provenance are frozen before calls:

```sh
docker compose --env-file "$INTEGRATION_ENV" \
  -f workflows/evals/hindsight_integration/compose.yaml run --rm runner \
  -m workflows.evals.hindsight_integration.native_gate \
  --case q01-relevant --out /evidence/native-q01-01 --lose-first-ack
```

Use a new evidence directory for every attempt. The gate records actual native
HTTP requests/outcomes, source documents, facts/observations and traced recall.
The lost-ack fault happens after real server acceptance. Reconciliation polls
the same operation; immutable replay must create no new extraction work.
Automatic consolidation must finish without a manual consolidate command.
The populated Chinese recall requires complete cross-encoder scoring.

Other source fixtures are `q02-correction`, `q02-change`, `reference` and
`attribution`. Native mechanical status and semantic inspection remain distinct.
Failed/partial-operation recovery requires additional captured fault/retry proof;
successful ordinary replay alone does not close that M1 requirement.

For real failed/partial recovery, run the host orchestrator from the staged source:

```sh
python3 -m workflows.evals.hindsight_integration.native_faults \
  --root "$INTEGRATION_ACTIVATION" --environment "$INTEGRATION_ENV" \
  --out "$INTEGRATION_ACTIVATION/evidence/native-failed-01"
python3 -m workflows.evals.hindsight_integration.native_faults \
  --root "$INTEGRATION_ACTIVATION" --environment "$INTEGRATION_ENV" \
  --out "$INTEGRATION_ACTIVATION/evidence/native-partial-01" --partial
```

It stops only the inspected, source-bound candidate Router. The partial case waits
for actual committed memories while the same operation is processing. The runner
must observe a genuinely failed operation before the host restores Router, retries
the same operation, and verifies unchanged source and preserved prefix identities
plus newly completed work. A completed-before-interruption attempt fails the proof.
These dedicated diagnostic banks disable automatic consolidation to isolate retain
recovery, and the partial bank uses small streaming chunks; neither setting changes
the default Memory bank configuration or qualifies semantics. Preserve every attempt.

## Closeout

Quiesce candidate writes, capture the paired recovery point and pending operation
identities, then stop only this activation:

```sh
python3 -m workflows.evals.hindsight_integration.operations_cli stop \
  --root "$INTEGRATION_ACTIVATION"
```

Verify baseline identity/health and owned-container shutdown. Stop/remove only the
recorded systemd units. Preserve both databases, private evidence and failure
receipts unless an explicitly registered disposable resource is being retired.
Never use global prune or delete retained baseline/experiment archives.
Restarting under a new lease requires fresh checks and operation reconciliation;
it does not authorize whole-history replay or production cutover.

## ADE Persistence Checks

The delivery libraries and maintained reply path have separate real-PostgreSQL
tests with controlled native/provider substitutes. These are not live native
product or Character qualification. Use the
existing `ade_api.features.agent_runtime.bootstrap` before Alembic: the version
table lives in `ade`, so a bare empty database is not a bootstrapped database.
Keep distinct non-login owner and application roles; run data-path tests as the
application role, not the database superuser.

For these tests, `ADE_TEST_DATABASE_URL` must name a disposable loopback database
whose name starts with `ade_hindsight_test`, using role `ade_hindsight_app`.
Supply credentials only through private environment/configuration, never Git:

```sh
uv run --locked pytest \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_delivery_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_leases_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_worker_sql.py -q
```

The normal product-path tests additionally cover acceptance/finalization atomic
intent, required automatic/tool lookup failure, concurrent saved-input Retry,
cancellation, stale candidates, compaction provenance, immutable version/bank
continuity and public API removal of one-store purge/reset:

```sh
uv run --locked pytest \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_runtime_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_runtime_fences_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_claim_races_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_lease_wall_clock_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_hindsight_sessions_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_lock_order.py \
  services/ade-api/tests/agent_runtime/test_hindsight_execution.py -q
```

The tests create controlled SQL fixtures, not product-established dialogue.
The native substitute records calls and checks that another connection can lock
the bank/outbox during each simulated HTTP call. Tests cover rollback, immutable
source/hash/scope, ordered dispatch, unrelated progress, lost acknowledgement,
native Retry, missing established banks and expired-worker fencing. Native live
feasibility remains separate; actual native product and browser verification
remain required in subsequent increments. Some maintained native-era tests still
assert superseded reviewer/role/reset contracts; their reconciliation is explicit
unfinished implementation work, not a claim that the full suite passes.

## New Runtime Configuration

Use `ADE_API_AGENT_RUNTIME_MODE=development`, an explicit non-`default`
`ADE_API_AGENT_RUNTIME_WORKSPACE_KEY`, private `ADE_API_HINDSIGHT_API_KEY` and
the owned `ADE_API_HINDSIGHT_BASE_URL`. API and worker must share those bindings
and source identity. Never point this runtime at an incumbent workspace or use
old SQL-only purge/reset as cleanup. Both databases remain paired resources.

The candidate-only manifest is generated after runtime source edits:

```sh
uv run --locked python -m workflows.evals.hindsight_integration.deployment_config --write
```

This writes only this workflow's new `config/deployments.json`, using the existing
approved DeepSeek development identity and current source policy hashes. It does
not rewrite root provider/model defaults, a release ledger, qualification rounds
or any staged/active release. Set
`ADE_API_AGENT_RUNTIME_DEPLOYMENT_MANIFEST` to that same path in the candidate.
Definitions bind `model_key` and `compaction_model_key`; obsolete reviewer and
embedding role keys are rejected. Source publication alone does not start this
stack, authorize an old ADE/trial redeploy or complete the browser/capture gates.

## Product Request Capture

Set `ADE_API_AGENT_RUNTIME_OBSERVATION_ROOT` to a new private, operator-owned
absolute directory for the isolated development workspace. Mount it read/write
only in the candidate worker and read-only in the candidate API. It is disabled
by default and unavailable to reader credentials. Never enable it on an incumbent
workspace or mount provider secret files there.

The operator export is `/api/v3/private-observations/runs/{run_id}`. The normal
worker records each actual automatic/tool lookup, context component/source spans,
pre-Router request, correlation and execution outcome. It asks native recall for
a diagnostic rerank trace only while capture is enabled. The final-wire request
remains Router's actual sent bytes, not the pre-Router snapshot.

`product_capture.collect_saved_run` collects through the public ADE and Router
boundaries; `capture_validation.qualify_run_capture` rejects missing attempts,
requests, continuations, source/scope/byte mismatches, copied probe history and a
reply that differs from the actual final provider response. Setup/probe grouping
is a predeclared workflow sidecar, not an instruction sent to the Character.
Preserve the collected bundle, read journal and failed validation. Raw captures
remain ignored private evidence. A private-reasoning-bearing input is incomplete,
not silently redacted into a full capture. See [ADR 0075](../../../docs/adr/0075-product-memory-and-request-observations.md).

## Actual Product Demonstration

After image/model preparation, start the source-bound host supervisor and verify
its independent expiry timer. Use the guarded full-stack entrypoint:

```sh
python3 -m workflows.evals.hindsight_integration.operations_cli start-product \
  --root "$INTEGRATION_ACTIVATION" --environment "$INTEGRATION_ENV"
docker compose --env-file "$INTEGRATION_ENV" \
  -f workflows/evals/hindsight_integration/compose.yaml run --rm --no-deps runner \
  -m workflows.evals.hindsight_integration.live_runner \
  --run-id stage1-product-01 --out /evidence/stage1-product-01
```

`start-product` boots a fresh ADE database, runs the public bootstrap/Alembic
commands, then starts the owned native/API/worker/proxy/web services. ADE and
Hindsight use different volumes and database authorities. Never substitute an
incumbent database or import historical state. API/worker share a fresh explicit
workspace; worker calls traverse the normally transparent workflow fault proxy.
ADE web/API bind to loopback 18020/18021, and private fault control to 18890.
Use only activation-owned tunnels. The browser server uses the operator key.
The full Compose resource sum reserves at least one of this host's four CPUs.

The runner admits only the predeclared three cases times two repeats. Each slot
creates a new subject/character relationship and two same-version conversations.
Actual user seeds go through normal turn acceptance and actual worker-generated
assistant replies become source messages. The evaluator waits for source delivery
and native consolidation, reads original native documents, then sends the exact
probe in the already-created empty chat. No rubric, authored assistant answer,
source chat window or summary is injected into probe input.

It freezes the archive's explicit evaluator revision and source/config/runtime
binding before Character calls. API/Router HTTP journals omit all headers. Each
completed slot has a physical-hash-bound sidecar tying actual setup and probe
collections, native documents, processing readbacks, exact recall and committed
reply together. `record_capture` and report loading independently revalidate it.
Do not repair a failed slot with edited JSON or a second recall. Failed slots,
partial source receipts and capture limitations remain visible. A failed or
private-reasoning-incomplete capture does not imply that the saved reply failed.

Each slot writes `human-review-template.json`, not a submitted `review-*.json`.
Report Memory findings separately and keep Character `UNREVIEWED` until genuine
human review. The end-of-run traffic snapshot includes all observable candidate
Router requests, including native traffic and missing outcomes. Native processing
may continue afterward; M6 still needs quiescence, in-flight identities, paired
backups, owned shutdown and baseline verification. See
[ADR 0076](../../../docs/adr/0076-isolated-product-actor-and-provenance.md).

The controlled SQL actor tests exercise this whole software path with explicitly
fake native/provider responses, not live semantics:

```sh
uv run --locked pytest \
  services/ade-api/tests/agent_runtime/persistence/test_product_actor_sql.py \
  services/ade-api/tests/agent_runtime/persistence/test_product_capture_sql.py -q
```
