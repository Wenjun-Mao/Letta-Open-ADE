# ADR 0062: Self-Hosted Hindsight

Status: Accepted hosting direction and OCI experiment placement, 2026-10-10,
by explicit user direction.
Autonomous-campaign planning direction clarified 2026-10-11; execution waits for
the user's explicit Goal-mode start against the linked plan, not this ADR alone.

## Problem

The user rejected Hindsight Cloud's usage pricing for ADE's iterative test
workload: repeated suites and re-ingestion can make a small per-pass illustration
misleading. The user's concern about easily spending $100 on tests is a reason
for choosing self-hosting, not a measured forecast or a new spending gate.

The [source-pinned assessment](../findings/hindsight-integration-assessment-2026-10-10.md)
and [consultation synthesis](../findings/hindsight-consultation/assessment.md)
remain the technical inputs. Neither establishes behavioral fit or approves
production adoption.

## Decision

Use **self-hosted Hindsight**, rather than Hindsight Cloud, for the planned
experimentation and any subsequent adoption under this direction.
[PC-13](../product-contract.md#hindsight-hosting) owns the agreement. Do not
reopen Cloud as the default next step or create a Cloud account/comparison
campaign without a changed user direction.

During setup planning the user explicitly required an isolated first experiment.
Keep its persistence and execution separate from native memory; reuse of model
infrastructure must not alter the running ADE/trial services. The
[draft setup plan](../plans/hindsight-self-hosted-experiment.md) contains the
selected placement and proposed service/model configuration.

The user subsequently selected the existing OCI ARM host for the isolated
experiment after raising Mac RAM/swap concerns. This supersedes the plan's original
Mac placement recommendation. Read-only inspection found resource headroom and
Spark connectivity; it did not qualify deployment or CPU inference. The user's
planned 4-core/24 GB resize is owner-managed and unverified. The user then clarified
that the end-to-end plan must target the current 2-core/approximately 12 GB host:
the upgrade is optional headroom, not a deployment prerequisite. Refresh actual
capacity and prove the candidate within measured limits; do not confuse this
target with completed qualification. Keep the Mac as a development/browser client
and existing OCI services untouched.

Self-hosting selects who operates Hindsight, not where every model runs. The plan
defines starting model routes and permitted evidence-backed experimental changes,
not a production model decision. Model usage, compute, storage and operation
still have costs; self-hosting is not a zero-cost or all-local-processing guarantee.

### Autonomous Campaign Clarification, 2026-10-11

The user requested an approximately ten-hour execution window and explicitly
rejected fixed replay-count restrictions that could block routine progress.
Use the plan's autonomy envelope: diagnose, repair, redeploy owned resources,
adjust experimental configuration and rerun useful tests without repeated owner
approval. Preserve failed evidence and unchanged product expectations; technical
choices are reversible experiment decisions, not implicit production adoption.

Reject both a fixed one-baseline/one-correction approval gate and unrestricted
experimentation. Bound work by purpose, elapsed time, finite request mechanics,
observed usage, host safety and explicit exclusions. Distinguish local repairable
failures from genuine authority/risk changes. The plan carries the activation,
OCI-side expiry, recovery and closeout requirements; do not start work or create
an automation merely because this planning clarification was published.

## Alternatives

- Cloud-first experiment: rejected for this project's expected repeated test
  workload, despite the convenience of managed operation.
- Mac-hosted first experiment: superseded by the user's OCI selection to avoid
  adding server/reranker memory pressure to the daily workstation.
- All-local models as an automatic consequence: not selected; hosting and
  model placement are separate choices, with quality and resource tradeoffs.
- Resume native-memory feature development instead: not implied by rejecting
  Cloud pricing; the Hindsight-first investigation direction remains.

## Consequences And Guardrails

Bounded experiment preparation starts from the pinned self-hosted baseline;
justified compatible candidate repairs require fresh pins and relevant checks,
not repeated permission to fix ordinary packaging/configuration failures. Service operation and
eventual backup/recovery become project responsibilities, not Cloud features to
assume. No service is installed or started by this documentation decision.

Bank layout, ingestion/delivery semantics, storage authority and Character
integration still need adoption decisions after experimental evidence. The
incumbent remains unchanged under PC-05/08/09; this does not amend its transaction
contracts or authorize migration, dual writing, native isolation or cutover.
Provider runs fall only within the plan's subsequently activated campaign.
Observational request accounting
remains the PC-09 policy; no new runtime spending gate is introduced.
