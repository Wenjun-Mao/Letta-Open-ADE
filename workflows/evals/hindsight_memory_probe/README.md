# Isolated Hindsight infrastructure probe

P0 offline package for revision 4 of the
[experiment plan](../../../docs/plans/hindsight-self-hosted-experiment.md),
[ADR 0064](../../../docs/adr/0064-isolated-hindsight-infrastructure.md), PC-08/09/13.
The existing [feature CLI](../../../services/ade-api/src/ade_api/features/agent_runtime/HINDSIGHT_EVALUATION.md)
is the only Character evaluation entrypoint. This package constructs no ADE API
or native persistence. The tracked Chinese corpus, offline freeze command,
public-HTTP ingestion/curation/replay driver and strict feature reranking gate
are implemented for P0. No fabricated live result is included.

Implemented: owned Compose, pinned recipes/configuration, observational router,
clean release export/identity, private environment provisioning, temporary Linux
supervision and offline tests. Latest campaign-manager report, 2026-10-11: detached
supervisor qualification is recorded with nine real evidence hashes; the pinned
ARM64 router, DB, Hindsight and runner images and the actual pinned-image fake-provider
test passed. Candidate PostgreSQL is running and healthy; pgvector 0.8.6, PGroonga
4.0.8 and Chinese term/vector smoke passed. No provider credentials or inference
were used. The pinned BGE cache download still awaits this streaming-hash fix in the
accepted release. These remote observations have not been independently refreshed
by this source iteration; a source build or config render is not acceptance.

## Ownership and candidate configuration

Explicit project `ade-hindsight-probe`; default owned network only. Dedicated
PostgreSQL17 pgvector0.8.6/PGroonga4.0.8, full Hindsight0.10.3 API/UI and one
embedded stable-ID worker, workflow-instrumented existing router, and one-shot
feature CLI runner. Named volumes `ade-hindsight-probe_db-data` and
`ade-hindsight-probe_model-cache` survive stop. API `127.0.0.1:18888`, UI
`127.0.0.1:19999`; DB and router have no published sockets. Optional 18010 is
reserved for a separately inspected loopback diagnostic override, absent here.
No global names, host networking/socket, external networks/volumes, shared data,
native `.env` or shared service edits. Qualification scripts are a read-only
owned source mount; receipts are the only writable private host bind.

Initial caps: Hindsight6GiB/1core, DB1GiB/.25core, router256MiB/.125core,
runner512MiB/.125core; total7.75GiB/1.5cores. Runtime `restart: no` prevents
unaccounted crash/startup loops. Epoch allocation files permit measured retuning;
require MemAvailable >= sum candidate caps +1.5GiB with candidates stopped,
CPU capacity >= sum caps +.5core, >=25GiB staging storage. Live guard stops
work below15GiB, below1.5GiB for30s, on candidate OOM/restart/health/limit drift,
or any baseline container identity/start/image/status/health change. It samples
host load/CPU/IO/memory pressure and cgroup-v2 peaks/events (null if unavailable).
Runtime quotas never constrain Docker builds: register each serial build process,
watch host headroom, and qualify BuildKit cancellation on OCI before live work using the
[owned build-only sentinel procedure](BUILD_CANCELLATION.md).

Required standalone API extension is exactly
`hindsight_api.extensions.builtin.tenant:ApiKeyTenantExtension` with
`HINDSIGHT_API_TENANT_API_KEY`. UI access key is independent; its dataplane key
matches standalone API auth. Router and DB keys are mandatory. Existing Spark
Qwen provider auth is optional/empty, matching the served route; that does not
make Hindsight or router unauthenticated. MCP is disabled.

Only DeepSeek official API and `http://100.64.35.71:8001/v1` Qwen over Tailscale
are configured. DeepSeek Character profile is copied exactly, thinking default
high; Memory explicitly disables thinking and uses schema-in-prompt JSONobject,
strict_schema=false. Qwen prefix has one **actual newline**, applied upstream by
Hindsight only to queries. No passage prefix; expected dimensions1024/served
max input8192 need live validation. Missing experiment deployment qualification
manifest deliberately uses the shared loader's supported empty binding; `{}`
is invalid and would break real catalog flattening. No qualification is invented.

