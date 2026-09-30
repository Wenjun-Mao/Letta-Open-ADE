# ADR 0049: Portable Offline Evidence Checks

Status: Accepted for test/evaluation separation, 2026-09-30. No product-policy
change, live-run approval or historical evidence requalification.

## Problem And Evidence

A full test run after integration into the clean primary checkout failed four
H4 checks because they loaded ignored historical outputs. The retained trial
checkout had those files, masking the dependency. Another test expected frozen
candidate deployment hashes to equal current policy even though changed source
had deliberately not been rebound or qualified.

These are test/evidence contract mismatches, not reasons to copy private captures
into every checkout, fabricate historical receipts or refresh release evidence.

## Decision

Separate loading the tracked H4 contract/schedule from loading exact historical
H2 results. Portable schedule tests use explicitly synthetic campaign states and
exercise dependency/exclusion mutations. Historical replay tests additionally run
when their private source files exist; if present but altered, they still fail.
Live loaders still require the original exact artifact hashes and never fall
back to synthetic data. Missing/corrupt evidence rejection is tested offline.

Candidate-policy tests reflect the retained, unqualified historical binding and
exercise release rejection rather than requiring an automatic rebind. Existing
stale-policy and historical-release rejection checks remain in place.

## Consequences And Alternatives

A clean checkout verifies mechanics without claiming historical replay coverage.
Reports must identify historical-evidence skips separately from database skips.
Reject blanket skipping of the failing tests, weakening loader checks, silently
relabeling old evidence, or tracking private outputs just to make CI green.
