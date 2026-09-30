# ADR 0047: Recalled Dialogue Attribution

Status: Accepted for bounded development on 2026-09-29. No deployment, live
semantic acceptance or release qualification is implied.

Follow-up: [bounded live observations and isolated trial adoption](../../workflows/evals/character_memory_dev/hands-on-feedback.md#live-attribution-confirmation-and-trial-adoption-2026-09-29)
now exist for this clarification. They do not establish general semantic quality
or change the release boundary; the recorded anecdote limitation remains.

## Problem

The [hands-on trial](../../workflows/evals/character_memory_dev/hands-on-feedback.md)
recalled a relevant exchange but attributed an assistant opinion to the user and
added unsupported details to a remembered story. Reconstructing the admitted
packets preserved the original roles and text for generation and review. The
original reviewer JSON was not retained, so its exact reason remains unknown.
This is a source-use and review-coverage issue, not evidence for changing ranking
or stripping assistant messages.

## Decision

Under PC-03/05/06/09, clarify the existing generation and H-review contracts:

- Shared generation instructions preserve speaker, uncertainty and temporal
  scope. Assistant suggestions/opinions do not become user assertions without
  separate user assertion or endorsement. Recollection must not add motives,
  actions or locations. New suggestions and tentative inferences remain allowed
  when presented as such, rather than as remembered events.
- The existing H-capable reviewer checks speaker claims against attributed
  evidence, including supplied later user endorsement. A positively grounded
  mismatch uses the existing exact H quote, candidate quote and atomic conflict
  rejection. Identical wording alone does not establish a mismatch. Endorsement
  supports its own time and scope, not earlier user authorship.
- An unsupported detail is not necessarily contradicted by a source. Absence
  alone does not authorize a fabricated conflict citation or a new general
  answer-verification mandate. Generation remains responsible for faithful
  narration; this clarification is not a comprehensive hallucination filter.

The shared generation owner applies uniformly to existing context recipes;
H-specific review remains in the established H-capable instruction. No schema,
ranking, persistence, persona, prompt-template snapshot or retry changes.

## Alternatives And Guardrails

Reject phrase rules, removing assistant history, a second judge and a silent
absence-of-evidence veto. They either lose valid context or broaden semantics
without solving the demonstrated attribution contract (PC-06/09).

Packet and scripted-review tests cover false versus correct speaker attribution,
supported versus embellished recollection, a suggestion versus an asserted past
event, and explicit later endorsement. These prove assembly and conflict/write
mechanics only, not model recognition or improved conversational quality.
Preserve historical fixtures and receipts. Changed source fingerprints require
fresh evidence; prior release-policy freshness gates remain unwaived. Any live
follow-up must retain actual replies, reviewer decisions and complete memory
deltas, including accepted controls, without rerolling misses.
