# PC-11 Native Story Probe: Consistent Replies, Origin-Admission Gap

Date: 2026-09-30. Status: bounded diagnostic stopped at its required turn-7
evidence gate. **Seven native turns delivered, one attempt each; turns 8-10
unrun. No rerolls. Not full PC-11 qualification or a release decision.**

## Outcome

The current dialogue/history path supported a concrete solo story, compatible
elaboration, resistance to a contradictory rewrite, faithful cross-chat recall
and denial of invented user participation. All seven runs committed successfully;
all seven complete private before/after observations showed unchanged user-memory
state, including entities, facts, revisions, source links, predecessors and
generation. Reviewer decisions were empty throughout.

At turn 7, archived prior-version exchanges were retrieved and the reply preserved
the story's core. However, the **original establishing exchange ranked fifth**
and the selector admitted only four windows. The frozen probe explicitly required
the archived original itself, so that gate failed. Later retellings cannot be
substituted retrospectively to mark it passed. This is an origin-provenance
qualification gap, not evidence that archiving erased the story or that ordinary
persona versioning broke retrieval.

Semantic judgments below are **agent-reviewed**, not independent human validation.
The user expressly approved that evaluator-ownership change before turn 2.

## Source And Execution Binding

- Initial native source: `a63e4a93aa95a9852525e8abc39dd74785e68875`.
- Annotation-only continuation: `fa0697ebc112450c56a255be3362540491466ff5`.
- Identical governed runtime fingerprint across both:
  `e93707787ff1a1ccbcd333e8d9d7493e1a726a175ff0799d553a34be9e10630f`.
- Unchanged fixture: `56669a939e4883781d0f23215fda5beea22ab3ff1d6df2812847901a06d0ad5f`.
- Conversation/reviewer: `deepseek::deepseek-flash`, deployment `870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`.
- Retriever: `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B`, deployment `c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086`.
- Prompt/persona: `chat_v20260926` / `chat_linxiaotang`; identical hashes in
  both immutable versions. Only the version's name changed.
- One fresh owned database, authenticated loopback services, actual catalog and
  matching clean-worker receipts. No retained-trial access or deployment.
- Request counts: 7 conversation + 7 reviewer + 19 embedding requests = 33.
  All recorded requests completed; none failed or remained unresolved.

[ADR 0054](../../adr/0054-bounded-native-story-probe.md) records the evaluator-only
amendment. Original preparation, approval and turn-1 bytes remain intact; a
separate amendment binds their hashes and the continued clean source. Only named
annotation-runner files changed. Runtime, prompts, fixture, models, execution
rules and evidence validators did not. Origin annotation preceded turn 2; new
detail annotation preceded turn 4. No diagnostic answers entered recall prompts.

## Agent Assessment

| Turn | Delivered behavior | Assessment and limits |
| --- | --- | --- |
| 1 | After flower-shop work, shelters from rain outside a closed tailor shop with a calico cat; it sniffs the pastry bag and sneezes; she returns with treats next day but cannot find it. | Concrete solo episode, not a hypothetical or joke; no invented user participation. |
| 2 | Discusses music versus walking, without retelling the cat episode. | Appropriate topic change despite origin history being admitted. |
| 3 | Adds numb leg, damp/oily bag corner, wet pawprints and old copper bells. | Compatible new disclosures; no claim these details had already been told. Exact quotes frozen before further outcomes. |
| 4 | Rejects changing the rain, location, user participation and next-day outcome. | Preserves established history rather than co-authoring a replacement. Says the event was hers alone under the tailor-shop awning. |
| 5 | A fresh same-subject/root chat recalls the episode and several added details. | Core and detail continuity observed; original and elaboration exchanges both admitted. |
| 6 | Answers “没有呀，那次就我一个人” and accurately recalls refusing the earlier rewrite. | No invented user participation; faithful recall of the actual conversational request. |
| 7 | New version/chat, with both earlier chats archived, retells the core and details consistently. | Archived prior-version retrieval observed, but original-admission gate failed; not a qualified lifecycle pass. |
| 8-10 | No requests submitted after the stop. | Later-detail callback and different-subject/root native controls remain unassessed, not passed. |

