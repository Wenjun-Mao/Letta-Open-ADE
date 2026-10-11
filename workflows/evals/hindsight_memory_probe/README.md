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
supervision and offline tests. The revision-4 OCI campaign used immutable source
`537e93c993406c41050424ddee161a875f421077`; pinned infrastructure checks,
authentication, CPU BGE, semantic replays, same-volume restart readback, and
ordered main-candidate shutdown passed within their bounded claims. See the
[interim campaign finding](../../../docs/findings/hindsight-oci-campaign-2026-10-11.md).
The first separately admitted disposable restore failed before creating a
container or volume because host validation selected a tokenless job-result
receipt. A later attempt created the exact disposable container, completed
`pg_restore`, and then failed during the final snapshot with
`restore_process_identity_changed`; cleanup retained that failed container and
volume. The retained identity-list-readback registration has an empty
command-line hash and no child or wrapper result. That points to registration
being published without first proving exact argv, owner, UID, PID and start-tick
identity; it does not establish that the child had completed. A Linux procfs
terminal-transition race is a separate runtime possibility handled only after
bounded child-exit confirmation. The old receipts and deadlines remain
untouched. [ADR 0065](../../../docs/adr/0065-post-restore-snapshot-failure-recovery.md)
and the [P4 runbook](p4-runbook.md) document a bounded, separately authorized
preservation and retirement path. This source iteration has not run that path on
OCI and does not claim restore success. Restore acceptance and final
usage/resource totals remain open. Later source/docs/tests do not redeploy or
qualify a new runtime SHA.

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

### Versioned Memory profile classification

`config/bank-profile.json` is the Memory-only prompt/config contract for the
next fresh candidate (`candidate05-profile-v1`). It asks Hindsight to classify
each proposition independently. Portable subject properties and preferences may
include current values, clearly time-bounded former values, explicit corrections
and explicit changes when they are useful without interaction history. A value
does not become private just because it is historical. Source/chat origin,
participation, assistant narrative and relationship-specific experience remain
character-local. The profile label stays optional and nullable; this prompt does
not guarantee correct semantic classification.

The refined mission also preserves source attribution and time, hypothetical or
unverified status, solo versus shared participation, explicit uncertainty, and
the distinction between a correction and a preference change.

The offline freeze manifest carries the full configuration and its SHA256, and
also includes the tracked config file in `config_sha256`. Before any retain, the
runner checks the full supported bank-config readback and records the exact
missions, label description, version and hash. This guards the applied input,
not the model's interpretation. Candidate05 must use a fresh candidate bank/DB
and replay the unchanged frozen corpus; do not retry or re-ingest into
candidate04. Review fact text, labels, character tags, observations and q01's
private-origin exclusions after readback. The fixture, queries, persona,
Character profile and limits remain frozen. Offline serialization tests are not
semantic acceptance, provider qualification, or deployment authorization.

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

Canonical PostgreSQL snapshots share one schema query for candidate finalization
and disposable restore readback. It omits only numeric `pg_temp_N` and
`pg_toast_temp_N` namespaces, whose backend-local temporary objects do not
survive restore. Stable schema names and owners, extension names and versions,
Alembic rows, and the ten canonical data tables remain exact comparison inputs.

```sh
uv run --locked pytest workflows/evals/hindsight_memory_probe/tests \
  services/ade-api/tests/agent_runtime/test_hindsight_evaluation.py \
  services/ade-api/tests/agent_runtime/test_hindsight_evaluation_cli.py \
  services/ade-api/tests/agent_runtime/test_hindsight_eval_phase.py \
  services/ade-api/tests/agent_runtime/test_hindsight_eval_trace.py \
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
stop readback as dormant, including prior-release rows. During an admitted
replacement, the exact stopped predecessor may transition to Docker status
`removing`; it remains `replacement_pending` only while a service intent targets
the active epoch release and every other field still matches the stop receipt.
The intent deadline still requires a replacement to be observed. Unknown or
changed IDs, active identity loss, resurrection, and removal without an intent
remain fatal. Before Compose startup, a service/epoch/deadline intent is durably
registered; the detached reaper immediately binds actual Docker start identity
and fails early exits/limit drift. Dormant prior releases remain owned for
cleanup, never silently counted as active allocations.

The detached supervisor takes Docker inventory and lifecycle records under one
finite lifecycle lease. Startup preparation and Compose completion refresh
Docker under the same lease before changing activation records, so a stale
container snapshot cannot be paired with a later started receipt.

On a safety-triggered epoch stop, the supervisor writes one immutable
`epoch-NNNN-guard-failure.json` receipt from the same Docker sample and lifecycle
observation that produced the stop reason. It contains only baseline and dormant
projections, activation intent fields, the lifecycle classification, reason and
registry/epoch hashes; it never stores raw inspect data, environment, mounts or
network settings. If writing this receipt fails, safety cleanup still proceeds
and the missing evidence remains explicit.

## Operator runbooks

- [P1 qualification and P2 start/inspect](operator-runbook.md)
- [P4 restart readback, finalization, and failed post-restore recovery](p4-runbook.md)
