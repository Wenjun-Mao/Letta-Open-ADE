# Historical Recall: Pro Review Assessment

Date: 2026-09-25. Status: director assessment and recommended plan corrections;
not an amended product contract, implementation approval or behavioral acceptance.

## Recommendation

Keep the PostgreSQL/native-runtime foundation and narrow the first experiment to
baseline versus one automatic historical read. Defer discretionary retrieval and
the two-operation preview/read protocol. Preserve the narrow read-only `H` review
channel, source-relative lifecycle meaning and one atomic reviewer/write path.

The product reviewer recommends contract clarifications; the architecture reviewer
also recommends reducing the initial experiment. They agree on several risks, but
do not independently establish that either retrieval policy works. Do not describe
them as two approvals of an unchanged plan or as evidence that automatic is better.

## Original Reports

Both report inspecting source/plan `cece5bedd6032da3ebc3802c7be604eb505967e6`.
Neither executed code or inspected private captures. Preserved byte-for-byte:

| Report | SHA-256 |
| --- | --- |
| [Product and semantics](history-recall-pro-product-report.md) | `fd4ff7f60b2f25ff5f92a867acce972acb04d94ed67708fa519b5dc2125ad41e` |
| [Architecture and simplification](history-recall-pro-architecture-report.md) | `6d2d5c1fcb65d8c393cb107165c5931c934674abe9837f2f23970a03e935d985` |

The Mandarin cases are constructed counterexamples, not measured failures. This
assessment records interpretation separately; the original reports are unchanged.

## Verified Against Code

These are source-inspection results, not new executed-test evidence:

| Claim | Local verification and consequence |
| --- | --- |
| Reuse a coherent read snapshot | [turn_memory_snapshot.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_memory_snapshot.py) already uses a short repeatable-read, read-only state load and accepted-generation check. Extend that connection's bounded read; no new snapshot service/global clock. |
| Historical messages must not enter write-support handles | [natural_memory_binding.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_binding.py) creates `U/A` support and compares local sequence. Cross-conversation history needs a separate namespace. Independently eligible local messages keep existing authority. |
| `H` addresses a real read-only grounding gap | [natural_memory_review.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py) and [natural_memory_policy.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py) currently ground conflicts in `F/E`. Extending conflict grounding is different from adding a write mode. |
| Tool results do not automatically reach review | [turn_execution.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py) passes the original natural source messages to review, not executor tool evidence. Automatic-first avoids a new late-arrival path in the initial probe. |
| A tool exception can be misclassified | [executor.py](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py) catches ordinary handler `Exception` and returns provider unavailability. Argument validation is outside that catch; cancellation is not universally swallowed. Fatal handler integrity/version/timeout exceptions need explicit propagation if a history tool is later introduced. |
| Fact embeddings are not transcript embeddings | [embeddings.py](../../../services/ade-api/src/ade_api/features/agent_runtime/embeddings.py) defines a durable-fact query instruction, typed-fact document recipe and fact threshold. Reuse provider/model access, not the stored fact-space identity, formatting or threshold as transcript defaults. |
| Latest sources alone miss operator removal | [memory_source_read.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/memory_source_read.py) permits operator actions without message sources; [metadata.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/metadata.py) retains revision links/predecessors. Trace the source span through its originating revision/chain, not just the latest revision's source rows. |

## Insight Disposition

`Use` means incorporate in the recommended plan revision, not implement now.

| Disposition | Insight and boundary |
| --- | --- |
| Use | Baseline versus automatic first, with the same `H`-capable reviewer binding; baseline gets empty history. This isolates the addition better than comparing different reviewer policies. |
| Use | One combined bounded recall operation if discretion is later justified. No preview/read state machine in the first experiment. |
| Use | Freeze messages, linked lifecycle annotations, local facts and summaries in the existing coherent snapshot. Future-turn exclusion covers every input, including query construction, not just transcripts. |
| Use | Annotate the originating claim/span and material recorded transitions. A latest value that happens to equal the original value must not erase an intermediate correction. Keep unknown meaning explicit; do not generate a semantic timeline or expose forgotten revision values. |
| Use | Historical acknowledgment is not necessarily a fresh current assertion. Test the next turn as well as the recall turn: a correctly quoted old preference followed by acknowledgment must not silently resurrect it. Genuine supported current endorsement remains valid. |
| Use | If a fresh statement's referent exists only in `H`, do not quietly promote it to direct/write-support evidence. For the bounded probe, defer the write and allow natural local clarification. Do not ban short answers or mark a topic permanently unwritable. |
| Use | Temporal conflict review must permit both current change differing from old text and attributed historical answers differing from current facts. A difference alone is not a contradiction. |
| Use | Define source-existence checks before outbound packets containing history. Before first exposure, omit legitimately purged sources; after exposure, abort on discovered loss instead of silently changing only the reviewer packet. A purge after authorization cannot unsend a request. This is an evidence-consistency boundary, not topic suppression. |
| Use | Admit whole annotated windows against actual serialized generator/reviewer requests. Do not add rolling eviction to avoid a capacity result. |
| Use | Separate eligible corpus, sufficient-source retrieval, packet admission, candidate quality, complete review delta, delivery and persistence outcomes. A caught bad candidate is not a successful delivered reply. |
| Use | Independently reseed equivalent target-time prefixes for paired target-turn measurements. Separately label short follow-up sequences as trajectory/semantic tests once outputs diverge. |
| Use | Keep ranking-selection fixtures separate from dialogue scoring. Use a small transcript recipe identity and probe-local vectors, without modifying stored fact embeddings. |
| Test | Retrieval of correction/resolution evidence, rather than just the original topical passage; quality of Mandarin paraphrase ranking. Freeze minimum sufficient evidence sets. |
| Test | Whether lifecycle annotations and `H` review improve net delivered quality rather than false vetoes, output pressure or irrelevant callbacks. Namespace checks cannot prove semantic correctness. |
| Park | Discretionary tools, iterative retrieval, search-preview expansion, permanent indexing/backfill and production scaling until automatic-recall feasibility leaves a specific unresolved need. |
| Discard | Treating all findings labelled P0 as demonstrated production defects. Some are future contract gaps; snapshot semantics already exist. Fix the relevant contract without creating a large generic hardening project. |
| Discard | Requiring flawless general extraction before independent reader/ranking tests. A traceable native control is necessary before scoring delivered dialogue, not before testing read isolation. |
| Discard | Turning semantic counterexamples into phrase validators, suppression policies, extra reviewers or new fact types. None is justified by these reports. |

## Proposed Revision Order

1. Narrow the initial scope and public interpretation: automatic feasibility, not
   selection of a universal retrieval trigger or proof of population reliability.
2. Specify span-relative lifecycle annotations, fresh-assertion/clarification
   contrasts, temporal conflicts and the bounded purge race guarantee.
3. Anchor implementation in the existing snapshot and one admission path. Retain
   the exception-propagation issue as an explicit prerequisite to any future tool
   exposure; do not expand this read-only probe into a broad executor refactor.
4. Freeze stage-level results, target-time state, disjoint ranking inputs and the
   complete-delta acceptance cases before executing the comparison.

Apply these changes to the [existing plan](../../plans/natural-history-recall.md),
not a parallel plan. This assessment does not itself revise that plan. Re-review
only unresolved consequential contracts; implementation and live calls remain
separate approvals. The historical policy-freshness gate remains unwaived.
