# ADR 0076: Isolated Product Actor And Provenance

Status: Accepted for the approved Stage 1 candidate, 2026-10-19. Actual native
product demonstration, M6 recovery and human Character review remain distinct.

## Problem

The native boundary and request collector did not establish actual ADE dialogue.
A live-capture label or operator-authored Memory snapshot cannot prove that
frozen user seeds, actual assistant replies, native sources and final model input
belong to one relationship. OCI also needs the full isolated product stack without
touching incumbent databases or surrendering the reserved host CPU.

## Decision

The workflow owns a fresh ADE PostgreSQL service/volume in addition to native
Hindsight PostgreSQL. Its public bootstrap/migration commands create a separate
non-login owner and application role. A fresh development workspace, API, worker
and web use only these candidate stores. No history import or incumbent deployment
is implied. API has read-only private observations; worker writes them. The browser
server uses the operator credential, not admin. All published ports are loopback.

The six-slot actor freezes the three approved cases with two repeats, immutable
source/runtime/persona/config identities and fresh relationships. It creates a
source chat and a fresh same-version/same-bank probe chat before user seeds. Only
the exact user seeds enter normal ADE turn acceptance; assistant messages must be
actually generated and committed. Evaluation waits for native processing without
adding a product reply barrier. Probe input contains no source dialogue/summary.
PC-02/03/04/05/09/12/14 remain the owning product agreements.

Completed `live_capture` records require a typed, physical-file-hash-bound product
sidecar. Record and report loading both independently revalidate every collected
setup/probe request, source/config/scope, public-read journal, original native
document, processing readback, actual lookup and committed reply. The product
observation binds the relationship's frozen bank-configuration hash. This detects
accidental drift, not malicious operator forgery or remote model-weight identity.
Historical records/fingerprints are not rebound. Failed slots retain raw receipts
and explicit limitations, not a synthesized success or semantic reroll.

Pre-inference guard, 2026-10-19: validate actual public session prompt/persona
hashes, Character/compaction fingerprints, relationship roots and distinct
same-version source/probe conversations immediately after provisioning, before
any seed or Character call. Previously these checks happened only at capture
validation. Keep that reload validation too. A controlled mismatched-persona
SQL test must fail with zero Character requests, not consume a wrong-input slot.

The staged archive has no `.git`. Its caller must supply the exact evaluator
commit explicitly; there is no missing-Git/unknown-identity fallback. Human review
templates remain outside `review-*.json` and all six Character results initially
remain `UNREVIEWED`. The final traffic snapshot includes unfiltered native/Character
Router requests and missing outcomes at collection time; it is not a quiescent
closeout, billing statement or assertion that native background work has finished.

A workflow-only transparent HTTP proxy provides explicit per-conversation,
one-shot fault rules for generation and native retain. It forwards original bytes
to fixed candidate upstreams and records IDs/hashes/status only. It cannot alter
semantic input, access Docker, target baseline services or implement product policy.
Holds have finite deadlines and recheck activation closure before forwarding.

Candidate image builds run serially before supervision/inference startup, reserving
host CPU 3 and limiting each build to three CPUs and 3 GiB RAM. The installed OCI
Buildx command has no per-build resource-limit option. **Temporary build-tool
mitigation:** use the legacy Docker builder only in the child process environment,
with explicit CPU/cpuset/RAM flags and a finite timeout. First build a no-cache
cgroup assertion image; if actual limits are absent, stop rather than weaken them.
No global Docker setting or persistent builder service changes. Stage 3 must
replace this deprecated toolchain with a supported resource-isolated build path
before ongoing release use. Preserve failed build logs and enforce the same
resource contract in the replacement.

## Alternatives And Guardrails

Authored assistant history, direct feature/database calls from the actor and a
second recall to reconstruct input were rejected: they do not prove the normal
product path. A fake provider/native service is permitted only in explicitly
controlled mechanics tests, never as fallback in actual live slots. Private
reasoning-bearing continuations remain incomplete rather than being stripped.
Missing or altered sidecars fail reload/report validation. Source-clean images
and candidate-only manifest generation do not promote the release ledger.

Controlled application-role SQL tests exercise the whole actor through the normal
worker and actual Router, including tools, private-reasoning exclusion and corrupt
readbacks. They do not qualify native semantics, Character quality, M6 or later
paired restore. Every actual activation still needs independent expiry, fresh
source-bound supervision, baseline/headroom checks and explicit safe closeout.
