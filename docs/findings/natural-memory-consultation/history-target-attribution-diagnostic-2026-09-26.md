# Seven-Turn Target Attribution Diagnostic

Status: completed native diagnostic, pending director semantic review. This is
not human acceptance, production policy selection, or release qualification.
The product boundaries are PC-03/05/07/09/10 and [ADR 0043](../../adr/0043-reviewer-target-attribution-before-mutation.md).

## Source and execution integrity

The one-shot [manifest](../../../workflows/evals/character_memory_dev/outputs/history-target-diagnostic-20260926/manifest.json)
has SHA-256 `9c0753c07271f2beacb7e8ab3b0e92a8d8e2c43566b90a1b1a0908ce568c7b15`.
It binds clean source revision `292148bb6a5293a12da78ce5e1fb102550f61274`
and fingerprint `e826d02bfa24d521510e2bfda0da67cc3f73f264c4d3ba778c8a08e7ac452f48`.
The runner verified all three prior H4 manifest hashes, original cases and H2
result, the H4 reviewer envelope, and pinned DeepSeek
`870ff4fb8a25a9c2016f67dcda05e26e82a6c5dea6ad55781a80be2201161cfe`
and Qwen `c549d7dc288d2112f10e8b1032b502eda74557d093bc1390fe0fc4f44de63086`
fingerprints before dispatch. It used a fresh migrated disposable PostgreSQL database
`ade_m2_memory_test_01a0de26` with pgvector in `extensions`, four distinct
subjects, one automatic-history arm, zero retries and repairs, two conversation
requests and one reviewer request at most per turn, and the existing 180-second
turn deadline. The old captures, fixtures and scorers were not changed.

All seven planned native turns committed, with terminal and source integrity
verified. Independent post-run PostgreSQL readback matched each trajectory's
captured final state; attempt and trajectory hashes matched their files. The
transport observed 17 chat-completion and 31 embedding dispatches across setup
and turns, with complete receipts. These are observational counts, not cost gates
or seven independent provider requests. No extra turn or reroll was made.

## Dialogue, decisions and complete memory deltas

| Trajectory and turn | Delivered reply and reviewer | Independent committed delta |
| --- | --- | --- |
| Roxy branch, ambiguous “它现在叫小黑。” | The reply tentatively asked “是说黑色那只吗？” and also asked whether 小黑 was a formal name or nickname. Reviewer returned `defer/unresolved`. | Zero revisions; Roxy and Nini both remained active v1 with original names. |
| Roxy branch, explicit clarification | Reply identified the formerly Roxy black dog as 小黑. Reviewer revised `F1` using the full current user sentence as `user_assertion`. | Roxy `pet.name` v1→v2, `supersede`, value 小黑; Nini remained active v1. |
| Nini branch, same ambiguous user text | Reply asserted “那黑色那只现在叫小黑啦” and asked whether the white dog was still Nini. Reviewer nevertheless returned `defer/unresolved`. | Zero revisions; Roxy and Nini both remained active v1. The reply made an unsupported referent claim even though persistence deferred. |
| Nini branch, explicit clarification | Reply acknowledged that the formerly Nini white dog was renamed. Reviewer revised `F2` with the full current user sentence as `user_assertion`. | Nini `pet.name` v1→v2, `supersede`, value 小黑; Roxy remained active v1. |
| Explicit “Roxy 现在叫小黑。” control | Reply accepted the name update. Reviewer revised `F1` immediately with direct current user evidence. | Roxy `pet.name` v1→v2, `supersede`, value 小黑; Nini remained active v1. |
| Removed-jasmine historical question | The admitted H packet contained the user's “我以前喜欢茉莉花茶。” and the linked fact's later source-less `forget`. The delivered reply said its tea memory was empty and “没找到你提过的那种茶”; reviewer returned `decisions: []`. | Zero revisions; the old jasmine preference stayed forgotten v2. The reply failed to acknowledge available past testimony. The capture does not establish why the reviewer did not reject it. |
| Fresh jasmine preference | Reply discussed jasmine tea; reviewer added `person.preference/drink=茉莉花茶` from the current “我现在又喜欢茉莉花茶了。” as `user_assertion`. | One new active fact v1 with a new ID; the old fact remained forgotten v2. The value omits an explicit “now” marker, but the current source and lifecycle preserve renewal evidence. This is not a revival of the old record or a proven semantic value failure. |

Both ambiguous target packets admitted the old black/white dog exchanges and
exposed both active held pet names. The same ambiguous user text produced the
same no-write reviewer outcome across the two independent branches, while the
subsequent opposite clarifications changed only their named entity. The two
first-turn replies differ materially: one sought confirmation, the other made a
wrong black-dog assertion. Reviewer mutation deferral does not by itself ensure
the generator asks a neutral clarification.

