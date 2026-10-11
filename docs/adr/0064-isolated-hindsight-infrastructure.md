# ADR 0064: Isolated Hindsight Infrastructure and Observational Supervision

Status: Accepted for the assigned P0 offline package, 2026-10-11. No deployment,
provider qualification, semantic acceptance or native adoption is implied.

## Problem

Revision 4 needs reproducible OCI infrastructure without touching incumbent ADE
or other host services (PC-08/13), and complete observational provider requests
without spending controls or another product runtime (PC-09). A guessed outbound
payload cannot prove shared adapter/profile serialization. Best-effort capture
can silently lose evidence. SSH-connected expiry or a permanent stop latch cannot
support the authorized autonomous campaign's disconnects, repairs and persistence
restarts under one immutable hard cap. Director review of `3f85405` found the
guard incorrectly applied active exit/cap checks to intentionally stopped prior
epochs: rearm succeeded, but controller/startup immediately stopped. The missing
lifecycle admission contract belongs in the owning guard, not a broad ignore-exits
exception.

Source review found concrete default mismatches: a one-slot worker's default
reserved consolidation slots exceed capacity; global embedding retries are not
forwarded by the OpenAI factory; startup verification has its own LLM attempts.
The deployment loader rejects `{}` as a manifest. Compose env-file string escapes
do not provide the required actual query-prefix newline. These belong at owned
configuration/capture/supervision boundaries, not shared router tolerance patches.

## Decision

Own all assets in `workflows/evals/hindsight_memory_probe/`: explicit candidate
Compose, dedicated pinned PostgreSQL17 pgvector/PGroonga recipe, pinned full
Hindsight0.10.3 with one embedded worker/BGE CPU cache, existing router service
with a workflow-only instrumented entrypoint, and one-shot documented feature CLI
runner (ADR0063). No ADE API/native DB/reviewer is constructed. Recipes/configuration,
model revision and clean source SHA contribute to candidate identity; actual
image IDs and semantic fixtures belong to subsequent evidence.

Inject an observed httpx client through the shared app lifespan, retaining the
existing catalog/routes/adapters/defaults/policy. Durable exclusive/fsync inbound
capture and final outbound request bytes precede upstream dispatch. Capture failure
prevents forwarding and invalidates qualification. Project only status, finite
nonnegative numeric usage, time, embedding dimensions and input count; exclude
authentication, error text, raw responses, vectors and private reasoning. For
successful embedding responses, validate input cardinality, contiguous unique
indices, consistent nonempty dimensions and any explicitly requested dimension.
Accept finite numeric arrays and strict base64 float32 payloads. This is an
observation contract: preserve the serialized request and SDK encoding default.
The former list-only projection recorded no dimensions for successful SDK-default
base64 replies, even though Hindsight decoded them; this was a capture omission,
not evidence of failed embeddings.
Malformed successful embeddings fail and latch qualification; HTTP error bodies
are not parsed or projected. Disable the pinned native raw LLM trace and external
OTEL export; retrieval/recall trace remains available. Reject streaming and
secret/reasoning request fields.
The existing Character profile remains frozen high thinking, while Memory explicitly
disables thinking and uses JSONobject. Tests use the real shared forwarding/catalog
path to fake HTTP. Pinned-image actual Hindsight providers remain P1 qualification.

Use private generated candidate env, separate UI access/dataplane auth, the exact
built-in API tenant extension and disabled MCP. Existing Spark provider auth remains
optional; candidate router/API/DB auth does not. Owned named volumes/network and
loopback API/UI ports preserve isolation. Explicit absent deployment qualification
manifest means unqualified binding, not a fabricated deployment record.

