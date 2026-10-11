# Hindsight Consultation: Source-Checked Assessment

Date: 2026-10-10. Status: returned reports reviewed; revised recommendation for
user consideration, not implementation or live-run authorization. Runtime and
product agreements are unchanged. Relevant agreements: PC-01/02/03/04/06/07/10/11/12;
PC-05/08/09 still govern the incumbent and need explicit amendment for adoption.

## Outcome

**Freeze new native-memory feature work; isolate the experiment, not the whole
incumbent implementation.** The next useful investment is a small, disposable
Hindsight-to-Character replay, not a behavior-preserving native refactor first.
This revises our recommended order in the [original assessment](../hindsight-integration-assessment-2026-10-10.md),
especially sections 4 and 6. It does not change the source findings about native
coupling or assert that Hindsight is already suitable.

The important distinction is the next decision: whether Hindsight supplies
useful conversational memory, versus how to integrate it into production turn
finalization. The existing executor provides enough of a seam to investigate the
first without paying for the second. Preserving unchanged native execution and
its Git baseline is sufficient for this separate experiment.

The reports disagree on bank layout. A proposes one subject bank with native
extraction labels; B prefers separate profile and relationship banks. Neither
has measured semantic quality. Our original assessment underweighted extraction
labels that become fact tags, making A's proposal worth trying before paying for
two extraction routes. **Recommend A as the first experimental candidate, not an
adopted access-control design; retain B as an alternative if a concrete failure
justifies it.** No comparative campaign is required before a first useful case.

## Report Provenance

Preserved byte-for-byte in attachment order, including original whitespace and
absence of a final newline. Our interpretation is separate from both reports.

| Report | SHA-256 of supplied text and retained copy |
| --- | --- |
| [A](reports/review-a-2026-10-10.md) | `48fcab47e550a999d3edd2826d404b087b57ed988d2d75b30d402a352d2852c7` |
| [B](reports/review-b-2026-10-10.md) | `0a3a9d6027a2ee5d4ad052578d1008f902940a164832fd4ebba1c28e2537a1b4` |

Both identify ADE `c46ac380a81a89775c25c4c0edf49825a222d91b` and Hindsight
`eb6df499d35300e5b2f3f029b2e6adda04ed90f8` (v0.10.3). Neither reports running a
service or experiment. Reviewer identity and independence are not established;
agreement is not replication. Both disclose inability to inspect the large
Hindsight engine file. We checked the relevant portions locally from the pinned
upstream source retained during the assessment. ADE was clean at their exact
revision when this review began. No newer Hindsight version was substituted.

## Insight Dispositions

`Use` means incorporate into this recommendation, not silently adopt a runtime
contract. `Test` is an unrun hypothesis; `Park` is deferred work.

| Disposition | Insight | Integration / boundary |
| --- | --- | --- |
| Use | Both: test semantic fit before refactoring native finalization. | Leave native execution alone; recommend a disposable memory-to-Character replay. |
| Use | Both: ADE owns identity, source eligibility and Character request composition; Hindsight owns memory interpretation and retrieval. | No duplicate semantic reviewer, native fact emulation or generic provider framework. |
| Use / Test | Both: accepted user inputs remain eligible after reply failure; committed assistant text is needed for PC-11 stories. | Separate eligibility from delivery timing. Test attributed immutable exchanges; exclude uncommitted candidates. |
| Test | A: extraction labels plus strict character/profile recall could avoid a separate profile pipeline. | First candidate; verify mixed profile/private sentences, correction and derived observations, not just labels. |
| Park / Test | B: separate relationship and profile banks provide simpler default separation. | Alternative if needed. A narrow profile mission still depends on semantic classification and may duplicate curation work. |
| Use / Test | Both: prefer immutable source units to routine whole-conversation replacement. | Lower revision/curation interaction, not guaranteed extraction quality or duplicate prevention. Compare native append only if reference resolution warrants it. |
| Use | Both: durable delivery is necessary for adoption, but a new outbox is not the only implementation. | Inspect existing committed sources plus delivery receipts later; do not build a worker or pretend it already exists now. |
| Use | Both: local dialogue is immediate; external long-term memory need not imitate native generations. | Wait for retain completion in semantic cases, then measure freshness separately. Consolidation can lag extraction. |
| Use / Test | Native invalidation is a plausible PC-07 mechanism. | Test later ingestion and source replay; removal of a selected fact is not universal topic suppression. |
| Use | A: Hindsight curation is state, not a disposable index rebuilt from transcripts. | Preserve this adoption implication; recovery/backfill design remains later work, not a prerequisite for the replay. |
| Park | Production finalization, durable delivery, backfill, full Studio views and recovery qualification. | Revisit after semantic fit justifies integration; no automatic native fallback or dual writer. |
| Discard | Consensus as acceptance; immutability as a semantic deduplication guarantee; fake native versions; another consultation by default. | None supplies useful evidence or authority for the next step. |