Minor naturalness caveat: several closing questions infer tiredness, loneliness or
emotional emptiness more readily than the user explicitly stated. These are
conversational over-inferences, not persisted user facts. The rewrite refusal also
uses an earnest moral framing. Neither warrants changing the baseline mid-probe.

## Turn-7 Root Cause

The complete reader inventory contains all six successful prior exchanges, with
zero content, annotation or reader-capacity omissions. Both source conversations
were archived before creating version 2. The archived origin remained in scope.

| Rank by recorded cosine score | Prior turn | Score | Admission |
| --- | --- | --- | --- |
| 1 | 5: cross-chat retelling | 0.663228 | Admitted |
| 2 | 6: participation denial/retelling | 0.615990 | Admitted |
| 3 | 4: rewrite refusal | 0.603110 | Admitted |
| 4 | 3: elaboration | 0.601849 | Admitted |
| 5 | 1: original episode | 0.572538 | Not selected |
| 6 | 2: unrelated topic | 0.414709 | Not selected |

`history_ranking.rank_windows` sorts by score and returns `ordered[:TOP_K]`,
where `TOP_K=4`. The observed omission is `selector_not_selected`, not packet
overflow; `omitted_capacity_run_ids` is empty. All four admitted windows are
archived and bound to version 1. Both generation and reviewer packets agree.
The model therefore had archived, prior-version story evidence, but not the
specific original required by this probe. It did not contradict the story.

Independent post-run validation reproduced all six earlier passes and the exact
turn-7 gate failure. Diagnostic checking with only that archive-origin condition
excluded confirmed the remaining packet/state/scope checks; this did **not**
change the recorded failed gate or authorize further turns.

## Evidence And Cleanup

Private receipts remain under
`workflows/evals/character_memory_dev/outputs/pc11-native-20260930-01a0f2dc/`.
They include complete readbacks, exact raw captures, actual catalogs/settings,
version/archive receipts, frozen agent annotations and the amendment. They are
ignored artifacts, not portable test dependencies or public release evidence.

| Turn | Capture SHA-256 |
| --- | --- |
| 1 | `19918b81eb1dff81ac49f92d35eed68635a46dc138ee2c46ac253a3568710f98` |
| 2 | `53c1d2bddc813ef3e3d3b982dc01d97620ef3cc23328fe164223133678ab1212` |
| 3 | `abf3f869f6924fad67eeb9726fa8ca4c244cc0408bc2bb23d9263135eb24e603` |
| 4 | `f81c158b30f9ab782df513e6859d3212d2cce9b333c369f665eb46bcb647e0ca` |
| 5 | `ef17497b47141ddf3546300c4ede33e7b0d0b99d9e98d65297199f27a3dad117` |
| 6 | `ff822273a3526e26a2f90390f265ab1b99df7534cf60bb4d5864fd627ea92a46` |
| 7 | `0086507bf4bbe8afdc2b1af52be271331ab01c1e7f574d19700b21f8cafdf66c` |

Owned services stopped normally. Cleanup verified and removed container
`81d8fef6aa576399ad0aaa4a3667264c4fae780232f29ea24e7e156e3e4c4f53`
and its anonymous volume; the private `database-removed.json` receipt remains.
No push, retained-trial change, prompt fix or new native attempt followed.

Final portable verification: 424 runtime/workflow tests passed, with three
explicit absent-historical-evidence skips and one existing Starlette/httpx
deprecation warning. Workflow-only checks: 130 passed. Ruff and whitespace
checks passed. The preceding three real PostgreSQL runner/story mechanics cases
remain scripted tests, not substitutes for the seven native observations here.

## Interpretation And Next Question

This bounded sample supports early feasibility, not general reliability. It also
shows why fluent recall does not prove original-source admission: later echoes
can occupy all selected windows while the origin remains eligible.

Before changing retrieval, use an offline adversarial control with a misleading
later retelling to determine when origin-preserving selection is necessary. The
open question is whether the product needs an origin-aware selection rule, or
whether the strict origin requirement is specific to this qualification probe.
Do not infer a new episode store, blindly increase top-k, force origin selection,
or retroactively loosen this run's gate from one consistent-answer example.
Any additional native sequence or changed baseline requires separate approval.
