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
prevents forwarding and invalidates qualification. Project only status/usage/time/
embedding shape from responses; exclude authentication, error text, raw responses
and private reasoning. Disable the pinned native raw LLM trace and external
OTEL export; retrieval/recall trace remains available. Reject streaming and secret/reasoning request fields.
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

Optional disposable restore remains deferred. If implemented later, it needs an
explicit exact project/volume/token/image/dump-result registry binding, mutually
exclusive restore epoch, DB-only isolated execution, canonical snapshot/scope
comparison, deliberate mismatch checks, and exact-ID/volume-consumer cleanup.
The current P4 contract makes no claim of successful restoration, API auth,
ranked retrieval, reranking or Character behavior. Offline tests establish local
mechanics only; the campaign still needs actual OCI/P4 execution proof.

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
and finalization own only the candidate project; disposable P4 restore support
requires a later explicit registry extension and dummy qualification.