BGE snapshot953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e loads local
`/models/bge-v2-m3`, CPU/batch1/thread1, remote-code false, HF offline during
runtime. One worker slot, zero reserved consolidation slots, small DB pool,
no auto-consolidation, fail-on-extraction errors, retain/consolidation600s walls,
120s LLM/reranker, 4096 completion ceilings, zero extra operation LLM/worker
retries and one consolidation attempt. These are mechanical bounds, not spending
gates (PC-09).

Actual upstream exceptions to a global zero-retry interpretation: OpenAI
embeddings factory omits the global max-retry argument, so SDK defaults to3
retries/4 attempts and600s read timeout; unknown Qwen dimensions cause startup
`input=["test"]`. LLM `verify_connection` hardcodes2 retries/3 attempts and a
512-token verification cap. Ordinary LLM SDK transport retries are0. No upstream
patch hides these behaviors. `qualification/providers.py` tests the actual
factory/provider classes inside the pinned image, including retry counts, prefix,
probe, timeout and JSON schema-in-prompt serialization. The90s fake-test deadline,
600s run-job wall, startup initialization cap and campaign expiry bound owning
operations; the600s SDK default is not falsely described as a120s SDK timeout.
Account for every startup, retain, consolidation, recall and Character request.

## Observational capture contract

Workflow-only `router_entrypoint:create_app` replaces the shared app's lifespan
and injects `state.upstream_client`; routes, catalog, adapters, policy and profiles
are unchanged. AsyncBaseTransport wraps AsyncHTTPTransport(retries=0), with the
shared pool limits. Real tests pass through catalog/profile loading and shared
forwarding to fake HTTP, never reconstructing an expected wire request.

Before dispatch, record inbound payload plus safe phase/operation/request IDs
and time, then the actual httpx bytes **after adapter/default serialization**.
`*.outbound.body.json` is byte-exact; `.outbound.json` binds its SHA256.
No headers/auth, exception text, provider bodies or reasoning are recorded.
Pinned Hindsight native LLM trace is explicitly disabled (its default is true),
as is OTEL export; neither may become a second raw output/error sink. This does
not disable retrieval/recall trace used for complete reranking qualification.
Safe response projection: status, finite nonnegative numeric usage, latency,
embedding dimensions and input count only. Successful embedding responses are
validated for input cardinality, contiguous unique indices, consistent nonempty
dimensions and any explicitly requested dimension. Finite numeric arrays and
strict base64 float32 payloads are accepted; malformed successful responses fail
and latch qualification. This validates observations without changing the
serialized request or SDK encoding default. HTTP error bodies are not parsed or
projected, and vectors are never retained. Streaming and reasoning/credential
fields in request JSON are rejected. Capture failure prevents forwarding, latches qualification failure,
and attempts a fixed-code failure receipt; if the filesystem itself is unavailable,
a fixed stderr code and failed health/readback remain, never a claim of durable
receipt success. Capture directory0700/files0600 use exclusive atomic link publication after fsync, then fsync(directory).
`/probe/qualification` reports503 after failure. Keep all receipts; requalify a
new output directory only after diagnosis. Phase intents are immutable, active
phase atomic. Serial callers must annotate before startup/retain/consolidation/
recall/Character; phase distinguishes operational categories, not hidden model
reasoning. The subsequent replay assignment must separate recalled context from
full trace and reject incomplete reranking **before** Character dispatch; upstream
can return HTTP200 with zero-score candidates after a reranker timeout.

## Offline verification

```sh
uv run --locked pytest workflows/evals/hindsight_memory_probe/tests \
  services/ade-api/tests/agent_runtime/test_hindsight_evaluation.py \
  services/ade-api/tests/agent_runtime/test_hindsight_evaluation_cli.py \
  services/ade-api/tests/agent_runtime/test_executor.py services/model-router/tests -q
uv run --locked ruff check workflows/evals/hindsight_memory_probe
uv run --locked python -m workflows.evals.hindsight_memory_probe.validate \
  --env-file workflows/evals/hindsight_memory_probe/config/dummy.env.example \
  --private-dir /tmp/ade-hindsight-probe-dummy --release-sha 0000000000000000000000000000000000000000
git diff --check
```

