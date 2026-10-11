# Operator runbook: qualification and candidate lifecycle

Follow the [workflow entrypoint](README.md) and its product/authority boundaries.

Revision-4 campaign closed on final runtime source
`a3e78c5c63b17eadc3d02b05ce7e04eb6042944f`. This file retains procedural
commands and does not itself authorize a new live campaign. See the
[campaign finding](../../../docs/findings/hindsight-oci-campaign-2026-10-11.md)
for verified closeout evidence and semantic limits.

Revision 5 binds supervisor state and captures to
`$PROBE_PRIVATE/activations/hindsight-semantic-follow-up-2026-10-11/receipts`.
Reuse the retained `$PROBE_PRIVATE/secrets.env` and the existing
`ade-hindsight-probe_db-data` and `ade-hindsight-probe_model-cache` volumes.
Do not regenerate credentials, change the Compose project, or remove volumes.
`launch` derives `PROBE_RECEIPTS_DIR` from the immutable registry; do not export
an alternate receipt path when launching work.

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
# Revision 5 reuses retained secrets.env; verify its presence and mode without
# printing or rewriting its contents.
test -f "$PROBE_PRIVATE/secrets.env"
test ! -L "$PROBE_PRIVATE/secrets.env"
test "$(stat -c %a "$PROBE_PRIVATE/secrets.env")" = 600
python3 -m workflows.evals.hindsight_memory_probe.phase \
  --receipts "$PROBE_RECEIPTS" --phase startup --operation-id image-qualification
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

For resolved config verification on OCI, `PROBE_RECEIPTS_DIR="$PROBE_RECEIPTS" docker compose --env-file
"$PROBE_PRIVATE/secrets.env" -f "$PROBE_RELEASE/workflows/evals/hindsight_memory_probe/compose.yaml"
--profile runner config --format json` is consumed privately by the owned validator, never printed. The validator is
stdlib and runs directly with `python3 -m ...validate` using these exact args:

```sh
# Bind the three nonsecret Compose identity values from the immutable active
# registry/epoch. secrets.env intentionally remains unchanged and contains no
# live epoch identity. This prints only hex release/registry/epoch identifiers.
read -r PROBE_RELEASE_SHA ADE_PROBE_REGISTRY_SHA256 ADE_PROBE_EPOCH_SHA256 <<EOF
$(python3 - "$PROBE_STATE" <<'PY'
import sys
from pathlib import Path
from workflows.evals.hindsight_memory_probe import epochs
from workflows.evals.hindsight_memory_probe.supervisor import load_registry

state = Path(sys.argv[1])
registry = load_registry(state)
epoch = epochs.active(state, registry)
print(Path(epoch["release"]).name, registry["registry_sha256"], epoch["sha256"])
PY
)
EOF
export PROBE_RELEASE_SHA ADE_PROBE_REGISTRY_SHA256 ADE_PROBE_EPOCH_SHA256

python3 -m workflows.evals.hindsight_memory_probe.validate \
  --env-file "$PROBE_PRIVATE/secrets.env" --private-dir "$PROBE_PRIVATE" --release-sha "$PROBE_RELEASE_SHA"
python3 -m workflows.evals.hindsight_memory_probe.phase \
  --receipts "$PROBE_RECEIPTS" --phase startup --operation-id first-start
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

The completed candidate05 initial-compare-a qualified recall/rerank and
Character request mechanics. Candidate05 initial and post-consolidation q01 responses
both said hot, unsweetened oolong and also asserted an October 1 first-chat
origin. q01 targets the other root: the profile preference is portable, but
private source origin, first-chat participation and time should be excluded.
The s01 message timestamp is October 1 at 09:00 and refers to an event the day
before; event and message dates are distinct, so September 30 is not an expected
cross-root answer. A separate structural source-context projection retest
produced one empty q01 output at the exact 2048-token cap. This is incomplete,
not a semantic pass. Source windows with unknown/conflicting character ownership are omitted
while the portable fact and original recall diagnostic remain. See [ADR 0063](../../../docs/adr/0063-hindsight-character-evaluation-boundary.md#structural-character-context-ownership-2026-10-11)
and the [campaign finding](../../../docs/findings/hindsight-oci-campaign-2026-10-11.md).

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
and arm/phase correlation ID, then capture that mapping before dispatch. The
feature output contains one immutable `<arm>.<phase>.phase.json` receipt per
operation; the shared `phase.json` remains the router's current-phase pointer.
Workflow phases annotate retain and consolidation, separating recall embedding
from Character generation in Model Router wire captures.

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

## P4 restart readback and finalization

See the [P4 restart and recovery runbook](p4-runbook.md) for release-scoped evidence, ordered finalization and optional restore qualification.
