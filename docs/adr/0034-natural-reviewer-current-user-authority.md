# ADR 0034: Reviewer Citation Authority for Natural-Memory Proposals

- Status: Historical diagnostic; source-authority interface superseded by
  [ADR 0035](0035-compact-natural-review-and-observational-dispatch.md).

> Preserve the failed diagnostic evidence; do not restore its model-owned
> authority choices or treat the original authorization as a new-run approval.
- Scope: shared natural-memory reviewer instruction contract

## Problem

The reviewer correctly identified a pet-name correction from Rocky to Roxy
but cited both the current correction and the earlier user statement as
`user_assertion` evidence. Native binding rejected the latter: every user
assertion or endorsement citation must point to the current user message.
The exact target fact and version were already supplied, so the old statement
was context, not required write authority. The prior prompt emphasized
current-user authority but did not explicitly prohibit citing older user text.

## Decision

State in the shared reviewer instruction that every proposal cites a current
user assertion or endorsement, earlier user turns are context only, and
revisions identify prior facts through the supplied fact ID and version.
A prior assistant referent remains citable only with explicit current-user
endorsement. Keep native source binding strict for all outcomes; do not remove
invalid citations after generation, reinterpret old authority, or special-case
one correction. Keep the separately named 4,096-token evaluation output
diagnostic, 6,759-token input limit, and pinned provider route unchanged.

## Consequences and guardrails

This changes the reviewer instruction hash, so iteration 3 is a separate
versioned diagnostic and cannot count toward the original frozen comparison.
A captured-shaped regression rejects the old-user citation and accepts the
current-only correction. Existing endorsement tests retain the assistant
referent path. Frozen pressure-packet tests guard the unchanged input bound.
The output-envelope diagnostic still needs explicit review before any future
qualification matrix amendment or product adoption.
