# ADR 0056: Matched Correction-Dependency Measurement

Status: Accepted for the user-approved bounded offline measurement, 2026-09-30.
No production runtime change, provider call, database access or native qualification.

## Problem And Evidence

The packet-sufficiency diagnostic's C01 admitted a reference-dependent correction
without its named-day antecedent in the baseline; the candidate admitted neither.
All packets fit, so selection, not token capacity, caused the observed omission.
C06's varied retellings showed useful novelty recovery but no dependency guarantee.
One authored case does not establish how this limitation repeats.

The user approved the correction-dependency plan and requested Relay-directed
implementation. This permits internal technical delegation, not another external
semantic review or a restart of the closed native sequence.

## Decision

Freeze exactly three new episode pairs before any scoring: self-contained versus
antecedent-dependent correction, changing only the correction's assistant text.
Use one archived synthetic conversation per case, with eight ordered complete
windows and a fresh current chat. Unlike the old separate-chat audit, this makes
the original a declared antecedent in the same dialogue. Keep that topology
explicit, not disguised as observed reader behavior.

Use source-quoted non-blind author-agent judgments and deletion challenges;
earlier Pro reports are rubric context, not annotations or endorsements of new
cases. Commit/push the input and label freeze before comparing unchanged literal
selectors and real request/admission builders. Preserve old artifacts exactly.

Separate named-answer alternatives, absent correction, dangling reference,
resolved dependency, correction explanation, mistaken-retelling visibility and
optional/unrelated admissions. Original-only answer support does not require the
correction merely to improve a coverage metric. Reference packets are evaluator
aids, never selector inputs. A repeat in at least two matched episode pairs is
only an investment trigger for proposing a bounded design, not a reliability
threshold, statistical claim, selector adoption or implementation authority.

## Alternatives And Guardrails

Reject another broad review, a larger mixed benchmark, automatic origin priority,
more slots or a new semantic selector before measuring this question. Do not tune
wording against results or force an ambiguous restoration into a resolved label.
Lexical wording differences and author exposure remain explicit study limitations.

Workflow input/label loaders remain standard-library-only. Reuse only narrow
runtime-owned packet mechanics in service tests, keeping old frozen labels and
artifact writers separate. Tests bind pair invariants, quotes, hashes, history
roles/handles, conversation order, real budgets and exact regeneration. No API,
provider, database, runtime prompt or persistence change is part of the work.
PC-01/03/04/05/06/09/10/11 and ADR 0055's historical report provenance are unchanged.
