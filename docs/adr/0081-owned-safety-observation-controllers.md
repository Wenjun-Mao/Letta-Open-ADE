# ADR 0081: Owned Safety Observation Controllers

Status: Accepted for Stage 1, 2026-10-19. The first four proxy scenarios and
paired-backup mechanics have controlled tests; actual gates remain pending.

## Decision And Boundaries

M6 evaluators use public product, private-observation and finite fault-control
APIs. They record the frozen product-image revision separately from the committed
controller revision and physical controller-file hashes. A controller runs from a
read-only, commit-named staged source directory, not a dirty checkout or relabeled
product image. Any product/runtime fix still requires affected live retests.
This is evaluator locality under PC-05/08/09/12/14, not another Memory service.

Predeclared cases cover failed generation, cancellation, deliberately delayed
retention with unrelated progress, and lost acknowledgement after real native
acceptance. Fresh relationships and normal accepted turns establish every source.
Native original text/IDs/roles/version/sequence are independently checked against
saved messages. No authored assistant input, manual fact edit, recall fallback,
semantic grading or best-answer selection is allowed. A failed case or incomplete
readback stays failed; cleanup failures cannot turn it into a pass. These four
cases alone do not complete M6's outage, restart, stale-worker, isolation or
coordinated-recovery gates.

The proxy must check caller disconnection again when a hold is released. A
deterministic regression exposed the prior release race: a disconnected held
request was forwarded and returned 200. It now returns 499 without forwarding.
This is a candidate fault-fixture correction, not a promise that cancellation
can undo an upstream request already sent.

## Paired Checkpoint

The host controller validates the unclosed, healthy lease, sealed configuration,
source-bound product run, exact owned services and finite remaining time. Capture
public state/delivery/processing readbacks, then stop candidate ingress/reply
writers. Observe native pending/failed operation IDs through a bounded drain;
preserve incomplete pages and non-terminal work, never replay history to settle it.
Stop native writers and record final Router traffic, including missing outcomes.

With both stores writer-free, dump ADE and Hindsight PostgreSQL separately using
their owned Unix-socket roles, custom archives, owners/grants, physical hashes and
`pg_restore --list` readability. No passwords or global-role dumps are exported.
Record migration/image identity and pending operations. Even on partial failure,
close admission and stop only owned resources; separately verify exact baseline
identity/health and no running candidate containers. Preserve partial dumps and
failure receipts rather than overwriting them.

This is a coordinated backup without live product writers, not a restored or
release-qualified recovery point. Stage 3 still needs deliberate paired restore,
role/schema compatibility and product behavior qualification. Do not point the
incumbent runtime at this workspace or infer a cutover from successful dumps.
