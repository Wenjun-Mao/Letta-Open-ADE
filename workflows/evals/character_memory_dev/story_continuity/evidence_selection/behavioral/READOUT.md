# D04 Behavioral Comparison: Reviewed AI Readout

Date: 2026-10-02. **All six planned requests captured and independently
manager-reviewed.** Initial assessor: Codex implementation worker, task
`01a0fd64-2a64-7a81-8f83-8e48c695c1d5`, **AI**. This is a manual, source-quoted,
exposed/non-blind assessment, not an independent human review. Reviewing assessor:
Codex manager, task `019db09f-a9e0-7d93-a8b8-7697d67ad5bc`, also **AI**. The manager
independently checked the original visible responses, requests, source ledger,
reviewer contract and private receipts; no separate human assessment is claimed.

In this single witness, literal-four correctly remained uncertain about the
missing location. Replacing its last redundant mistaken retelling with E01
produced a supported named answer; whole-pool also produced that answer. The
literal reviewer returned a source-bound ownership conflict about an optional
aside, not the missing-location uncertainty. Structural validity does not settle
the interpretation of that tentative aside.

## Frozen Source And Execution

The [prospective protocol](PROTOCOL.md), requests and preparation were committed
before outcomes at `ffaf24dab13a9b74b78339a600c032bf1adba899`, on clean `main`.
Manager continuation authorized this fixed pass after offline readiness review.
No frozen source, protocol, request, configuration or preparation was changed
during dispatch. Historical builders/artifacts and runtime admission remain intact.
PC-03/05/09/11 govern interpretation; PC-04/06/10 and the native turn-7 stop remain
unchanged. [ADR 0059](../../../../../../docs/adr/0059-bounded-d04-behavioral-comparison.md)
records the narrow exception, not a production policy change.

- Protocol exact-byte SHA-256:
  `f797eb0547244f3ba2dbc58d21dfa834185500a6c98b431d488b9466179a6067`.
- Frozen requests canonical-JSON SHA-256:
  `298932022e3f183ae7c201597c0b8927a2707bdbfc4b01737c48ae5eb0cf84e8`.
- [Redacted machine summary](results.json) retains exact source-head/input
  linkage, per-stage request hashes, original-body hashes, exact visible answers,
  parsed reviewer decisions and provider usage. Raw Model Router response bodies,
  provider reasoning, effective configuration,
  operator/process receipts and schema-binding audit remain privately ignored under
  `behavioral/outputs`; originals were preserved without repair or replacement.

Body hashes identify the captured Model Router HTTP bodies, not necessarily the
provider's original JSON serialization; the router can reserialize upstream JSON.

A new authenticated loopback Model Router process used only the frozen DeepSeek
source, reviewed profiles/manifest, designated existing repository-dotenv
`DEEPSEEK_API_KEY` binding, and 180-second upstream timeout. Effective settings,
secret precedence and loopback token binding were verified without exposing keys.
Startup discovery and fresh catalog confirmed the exact official route/adapter
and enabled/high profile. No retained service, ADE API/worker, database, embedding,
persistence or native continuation was used.

Exactly **six chat-completion intents and outcomes** were recorded: one generation
and one dependent reviewer per arm. All returned one usable visible choice with
`finish_reason=stop`, model `deepseek-flash`; no retry, repair, reroll or fallback.
Only final visible generation text entered its own reviewer, with identical H.
The isolated owned process exited after the final capture; its PID was absent and
its loopback port accepted no connection afterward. No other process was touched.

## Source-Quoted Interpretation

The question remained “你那晚看到木制风铃是在什么地方？”. Persona was neutral;
saved facts, related entities and local context were empty. Source authority is
the unchanged [frozen ledger](../../correction_dependencies/cases.json) and actual
H, not evaluator knowledge carried into a model request:

- E01: “那晚我独自散步，在旧书店门口看见一串木制风铃，风吹起来声音很轻。”
- E07: “我后来把那晚看到木制风铃的地方说错了：不是茶馆里，是最初说的那个地方，最初的说法才对。”
- E05 assistant: “茶馆里那串木制风铃的轻响，让我想起小时候用木片做的小玩具。”

### Literal-Four: E07, E02, E05, E04

Actual H2 contains E07; E01 is absent. H6 contains E05's assistant-owned childhood
association. The response states: “我手头保留的这些片段里**没有我更早那次的说法**”
and “我不想凭印象给你编一个地方。” It rejects the teahouse as the corrected mistake
without inventing the restored location.

