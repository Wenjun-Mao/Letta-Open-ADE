# Historical Recall Revision 2: Review Assessment

Date: 2026-09-25. Status: source-checked assessment, not implementation approval.
Both reviewers inspected `8e298881e4165128c5a680a0b02c1789c894d8ff`; the relevant
runtime/scorer code remains unchanged at this assessment. Neither reviewer ran
tests, providers or databases. Constructed dialogues are not observed failures.

## Recommendation

Make one small plan amendment, then seek approval for the bounded checkpoints.
No architecture redesign or additional experimental arm is warranted. The reports
are conditional go recommendations, not acceptance of implemented behavior.
Reader and ranking work need not wait for general reviewer reliability.

Two conditions need explicit wording before their respective checkpoints:

1. **H1: memory repair is not user retraction.** Lifecycle codes describe changes
   to saved representations. A `correct` revision does not establish that the
   original utterance was false or that the user changed their account. If ADE
   dropped "morning" from a correctly scoped source, fixing the fact must not
   rewrite the story as "you first said all day." The content and scope of a
   correction require admitted evidence; transition metadata alone supplies neither.
2. **H3: bound the new finalization history read.** Carry the successful attempt's
   absolute monotonic deadline into the required source-validation step, with a
   bounded remaining-time wait and fatal pre-commit failure on expiry. Do not move
   finalization into generation retries or claim this alone bounds every existing
   finalizer operation. Preserve authoritative success after commit/acknowledgment loss.

The rest are implementation/test criteria within the existing scope, not new
product features. Another broad Pro round is unnecessary unless the amendment
introduces a material unresolved contract change. No implementation starts merely
because consultants recommend proceeding.

## Preserved Reports

Original files are byte-identical to the supplied attachments:

| Report | SHA-256 |
| --- | --- |
| [Product semantics](history-recall-r2-pro-product-report.md) | `9d7c9a26a63b23114e6ab7dcc204ef2b9ea934ca7bbbcfcab41f46abdb44e843` |
| [Architecture](history-recall-r2-pro-architecture-report.md) | `a3b03c66e105713711ee6905866194c9c72aa554abe1405d657a66c0bde78e3f` |

## Verified Claims And Disposition

`Use` means incorporate into the plan/checkpoint criteria, not implement now.

| Disposition | Finding, verification and bounded response |
| --- | --- |
| Use | [NaturalRevise](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py) changes a target fact, not immutable testimony. Add extraction-repair versus user-retraction contrasts; do not infer missing corrective content from reason codes. |
| Use | [worker_control.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_control.py) creates the deadline inside `execute_attempt`; [worker.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker.py) calls [commit_success](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py) afterward, outside retries, without passing it. Test expiry of the new source check with no reply/revision commit or repeated provider dispatch. This is a real integration gap, not an observed hanging history run. |
| Use | [natural_memory_commit.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_commit.py) revalidates mutation sources per operation and returns early from mutation commit for no operations. Keep admitted-history identities independently in the attempt result and validate them even when `decisions: []`. |
| Use | [natural_memory_reviewer.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py) deliberately ignores observation callback failures. Required source checks must be awaited fatal guards, not observation callbacks or tools. Apply before existing generator continuations and reviewer calls as well as the first request. |
| Use | Source-bearing embedding requests need the same outbound check. Only admitted reply evidence becomes a finalization dependency, not every unused ranking candidate. Preserve the bounded check/dispatch race guarantee; no long-held source locks. |
| Use | [turn_execution.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py) may compact A/A0 at target time; B skips compaction. Freeze one recipe with no fresh target compaction, or equivalent pre-existing summaries, and compare actual base packets. B is a simple probe choice, not a selected production default. |
| Use | [natural_live_results.py](../../../workflows/evals/character_memory_dev/natural_live_results.py) rejects zero revisions in mutation-specific scoring. Reuse orchestration/structural readback, not that assumption: a correct committed recall with no writes can succeed; unintended extra writes must fail. |
| Use | Preserve mandatory snapshot material on recoverable optional-read failure; do not reload a newer state silently. Test snapshot exclusion with a concurrently committed exchange that has no memory mutation, so generation fencing cannot mask a transcript bug. |
| Use | Represent source-relative lineage as bounded deduplicated revision records/edges, not enumerated path timelines or a graph framework. Omit when the required envelope cannot fit. |
| Use | Keep final actual reviewer-packet capacity checking: the current candidate reserve is an estimate. Overflow is a recorded failure, not permission to strip exposed history or add repair. |
| Use | Score safe incompleteness separately from adequate recall. Zero writes is correct for historical acknowledgment, but not a universal desired result when a fresh supported assertion should update memory. |
| Test | Whether acknowledgment/restatement, clarification, habits, resolutions, ambiguity and callbacks work across turns. Retain each turn's actual history packet to distinguish repeated history support from local-only follow-up support. |
| Park | Discretionary retrieval, preview/read separation, indexes/backfill and broad timeout/executor redesign. Only reopen for a demonstrated need or actual blocking dependency. |
| Discard | Interpreting lifecycle codes as proof of user retraction, consultants' go verdicts as implementation evidence, or structurally valid provenance as proof of semantic correctness. No new phrase rules, topic restrictions, reviewers or evidence modes. |

## Next Amendment And Verification

Update the [existing plan](../../plans/natural-history-recall.md), not a new plan.
Put the two conditions in the relevant contracts and H1/H3 acceptance criteria;
incorporate the bounded packet, no-write, ranking and scoring tests in existing
checkpoints. Keep accepted product agreements unchanged and original reports intact.

This assessment used code inspection, byte comparisons and documentation checks.
No tests, provider calls, implementation, binding changes or promotion occurred.
The current plan remains revision 2 pending that amendment and user approval.