`validate` captures resolved Compose in memory and prints only pass/fail; do not
publish live `docker compose config` output. The dummy env is configuration-only,
never permission to start an image or claim auth qualification. CPU/memory retuning
requires a validated epoch allocation JSON passed to `validate --allocations`.

## P1 preflight, clean stage and detached guard

The following are future OCI operator commands, **not executed at P0**. Run as
the OCI Docker owner with python3 and Tailscale already available. Do not alter
existing services/networking. Supply the reviewed clean commit as `PROBE_SHA`.
All commands use scoped variables, not native `.env` sourcing.

On the clean Mac checkout, export tracked source and candidate manifest:

```sh
PROBE_SHA=$(git rev-parse HEAD)
uv run --locked python -m workflows.evals.hindsight_memory_probe.bundle \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/bundles
uv run --locked python -m workflows.evals.hindsight_memory_probe.manifest \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/identity-$PROBE_SHA
scp workflows/evals/hindsight_memory_probe/outputs/bundles/$PROBE_SHA.tar OCI:/tmp/$PROBE_SHA.tar
```

On OCI, inventory without querying existing databases. Check sockets, free space,
headroom, container IDs/images/start/health and the unused owned path:

```sh
ss -ltn '( sport = :18888 or sport = :19999 or sport = :18010 )'
df -B1 /mnt/projects/apps
cat /proc/meminfo
nproc
docker ps --no-trunc
PROBE_ROOT=/mnt/projects/apps/ade-hindsight-probe
PROBE_RELEASE=$PROBE_ROOT/releases/$PROBE_SHA
PROBE_PRIVATE=$PROBE_ROOT/private
PROBE_STATE=$PROBE_PRIVATE/receipts/supervisor
# First stage only; test refuses existing/conflicting release content.
test ! -e "$PROBE_RELEASE"
install -d -m 755 "$PROBE_RELEASE"
tar -xf /tmp/$PROBE_SHA.tar -C "$PROBE_RELEASE"
install -d -m 700 "$PROBE_PRIVATE" "$PROBE_PRIVATE/receipts" "$PROBE_STATE"
cd "$PROBE_RELEASE"
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" \
  init --release "$PROBE_RELEASE"
# Detached host-local supervisor: no SSH/Mac controller needed for expiry.
nohup setsid python3 -m workflows.evals.hindsight_memory_probe.supervisor \
  --state "$PROBE_STATE" run </dev/null >"$PROBE_STATE/supervisor.log" 2>&1 &
chmod 600 "$PROBE_STATE/supervisor.log"
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" inspect
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind dummy --timeout 20
```

Disconnect SSH during this90s dummy process. Reconnect after25s: verify the job's
start identity is gone, no owned containers are running, an epoch stop receipt
exists, and baseline remains unchanged. Kill only a verified dummy controller in
a separate test, then run `inspect` followed by detached `run --resume`; verify
readback receipt, held flock, no duplicate, unchanged deadline. Record all qualification receipts and their SHA256 hashes in
`oci-supervisor-proof.json` as described below. SIGTERM causes
owned cleanup; SIGKILL recovery requires readback/resume. Test owned BuildKit
client cancellation before treating builds as supervised. Do not proceed to live
credentials if dummy expiry/disconnect/cancellation proof fails. Provider activation
mechanically requires `private/receipts/supervisor/oci-supervisor-proof.json` with
hard_deadline1791737365, boolean true `dummy_disconnect`, `dummy_expiry`,
`resume_readback`, `build_daemon_cancelled`, `baseline_unchanged`, plus `build_cancellation_receipt` naming the typed successful build-only
proof and nonempty `evidence_sha256` mapping scoped receipt filenames to verified SHA256 hashes.
Write this only after observing the real OCI proofs; synthetic offline tests are
not qualification receipts. Hash/readback validation cannot interpret the truth
of an operator's assertion; the subsequent live task must review the evidence.