A temporary detached Linux stdlib supervisor persists immutable start/target/hard
cap, baseline and initial owned release; flock prevents duplicates. Audited,
append-only operating epochs allow diagnosis-backed rearm, measured allocation
changes and admission of new verified clean SHA releases. Prior release paths
remain explicitly owned for safe stop. A stop receipt binds exact stopped Docker
identities. Rearm admits only that proven readback as dormant, without applying
new allocation or active-exit checks to those historical rows. Durable per-service
startup admission precedes Compose dispatch; its detached reaper persists actual
start identity immediately and fails early exits, before the five-second sample.
Active identities/limits/exits remain strict across controller resume and changes.
Unadmitted resurrection, missing active identity or incomplete startup fails closed. Deadlines never extend; no implicit restore
project ownership is added. A 300-second cleanup margin blocks fresh work before
the absolute hard cap. Positive container labels/release checks and unique
PID-token/start/UID identity prevent broad kills or PID reuse. Durable stop
admission precedes bounded registration drain, with final dispatch under an
admission lock; stop never holds admission while waiting for registration.
Atomic exclusive publication prevents partial job JSON, and unregistered gated
children expire after20s. Lock contention does not skip known owned cleanup, but
registration-drain timeout records `registration_quiescence_unproven` and withholds
completed-stop/rearm proof. A late registration cannot dispatch past the durable
barrier; a later exclusive lease and fresh cleanup/readback must prove stop. Selected
Hindsight image shutdown receives35s Docker grace/45s wall, within the300s reserve;
forced-kill cleanup is not clean persistence evidence. Registered owned
processes include builds; source quotas alone do not bound BuildKit work. OCI
sleep/disconnect and daemon-side build-cancellation proofs precede live operation.
The build-only pinned sentinel uses an isolated context/unique experiment tag,
with no extra Compose service or private/provider inputs. Positive RUN argv and
post-deadline daemon/client readback bind a typed cancellation receipt to its
registered job; a timed-out Docker client or boolean alone is insufficient.

Take Docker inventory and lifecycle-record reads under the same finite flock
lease. Previously a caller could snapshot Docker, wait for the lease while the
detached reaper published a new started identity, then classify the stale
snapshot against newer lifecycle records and report the active replacement
missing. Startup preparation and reaper completion also refresh Docker under
the lease immediately before changing admission state. Docker commands retain
their finite read timeouts; the lease serializes durable admission state and its
corresponding observation without suppressing container transitions.

Compose may report an old, stop-proven container as `removing` while replacing it
for a newly admitted release. The ordinary dormant projection includes status,
so that transition no longer equals the stop receipt and previously caused the
guard to call the known predecessor an unadmitted startup. Treat only that exact
prior identity as `replacement_pending`, and only while a service activation
intent targets the epoch release. All other projected fields must still match
the stop receipt. The intent's finite deadline still requires a replacement to
be observed; once a replacement is admitted, its exact active identity must
remain present. Unknown IDs, changed identity/resource fields, running
resurrection, and removal without an activation intent remain fatal. The
incident's pre-stop container snapshot was not retained, so the synthetic
reproduction establishes this failure mode, not the precise Docker state at the
original OCI stop. For future guard stop decisions, publish one immutable,
redacted epoch receipt containing the exact sampled candidate projections,
lifecycle decision and activation intents used for that decision, stop reason,
sample time and registry/epoch hashes. It deliberately excludes Docker `Config`,
environment, mounts and network details. If receipt storage fails, the guard
still stops owned work and does not claim diagnostic evidence was saved.

## P4 ordered finalization and bounded restart evidence

Revision-4 P4 makes independent restart readback and exact shutdown order part of
the isolated Hindsight experiment evidence (PC-07/08/13). The former single
stop could not leave PostgreSQL available after worker shutdown, and the previous
operator dump recipe ran before that stop. A launcher log also joined binary
stdout and stderr, so it was not a valid archive sink. The fix belongs in the
guard-owned lifecycle and archive publisher; a Docker exception or renamed log
would hide the lifecycle mismatch.

Admit one immutable finalization under the existing jobs-then-admission lock
order. It binds registry and epoch hashes, selected release SHA, a unique token,
exact candidate container IDs/image IDs/start times/service/project labels,
registered job identities and deadlines, plus the completed restart-proof path
and hash or explicit absence. This receipt itself closes ordinary dispatch.
Emergency stop still preempts it. The detached supervisor runs finite stages;
stage intents are durable before dispatch, and planned exits are accepted only
for exact identities named by those stop intents. Baseline drift, missing or
replaced identities, resource-limit drift, OOM, restart, unexpected exits and
headroom failures remain fatal. Long process stages retain five-second safety
sampling, and the immutable work cutoff/hard deadline do not move.

The launcher validates a narrow operation-specific Compose option allowlist and
explicit candidate service names. `run`/`exec` switch to child argv at their
service operand; `up`/`build`/`pull` have no child boundary and validate the full
remaining command. This avoids treating child options such as `psql -v` as
Compose ownership flags without admitting host-volume, project, environment,
privilege, or resource overrides.

The only root container exception is the exact 1800-second P1 cache provisioning
recipe: pinned Hindsight service/image, `python3` entrypoint, fixed cache script,
offline toggles set to zero, no dependencies or image pulls. That script admits
only the pinned Hugging Face file allowlist and revision, verifies weight size
and SHA256, writes a manifest, then chowns the named cache to UID1000. Root is
denied for the runner and every other command, environment, entrypoint or timeout.

