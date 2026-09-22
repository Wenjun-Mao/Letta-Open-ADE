# ADR 0021: Evidence-Scoped Memory Confidence And Affirmative Tool Requirements

- Status: Accepted
- Date: 2026-09-22

## Context

The native runtime blocked a supported memory proposal when any uncertainty
substring appeared anywhere in the current user message. It therefore rejected
names such as `Mighty` and definite facts beside an unrelated hypothetical. Its
free-form tool detector likewise forced a call when capability/action keywords
occurred in an explicit opt-out such as “don't search memory.” Both decisions
were made before model execution, so the defects altered the runtime contract.

## Decision

Memory confidence is evaluated in the clause containing the uniquely bound
user-evidence span. English uncertainty markers are word-aware; Chinese markers
remain phrase markers. A cited uncertain claim is still rejected, while an
unrelated clause cannot veto a supported fact. Evidence remains user-authored,
unique, source-bound, and value-supporting.

A curated tool becomes required only when a matched action phrase is
affirmative in its local clause. Direct English and Chinese negation suppresses
the requirement, and the capability must occur in that same clause. An unrelated
action in another clause cannot override an opt-out; ambiguity remains
discretionary. The executor still requires a
corresponding tool result before a response can claim a call or its success.

## Consequences

These are bounded deterministic language checks, not semantic understanding.
They do not make Luna dialogue evidence of native persistence, retrieval, or
provider tool behavior. The governed runtime source digest changes, so existing
release evidence is intentionally stale until native qualification and review
are repeated. No release fingerprint is rebound or promoted in this milestone.
