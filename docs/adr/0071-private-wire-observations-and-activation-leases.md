# ADR 0071: Private Wire Observations And Activation Leases

Status: Accepted for the approved isolated Stage 1 implementation, 2026-10-18.
Live collector qualification and host activation checks remain pending.

## Problem

ADE's existing provider traces record lifecycle metadata, not the full request.
Model Router subsequently changes the model name, adapter payload and defaults,
so an earlier reconstructed prompt cannot establish what the provider received.
The unattended integration also needs a host safety stop that does not depend
on the Codex client staying connected or on another approval at every restart.

## Decision

Add opt-in private observations at Model Router's final HTTP send boundary.
Serialize the actual normalized request once and send that request object.
Record its exact bytes/hash, generated request ID, source/model identity and
supplied role/run/attempt metadata before dispatch. Record visible response
fields or transport failure afterward, without provider retries in Router.
Return the Router request ID for correlation, including failed HTTP outcomes.

Capture is disabled by default and requires Router authentication when enabled.
Expose authenticated private observation reads and a paginated metadata index;
do not put raw prompts in ordinary product activity. The isolated candidate
holds only authorized synthetic dialogue. Headers/credentials/private reasoning
are excluded at collection. If a request contains private fields, preserve its
hash and an explicit incomplete-capture reason and forward the original request
unchanged; never silently redact it into a supposedly complete input record.
Streaming observations collect visible fields as bytes pass through and retain
incomplete/cancelled outcomes. They do not buffer the product stream before use.

Use create-only, atomically visible private records. A missing outcome or an
incomplete input is not a successful assessment capture. Caller-supplied phase
labels and hashes are observable declarations, not external authenticity proof
or a causal diagnosis of Character/Memory behavior.

Each owned OCI activation has a sealed immutable manifest, exact committed
source, project/activation labels, baseline snapshot, resource reserves and a
finite deadline. Stop admission at least one hour before the maximum twelve-hour
expiry. Host supervision and an independent systemd expiry stop only containers
owned by that project and activation. Source-label mismatch is an unsafe owned
candidate, not a reason to leave it running. Existing baseline containers remain
outside the stop set.

Before attempting Docker stops, atomically create a permanent close marker.
Router verifies the sealed lease, time window and absence of that marker before
each inference dispatch. It also requires a healthy source/activation-bound host
heartbeat no older than 60 seconds. Thus loss of supervision or Docker failure
cannot leave new inference admitted,
and restarting the same closed activation cannot reopen it. A fresh activation
requires reconciliation, capacity/baseline checks and no simultaneous old owner;
the user's A6 approval already covers this renewal.

## Alternatives And Consequences

Reconstructing requests in the evaluation CLI was rejected because it misses
Router normalization and actual continuations. Global logging would expose
unrelated dialogue and secrets. A client-only timeout would not survive loss
of the client. Finite host leases plus per-dispatch admission protect this one
candidate without creating a general scheduler or an approval-per-activation loop.

Tests must compare captured bytes with a recording provider through the real
Router, cover tools/failures/private fields/stream cancellation, and prove zero
dispatch after expiry, tampering or closure. Ownership tests must prove baseline
preservation, resource-pressure closure and recovery after Docker unavailability.
Live tests must additionally verify host timer/process identities and source
bindings. These mechanics do not qualify Memory semantics or Character quality.