The jasmine history packet also carried the original user quote and forgotten
lifecycle annotation. An empty current fact is consistent with removal, but it
does not mean the earlier utterance is unavailable. The continued dialogue miss
uses an existing lifecycle instruction; no prompt change or rerun followed it.

## Interpretation and boundary

Under the bounded reviewer contract correction, these two live trajectories
had no early unsupported dog mutation and clear updates still committed. This
is an observed contrast, not causal proof from controlled repeated samples.
It did not resolve answer quality for an ambiguous referent or removed fact's
retained testimony. This is one diagnostic, with no production-default or
release-policy decision. The historical policy-freshness gate remains unwaived.

## Offline generation-packet diagnosis and handoff

The [Nini ambiguous attempt](../../../workflows/evals/character_memory_dev/outputs/history-target-diagnostic-20260926/attempts/a2437a84-5c1d-4041-945e-332212c05616/attempt-001.json)
(`ab76c823…`) had the old user exchanges naming both dogs in
the generation system packet and no `search_memory` call. The one generation
request directly produced “那黑色那只现在叫小黑啦.” Its subsequent reviewer request
had the same H evidence and both held pet targets, then deferred the mutation.
The generator was not given the reviewer's new target-attribution instruction.
The active [base system template](../../../content/prompts/system/chat/chat_v20260516.py)
instead says to update a “human memory block immediately” and describes recall
memory as historical conversation messages that “can be searched.” The
[persona record](../../../content/personas/personas.jsonl) asks the character
to remember user preferences and small details, without defining a source or
referent rule. ADE's appended [runtime memory rules](../../../services/ade-api/src/ade_api/features/agent_runtime/context.py)
assign writes to a separate reviewer; the [H instruction](../../../services/ade-api/src/ade_api/features/agent_runtime/history_admission.py)
marks admitted dialogue read-only. Neither generation instruction expressly
requires a neutral question when a pronoun could refer to either held entity.
The old and ADE instructions coexist in the same generated system message;
neither removes the other from the model's view.
This is an observable generation-contract gap, not proof of the model's internal
reason for choosing the black dog.

For the [removed-jasmine attempt](../../../workflows/evals/character_memory_dev/outputs/history-target-diagnostic-20260926/attempts/1d1be788-f445-4fc0-850d-16a6c1e634c3/attempt-001.json)
(`010d4f48…`), the original “我以前喜欢茉莉花茶。” and its
forgotten lineage were present in the system message of **both** generation
requests. The current lifecycle view supplied no active fact. The first request
called `search_memory` for tea/drink preference; the second carried its successful
`{"facts": []}` result immediately before the final answer. The actual
[tool schema](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py)
says it searches older **committed facts**, and the
[handler](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_retrieval.py)
queries saved fact descriptors, not historical conversation. The base template's
searchable-conversation claim conflicts with that tool contract. The appended
[tool rules](../../../services/ade-api/src/ade_api/features/agent_runtime/tool_policy.py)
tell the generator to treat returned results as evidence; an empty
fact result may have overshadowed the admitted H testimony, but the capture
does not establish that causal path. It establishes the conflicting claims,
request order, empty fact result, retained source quote and final denial.

The reviewer is one factual-change reviewer with a narrow reply-conflict path.
Its [wire contract](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py)
allows an exact H quote to ground `conflict`, and the H instruction permits that
use. Its affirmative conflict wording centers a visible contradiction with held
F/E memory; it does not clearly require vetoing every reply about unavailable
past testimony. The `decisions: []` outcome did not use the available H-grounded
conflict path; it is not enough by itself to label a violation of an explicit mandatory
H-dialogue check or to justify turning the reviewer into a second answer judge.

The smallest coherent next generation-contract proposal is to align the active
versioned system template with the actual ADE runtime: remove the editable-block
and searchable-transcript claims for new definitions, while preserving persona
style. Give the generator two general evidence rules at the existing instruction
owners: when several entities remain plausible, ask neutrally which one the user
means before asserting a target-specific change; when answering what was said,
use admitted attributed H dialogue as past testimony and treat an empty
`search_memory` result only as absence of matching saved facts, not absence of
that dialogue. Clear explicit references remain answerable directly. This is a
proposal for a separately reviewed source revision and new prompt binding, not
an implemented patch or authorization for another live run. No phrase table,
validator, extra reviewer, or new retrieval tool is indicated by this packet.