Campaign started1791694165 (04:49:25Z), target1791730165 (14:49:25Z), hard
cap1791737365 (16:49:25Z) on2026-10-11. Fresh work/rearm stop300s before hard
cap (16:44:25Z) to reserve finite owned cleanup. Clock constants are immutable;
resume/new source/allocations never move them. Stop only explicit IDs after project,
service, release-path labels and fresh inspect checks. PIDs require start ticks,
UID and unique inherited ownership token; no PID/group reuse or global kill.
Lease/flock rejects duplicates. Durable stop admission precedes a bounded60s
registration drain; launch rechecks epoch/stop/deadline under admission lock at
its final execution handshake. Stop releases admission lock before waiting on
registration, avoiding lock inversion. Atomic receipt publication prevents partial
job JSON reads; a gated child expires after20s without a handshake. Even a held
registration lease cannot skip cleanup of already owned work. If its bounded wait
expires, record `registration_quiescence_unproven` and withhold the completed-stop
marker: a gated child may still register after that cleanup snapshot. The stop
barrier denies its dispatch; rearm requires a later successful exclusive stop and
fresh job/process/container readback. Baseline remains immutable across operating epochs.
A receipt-specified cause and fresh baseline/headroom proof are required to rearm;
append-only epoch chain records allocations and explicitly admitted clean SHA
releases. Rearm admits only exact stopped identities captured by the preceding
stop readback as dormant, including prior-release rows. No current cap check or
exit exemption applies to an unproven stopped row. Before Compose startup, a
service/epoch/deadline intent is durably registered; the detached reaper immediately
binds actual Docker start identity and fails early exits/limit drift. Active IDs
remain strict across resume, disappearance, exit and replacement. Dormant prior
releases remain owned for cleanup, never silently counted as active allocations.

## P1 qualification and P2 start/inspect

After the dummy stop, write a private diagnosis (cause, evidence, correction,
current safety readback), then rearm. The guard verifies its path/hash, current
baseline/headroom and stopped jobs/candidate; the operator owns the diagnosis's
meaning. Every retune uses this same stop/rearm path. Keep the same state directory.

```sh
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" \
  rearm --reason dummy_expiry_proven --diagnosis "$PROBE_STATE/dummy-proof.json"
nohup setsid python3 -m workflows.evals.hindsight_memory_probe.supervisor \
  --state "$PROBE_STATE" run </dev/null >"$PROBE_STATE/supervisor-epoch2.log" 2>&1 &
chmod 600 "$PROBE_STATE/supervisor-epoch2.log"
# Generate internal candidate keys, with synthetic provider key until qualification passes.
python3 -m workflows.evals.hindsight_memory_probe.private_env \
  --private-dir "$PROBE_PRIVATE" --release-sha "$PROBE_SHA" --dummy-provider
python3 -m workflows.evals.hindsight_memory_probe.phase \
  --receipts "$PROBE_PRIVATE/receipts" --phase startup --operation-id image-qualification
```

Use one registered operation at a time; `inspect` until its token-tagged processes
are gone, then review the private process log and expected artifacts. All builds
and pulls require `--kind build`; runtime launches reject implicit build/pull.
A failed command is not permission to repeat unchanged input without a diagnosis.
The launcher parses its narrow Compose option allowlist through the service
boundary; `run` and `exec` child argv is passed intact. Project/file/env-file and
volume ownership overrides are rejected before the service, while child
`psql -v ON_ERROR_STOP=1` remains a child option. `up`, `build` and `pull` have no
child-command boundary: every remaining option and service operand is validated.
Only explicit candidate service names are accepted, and `up`/`run` require one
`--pull never` policy.

```sh
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind build --timeout 1800 -- pull hindsight
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind build --timeout 1800 -- build db
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind build --timeout 1800 -- build model-router
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind build --timeout 1800 -- build runner
# Actual installed Hindsight provider classes against localhost fake HTTP; no models/providers contacted.
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 120 -- run --rm --no-deps --pull never \
  --entrypoint python3 hindsight /probe/providers.py
# Pinned HF download into the owned named cache, provisioning only (no live key yet).
# Root is admitted only for this exact 1800-second Hindsight cache command. The
# script verifies pinned files, writes a manifest, then chowns the named cache to UID1000.
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 1800 -- run --rm --no-deps --pull never --user 0 \
  -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 --entrypoint python3 \
  hindsight /probe/cache_model.py
```