- **Supported naming:** no restored location is named, as warranted by this packet.
- **Honest uncertainty:** explicitly identifies the missing antecedent. This is
  correct behavior under the frozen rubric, not failure because the answer is absent.
- **Unsupported/invented detail:** no invented location. The closing optional
  suggestion borrows E05's childhood-toy association: “比如它让你想到小时候的木片小玩具”.
  It shifts the suggested association to the user, but is phrased as an example in
  an invitation, not an unequivocal claim that the user made toys in the past.
- **Correction handling:** distinguishes the mistaken teahouse retelling from the
  unavailable restored location rather than electing the repeated mistaken claim.
- **Ownership:** the main location answer preserves assistant history. The optional
  aside creates a possible ownership ambiguity: source “让我想起” becomes suggested
  “让你想到”. Treat this separately from successful missing-location uncertainty.
- **Naturalness:** clear and helpful uncertainty, but a long evidence-accounting
  answer exposes “对话片段” and “已保存事实”; the toy-topic pivot is less direct than
  needed for the question. This is qualitative AI judgment under a neutral persona.
- **Reviewer interpretation:** returned one `conflict`, quoting the full closing
  invitation and exact H6/E05 assistant passage. Runtime schema/source binding
  validated that conflict's quotes and handle. It does not prove factual error or
  a necessary rejection: the reviewer instruction distinguishes new suggestions
  and tentative inferences from assertions of user past events. Whether this aside
  warrants conflict remains an interpretation question, not a keyword rule.

### Repaired-Four: E07, E02, E05, E01

E07 remains H2; E01 appears H8. The first three sources retain the same order and
count; only E04 is replaced. The visible answer begins “是旧书店门口。” and explains
“后来我一度说成是在茶馆里，那是我讲错了”.

- **Supported naming:** old-bookstore entrance is directly supported by E01 plus E07.
- **Honest uncertainty:** does not feign missing evidence once the antecedent is supplied.
- **Unsupported/invented detail:** the solo walk and quiet sound are present in E01;
  no additional established episode detail is asserted.
- **Correction handling:** explicitly acknowledges the mistaken teahouse retelling
  and restoration of the initial location.
- **Ownership:** “我独自散步” preserves the source's assistant solo experience.
- **Naturalness:** direct answer, followed by a short source-consistent explanation;
  the correction is somewhat formal but responsive to the conflicting packet.
- **Reviewer interpretation:** visible `{"decisions": []}` passed existing runtime
  schema/source binding. No-change is an observation, not a factual correctness or
  persistence certificate.

### Whole-Pool: E01–E08 In Original Chronology

E01 appears H2 and E07 H14. The answer begins “那晚看到木制风铃的地方是**旧书店门口**”
and states `后来我说成“茶馆里”，那是我说错了`.

- **Supported naming:** matches the restored E01 location, with both antecedent and
  correction available.
- **Honest uncertainty:** no unsupported uncertainty or missing-location invention.
- **Unsupported/invented detail:** no extra episode fact; the answer stays on location.
- **Correction handling:** explains restoration rather than following repeated teahouse claims.
- **Ownership:** maintains assistant first-person history and invents no user participation.
- **Naturalness:** concise and focused, with emphasis on the location and correction.
- **Reviewer interpretation:** visible `{"decisions":[]}` passed schema/source binding;
  it remains observational no-change rather than independent factual validation.

## Independent Manager Assessment

The manager agrees with the three source-quoted assessments above. E07 rejects
the repeated teahouse account but does not name the restored location; E01 supplies
that location in the repaired and whole-pool packets. Literal-four's uncertainty
is appropriate. The other two responses name the supported location without
inventing shared participation. This is one observation per arm, not a reliability
estimate or a reason to prefer eight sources as a runtime default.

The literal aside is an avoidable ownership ambiguity: E05's assistant association
becomes a suggested user association. The reviewer correctly binds the two quoted
passages, but its prompt also says: "Questions, new suggestions and explicitly
tentative inferences are not assertions that an event happened in the user's past."
The candidate's optional invitation is not an unambiguous assertion of such a past
event. The manager therefore does not treat this conflict as proof of a factual
ownership error, nor declare a definitive false positive. The assertion-versus-
suggestion interpretation remains a named open question; the prompt already
contains the distinction, so this observation does not justify a keyword rule,
second judge or speculative prompt repair.

