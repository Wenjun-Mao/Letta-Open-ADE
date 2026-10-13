# ADR 0069: Offline Character Assessment Kit

Date: 2026-10-13. Status: accepted for the first bounded implementation
deliverable authorized by the user. Offline mechanics implemented; live adapter,
human calibration and behavioral qualification remain pending.

## Context

[PC-12](../product-contract.md#character-specification-and-assessment) and
[ADR 0061](0061-capability-responsibility-map.md) establish case/run/review
assessment with three lenses. The starter prose alone cannot freeze exact
Mandarin inputs, capture actual attempts or preserve revised judgments. Reusing
the old native evaluator would import native fact/reviewer assumptions superseded
by PC-14; historical Hindsight campaign artifacts are not a new product baseline.

## Decision

Own a small local artifact workflow under
`workflows/evals/hindsight_integration/`, with frozen Mandarin cases, a persona
snapshot, explicitly authored calibration examples, and a no-network rehearsal.
Keep its contracts local rather than adding product schemas, a Memory abstraction
or a new model-judge phase. Reuse the public pure file-fingerprint utility only.

Freeze selected cases, runtime identities and repeat slots before execution.
Create the attempt journal before external work. Preserve original attributed
source messages, processing/recall evidence and actual serialized generation
input separately from the reply. Controlled histories remain diagnostic setup,
not proof of product memory formation. Export actor inputs without rubrics.

Use strict, content-bound, create-only JSON records. Bind run -> attempt ->
capture -> review, with append-only review revisions and explicit correction
reasons. Keep failed/incomplete/unrun attempts visible. Mechanical issues prevent
semantic qualification; reused relationship scopes exclude affected captures.
Report each promise/lens with counts and denominators, repeat consistency and
uncertainty, never a composite score. A quoted passage and contextual reason
support each judgment; quote validation is not semantic grading.

Offline scripted evidence and live artifact imports are distinct modes. Import
support does not execute a live run or authorize one. The future verified ADE
adapter must collect actual public-boundary observations; seals cannot establish
remote authenticity or completeness. Known credential/private-reasoning fields
are rejected, not silently redacted into misleading complete evidence.

## Alternatives And Consequences

- Prose-only delivery leaves the agreed review method non-repeatable. The kit
  makes mechanics testable without waiting for product integration.
- Extending native fact scoring or historical campaign runners would preserve
  the wrong runtime coupling. No compatibility adapter or native fallback is added.
- An autonomous AI judge or numeric threshold would exceed the agreed method.
  The authored examples require human calibration; no model-quality claim follows.
- Hashes are drift checks, not an adversarial audit system. Live readback checks,
  private-evidence handling and committed-source binding remain collector duties.

Regression tests cover frozen fixtures, mixed/stale evidence, quote bindings,
corrections, repeat accounting, scope contamination, failed/missing artifacts and
CLI rehearsal. The [workflow README](../../workflows/evals/hindsight_integration/README.md)
owns procedure and current limitations. Stage 1 still needs its real adapter;
Stage 2 still needs human-calibrated, source-bound live evidence and broader gates.
