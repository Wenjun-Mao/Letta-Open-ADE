# Capability Boundary Cleanup: Consultation Assessment

Status: Review integration, 2026-10-08. The revised
[cleanup plan](../../plans/capability-boundary-cleanup.md) remains proposed; this
assessment does not authorize implementation or adopt a replacement architecture.
PC-04/05/08/09/12 and the existing product exclusions remain unchanged.

## Outcome

Retain A1 -> A3 -> A2 -> A4. The reports support the existing approach rather than
a broader refactor. Their useful additions are a sharper A4 ownership boundary,
stronger but bounded A2 characterization/rollback checks, and fewer unrelated
verification gates. Source inspection supports these refinements; neither report
nor this assessment measures maintenance benefit or proves behavior preservation.

Preserved verbatim, in attachment order:

| Report | SHA-256 of supplied text and retained copy |
| --- | --- |
| [A](reports/pro-review-a-2026-10-08.md) | `e70e8a8a2b002b7323fb2f23fd3a110fa2d980455d74b6d5d0cf2f680920f5c8` |
| [B](reports/pro-review-b-2026-10-08.md) | `a361b8c5d7d5f1d38f872b26ff02b654fe0fd28ed316e491a3eb6f4c9a9ff472` |

Both identify reviewed commit `74e993a9b4d50cc367778392aab71937f5b541ff`.
They report pinned GitHub connector access but not successful anonymous browser
access. Neither ran tests or inspected private runtime evidence. Agreement is not
independent verification, and independence of the two review processes is not
established by the supplied text. Our local checks below used that same commit,
clean at entry. Unchanged report text is separate from our interpretation here.

## Insight Dispositions

`Use` means incorporate into the proposed plan, not implement now. `Test` means
verify the stated invariant during an approved implementation; it is not a result.

| Insight | Disposition | Reason and integration |
| --- | --- | --- |
| Both: keep the sequence and internal protocol/lifecycle boundaries, not a generic replacement API. | Use | Existing call sites support the modest A2 split; A4 remains a bounded extraction with a retain-controller fallback. No new milestone. |
| Both: monitor lifetime is distinct from displayed run/event state. | Use | Acceptance, cancellation and refresh legitimately update displayed state. Keep one controller-owned copy; monitor owns resources, active identity, terminal latch and disposal. |
| Both: preserve separate selection/read lifetimes and guarded callbacks; B highlights the selection effect's dependency on stable `stopMonitoring`. | Use / Test | Prevent duplicate authority, A -> B -> A stale updates, post-await callback mutations and unrelated-render resets. Add focused async cases, not a second epoch system. |
| Both: exact compaction fixtures should not assert only hash length or recompute all expectations with production helpers. | Use / Test | Two independently specified adapter fixtures plus small parser/usage/error cases; each branch preserves its own baseline, not equality between adapters. |
| A: reject a prepared summary before finalization; B: fail after real summary SQL writes are staged. | Test, selecting B's late fault | One existing-fixture extension exercises actual rollback. Do not require both suggestions as separate new campaigns; rationale below. |
| B: request composition does not make Memory the owner of characterization; compaction still uses the conversation deployment/adapter. | Use | Clarify the boundary sketch without new interfaces, model roles or a portable persona schema. |
| B: retention prose mentions compaction after generation; A1 assertion must examine consumers. | Use | Correct the planned A3 wording and A1 acceptance. Do not demand that execution stop importing a type it uses. |
| Both: keep SQL/browser evidence relevant and make unchanged diagram suites conditional. | Use | Reduced A1 slice checks, one browser wiring smoke, deterministic race tests, conditional journey checks. Required missing checks still remain pending. |
| Future portable persona/state schemas, vendor adapters and external-write consistency. | Park | No concrete replacement integration is selected. Preserve constraints without freezing speculative contracts. |
| Mirrored monitor state, generalized dispatch helpers, duplicate construction harnesses or an automatic additional consultation round. | Discard as additions | These are implementation traps or unnecessary work, not capabilities requested by this cleanup. Both reports caution against them. |

## Source Checks And Limits

Locators below are pinned to the reviewed revision, not changing local line numbers.
Only claims needed for revision 2 were checked; this is not a renewed full audit.