A source-bound `conflict` would reject the candidate under the existing reviewer
contract. That is a contract implication, not observed native delivery: this pass
called generation and review separately, with no ADE worker or persistence.
Consequently, correct uncertainty at generation is not an end-to-end acceptance
claim. None of the six observations qualifies the native path.

## Capacity And Observed Usage

All actual complete reviewer requests fit without truncation. Estimates below use
complete serialized UTF-8 bytes divided by four and remain distinct from provider
token counts. The full candidate reserve was verified before launch. Both calls
kept their own 4096 output cap and enabled/high thinking fields.

| Arm | Generation estimate | Actual reviewer estimate | Full-reserve reviewer estimate |
| --- | ---: | ---: | ---: |
| Literal-four | 1669 | 5334 | 9200 |
| Repaired-four | 1680 | 5178 | 9211 |
| Whole-pool | 2424 | 5951 | 9993 |

| Arm / stage | Provider prompt tokens | Provider completion tokens | Provider total tokens | Intent-to-outcome seconds |
| --- | ---: | ---: | ---: | ---: |
| Literal / generation | 1672 | 747 | 2419 | 4.588 |
| Literal / reviewer | 5565 | 2917 | 8482 | 13.282 |
| Repaired / generation | 1682 | 236 | 1918 | 1.882 |
| Repaired / reviewer | 5434 | 3530 | 8964 | 16.720 |
| Whole / generation | 2664 | 197 | 2861 | 2.424 |
| Whole / reviewer | 6519 | 1606 | 8125 | 8.470 |

Usage is the captured provider report: **23536 prompt, 9233 completion, 32769 total
tokens**. Completion counts include reasoning; no reasoning text is included in
the published summary. Provider latency is unavailable. The timestamp intervals
include local transport/receipt/capture overhead and are **not provider latency** or a latency
comparison estimate. Provider prefix caching also differed across requests; no
prior answer was included in another arm's caller messages.

## Post-Run Verification

The runtime-owned offline schema/source-binding audit reported one source-bound
conflict and two valid no-change observations, with `execution_state=complete` and
no stop. Independent original-receipt checks confirmed six sends, exact reviewer
candidate substitution and shared H, published visible-output/usage equality, and
unchanged freeze hashes; the private verification receipt records original hashes.
The combined focused/historical suites passed **124 tests**. Repository Ruff lint,
authored whitespace and **58 local documentation links/anchors** passed. The plan
remains 499 lines. No tracked runtime/runner or frozen file was edited after launch;
only outcome and status documents changed. No persistence, database or
production verification was performed.

Manager verification independently reproduced the runtime schema/source-binding
audit, matched all six published observations and usage counts to original bodies,
checked all original receipt hashes, exact generation/reviewer H and candidate
substitution, source/configuration and fresh catalog bindings, and confirmed the
owned PID and listener were absent. Frozen inputs remain byte-identical to the
pre-outcome commit. The 124 focused/historical checks, Ruff and documentation checks
were rerun at publication review. The earlier broader readiness check remains
535 passed with 76 unavailable database/private-evidence skips; no such gap is
represented as live or native verification.

## Limits And Recommended Next Decision

One result per arm shows a source-availability gap and a successful restoration
witness; it cannot establish reliability, a population causal effect, production
retrieval quality, persistence or release qualification. Literal versus repaired
holds the other three sources/count/order fixed. Whole-pool differs in content and
ordering as well as count, so its result is not a pure count ablation.

Under PC-03/11, decide whether the next scoped work should define how retrieval
preserves an eligible correction together with its missing antecedent. This witness
supports investigating that source-recovery contract; it selects neither a larger
runtime default nor a new selector, episode store or service (PC-09). Maintain
honest uncertainty when the necessary evidence is absent.

Under PC-05, retain the literal reviewer disagreement as a named open question:
does the optional tentative toy suggestion warrant an ownership conflict? The
present binding audit cannot settle it. Do not introduce a second factual judge,
semantic keyword scorer or reviewer rewrite from this one observation. No further
experiment, reroll, provider call, native run or deployment is authorized by this
readout. Runtime count limits and the native turn-7 stop are unchanged.

**Follow-up recommendation: none.** Neither Pro nor Deep Research adds necessary
evidence for the immediate next decision: scope a correction-plus-antecedent
recovery contract from the observed source gap, with uncertainty retained when
support is unavailable. This is a proposed design step, not approval to implement
a selector or increase runtime limits. Reopen consultation if that bounded design
exposes materially competing recovery approaches or an interpretation dispute
that blocks adoption; do not commission another review merely because a single
observation leaves uncertainty.
