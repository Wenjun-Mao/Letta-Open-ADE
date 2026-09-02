# ADR 0017: An Observed Incumbent Baseline Does Not Veto Native Cutover

- Status: Accepted
- Date: 2026-09-02
- Related: [ADR 0012](0012-content-addressed-behavior-evaluation-decisions.md) and
  [ADR 0016](0016-ade-native-agent-studio-cutover.md)

## Context

The original paired Agent Studio gate treated a round as passing only when both the
Letta-v2 incumbent and the ADE-native-v3 candidate passed the same observable
checks. That conflated two different questions: whether the candidate is ready to
own the product, and whether the incumbent still performs the scenario well.

In a Test Center observation with identical fixture, prompt, persona, model,
timeout, and zero-retry controls, native v3 captured the required durable facts in
all three rounds. Letta v2 completed the turns and cleanup but captured the expected
facts in none of the rounds. The v2 prompt and memory tools were present. Requiring
the incumbent to pass would therefore veto the strictly better candidate for an
incumbent deficiency that the candidate had corrected.

This observation is diagnostic evidence, not a release approval. Release evidence
is authoritative only when the reviewed ledger records the source identity and the
content hashes of the parity specification, provenance, comparison, and summary
artifacts. A locally retained Test Center output is a reproducible convenience, not
the sole or durable authority for this decision.

## Decision

- Schema-v2 paired artifacts name Letta v2 as the `observed_incumbent` baseline and
  ADE-native v3 as the `cutover_candidate`.
- A candidate qualifies from the paired comparison only when all three native rounds
  pass, inputs are comparable, timeout/retry controls are exact with zero retries,
  and cleanup is complete.
- Native must be non-regressive in every paired round: whenever the observed
  incumbent passes a round, the candidate must also pass that round. A failed
  incumbent round does not make a failed candidate round pass.
- The incumbent outcome remains first-class evidence. Every round must show separate
  native and Letta outcomes plus non-regression; summaries must show their separate
  pass counts.
- A failing incumbent does not veto a passing, non-regressive candidate. It remains
  a visible diagnosis and may justify separate incumbent remediation, but it is not
  a native-cutover blocker.
- This is a paired baseline comparison, not a claim of product parity or
  equivalence. Native-only guarantees remain owned by qualification and deterministic
  conformance evidence as defined in ADR 0016.
- Schema-v1 bundles remain historical evidence only. They cannot satisfy this
  cutover gate because they do not encode the distinct candidate, baseline, and
  non-regression outcomes.

## Rejected Alternatives

### Require Both Engines To Pass Every Round

This lets an incumbent defect veto a replacement that demonstrably fixes it. It also
makes the candidate's acceptance criteria depend on behavior ADE intends to retire.

### Stop Collecting Letta Results

Removing the incumbent loses the most useful regression signal during the transition.
The comparison must keep the same inputs and expose both outcomes even though only
the candidate is being qualified.

### Use Average Scores Or A Best-Of Rule

An average can hide a failed candidate round, and a best-of rule turns a paired
comparison into an unreliable quality sample. The contract remains round-by-round
and fail-closed.

### Rewrite Historical Bundles

Changing an old receipt would destroy the audit boundary. New schema-v2 evidence is
collected for the new decision; older artifacts remain readable as history.

## Consequences And Guardrails

Release reviewers must read the native candidate result and the Letta baseline result
separately. A native `3/3` with a Letta `0/3` can meet this paired-comparison gate if
the other required controls pass; it must be described exactly that way, never as
equivalence. A native failure in a round that Letta passes blocks cutover.

- Require the schema-v2 candidate, baseline, and non-regression fields in the
  signed comparison and summary artifacts before release review.
- Bind the reviewed artifacts and their source/deployment identities into the
  content-addressed release ledger under ADR 0012.
- Reject incomplete rounds, incomparable inputs, nonzero or hidden retries,
  incomplete cleanup, and any native regression.
- Keep native-only memory, isolation, tool, trace, cancellation, and idempotency
  requirements outside this comparison; they continue to require their dedicated
  qualification and conformance receipts.
- Do not call a failed-baseline result `parity`, `equivalence`, or a two-engine pass.
  Use `paired baseline comparison`, `candidate qualification`, and
  `non-regression` in operator-facing documentation and UI.
