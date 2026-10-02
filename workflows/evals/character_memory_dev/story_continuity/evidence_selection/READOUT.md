# Offline Packet Capacity And Qualification Readout

Date: 2026-10-02. **Measurement complete; implementation/results independently
manager-reviewed.** Under unchanged budgets, D04's complete eight-exchange pool
fits both fresh downstream requests, including the full candidate-reply reserve.
Four-window compression is not required by these budgets for this short fixture.
The prospective rubric also distinguishes answer availability from warranted
certainty without rewriting historical labels. PC-03/04/05/06/09/10/11 remain
unchanged. No provider/model or database call was made; native turn 7 remains the
stop. This is offline counterfactual capacity, not runtime admission or continuity
qualification.

## Freeze And Reproducible Evidence

The [protocol](OFFLINE_PROTOCOL.md) was committed and pushed **before** constructing
the new eight-source request, at
`62d461d4e2b6939fc8dff2fff9309c1f542f9189`. Its exact-byte SHA-256 is
`4de8c8ad2e7ff4142bbb3b9550965d9338782a0bb8a28ee9920dcda2cec59521`.
The [receipt](offline_capacity.json) binds that commit/byte hash, the unchanged
correction-study manifest and artifacts, and execution-source hashes. The
[packet file](offline_packets.jsonl) SHA-256 is
`30e42a17b021531e3a0f5ae47f52d2de850619986eab022e03234609dae89cdf`.
[Reproduction commands](README.md#reproduction-and-outputs) use the locked workspace.

Exactly the eight predeclared rows were constructed. The unchanged D04 literal
ranker still returns E07, E02, E05, E04. The sole exception calls the existing
runtime history renderer with E01 through E08 in original chronology; it never
changes admission/ranker constants. Seven ordinary controls match historical
generation and synthetic-reviewer requests byte-for-byte, with equal estimates.

## Complete Request Capacity

All numbers below are the runtime's serialized UTF-8-byte/4 estimates, not measured
provider tokens. Generation input limit remains **11,213**; reviewer input limit
remains **11,469**. Both requests retain their own **4,096** output reserves. The
reviewer estimate additionally includes **16,384 ASCII `x` characters** for the
future candidate reply, reserving 4,096 estimated input tokens. The suffix ceiling
remains 640; saved facts, entities and local context are empty. The serializer uses
`deepseek::deepseek-flash` / `deepseek_openai`; this is not a deployment verification.

| Packet | Included complete exchanges | Generation estimate / headroom | Full-reserve reviewer estimate / headroom | Synthetic reviewer estimate | Overflow / fit |
| --- | --- | --- | --- | --- | --- |
| D04/empty | 0 | 879 / 10,334 | 8,396 / 3,073 | 4,315 | 0 / both fit |
| D04/literal-four | 4 | 1,655 / 9,558 | 9,200 / 2,269 | 5,119 | 0 / both fit |
| D04/whole-pool | 8 | 2,410 / 8,803 | 9,993 / 1,476 | 5,912 | 0 / both fit |
| D02/empty | 0 | 879 / 10,334 | 8,396 / 3,073 | 4,315 | 0 / both fit |
| D02/original | 1 | 1,079 / 10,134 | 8,595 / 2,874 | 4,515 | 0 / both fit |
| D02/competing | 2 | 1,267 / 9,946 | 8,793 / 2,676 | 4,712 | 0 / both fit |
| D02/restored | 2 | 1,288 / 9,925 | 8,814 / 2,655 | 4,734 | 0 / both fit |
| D02/neighborhood | 4 | 1,635 / 9,578 | 9,180 / 2,289 | 5,099 | 0 / both fit |

The whole pool adds 755 generation and 793 full-reserve reviewer estimated tokens
over literal-four. The reviewer is the tighter consumer, with 1,476 tokens left.
There was no pruning, truncation, shortened exchange or increased budget. All 16
D04 messages reach generation and both retained reviewer payloads with equal H.
The synthetic reviewer alone would understate the binding request by 4,081 tokens
for this row; its 5,557-token headroom is not the capacity conclusion.

Each receipt maps original message IDs/sequences to H handles and checks run,
conversation, prior version, archive status, U/A roles, text hashes and timestamps.
H retains the established exchange identities and per-message handles/content/
hash/timestamp; original message IDs and within-chat sequence remain receipt-only.
Same-workspace/subject/character-root eligibility and version lineage are frozen
synthetic assumptions, not database observations. No evaluator topology or labels
are inserted into model payloads. The requests and their hashes remain inspectable.

## Source-Grounded Whole-Packet Interpretation

These are exposed, non-blind author interpretations of the full frozen ledger and
actual final H. They are prospective rubric witnesses, not independent annotations
or observed model responses. The semantic rubric records available answer, visible
competition, necessary qualification, permissible answer status, and separate
correction/dependency/irrelevance/capacity observations. It supplies no keyword
engine, chronology-based truth election or aggregate quality score.

D02 asks: “你在公交站捡到银色书签是在周几？” Complete assistant passages in the
[frozen source ledger](../correction_dependencies/cases.json) are:

- E01: “那是周一下班后，我独自在公交站等车时捡到一枚银色书签。”
- E02: “公交站捡到银色书签是在周三，下班等车时看见的。”
- E03: “我下班经过公交站，在周三捡起那枚银色书签。”
- E04: “银色书签是周三在公交站捡到的，我当时刚下班。”
- E07: “我后来把公交站捡到银色书签的日期说错了：不是周三，是最初说的那天，最初的说法才对。”

| Actual D02 packet | Delivered assistant handles and available meaning | Competition / ledger qualification | Permissible answer status |
| --- | --- | --- | --- |
| Empty | H is empty; no historical weekday delivered. | E01/E07 remain evaluator-only; absence does not preserve competing evidence. | Historical answer unavailable. |
| Original | H2 is E01: Monday. | The ledger's E07 restores this same value. Omitting its explanation does not make Monday wrong here. | Settled Monday supported; correction explanation unavailable. |
| Competing | H2 is E01/Monday; H4 is E02/Wednesday. | E07 resolves the ledger but is omitted from H. Consumers cannot receive credit for it. | Qualified/uncertain weekday answer only. |
| Restored | H2 is E01/Monday; H4 is E07 rejecting Wednesday and restoring the original. | Restoration and antecedent are both delivered. | Settled Monday and correction explanation supported. |
| Neighborhood | H2 is E02/Wednesday; H4 is E01/Monday; H6/H8 are E03/E04/Wednesday. | E07 is absent; three repetitions do not settle competing accounts. | Qualified/uncertain weekday answer only. |

The unchanged historical `named_answer_supported` is true for all four nonempty
D02 rows. Its monotonic inclusion arithmetic is correct; it cannot distinguish
the warranted statuses above. Historical `unresolved` remains its full-ledger
annotation, not a subset adjudication. Neither field is renamed or redefined.
This clarifies the assessment contract rather than patching runtime truth rules.
An earliest-statement rule would fail a genuinely corrected-original case, and an
ambiguous referent requires material alternatives. N01/N02 are still uncreated;
these witnesses establish neither broader rubric calibration nor behavioral gains.

D04 asks: “你那晚看到木制风铃是在什么地方？” E01 says
“那晚我独自散步，在旧书店门口看见一串木制风铃，风吹起来声音很轻。”
E07 says “我后来把那晚看到木制风铃的地方说错了：不是茶馆里，是最初说的那个地方，最初的说法才对。”
The literal-four packet delivers E07 at H2, but not E01: it can reject the teahouse
account without recovering the restored location. Whole-pool delivers E01 at H2
and E07 at H14, preserving the antecedent and restoration alongside the mistaken
retellings. The actual H therefore removes this known source-availability gap.
E08 remains an unrelated desk-organizing exchange at H15/H16, illustrating that
complete coverage need not mean every source is relevant. This is a semantic
source reading, not proof that generation or review will interpret it correctly.

## Recommendation And Remaining Decision

Defer the selector runner unless compactness has a separately important benefit.
This fixture does not need four-source compression to fit the approved budgets;
its known missing antecedent can be delivered intact. Retain the runtime four-window
ceiling, H contract, historical artifacts and native stop. Any larger runtime
packet, behavioral evidence-restoration test, retrieval expansion or selector
campaign needs a separate decision and authorization. If selector investigation
later continues, use whole-packet qualification judgments and decide its planned
N01/N02 controls and continuation criterion before implementation; this slice does
not adopt B's stronger new-case gate.

**Follow-up consultation recommendation: none.** The local measurement resolves
the capacity uncertainty; another Pro or Deep Research round adds no concrete
contribution to this decision. The next step is a separate decision on whether
actual behavioral evidence is needed before choosing a retrieval repair. Reopen
Pro for a concrete consequential disagreement over a qualification or experiment
contract; reopen Deep Research if production candidate retrieval presents an
external-method question that local source inspection cannot resolve. Neither is
needed now, and no consultant dispatch is authorized by this recommendation.

## Verification And Limits

Focused mechanics tests cover exact artifact/hash reproduction, all-source and
shared-H preservation, historical byte parity, no mutation or metadata leakage,
freeze/input/scope/count/order drift, identity/role/hash/annotation rejection, and
generation-only, reviewer-only and both-consumer overflow. Overflow tests retain
all eight complete sources and distinguish failure from admission. Synthetic
negative controls do not enter the eight-row results.

- Focused new diagnostic suite: **34 passed**. Combined with the unchanged
  correction and packet-comparison suites: **54 passed**, including exact old
  summary/request bytes and execution-source hashes; no historical rehashing.
- Broader admission, capacity, natural reviewer, sufficiency and workflow-input
  suites: **64 passed, 1 skipped**. The skip is the existing ignored historical H2
  result being unavailable; available invalid evidence still fails. These suites
  use portable fixtures and make no live provider/database calls.
- Repository Python lint: `uv run --locked ruff check services packages workflows scripts tests`
  passed. Changed-file format check against `origin/main` passed for all three
  new Python files. Authored-doc whitespace and **130 local links/anchors** passed;
  the continuity plan remains below 500 lines (499). Original report whitespace
  was preserved, not normalized.

Provider token counts, latency, model answers, naturalness, reviewer behavior,
persistence, production-scale candidate retrieval and runtime release remain
unmeasured. No frontend/full-stack, database or native/provider verification was
needed or run for this offline service-test/documentation change.

### Independent Manager Audit

The manager inspected the diagnostic, frozen loader, tests, artifacts and source
diff, with no actionable findings. An independent direct JSON/source check (not
the diagnostic helper) recovered all eight D04 exchanges and 16 original messages,
verified content hashes and identical H, and recomputed 2,410 / 9,993 estimates
from complete UTF-8 serialization with the full 16,384-character candidate reserve.
Runtime source, historical builders, old studies, report bytes and product intent
have no diff from the pre-slice revision `51e39c0`.

The [focused command](README.md#reproduction-and-outputs) was rerun: **54 passed**.
Broader independent command:

```sh
env -u ADE_TEST_DATABASE_URL uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity/tests workflows/evals/character_memory_dev/tests/test_history_ranking.py --ignore=services/ade-api/tests/agent_runtime/persistence -q -rs
```

**516 passed, 3 skipped**: one unavailable ignored H2 result and two unavailable
ignored H4 schedule-evidence checks. One existing Starlette/httpx deprecation
warning remains. Repository Ruff lint and format checks of all three new Python
files pass; 131 local documentation links/anchors also pass. This accepts the
bounded offline implementation and its measurements,
not provider behavior, continuity quality, a larger runtime default or another run.