Drain every registered process and all candidate PostgreSQL async operations in
`pending`, `processing` or `deferred` to one shared drain deadline, then preserve
the full status-count summary, including failed and cancelled operations.
Stop runner and Hindsight/worker next. While the exact candidate DB remains
running, write a private canonical read-only snapshot of schema/extensions,
banks, documents, chunks, live facts/observations, invalidated facts, provenance,
history, entities and links. Verify `current_database()` and the named candidate
volume before dumping. Stream only `pg_dump -Fc --no-owner --no-acl` stdout to an
exclusive private file, keep stderr separate, enforce lock/wall bounds, verify
nonempty bytes and `pg_restore --list`, hash and fsync before exclusive archive
publication. Publish a typed dump result before stopping router and DB. On any
failure the supervisor still performs bounded full cleanup; a failed partial
archive is not reported as a successful dump. Final stopped/baseline/headroom
readback occurs before the finalization receipt is written.

Canonical table files are JSONL: both candidate and restored-database producers
use the workflow's whitelist-checked `SELECT to_jsonb(row)::text ... ORDER BY`
query. PostgreSQL `psql -At` emits one newline per returned row and zero bytes
when a table has no rows. An aggregate-to-empty-string query instead emits a
newline for that empty result, creating a malformed blank JSONL record. The
consumer remains strict: it accepts an empty file as zero rows and rejects every
blank or malformed record. Row content and lexical ordering are unchanged.

The `restart_readback` helper uses only the public Hindsight HTTP API. Its frozen
selection binds workspace/subject bank identity, one or more character-root
scopes, source/curation/fact IDs, and original text, document content, retain
context and fact text hashes. The tag rule mirrors the pinned
`hindsight-api-slim/hindsight_api/engine/search/tags.py` from Hindsight source
`eb6df499d35300e5b2f3f029b2e6adda04ed90f8`: `any_strict` means nonempty OR tag
overlap, so character-tagged facts and profile-only facts can both match. The
feature's readback contract further admits observations only when their character
tags name exactly the selected root. Separate subject-derived bank IDs preserve
subject isolation. Pagination and state sets reject invalid totals, malformed or
duplicate IDs, including IDs present as both valid and invalidated. Independent
pre/post observations must preserve full public fact/curation projections and
valid versus invalidated states across the registered restart epoch, with the
same registry/release and a distinct post-restart epoch. It never re-ingests or
invokes Character generation. If a prior
failure prevented the check, finalization can preserve a failure-case dump and
still stop safely, but marks P4 incomplete; no restart evidence is fabricated.

The runner receives release, registry and epoch identities from the guard-owned
launcher environment through required Compose mappings; restart receipts bind
the identity of the actual readback job. Selection validation calls the existing
offline feature scope command and checks its public bank/tag result, avoiding a
second implementation of subject-bank derivation or tag policy. The candidate
manifest binds the tracked campaign fixture and the current offline freeze/replay
implementation hashes; runtime image IDs remain separately unmeasured until P1.

The OCI supervisor is stdlib-only and does not install ADE or runner dependencies.
Its selection admission and canonical snapshot path therefore use a separate
stdlib structural contract for identities, IDs and hashes. Public feature-scope
qualification and HTTP capture/compare stay inside the qualified runner. The
runner's completed proof binds the canonical selection hash and exact selection,
before-snapshot and after-snapshot file hashes; host admission checks those
bindings and campaign identities without reimplementing feature semantics.

### Candidate05 fact-level profile classification

The completed candidate04 q01 replay exposed an ingestion-classification gap:
Hindsight extracted the source-supported correction and preference change in s03,
but both facts had only `character:root_xiaotang` and no `kind:profile`. The
`root_other` recall therefore excluded those fact IDs under the intended
character-or-profile filter. This is upstream of recall ranking. The initial
failure capture occurred before Character dispatch, so it does not establish a
stale Character answer. PC-02/03/04/06/07/09/12/13 continue to govern profile
ownership, character boundaries, corrections, minimum scope, and the isolated
evaluation.

For a fresh candidate05, keep one optional nullable `kind:profile` label and
refine only the tracked Memory retain mission and label description. Ask the
extractor to classify each proposition independently and separate portable
subject properties/preferences from source, chat, assistant, and interaction
narrative. A supported current value, clearly time-bounded former value, explicit
correction, or preference change can be profile when it stands alone and remains
useful without private origin; history is not private merely because it is old.
Private origin, participation, assistant action/confirmation, and
relationship-specific experience remain character-local. Preserve each source's
character tag and observation root gate; never label the whole source. This
refinement retains the original extraction obligations for speaker attribution,
time, hypothetical versus completed events, solo versus shared participation,
uncertainty, and correction versus preference change. The exact prompt and label
bytes are versioned in the workflow, frozen into the candidate manifest, sent
through the bank configuration API, and compared against full supported
bank-config readback before retain. Offline loader validation also requires
observations enabled and automatic consolidation disabled.