Record real resolved image IDs/RepoDigests and DB package versions into a new
private immutable receipt. Inspect model snapshot-manifest hashes inside owned
cache, offline loading and absence of remote-code trust. No magic latest tags;
changing a pin requires editing owned recipe/pins, new clean release hash and
requalification, preserving old manifests. Python3.12.12/uv0.12.5 ARM digests
were read from official Docker Hub/GHCR metadata without pulls.

Start the dedicated DB and verify actual installed extensions with fatal SQL:

```sh
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 120 -- up -d --no-build --pull never db
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 60 -- exec -T db psql -U hindsight_probe -d hindsight_probe \
  -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS pgroonga;' \
  -c 'SELECT extname, extversion FROM pg_extension WHERE extname IN ('"'"'vector'"'"','"'"'pgroonga'"'"');'
# After fake tests, cache and DB smoke pass, activate only the existing DeepSeek provider secret.
python3 -m workflows.evals.hindsight_memory_probe.private_env \
  --private-dir "$PROBE_PRIVATE" --activate-provider
# Use the installed locked runtime, never uv sync or network resolution during supervision.
# The resolved-configuration validator and supervisor are stdlib; no uv/venv needed on OCI.
```

For resolved config verification on OCI, `docker compose --env-file
"$PROBE_PRIVATE/secrets.env" -f "$PROBE_RELEASE/workflows/evals/hindsight_memory_probe/compose.yaml"
--profile runner config --format json` is consumed privately by the owned validator, never printed. The validator is
stdlib and runs directly with `python3 -m ...validate` using these exact args:

```sh
python3 -m workflows.evals.hindsight_memory_probe.validate \
  --env-file "$PROBE_PRIVATE/secrets.env" --private-dir "$PROBE_PRIVATE" --release-sha "$PROBE_SHA"
python3 -m workflows.evals.hindsight_memory_probe.phase \
  --receipts "$PROBE_PRIVATE/receipts" --phase startup --operation-id first-start
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 120 -- up -d --no-build --pull never model-router
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 300 -- up -d --no-build --pull never hindsight
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" inspect
# Candidate-only inspection. Do not include Config.Env/secret-bearing raw inspect in public output.
docker ps --filter label=com.docker.compose.project=ade-hindsight-probe --no-trunc
```

Verify cgroup effective memory/CPU, OOM/restarts, volumes, API/UI auth rejection
and successful private login, MCP absence, and loopback sockets. UI adds no
permission to generate/Reflect. Mac tunnel: `ssh -N -L 18888:127.0.0.1:18888
-L 19999:127.0.0.1:19999 OCI`; browse `http://localhost:19999` and log in with
private CP access key. Never print keys or pass them as CLI arguments. Confirm
Tailscale container routing, dimension1024, query prefix and8192 untruncated
served limit later, with a disposable readiness bank. Healthy API or partial
rerank HTTP200 does not advance to P3. The feature-owned `recall` command
proves strict scoped retrieval and complete reranking without constructing
Character generation. Tracked fixtures and the workflow driver below implement
the offline P0 protocol; use them against the candidate only during later P2/P3.

Freeze a unique candidate workspace and immutable inputs offline. The freeze
command rejects a dirty checkout, invokes the feature's offline `scope` command,
binds fixture/source/query/persona/model/config/runtime-pin hashes, renders and
hashes each full retain payload, and seals a fixed UUID for every operation. It
checks historical reference context against exact prior source excerpts. A
source's Character-local dialogue remains only the current question. The 12
source exchanges, eight paired cases, two adequate controls, and separate
readiness source are in `fixtures/campaign.json`. q01's feature input carries
the exact private-origin exclusion terms, which are checked in recalled text
and context before Character generation (PC-02/03/04/07/10/11/12/13).

