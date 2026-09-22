# M1 Character-Continuity Baseline Plan

Status: Complete (implementation baseline; native release requalification pending)

## Goal

Establish a compact, reviewable baseline for `chat_linxiaotang` in everyday
Chinese companionship, repair the two confirmed deterministic policy defects,
and leave M2 with comparable cases rather than a presumed memory architecture.

## Work

1. Reproduce the memory uncertainty and tool-negation failures in native unit
   contracts; replace whole-message/keyword classification with evidence- and
   action-scoped checks.
2. Run the checked-in synthetic cases through the existing serial Luna workflow:
   preferences, concern follow-up, promise/shared conversation, correction,
   forgetting, supplied-memory isolation, irrelevant memory, repetition, and
   two source-linked memory-review cases.
3. Inspect the saved outputs manually, record excerpts and failure attribution,
   and keep in-context findings separate from ADE persistence and qualification.
4. Run focused, full Python, lint, formatting, and diff checks. Do not rebind
   policy hashes, promote release evidence, use Spark, or add a memory service.

## Completion Boundary

M1 is implementation- and baseline-complete: the report records actual outputs,
limitations, release-evidence invalidation, and M2 comparison requirements.
Native deployment qualification remains pending provider access.
