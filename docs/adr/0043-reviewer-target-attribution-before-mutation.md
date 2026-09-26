# ADR 0043: Reviewer Target Attribution Before Mutation

Status: Accepted for the bounded diagnostic on 2026-09-26 after director
offline review. No live semantic acceptance, production history policy, or
release qualification.

## Problem

In H4's `h_only_referent` automatic trajectory, the current user said only
“它现在叫小黑。” with two plausible held dogs, Roxy and Nini. The reviewer
revised Roxy before clarification. ADE correctly bound an exact current quote
and a held active F target, but neither structural condition established which
dog the pronoun identified. The missing condition belongs to the one reviewer's
meaning and target-selection contract (PC-05), not to source, version, subject,
or atomicity validation. H is read-only testimony under ADR 0039.

An independent Pro review of the published H5 evidence packet advised against
safe-persistence/default acceptance. In attributed summary, it treated the
early Roxy write as an unsupported referent selection; later Roxy clarification
supports the final name but cannot justify the earlier write. It treated the
later no-op as part of that same trajectory, the empty arm's longer exact quote
as valid, and the removed-tea followup as a fresh preference rather than a
revival of the forgotten record. This is independent AI advice, not human
acceptance or a verbatim reproduction of the report.

## Decision

The model-facing natural reviewer instruction and target/defer schema descriptions
now require evidence for both the asserted change and attachment to the intended
entity or fact. A held target plus an exact quote is insufficient when materially
plausible alternatives remain. The reviewer should clarify and defer the write;
history may inform the clarification. Explicit updates and clear references
remain eligible for immediate writes. The existing instruction that removal
does not erase retained dialogue continues to govern historical testimony
(PC-07, PC-10).

## Alternatives, consequences, and guardrails

Rejected phrase matching, target-guess rules, a second judge, and a global
semantic validator: none can reliably establish an ambiguous referent while
preserving PC-06/09. ADE's structural binding and atomic commit rules remain
unchanged. The revised wire wording changes the source fingerprint and requires
fresh offline serialization and disposable-PostgreSQL checks before a bounded
live diagnostic. Fake-provider tests show mechanics, not model semantics.
The historical failing policy-freshness release gate remains unwaived. Original
H4 fixtures, scorers, and capture hashes remain immutable.
