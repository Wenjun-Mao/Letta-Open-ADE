# Hindsight Stage-1 Review Repairs

Status: three review findings addressed in source and verified offline. This is
not live qualification, redeployment, human Character acceptance or paired-restore
qualification. The [original Stage-1 finding](hindsight-product-flow-2026-10-19.md)
retains its revision-bound observations unchanged.

Authority: user-approved repair of the focused review at
`4c354cde6f5fff22d05abd13adb785c1fb730751`; PC-03/05/09/12/14 and
[ADR 0086](../adr/0086-stage1-review-repair-contracts.md). Product direction is
unchanged. The private review and its pre-repair witnesses remain under workflow
`outputs/stage1-review-20261019/`; they describe the reviewed revision, not the
repaired source.

## Root-Layer Repairs

| Finding | Cause And Repair |
| --- | --- |
| R1: lookup SQL availability escaped saved-input pausing | Normalize known database availability errors at `TurnRecall`, preserving cancellation and programming/integrity errors. Both automatic and discretionary lookup use the existing pause contract; a tool outage cannot dispatch a Character apology continuation. |
| R2: local dialogue could disappear without compaction | Share the established raw-message budget with the compaction planner. Composition preserves its complete summary-prefix/raw-suffix partition, trims optional recall first and explicitly fails remaining overflow rather than discarding dialogue. |
| R3: pooled IDs accepted altered tool memories | Version private lookup lifecycle metadata and bind each serial tool call to its causal lookup pair and exact ordered native objects, including successful-empty semantics. Reject missing/extra/cross-call records and altered content; validate interrupted prefixes without inventing unseen execution. |

These are boundary/coverage/provenance repairs, not semantic Memory rules, a new
reviewer, generic tool framework or larger arbitrary context window. ADR 0086
records the rejected alternatives and sequential-executor invariant.

## Offline Verification

The focused workflow/runtime selection passed **450 tests**. It includes 92 new
portable regressions for availability/recovery, mocked real finalization of the
same saved run, no second Character dispatch, ASCII/Mandarin/escaping boundaries,
11/64/65-message coverage, serialized pressure and per-call capture mutations.
An independent read-only patch audit found and reproduced a terminal in-flight
lookup rejection during whole-attempt timeout. A regression failed before its
root-layer validator repair; a terminal start without a fabricated finish is now
allowed only in failed attempts, with causal binding and no later dispatch.
Actual executor/recall/private-trace integration uses synthetic provider/native
dependencies, not real inference or SQL commit evidence.

The unfiltered repository sweep finished with **1,949 passed, 135 skipped,
53 failed and 61 errors**. The 114 failing/error identities exactly match
`outputs/implementation-20261018/repository-current-contracts-reconciled.xml`:
no new or cleared failing identity. Frozen historical story/qualification
mismatches remain visible; this is not a full-suite-green claim and no historical
hash was rebound. Current receipts are separate under workflow
`outputs/review-repair-20261019/`.

Repository Ruff, changed-Python formatting, OpenAPI drift and whitespace checks
pass. Frontend source and public HTTP/tool schemas are unchanged. Database/live
provider/browser/host checks were not rerun; no service, deployment, external
account or GitHub Actions run was started by this repair iteration.

## Evidence Boundaries

All 383 indexed artifacts and the original content seal
`e8962fde0111078e822e5bfe6d1f4ed459d631c9780dcd0f301488265ba92270`
still verify. The six successful captures reload with zero mechanical issues and
remain human-unreviewed. Each probe used automatic recall without a discretionary
tool lookup: they do not qualify the repaired tool path or repaired runtime.

Only the unqualified development candidate manifest was regenerated for changed
policy sources. Its zero observed rounds remain zero. The tested live product
revision `325378bd743e85c404cdd80b4d43c4010f72c69c`, historical publication bindings,
images, release ledgers and closed activations were not relabelled or changed.

The next decision is human review of the six retained captures, keeping Memory
inputs and Character responses separate (PC-05/12), before approving broader
Stage-2 qualification. General semantic reliability and paired restore remain
unqualified; these offline repairs do not expand the earlier execution grant.
