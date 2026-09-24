# Revision 5: external GO assessment

Status: review complete, awaiting implementation authorization, 2026-09-24.
Both [authority review](reports/pro-compact-plan-r5-a.md) and
[execution review](reports/pro-compact-plan-r5-b.md) inspected
`a38d3e4e778899fab2763853c04cfd52bdb0ca2c` and return GO with no further
mandatory plan amendment. Originals are preserved; neither consultant executed
tests, inspected private artifacts, or proved runtime acceptance.

## Disposition

Use revision 5 as the bounded implementation contract. Stop prose-review cycling:
the next useful review is of implementation diffs and checkpoint evidence. The
reviews agree on scope, not empirical reliability. User delivery of the reports
is not implementation, live-call, deployment or release authorization.

Retain these existing checkpoint obligations rather than expanding the plan:

- Replace pooled-source support; explicit current authority and mode-specific
  sources must survive preparation, SQL storage, readback and diagnostics.
- Preserve inherited uncertainty/no-save/withdrawal, short assent versus bare
  names, and factual ending versus permission to remove. Test mode-switch bypasses.
- Bind identities/targets once and transactionally revalidate ownership, sources,
  original versions and generation without remapping or reallocating meaning.
- Delete spending enforcement and reconstructed request events. Count canonical
  local dispatch IDs once across retained copies; include setup and embeddings.
- Keep optional observation incapable of changing transport/product outcomes;
  mandatory provenance, domain events and finalization remain authoritative.
- Score the complete permitted mutation delta, including extra revisions even
  when final values look correct. Distinguish required writes from valid negatives.
- Preserve applicable per-request and shared-attempt timeout behavior, explicit
  retries, cancellation, lease fencing, old-history reads and terminal replay.

## Deferred choices and limits

Use one ordinary aggregation function and simple best-effort observation, not
new metering infrastructure. Later-recall probes remain optional and narrow claims
if absent. No second reviewer, persistent handle registry, degraded delivery,
silent repair or extra semantic judge is justified by these reports.

After authorization, implement checkpoints 1-4 serially with focused and broad
offline checks. Checkpoint 5 remains a separately authorized fixed live diagnostic.
The old campaigns and three diagnostics remain immutable historical evidence;
no A/B winner, source-fingerprint rebind or release qualification follows from GO.