```sh
uv run --locked python -m workflows.evals.hindsight_memory_probe.freeze \
  --workspace-id hs_campaign_r4_candidate01 \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/candidate01/frozen
```

Each stage uses a new output directory. The driver uses public Hindsight HTTP
endpoints for bank setup, retain, consolidation, curation, pagination, operation
polling and document/fact readback. It invokes the feature CLI as a subprocess
for scope, run, and readiness recall. It captures terminal operation status and
descendants separately, and omits arbitrary error bodies. Repeat s10 only with
its exact frozen payload and original UUID. Archive/version is an eligibility
marker, not qualification of Studio's native path.

```sh
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest workflows/evals/hindsight_memory_probe/outputs/candidate01/frozen/campaign-manifest.json \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/candidate01/readiness \
  --stage readiness
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest workflows/evals/hindsight_memory_probe/outputs/candidate01/frozen/campaign-manifest.json \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/candidate01/initial-retain-a \
  --stage initial-retain-a
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest workflows/evals/hindsight_memory_probe/outputs/candidate01/frozen/campaign-manifest.json \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/candidate01/initial-retain-b \
  --stage initial-retain-b
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest workflows/evals/hindsight_memory_probe/outputs/candidate01/frozen/campaign-manifest.json \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/candidate01/initial-compare-a \
  --stage initial-compare-a
uv run --locked python -m workflows.evals.hindsight_memory_probe.replay \
  --manifest workflows/evals/hindsight_memory_probe/outputs/candidate01/frozen/campaign-manifest.json \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/candidate01/initial-compare-b \
  --stage initial-compare-b
```

Later stages are `consolidate`, `version-archive`, `invalidate-s10`, `s11`,
`retry-s10`, and `s12`. Consolidation uses explicit character-root scopes.
Invalidation selects raw world/experience facts rooted in s10, records linked
observations, invalidates the selected raw facts, then captures both valid and
invalidated readbacks. The pinned engine archives invalidated rows separately;
absence from live state alone is not proof of removal. Unrelated s11, exact s10
retry, and quoted historical s12 remain distinct checkpoints.
Run the stages under the same private candidate output directory so later
s11, retry, and s12 checkpoints can read `invalidate-s10/s10-curation-lineage.json`.
Each checkpoint captures full valid and invalidated lists alongside the exact
selected s10 IDs. A newly extracted s12 fact with matching text remains a distinct
source fact; only reuse of an original selected fact ID counts as reactivation
(PC-07).

The runner image copies the tracked driver, fixture, and authored persona while
preserving its default feature entrypoint. Compose binds the clean release SHA
to `ADE_EVAL_SOURCE_SHA`; replay checks that identity and all frozen inputs
before constructing the Hindsight client, so the slim image does not depend on
`.git`. Override only that one-shot command:

```sh
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 3600 -- run --rm --no-deps --pull never \
  --entrypoint python runner -m workflows.evals.hindsight_memory_probe.replay \
  --manifest /receipts/frozen/campaign-manifest.json \
  --output-directory /receipts/initial-retain-a --stage initial-retain-a
```

Use a 3600-second launcher timeout for each initial retain group and 2400 seconds
for each initial compare group. These bounded groups keep every launcher command
within its one-hour ceiling; run later lifecycle checkpoints sequentially with a
new output directory each time.

The runner sets `ADE_EVAL_PHASE_FILE=/receipts/phase.json`. Feature recall and
each Character request publish a fresh atomic phase intent, unique operation ID,
and case/arm correlation ID, then capture that mapping before dispatch. Workflow
phases annotate retain and consolidation, separating recall embedding from
Character generation in Model Router wire captures.

## Inspect, diagnosed restart/new release and final stop

To stop safely or perform P4 drain/restart, use guard stop then inspect until an
epoch stop receipt exists and all owned processes/containers are stopped. Preserve
receipts/volumes. A controlled stop is recoverable; hard-deadline stop is not.

