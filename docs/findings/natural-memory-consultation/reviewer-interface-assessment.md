# Reviewer-interface consultation assessment

Status: director assessment, 2026-09-24. No new runtime implementation or live
experiment is authorized by the reports themselves. Originals are preserved in
[report A](reports/pro-reviewer-interface-a.md) and
[report B](reports/pro-reviewer-interface-b.md).

## Verified findings

Both reviewers inspected source `92809c4` and the publication amendment, not
private runtime captures. Agreement is not independent execution evidence.
Director inspection at `aea2719` confirmed these code properties:

- Subject additions expose an unnecessary entity selector; target versions and
  authority metadata also ask the model to repeat server-known information.
- The evidence binder requires a referent for endorsement but not endorsement
  for assistant-derived factual support. An offline call to
  `prepare_natural_memory_review` with an existing Roxy pet, current user
  `Roxy.`, assistant `Is Roxy a Husky?`, and a breed proposal citing those as
  `user_assertion` and `assistant_referent` prepared one operation. No database
  write or provider call was used. This reproduces the reported preparation
  gap, not a claim of an observed production incident.
- `NaturalReviewDecision.model_validate({})` accepts empty proposals and
  dispositions. Missing output is not distinguished from intentional no-change.
- Historical user support cannot be represented by the current evidence roles;
  current authorization and a prior supporting antecedent need distinct roles.
- Deferral is paired with a complete proposal and preparation validates that
  proposal before pruning deferred writes. Genuine unresolved claims should
  not require guessed identities or values.

## Use, test, and defer

Use the compact semantic-interface direction: omit subject selectors, bind
snapshot-local target handles to server-held IDs/versions, separate current
authority from bounded contextual support, and replace parallel proposal/
disposition arrays with explicit write/defer/conflict items. Require an explicit
complete output shape and classify truncation separately. Preserve exact
matching, subject ownership, version fencing, no-save precedence, and truthful
atomic outcomes. These are proposed contract amendments, not permissive repair
of invalid old responses.

Test the endorsement counterexample first. Explicit assertion, antecedent
resolution, and affirmative endorsement need distinct allowed combinations;
merely renaming source fields does not establish semantic consent. Test genuine
deferral, scoped preferences, corrections, forgotten-identity exposure, and
unknown/stale/cross-subject handles. Keep one post-response reviewer and atomic
finalization for the next design unless a separate decision changes them.

Defer two-reviewer phases, memory-first ordering, and degraded reply delivery.
They introduce extra behavior and are not justified by the observed clerical
failures. Smaller output cannot by itself guarantee semantic accuracy or a
particular thinking-token requirement. A new interface/envelope needs new live
evidence; do not reuse old partial cells as qualifying results.

## Request accounting direction

The user requests removing request-budget enforcement in favor of simple
counters. Adopt that direction in the next bounded implementation: remove
generation/embedding spending caps, reservation/limit bindings, scope allocation
gates, cap environment settings, and budget-exhaustion scheduling branches.
Count actual outbound attempts, including failed calls, by request kind and
provider/model, with run/iteration association and outcomes where already
available. Unexpected counts are visible diagnostics, not spending vetoes.
Prefer existing request events/artifacts; do not replace the budget subsystem
with another general metering framework. Cross-process counts must not silently
omit worker calls or double-count wrapper layers.

Keep context/input/output token limits, timeout and cancellation, explicit retry
semantics, and bounded tool-loop termination: these protect execution correctness,
not monetary budgets. Preserve previous ledgers/findings unchanged as historical
evidence. This assessment changes no runtime files or release receipts.