Offline tests establish request serialization, config drift rejection, and
candidate-manifest binding only. They cannot establish that a model applies the
classification correctly. Candidate05 requires fresh ingestion of the frozen
corpus and q01 replay with private-origin exclusions; candidate04 remains an
immutable negative result. No deployed candidate is changed or redeployed by
this decision.

### Optional disposable PostgreSQL restore qualification

The optional local P4 restore is admitted only after ordered finalization has
closed the candidate epoch and published its exact archive, canonical snapshot,
and frozen selection. The sealed operation binds registry/epoch/finalization,
image ID, release, archive and control-evidence hashes, plus one exact Compose
project, container and named volume. A distinct typed process-owner scope
authorizes the restore Compose launch; project-name prefixes grant no ownership
and the main candidate lifecycle completion path is never inferred from a
project string.

Restore runs a single PostgreSQL service with no network, published ports or
host mounts and bounded memory/CPU. The controller streams the immutable archive
to `pg_restore`, captures canonical table rows and schema/extensions through an
exact read-only SQL allowlist, then compares all rows and derives `any_strict`
scope eligibility from restored top-level fact tags. The finalizer's
`scope_eligibility` sidecar remains hash-validated control evidence rather than
database state. Full rows retain vector values, source lineage and history. A
mismatch preserves original and restored evidence and keeps the volume; success
removes only the exact registered container and volume after consumer readback.
An explicit stop intent preempts the detached controller at its next safety
check, stops its registered child process, and preserves the disposable volume
for review. An operation-scoped file lock makes admission/resume single-owner;
the process child validates the typed scope before executing Compose. Rearm
remains blocked until cleanup has completed successfully.

This implements optional offline mechanics under PC-07/08/09/13. It proves only
logical persisted PostgreSQL state restoration. It does not qualify API behavior,
authentication, ranking, reranking, Character behavior or live deployment.
Static and synthetic checks do not replace actual OCI execution evidence.

### Public fact entity readback

The candidate05 initial-retain-a recorded-versus-fresh-GET inspection showed
that `/memories/list` returns entity names as a comma-joined display string. The
inspection found the selected fact identities, order, text, scope, metadata and
lifecycle fields unchanged, while only the presentation order of that string
differed. The old hash projection would therefore falsely reject a P4 comparison
for a non-semantic presentation change; no P4 restart comparison had run. The
same public API's fact detail endpoint returns a structured array of entity
names, so P4 now reads that endpoint for each frozen fact and hashes canonical
JSON for the sorted names. It preserves multiplicity and commas in names, and
rejects missing/malformed details or mismatched fact, source, state or text
identity. Membership drift remains a readback failure.

Do not split the display string on commas or omit the entity projection: splitting
cannot preserve names containing commas, while omission would discard a real
public fact difference. This public name projection is distinct from entity IDs,
types and links; canonical database snapshot and restore comparisons remain the
authority for those stored relations. This repair addresses P4 readback under
PC-07/08/13 without changing storage, ingestion or product semantics.

## Alternatives and consequences

- Shared router edits or reconstructed adapter requests: rejected; observation
  belongs to the isolated workflow and must see actual serialization.
- Best-effort receipts, raw responses or exception logs: rejected; missing captures
  invalidate experiments and provider reasoning/credentials are not evidence.
- Mac/SSH-only expiry, silent marker deletion, or a single unrecoverable stop:
  rejected; detached expiry and explicit recovery epochs preserve both safety
  and authorized repairs without moving the campaign clock.
- Shared PostgreSQL or weaker vector-only CJK acceptance: rejected under PC-13.
- Upstream retry patch merely to force global0: not justified before diagnosis.
  Document actual SDK/startup mechanics, account for calls, bound owning work and
  prove them with pinned-image fakes.

Static validation and synthetic tests guard the contract. Offline success is
neither ARM provider/extension/reranker acceptance nor OCI guard proof or semantic
qualification. The owning README contains exact operator commands and remaining
P1/P2/P4 gates. Semantic replay and complete-trace pre-Character reranking
admission remain separate from this infrastructure decision. Initial supervision
finalization owns the candidate project; the optional restore has a separately
sealed, exact project/volume lifecycle and remains an unrun campaign gate until
fresh OCI evidence is reviewed.