```sh
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" stop
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" inspect
# Write private diagnosed-restart.json with cause/evidence/safety readback first.
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" \
  rearm --reason persistence_restart --diagnosis "$PROBE_STATE/diagnosed-restart.json"
# For measured retuning add --allocations "$PROBE_STATE/new-allocations.json".
# For a clean source repair stage/verify a new SHA path first, then add --release NEW_SHA_PATH.
# The immutable registry/epoch release chain continues owning old release containers too.
nohup setsid python3 -m workflows.evals.hindsight_memory_probe.supervisor \
  --state "$PROBE_STATE" run </dev/null >"$PROBE_STATE/supervisor-next-epoch.log" 2>&1 &
chmod 600 "$PROBE_STATE/supervisor-next-epoch.log"
# Repeat ordered DB/router/Hindsight up with --no-build --pull never; same retained volumes/worker ID.
```

New SHA needs registered serial rebuilds while candidates are stopped. The launcher
uses the active epoch SHA and allocations over stale env values. Do not delete
stop markers or alter original deadline/baseline to resume. Persistent wire-capture
failures require preserved old receipts and a reviewed new capture directory;
this is a qualification repair, not deletion of failed evidence.

### Restart readback and ordered finalization

P4 restart evidence is a public-HTTP readback against a frozen selection. Prepare
`$PROBE_PRIVATE/receipts/restart-selection.json` from the completed replay and
curation receipts. It must identify each bank and source, the independently frozen
original-text hash, Hindsight document content hash, retain-context hash, curation
IDs, and each selected fact ID/text hash under `valid` or `invalidated`. Each bank
also binds `workspace_id`, `subject_id`, and the subject-derived bank ID. Its
`scopes` list freezes `character_root_id`, tags, `tags_match: "any_strict"`, and
the candidate, positive and excluded IDs. `any_strict` is nonempty OR overlap:
`character:<root>` facts and `kind:profile`-only facts both match. A returned
observation is positive only when its character tags identify exactly that root,
matching the feature contract. Subject-derived bank IDs keep separate subjects
isolated. Empty scope/fact selections are rejected. Do not regenerate the selection after restart.
The readback helper issues only GETs; it does not ingest, curate, consolidate or
call the Character feature.

Feature-scope and HTTP readback checks run in the qualified runner. The detached
OCI supervisor has no ADE or third-party Python packages, so its admission and
snapshot path uses only the stdlib selection structure plus the runner proof's
selection and before/after file hashes.

```sh
# Capture before restart while selected state is live.
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 120 -- run --rm --no-deps --pull never \
  --entrypoint python runner -m workflows.evals.hindsight_memory_probe.restart_readback_cli \
  capture --selection /receipts/restart-selection.json \
  --output /receipts/restart-readback.before.json

# Use the diagnosed guard stop/rearm flow above. Restart the same candidate volumes,
# then capture again; don't re-run replay or Character.
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 120 -- run --rm --no-deps --pull never \
  --entrypoint python runner -m workflows.evals.hindsight_memory_probe.restart_readback_cli \
  capture --selection /receipts/restart-selection.json \
  --output /receipts/restart-readback.after.json
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 20 -- run --rm --no-deps --pull never \
  --entrypoint python runner -m workflows.evals.hindsight_memory_probe.restart_readback_cli \
  verify --selection /receipts/restart-selection.json \
  --before /receipts/restart-readback.before.json \
  --after /receipts/restart-readback.after.json \
  --output /receipts/restart-readback.completed.json
```

The completed readback binds original text, context/content hashes, and the full
public fact/curation projection (including metadata hash, proof count, chunk ID,
entity hash, timestamps, state, and source lineage) plus valid/invalidated states.
Compose passes the active guard's release, registry and epoch identities into
the runner; the readback records these values for both epochs.
It proves bounded persisted-state
readback only; it does not qualify authentication, ranking, reranking or
Character behavior. If an earlier campaign failure prevented the check, leave
the completed receipt absent and report that limitation.

To admit finalization, the detached supervisor must already be running. The
command durably closes ordinary dispatch and returns after admission; the
detached guard owns the remaining finite stages even if SSH/controller disconnects.
Emergency `stop` still preempts it. Admission is rejected if the requested drain,
dump and cleanup reserve do not fit before `WORK_CUTOFF`.

