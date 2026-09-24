# Natural Memory Reviewer Responsibility Assessment

Date: 2026-09-24. Status: director review requested; no implementation decision
promoted. Revision `845b08b` is the committed baseline. A later, uncommitted
Mandarin omitted-object guard, focused tests and fake-router script remain in the
worktree as provisional evidence. No provider calls, push or release occurred.

## Responsibility Boundary

ADE should deterministically enforce the closed review shape, exact current and
support quote binding, permitted source roles and chronology, subject and held
F/E handles, target status/version, current run authority, generation fencing,
readback integrity and atomic commit or rejection. Those checks do not require
ADE to decide what a natural sentence means. The reviewer should interpret the
user's factual update, its scope and temporal meaning, and whether a candidate
reply contradicts known memory. The current single-reviewer contract and the
complete-delta fixtures remain the starting point; no second judge is proposed.

No-save and withdrawal instructions remain safety requirements. ADE should keep
unambiguous, claim-bound protections and fail closed on invalid evidence. Their
semantics should be a secondary guardrail, not the organizing task or a growing
phrase catalogue. Deciding which earlier claim an omitted object refers to,
whether a short answer renews consent, or whether two paraphrases assert the
same preference is interpretation. The pending `别保存` prototype shows that a
rule can close one gap while still leaving that boundary unresolved.

## Current Semantic Heuristics And Risks

| Validator | Interpretation it currently attempts | Material risk |
| --- | --- | --- |
| `_claim_is_uncertain`, `_NO_SAVE`, `_WITHDRAWN` and `_preceding_claim_restriction` | Infer uncertainty, restriction and the preceding claim from clause markers | Miss natural omissions or paraphrases; attach a restriction to the wrong nearby claim |
| `_value_supported` in authority and restriction checks | Treat token inclusion as factual support or claim equivalence | Permit a negated or quoted value; reject a valid paraphrase or a scoped correction |
| `_AFFIRMATIVE`, `_NEGATED`, one-question/`or` test | Decide whether current text endorses one assistant proposition | Treat a casual assent as durable authority, or reject a clear multi-sentence clarification |
| `_fresh_current_assertion` and `_explicit_save_change` | Decide when a current sentence renews an earlier assertion or saving intent | Mistake an unrelated clause for authorization, or veto a genuine fresh correction |
| `_candidate_agrees_with_reference` | Infer agreement from a contained snapshot value | Miss negation, quotation, time change or a conflicting second clause |

These rules have useful named regression guards, but passing synthetic fixtures
does not establish semantic entailment or reviewer reliability. Do not keep
adding regex branches as though coverage proves humanlike continuity.

The provisional local browser replay used an isolated PostgreSQL subject per
journey, the real UI/API/worker, and a loopback scripted router. In one journey,
a same-turn coffee plus omitted-object no-save proposal failed atomically; a
later independent Toronto assertion committed. In the other, a no-save deferral
and assistant question preceded an attempted coffee endorsement plus Toronto;
that combined attempt failed, then Toronto alone committed. Both subjects ended
at generation 2 with exactly one active Toronto fact and no coffee fact. The
private receipt is
`workflows/evals/character_memory_dev/outputs/natural-browser-20260924-authority-zh/browser-evidence.json`.
This is prototype integration evidence, not natural reviewer evidence.

## Factual Continuity Priority

The next evaluation should center natural updates and recall. Given a saved
morning-coffee preference, `最近喝咖啡总睡不着，早上也改喝茶了` supports a scoped morning
change to tea, with the prior coffee revision retained. It does not establish
an all-day dislike of coffee. A follow-up question about the morning drink should
recall tea and, where relevant, the former coffee preference without inventing a
broader aversion. The sleep observation alone need not become a drink-preference
mutation.

Freeze paired positive and negative multi-turn cases before live evaluation:

| Exchange after morning coffee | Expected memory and reply behavior |
| --- | --- |
| `最近喝咖啡总睡不着，早上也改喝茶了` | Supersede morning coffee with morning tea; preserve history; later recall morning tea |
| `早上还是喝咖啡，晚上改喝茶了` | Keep morning coffee; add evening tea only |
| `可能早上改喝茶吧` | No definite morning revision; reply can discuss uncertainty |
| `咖啡让我睡不着` | Do not infer an all-day dislike or a definite morning switch |
| `不是早上改喝茶，是晚上` | Correct the scope to evening; morning coffee remains |
| `早上改喝茶了` followed by `我早上现在喝什么？` | Recall current morning tea, with no invented coffee ban |

Use the existing fact/revision/source model and one mixed review. Measure
complete deltas, retained history, false vetoes, unsupported saves, answer
usefulness and recall over natural phrasing. Fake responses can test integration
mechanics only; real model reliability remains unmeasured and separately gated.

## Smallest Next Decision

Pause the uncommitted phrase-rule expansion. Keep structural validators and
atomic persistence unchanged. Review whether the remaining semantic heuristics
should be narrowed to unambiguous safety guards while the reviewer owns scoped
factual interpretation; do not weaken privacy checks or replace them with silent
acceptance. Any simplification needs paired false-accept and false-reject tests
and a named contract amendment before code changes. The provisional Mandarin
patch and private browser readback are retained for that review, not accepted as
proof of a general language rule.
