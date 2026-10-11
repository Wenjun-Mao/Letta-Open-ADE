# P4 restart and recovery runbook

Follow the [workflow entrypoint](README.md). These commands use the same private receipt root and selected clean release SHA.

### Restart readback and ordered finalization

P4 restart evidence is a public-HTTP readback against a frozen selection. Create
the release-scoped directory and prepare
`$PROBE_PRIVATE/receipts/p4/$PROBE_SHA/restart-selection.json` from the completed replay and
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
Keep earlier root-level `restart-*` receipts untouched; they remain bound to
their original admission.

Both readbacks must report this same clean release SHA and registry hash, with
the selection's pre-restart epoch and the post-restart epoch distinct. The
selection and readbacks must remain available in this namespace through P4
admission and optional restore.

```sh
install -d -m 700 "$PROBE_PRIVATE/receipts/p4/$PROBE_SHA"
```
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
  capture --selection /receipts/p4/$PROBE_SHA/restart-selection.json \
  --output /receipts/p4/$PROBE_SHA/restart-readback.before.json

# Use the diagnosed guard stop/rearm flow above. Restart the same candidate volumes,
# then capture again; don't re-run replay or Character.
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 120 -- run --rm --no-deps --pull never \
  --entrypoint python runner -m workflows.evals.hindsight_memory_probe.restart_readback_cli \
  capture --selection /receipts/p4/$PROBE_SHA/restart-selection.json \
  --output /receipts/p4/$PROBE_SHA/restart-readback.after.json
python3 -m workflows.evals.hindsight_memory_probe.launch --state "$PROBE_STATE" \
  --kind work --timeout 20 -- run --rm --no-deps --pull never \
  --entrypoint python runner -m workflows.evals.hindsight_memory_probe.restart_readback_cli \
  verify --selection /receipts/p4/$PROBE_SHA/restart-selection.json \
  --before /receipts/p4/$PROBE_SHA/restart-readback.before.json \
  --after /receipts/p4/$PROBE_SHA/restart-readback.after.json \
  --output /receipts/p4/$PROBE_SHA/restart-readback.completed.json
```

The completed readback binds original text, context/content hashes, and the full
public fact/curation projection (including metadata hash, proof count, chunk ID,
entity membership, timestamps, state, and source lineage) plus valid/invalidated
states. For each selected fact, it reads the public memory detail endpoint and
hashes the sorted JSON entity-name array. This ignores presentation ordering while
preserving duplicate names and commas inside a name. Detail identity, source,
state and text must match the list row; a missing or malformed detail fails the
readback. The canonical database/restore comparison independently covers entity
IDs, rows and links.
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
