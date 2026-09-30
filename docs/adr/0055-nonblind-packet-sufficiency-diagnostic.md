# ADR 0055: Non-Blind Packet-Sufficiency Diagnostic

Status: Accepted for this bounded offline diagnostic, 2026-09-30. No runtime,
provider-call, deployment or native qualification authorization.

## Problem And Evidence

Two returned Pro-mode annotations disclosed inherited ADE context. A replacement
preflight also reported inherited context and stopped before opening the packet.
Strengthening a prompt detected that environment limitation but did not remove it.
The planned clean-session evidence condition was not achieved.

The user first retained that gate, then, after the failed replacement preflight,
declined an API alternative and chose to stay with the existing Pro reports.
This supersedes the clean-session prerequisite for the remaining offline
diagnostic only; it does not certify the existing reports as blind.

## Decision

Use the two byte-preserved reports as exposed-context AI annotations. Freeze the
operator transcription of their judgments before computing new-control results.
Preserve conditional readings and report-specific alternatives rather than
forcing agreement. Compare the unchanged selectors and source-owned admission
mechanics against those readings, and label the entire result non-blind and
synthetic. Do not infer native behavior, human validation, independently replicated
endorsement, general retrieval quality or production suitability.

The original input freeze, old outcome files, failed native gate and report
receipt remain immutable. The original receipt still correctly records that the
clean-session requirement was not satisfied. This amendment changes intended use
of those reports, not their provenance. PC-03/04/05/06/09/10/11 are unchanged.

## Alternatives And Consequences

Reject further identical prompt-only retries: they do not control inherited
context. Do not substitute an API mode for the user's chosen Pro-mode consultation.
Do not silently promote the reports to blind evidence or adopt a selector merely
because a diagnostic label improves. Ambiguous correction authority remains a
named product question, not a new ranking or keyword rule.

Tests bind inputs and reports, validate complete source/handle packets and real
estimated capacity limits, and reproduce case-level outcomes. An evaluator-only
reference packet is an annotated comparison aid, never selector input. Findings
must keep answer support, correction/conflict visibility, dependencies, optional
detail and other-episode/unrelated admissions separate. Unresolved readings must
remain visible in the final decision. Native turns 8-10 remain unrun.
