# Compact reviewer plan: review assessment

Status: assessment of revision 4, 2026-09-24; not implementation approval.
Reports are preserved unchanged in [Pro A](reports/pro-compact-plan-a.md) and
[Pro B](reports/pro-compact-plan-b.md). Both inspected `236024f`; neither ran
tests or inspected private runtime evidence.

## Decision summary

Use the compact interface and counter-only direction. Before implementation,
amend the existing plan with two authority decisions and one conflict-grounding
clarification; turn the execution findings into checkpoint tests. No new memory
architecture, extra model stage, or general metering system is justified.

## Required contract clarifications

1. Resolution completes an antecedent's missing part; it does not erase its
   uncertainty, quotation/fiction framing, withdrawal, or no-save restriction.
   Inspect the admitted surrounding exchange, including following-sentence
   restrictions. A fresh self-contained assertion or explicit changed saving
   intent is distinct from a bare clarification. This is bounded claim scope,
   not persistent topic suppression.
2. Contextual evidence must be operation-aware. A target answer completing an
   explicit removal request, or affirmative assent to a specific proposed
   removal, can authorize forgetting. Assent that a preference ended cannot
   authorize forgetting. Recommend supporting these natural exchanges through
   the same modes, not requiring repeated command wording or adding a model
   supplied authorization flag. This recommendation needs incorporation into
   the reviewed contract before implementation.
3. Conflict without write can cite relevant read-only snapshot fact/identity
   handles and the exact candidate span. A user query need not be recast as an
   assertion or an executable mutation. These handles convey no write authority.

## Required checkpoint obligations

- Represent the current authority anchor explicitly, independent of source
  ordering. Update preparation, SQL role constraints, readback, UI and diagnostic
  safety checks together; support-only antecedents must never satisfy authority.
- Bind semantic output once to trusted records; finalization rechecks ownership,
  source integrity and original versions rather than reconstructing handle meaning.
- Choose canonical request events with one local dispatch ID on success and
  failure; remove reconstructed transport events while preserving domain events.
  Include embeddings/setup and distinguish complete transport from product success.
- Make optional observation non-vetoing at start, completion and capture hooks.
  Preserve original return/exception; never swallow mandatory provenance or
  transaction persistence failures. Missing observations mean incomplete counts.
- State timeout ownership: preserve the existing attempt deadline and applicable
  per-request diagnostic ceiling without extending a fresh timeout at each stage.
  Explicit retry attempts remain separate; no new timeout framework.
- Freeze complete permitted memory deltas, not just presence of an expected fact.
  Unexpected additions, changed scopes/identities and extra revisions must fail
  mechanical checks or remain pending explicit semantic review.

## Source checks and evidence limits

Director source inspection confirmed `_claim_sentence_has_no_save` restricts
inspection to the current evidence sentence and recovers authority as the first
non-assistant source. That cannot be reused unchanged for antecedent support.
`worker_events.py` contains reconstructed request-start/completion paths in
addition to `append_attempt_trace`; canonicalization is substantive, not a rename.
Earlier inspection confirmed capture writes can raise in `finally` and replace
the provider outcome. No new runtime reproduction, database write or model call
was performed in this assessment.

## Defer and acceptance limits

Later-recall probes are useful but optional for interface reconciliation evidence;
do not call write-only success retrieval/continuity qualification. Defer a second
reviewer, memory-first ordering, degraded replies, persistent handle registries,
or generalized event reconciliation. Native binding proves allowed combinations,
not universal natural-language entailment. Freeze positive/negative contrast cases
and measure remaining semantic behavior separately.

The two reports are compatible: Pro A conditions readiness on narrow semantic
amendments; Pro B conditions it on explicit execution obligations. Revise the
single plan once, retaining the existing ordered checkpoints and release boundary.