- [Controller](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/apps/ade-web/src/features/agent-studio/use-agent-studio.ts): `refreshSelected`, `sendMessage` and `cancelActiveRun` write displayed run state. `finishRun` and `monitorRun` capture selection identity/epoch; selected reads have another epoch. The selection-reset effect depends on `stopMonitoring`. These support an extraction risk, not a diagnosed current regression.
- [Memory action outcome](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/apps/ade-web/src/features/agent-studio/memory-action.ts): confirmation requires both a matching committed event and refreshed revision. A null readback is not success evidence; keep this interpretation outside monitoring mechanics.
- [Executor](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/src/ade_api/features/agent_runtime/executor.py): generation awaits authorization and suppresses request-observer exceptions; compaction calls its observer directly. Preserve these differences and response message fields when moving common mechanics.
- [Turn execution](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py) constructs separately traced executors with the same conversation deployment/adapter. [Context](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/src/ade_api/features/agent_runtime/context.py), especially `_mandatory_prompt`, combines bound persona/prompt content and ADE-wide instructions; this is not Memory authoring a persona.
- [Inventory](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/docs/architecture/capability-map/inventory.json) retention step says "Generate candidate reply; prepare compaction only when needed". A3 should clarify pre-generation timing without changing topology or status.
- [Compaction tests](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/tests/agent_runtime/test_compaction.py) cover both adapters but assert selected request fields and several hash lengths. Some hashes already have content-based checks; the gap is complete independent expected payload/provenance, not absence of all hash verification.
- [Packet SQL test](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_compaction_packets.py) seeds long history, runs a synthetic-provider real worker, checks persisted summaries/sources and compaction traces, and excludes B compaction. [Fencing SQL tests](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_worker_fencing.py) use fresh conversations; `faulty_commit` raises before or after the original finalizer rather than inside its transaction. These source observations identify a gap in these suites, not proof of a repository-wide absence of rollback coverage.
- [Async UI tests](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/apps/ade-web/src/features/agent-studio/use-agent-studio.async.test.tsx) include stale acceptance/stream/read rejection and same-conversation evidence navigation. Additional controlled poll/completion, retry, cleanup and callback-stability cases should stay connected to the existing controller, not only the extracted hook.

No runtime tests, SQL connections, browser sessions or live provider calls were
made for this assessment. Prospective race scenarios remain tests to implement;
do not silently strengthen scheduling or read-error behavior under a cleanup label.

Documentation checks resolved nine local links and eleven pinned source paths,
and verified both report copies and recorded hashes against the attachments.
Authored plan/assessment whitespace checks pass. The preserved reports retain
their original trailing spaces, the only exception to the full diff whitespace
check; normalizing them would violate verbatim preservation.

## Resolve The Rollback Difference

Reports A and B identify related but different checks. Rejecting an attempt before
the success transaction verifies that prepared output is not eagerly persisted.
It does not show rollback after SQL writes have begun. A synthetic failure after
the real `create_compaction` stages summary/source rows exercises that stronger
property on the existing success path.

[RunFinalizer.commit_success](https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/74e993a9b4d50cc367778392aab71937f5b541ff/services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py)
opens one transaction, applies memory changes, appends the assistant, creates any
compaction, advances the conversation, marks success, appends events and releases
the lease. A test-only wrapper that awaits the real compaction write then raises
can fail inside this transaction without adding a production fault-injection API.
The fixture must confirm the fault point was reached and prevent an automatic
retry from converting this negative case into a later success.

Select one such case alongside existing success/fencing tests, using the existing
seeded fixture. Read authoritative state on a new connection: no new attempted
summary/source bundle, assistant, memory/index changes, conversation-version
advance or success events. Prior history and the accepted user message remain;
failed-run/attempt metadata is allowed. This is a small additional guard on a
protected invariant, not a finding that rollback is broken or a requirement for a
full policy-by-fault matrix. A4 does not block retaining earlier verified slices.

## Follow-Up Recommendation

**None.** Direct source inspection resolves the useful differences, and the
remaining uncertainty concerns the concrete extraction and its regression tests.
Review revision 2, then implement only after user approval. No additional research,
reviewer, replacement-design phase or live experiment is needed first. Reopen
consultation only if a concrete integration or implementation exposes a material
authority/contract choice that bounded local work cannot adequately resolve.
