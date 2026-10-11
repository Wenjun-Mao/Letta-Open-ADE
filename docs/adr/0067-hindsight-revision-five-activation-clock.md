# ADR 0067: Source-Bound Hindsight Revision-5 Activation Clock

Status: Accepted for the approved revision-5 semantic follow-up, 2026-10-11.
This records campaign admission mechanics only; it grants no additional live
operation authority.

## Problem

The revision-4 supervisor source still pinned its completed campaign timestamps.
Consequently `WORK_CUTOFF` expired before revision-5 staging, and offline tests
for expiry, finalization reserve and restore admissions inherited the closed
campaign clock. Advancing an individual deadline or rewriting a registry would
hide that mismatch and could carry expired authority into a new activation.

## Decision

Pin the already approved revision-5 activation from the plan in the source:
activation `2026-10-11T20:12:43Z`, target `2026-10-12T01:12:43Z`, new-work
cutoff `2026-10-12T01:27:43Z`, hard stop `2026-10-12T02:12:43Z`. Reserve the
final 45 minutes for bounded shutdown, verification and reporting. There is no
runtime date override or resume extension.

Every newly initialized registry stores the exact activation-clock receipt,
created time, and existing absolute timestamp fields under its immutable
registry digest. Registry readback requires the current receipt and a creation
time inside this activation. A revision-4 registry, a registry with no receipt,
or a modified/extended clock fails closed. Existing admitted operation deadlines
and source bundles are never rewritten; they remain evidence for their original
activation and cannot be renewed by the revision-5 supervisor.

Safety tests use a declared synthetic wall clock at activation +100 seconds.
Expiration, new-work cutoff, operation deadlines, finalization reserve, registry
identity, process identity and negative paths remain tested against that clock.
The stdlib `python -S` host-path child explicitly installs the same synthetic
clock where it exercises time-dependent behavior. Tests retain monotonic clocks
for measured waits. The deployed clock remains the source-pinned literal and is
bound into the candidate release identity and registry receipt.

## Alternatives and Consequences

- Rebinding archived registries or operation deadlines was rejected because it
  would renew old authority and alter evidence.
- A runtime environment/CLI clock override was rejected because it could move
  activation or extend a resume without a source change.
- Replacing deadlines with `now + duration` was rejected because it would turn
  one approved bounded campaign into an extensible scheduler.

The revision-5 guard can initialize only during its approved window. Tests no
longer depend on the machine's current date, while the guard's expiry and reserve
paths remain independently exercised. PC-09/13 isolation and the revision-4
evidence boundary are unchanged.
