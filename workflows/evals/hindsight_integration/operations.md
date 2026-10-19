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
  --database-image "$INTEGRATION_DATABASE_IMAGE"
docker compose --env-file "$INTEGRATION_ENV" \
  -f workflows/evals/hindsight_integration/compose.yaml config --quiet
docker compose --env-file "$INTEGRATION_ENV" \
  -f workflows/evals/hindsight_integration/compose.yaml build model-router runner
```

`INTEGRATION_ENV` must be outside the mounted activation directory. Provisioning
copies only the existing DeepSeek/embedding credentials into new private secret
files and generates separate candidate database/Router/Hindsight keys. It prints
paths/identity only. The runner never mounts provider credentials. Do not print
resolved Compose configuration or container environments.

Create the candidate model-cache volume with the Compose project/volume labels
and activation/source ownership recorded before use. Run `model_cache.py` in the
pinned Hindsight image, with no credentials, one CPU and bounded RAM. Mount only
that new volume and the helper source. It downloads the exact public BGE snapshot
and verifies the weight hash and metadata before the Hindsight server starts.
Preserve partial failures; repeated provisioning may resume the same pinned
download but cannot accept an unverified or silently substituted model.

Then recheck lease/headroom and start only the owned native services:

```sh
python3 -m workflows.evals.hindsight_integration.operations_cli check \
  --root "$INTEGRATION_ACTIVATION"
docker compose --env-file "$INTEGRATION_ENV" \
  -f workflows/evals/hindsight_integration/compose.yaml up -d db model-router hindsight
```

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