## Source Checks And Qualifications

### The Executor Seam Exists, With Specific Limits

[ConversationExecutor.execute][executor] accepts prepared messages and a
`CuratedTool` mapping without requiring native review results. `curated_tools`
accepts additional tools. Each model step uses `conversation_request`, preserves
the assistant message for continuation, and performs the serialized-request
estimate check when `input_token_limit` is supplied. These support the proposed
replay seam; they do not establish a finished Hindsight adapter.

The built-in `search_memory` description and `_search_memory_tool` wrapper are
explicitly about current-user facts, not character stories. A Hindsight binding
must use its own correctly described curated tool. The request observer catches
and ignores observer exceptions: an experiment must verify complete captures,
not assume passing a callback guarantees an audit record. The token guard is
estimate-based, not a provider-tokenization proof.

The [development conventions](../../development-conventions.md#workflow-locality)
also prohibit workflows from importing feature internals directly. Reuse the
executor through a feature-owned evaluation entrypoint or a specifically reviewed
narrow boundary; do not turn this recommendation into an undocumented workflow
exception or a general-purpose public execution API. Decide this during bounded
preparation, not through a broad native isolation project.

### Native Labels Are More Than Caller-Supplied Tags

[Bank configuration][banks] documents extraction-time `entity_labels` and
`tag: true`. [Label models][labels] provide the typed configuration, and
[`_inject_label_tags`][extraction] actually adds extracted label entities to fact
tags. Both ordinary extraction paths invoke it. This validates A's mechanism,
not correct classification by a particular provider.

Proposed first configuration: one bank per workspace/subject, ADE-assigned
`character:<root>` source tags, a narrow optional extracted `kind:profile` label,
and nonempty strict recall of the current character OR profile label. Keep
consolidation explicitly character-local, e.g. `[["character:C"]]`, with shared
raw profile facts rather than shared observations initially. Identity comes from
ADE, never model-selected bank IDs. Conversation/version/archive are not new banks.

A profile label is not sufficient if the fact text also contains a private
exchange. Test a combined preference-and-private-origin sentence. Missing labels
should fail toward character-local availability; incorrect shared labels remain
a semantic failure. Both layouts need this check: separate banks do not magically
select profile-only content. Prompt missions are guidance, not authorization.

### Source Text And Derived Views Need Their Own Scope

[Recall documentation][recall] distinguishes fact tags from document tags. The
[engine's chunk retrieval][engine-chunks] calls
[`visible_document_ids`][source-scope] using the caller's filter, then drops chunks
whose document is not visible. A shared fact therefore need not carry the rest of
its private source. Do not add `kind:profile` to the entire source document.

Start Character recall without raw chunks, source-fact bundles or unnecessary
entity diagnostics. That is a small experimental surface, not proof of all
Hindsight read paths or deployment authorization. Check scope before and after
consolidation; extraction completion is not consolidation completion.

B correctly flags imprecise prose in [retain documentation][retain]: its claim
that original text is not stored conflicts with actual storage paths.
[`DEFAULT_STORE_DOCUMENT_TEXT`][config] is true, and the [orchestrator][orchestrator]
stores source bodies in `documents.original_text` when enabled. Disabling that
setting is a separate configuration, not something a profile mission does.
Do not assume unwanted source text disappears after selective extraction.

### Immutability Reduces Risk; It Does Not Implement Forgetting

[Curation documentation][curation] explicitly says reprocessing resets curation.
Immutable sealed exchanges avoid ordinary document revision, but including old
dialogue as context can extract the same information into a new fact. Test both
redelivery of the same source and repeated old content in a new exchange. Do not
build a suppression engine or claim removal safety from document IDs alone.

[RunService.accept_turn][acceptance] persists exact user text and a committed
message event before later generation success. This supports retaining failed-run
user inputs. It does not prove an existing delivery scanner or justify waiting
forever for a stuck run. A later production design must make those inputs
discoverable; immutable per-message delivery remains an option if earlier
submission is needed. None of this requires a network call inside ADE's SQL
transaction.

Both reviewers could inspect the async request surface but not its replay
implementation. We rechecked [`_resolve_retain_replay`][replay]: it compares bank
and operation type, not new payload equality. The original assessment's warning
stands. Retry identities must refer to the same immutable source payload; the
remote operation ID alone does not enforce that relationship.

## Revised Next Step, Not Yet Authorized

Prepare one small synthetic replay: attributed sources -> pinned Hindsight
retain/recall -> a concrete ADE composer -> existing Character executor. Opening
retain/recall smoke checks and a few fake-transport checks belong inside that
slice, not in separate preparatory milestones. Real Hindsight/model calls make
this an **isolated live experiment**, not an offline test despite replayed inputs.

Use a few Chinese conversational cases where appropriate, two synthetic users
and two character roots. Choose cases that can change the next decision:

1. Profile sharing versus private exchange/solo story, including a mixed sentence,
   another user, a new persona version, archive metadata and consolidation.
2. Referential input, a correction, committed solo fiction versus hypothetical or
   unsupported user claims, and a question about an unstated story detail.
3. Invalidation followed by unrelated ingestion, source retry and repeated old
   context; keep the original transcript unchanged.
4. Actual initial/tool-follow-up requests, unavailable recall, oversized output
   and observed retention/freshness. Keep request limits and finite loops.

For selected failures compare Hindsight context, no memory, and a manually
supplied adequate-memory control through the same Character path. This separates
memory usefulness from answering ability without requiring another evaluator
subsystem. It is a diagnostic comparison, not proof of a unique root cause.

No full cross-product matrix, native refactor, new ingestion worker, native fact
compatibility, existing-chat export, backfill, deployment or Studio redesign is
required. Do not silently weaken profile sharing to claim a relationship-only
demo satisfies the whole product. A small success would justify the next
integration investment, not general acceptance.

The next authorization should bind the synthetic scope, isolated candidate and
storage, model/provider route, and permitted live calls. PC-05/08/09 and native
success/removal contracts remain unchanged until an actual binding is adopted.

## Verification And Follow-Up

This review inspected the pinned ADE executor/acceptance path and the upstream
sources linked above. Five key upstream files, including the large engine and
label projection implementation, matched fresh bytes fetched at the pinned SHA.
Both report copies matched their supplied bytes and recorded hashes; four local
links and thirteen pinned source paths/line locators passed checks.

`uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_executor.py -q`
using `/opt/homebrew/bin/uv`: **19 passed in 0.80s**. These are existing offline
executor checks, not Hindsight integration or semantic evidence. Authored
documentation whitespace is checked separately from preserved report formatting.
No runtime/configuration changes, Hindsight installation, service startup, live
model call, database inspection or semantic test occurred.

**Follow-up recommendation: none.** A bounded experiment now offers more useful
information than another Pro or Deep Research round. Reopen consultation only
after a specific result exposes a consequential question that direct inspection
or a small configuration comparison cannot resolve. The bank-layout disagreement
alone is not a reason to delay the experiment or commission a tie-breaker.

[executor]: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/c46ac380a81a89775c25c4c0edf49825a222d91b/services/ade-api/src/ade_api/features/agent_runtime/executor.py
[acceptance]: https://github.com/Wenjun-Mao/Letta-Open-ADE/blob/c46ac380a81a89775c25c4c0edf49825a222d91b/services/ade-api/src/ade_api/features/agent_runtime/run_service.py
[banks]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memory-banks.md#entity-labels
[labels]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/retain/entity_labels.py
[extraction]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/retain/fact_extraction.py#L3723
[recall]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/recall.md
[engine-chunks]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L10203
[source-scope]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/source_scope.py
[retain]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/retain.md
[config]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/config.py#L1718
[orchestrator]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/retain/orchestrator.py#L2212
[curation]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/skills/hindsight-docs/references/developer/api/memories.md#L414
[replay]: https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/memory_engine.py#L22245