```sh
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" \
  finalize --drain-timeout 600 --dump-timeout 120
# Inspect private receipts. The finalized receipt appears after stopped readback;
# p4_complete=false means restart evidence was absent.
python3 -m workflows.evals.hindsight_memory_probe.supervisor --state "$PROBE_STATE" inspect
```

Finalization drains registered jobs and pending/processing/deferred Hindsight
async operations, then records status counts (including failed and cancelled)
before stopping runner and Hindsight. It records a private canonical
snapshot of the pinned candidate database's schema/extensions, banks, documents,
chunks, live/invalidated facts, observations, sources, history, entities and links.
It then dumps only `hindsight_probe` from the positively identified candidate
PostgreSQL container and named volume. Binary `pg_dump -Fc` stdout goes to a fresh
exclusive `0600` file; stderr is separate. During long stages, the guard checks
baseline identity, host headroom, candidate limits, OOM/restart state and exact
container identity at intervals no longer than five seconds. It requires a
nonempty archive and successful `pg_restore --list`, hashes and fsyncs it, and
publishes the archive/result without overwrite. Only after the dump result is
durable does it stop router and database. The final receipt records baseline and
stopped-state proof, restart-proof path/hash or explicit absence, and whether P4
acceptance is complete. TOC validation proves archive readability, not restoration.

No separate `pg_dump`, process-log rename, whole-project stop or `down -v` before
`finalize`. On stage failure the supervisor performs bounded cleanup and writes a
fixed-code failure receipt; partial dump files remain private and are not
published as a successful archive. Retained volumes/cache are not removed.

After a completed finalization, the optional local restore qualification can run
against the exact published archive. It admits one token-bound project and
volume, pins the already-qualified PostgreSQL image by ID, disables networking,
ports and host mounts, and runs only `pg_restore` plus exact read-only snapshot
queries. It compares every canonical database row (including vectors and source
lineage) and derives the frozen scope from restored rows. The source
`scope_eligibility` file remains hash-bound control evidence; it is not treated
as a PostgreSQL table or copied into the disposable database. A mismatch keeps
failure evidence and the restore volume for inspection. A successful comparison
removes only the exact registered restore container and volume after checking
volume consumers.

```sh
python3 -m workflows.evals.hindsight_memory_probe.restore --state "$PROBE_STATE" start --timeout 900
python3 -m workflows.evals.hindsight_memory_probe.restore --state "$PROBE_STATE" inspect
# Resume only a registered, unambiguous operation; cleanup is also available as
# an explicit operator action after a terminal result.
python3 -m workflows.evals.hindsight_memory_probe.restore --state "$PROBE_STATE" resume
# Request bounded emergency preemption; the detached controller stops its exact
# registered process, records failure and preserves the disposable volume.
python3 -m workflows.evals.hindsight_memory_probe.restore --state "$PROBE_STATE" stop
python3 -m workflows.evals.hindsight_memory_probe.restore --state "$PROBE_STATE" cleanup
```

After an emergency stop or comparison mismatch, `cleanup` records
`preserved_failed_state` and retains the volume for review; that terminal state
continues to block rearm.

This proves logical persisted PostgreSQL state restore only. It does not qualify
Hindsight API behavior, authentication, ranking, reranking, Character behavior,
provider inference, or live deployment. The current campaign still requires its
separate OCI execution and evidence review.

No global stop/kill/prune or `down -v`. The finalizer stops exact recorded
container IDs in stage order and retains volumes/cache. Pinned Hindsight's wrapper
needs30s for internal cleanup, so it receives35s Docker grace with45s subprocess
wall; other services receive10s/20s. Forced-kill stop never qualifies clean
persistence. Recheck original baseline and host safety in the final receipt.
Remove temporary supervisor only after stopped readback; no daemon/automation
remains. A separate P4 restore project is admitted only by the sealed restore
operation's exact project/config/image/volume identity and typed process-owner
scope; project-name prefixes do not grant ownership. Unrun or failed restoration
stays visible and is never substituted by startup health.
