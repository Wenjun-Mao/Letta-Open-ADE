## Recommendation

**Proceed with A1 → A3 → A2 → A4. Retain the plan’s overall design, with a small clarification to A4’s ownership boundary and a more targeted verification package.** A2 separates a genuine protocol responsibility. A4 separates a coherent lifecycle, but its benefit depends on keeping that lifecycle intact—not merely moving callbacks into another hook.

The plan already handles the important architectural questions correctly: it retains coordination and atomic persistence, distinguishes internal contracts from replacement interfaces, and does not turn responsibility categories into model phases or services. I found no reason to reopen the broader audit or design Character/Memory replacement abstractions now. 

| Candidate | Disposition | What should change, if anything |
|---|---|---|
| **A1 — direct `AttemptResult` imports** | **Proceed.** | Keep it to import ownership. The new import-regression assertion can be very small; broader architectural enforcement is unnecessary. |
| **A3 — inventory and chart clarification** | **Proceed as proposed.** | The mutable-authoring and policy-specific reviewer corrections are supported by code. Preserve existing capability statuses and the shared Character generation. |
| **A2 — compaction dispatch extraction** | **Proceed as proposed.** | Keep the shared response helper mechanical and preserve the existing exception differences. Add one focused persistence check involving an actually prepared summary followed by rejection. |
| **A4 — focused run monitor** | **Proceed with a small ownership clarification.** | Explicitly distinguish **monitor lifecycle identity** from **displayed run/event state**, which currently has several legitimate writers. Preserve one lifecycle owner and guarded asynchronous completion. |

The principal plan changes I recommend are therefore limited: clarify A4’s state boundary, close the specific compaction/rejection test gap, and avoid making unchanged documentation journeys or repeated broad checks independent completion gates.

**Reviewed revision:** `74e993a9b4d50cc367778392aab71937f5b541ff`. Below, `runtime/` means `services/ade-api/src/ade_api/features/agent_runtime/`, and `web/` means `apps/ade-web/src/features/agent-studio/`. Findings labeled as observations come from that revision; maintainability benefits are engineering inferences, not measured outcomes.

## 1. A2 is justified by the protocol boundary, not by file size

### What the code establishes

`ConversationExecutor.execute()` owns conversation generation, curated-tool execution, continuation requests and generation-specific validation. Its `compact()` method instead constructs a separate summary request, applies a different response schema and parser, and returns summary-specific provenance. Those are distinct responsibilities despite sharing transport mechanics.  

The proposed boundary already exists in the call structure:

- `compaction.py` owns planning, parsing, hashes and `ModelCompaction`.
- `turn_compaction.compact_turn()` decides eligibility, handles A/A0 withholding and B disabling, and passes the remaining attempt time.
- `TurnExecution.execute()` already creates a **separately traced compaction executor**, using the conversation deployment and adapter, and invokes it **before generation**. Its compaction-only collaborator calls only `compact()`.   

**Assessment:** extraction has a modest but real maintenance benefit. Summary-protocol changes would no longer require editing or depending on the conversation/tool executor. This is stronger justification than “the file is large,” but weaker than claiming that it makes Memory replaceable.

Retaining the current structure would not be architecturally incorrect: `compact()` is already fairly isolated. Nevertheless, the existing separate construction and single-purpose caller make this a low-invention extraction. A small `CompactionExecutor` fits that wiring. A focused function could also work; choosing between them does not justify an additional design exercise.

### The shared response helper is acceptable—with its current narrow meaning

Moving `_first_choice` and `_merge_usage` into a small local module does not merely disguise domain coupling. They currently provide common response-envelope and usage mechanics. Neither needs to know about summary eligibility, memory authority, tool policy, persistence or runtime lifecycle. The plan appropriately keeps `initial_conversation_request` where admission and execution can continue using the same builder.  

The boundary would become worse if this helper grew into a generalized “model operation” abstraction that also owned dispatch, retries, observers or output normalization. Two details make that warning concrete:

**Observer behavior differs today.** Generation catches exceptions from its optional request observer; compaction does not. Generation’s awaited authorization callback is also distinct from observation and can veto dispatch. Unifying those behaviors would change semantics, not just ownership. The plan already identifies this correctly.   

**Response extraction must not become destructive normalization.** `_first_choice` preserves message fields needed elsewhere in the conversation protocol; the DeepSeek executor test specifically exercises reasoning-field replay in tool continuations while keeping that material out of visible output and retained evidence. A common helper should preserve those existing mechanics, not impose a new “clean assistant message” representation.  

### Keep the protected owners exactly where they are

The proposed extraction must not choose a new compaction deployment, create its own retry loop, reset the attempt deadline, or persist a summary immediately. `AttemptController.execute_attempt()` owns the deadline/cancellation/lease race. `RunFinalizer.commit_success()` owns the transaction containing permitted memory changes, the assistant reply, any summary and its sources, version advancement, success events and lease release. Provider-observation persistence also has a separate best-effort path; it should not be confused with the atomic success events.  

The plan preserves these distinctions. No product-contract change is necessary for A2.

## 2. A4 is worthwhile only as a complete lifecycle extraction

### There is a coherent responsibility to extract

The relevant cluster in `use-agent-studio.ts` is identifiable: stream and polling handles, active monitored-run identity, terminal deduplication, guarded event publication, terminal readback and disposal. That cluster is separate from workspace loading, persona/version choices, pagination, evidence navigation and memory-action interpretation.  

**Assessment:** a focused monitor could make this lifecycle easier to understand and test. However, its autonomy is limited by necessary interaction with selected-conversation reads. The benefit is conditional on a narrow interface; extracting only the stream/poll setup while leaving lifecycle decisions scattered would mostly relocate coupling.

The plan’s fallback—retain the controller if the split requires two lifecycle authorities—is appropriate. That fallback should remain an implementation stop rule, not become a separate exploratory project.

### Clarify lifecycle identity versus displayed state

This is the most useful additional sentence to put into A4:

> The monitor owns monitoring resources, active monitor identity and terminal coordination; it does not introduce a second copy of the controller’s displayed run/event state.

That distinction matters because the current displayed state is not written exclusively by monitoring. `refreshSelected()` reconciles the displayed run, `sendMessage()` reads and publishes the accepted run and event log, and `cancelActiveRun()` publishes the cancellation response. Those writes coexist with the monitoring callbacks.  

Moving `run` into a new hook and synchronizing it with a parent copy would introduce an additional consistency problem. Conversely, leaving displayed state with the controller and allowing narrow monitor notifications is not inherently bad coupling: it reflects the real collaboration.

The division should remain:

**Controller authority:** selected conversation, selection/read epochs, selected-state refresh, evidence and pagination reads, send/cancel policy, and memory-action interpretation.

**Monitor authority:** stream/poll resources, active monitor identity, terminal latch, terminal-readback coordination and disposal.

The controller may request start/stop at existing lifecycle boundaries, but a completion callback should not independently manipulate the terminal latch or decide whether monitoring has finished.

### Preserve the distinction between selection and read epochs

The current code deliberately uses different invalidation scopes. Conversation changes invalidate monitoring through selected identity and `selectionEpochRef`. Same-conversation reads advance `readEpochRef` without invalidating the monitor. That is why opening cited evidence in the current conversation can refresh the transcript while monitoring continues.  

Do not replace these with a single “something changed” epoch. Also do not rely on conversation ID alone: an old callback from A must remain obsolete after A → B → A.

A guarded completion callback is a reasonable arrangement, provided the guard survives its asynchronous work. The monitor must check ownership around its awaits; the controller’s completion work must retain the relevant guard for any state publication after its own awaits. Checking only when the callback is first invoked is insufficient.

There is another small, extraction-specific concern: **ordinary rerenders must not restart monitoring because callback or options-object identities changed.** A regression assertion is enough to protect this; no event bus, generalized subscription framework or second selection-epoch system is warranted.

### Do not move domain interpretation into the monitor

`memoryActionOutcome()` confirms a requested change only when it finds both a matching committed event and a matching refreshed revision for the run, operation and version. A terminal notification alone is not evidence that the requested memory change happened. Keep that interpretation with its existing UI owner. 

Likewise, `openRunEventStream()` closing its own EventSource on a terminal event is not, by itself, duplicate lifecycle authority. The higher-level monitor still owns polling and overall cleanup. Idempotent resource closure is acceptable; two independent terminal coordinators would not be. 

**Bottom line on A4:** proceed with the focused extraction, not a state-management rewrite. The source supports the boundary, but it does not establish a measured maintenance saving or a current stale-update defect.

## 3. The plan preserves replacement options without pretending they are implemented

The existing boundary sketch already contains most of the replacement-specific clarification worth making now. **I do not recommend an additional replacement-interface task, integration probe or architecture document as a prerequisite.**

### Character replacement is not one operation

The source distinguishes mutable persona authoring from execution binding. Prompt Center updates active authored content; `DefinitionService.prepare()` copies prompt/persona content and hashes into a snapshot that also contains tools, memory policy and deployment configuration. That is an ADE runtime binding, not a portable persona package.   

Consequently, replacing an authoring method and replacing conversation behavior are different future changes. A2 modestly helps the latter by removing summary dispatch from the generation executor. It does not determine whether a future Character implementation supplies content, supplies guidance or owns generation/tool execution.

The plan appropriately leaves that question open. Nothing about `persona_generators`’ supplied product direction establishes which integration would work. Nor should CHAR-03/04’s assessment responsibilities become separate execution phases: the inventory explicitly describes shared generation without a materialized handoff.  

### Memory replacement must preserve authority, not just data shapes

`AttemptResult` is a concrete internal aggregate: it contains generation/context results, typed or natural review results, embeddings, compaction and history information. A1 does not make that aggregate implementation-independent, and it should not try to. 

The useful protected boundaries are instead between supplied evidence, proposed changes, structural/source/version validation, and authoritative persistence. The runtime selects one policy-specific reviewer path, and finalization revalidates against current state before committing. Those are substantive constraints a future Memory integration must address.  

A future independently committing remote store would require an explicit consistency and migration decision. A renamed interface cannot make its writes part of the current PostgreSQL transaction. The plan already says this; that is a reason to defer the design until a concrete integration exists, not a reason to obstruct today’s cleanup. 

### Some existing coupling is protective

`history_admission.admit_history()` measures the actual generation request and preflights the actual reviewer bundle. Its dependency on consumer serialization protects capacity and evidence-delivery invariants. Replacing it now with a generic “context size” interface could hide precisely the differences that need checking. 

Keep that coupling visible. A future consumer may need a different admission mechanism, but the cleanup should not guess it.

Thus, the small clarification needed now is **A3’s accurate description of existing boundaries**, not new abstractions. Defer portable persona schemas, generic Memory protocols, alternative transaction strategies and replacement-specific tool-loop ownership.

## 4. Verification is broadly sound, but should concentrate on the moved seams

### A2: strengthen exact offline characterization

The existing `test_compaction.py` does exercise both provider-adapter branches, compaction boundaries and budgets. However, several provenance assertions check hash lengths rather than exact values, and request assertions cover selected fields rather than the complete request. The plan’s requirement for exact request/provenance fixtures is justified. 

Use a small set of independently reviewed expected fixtures to protect the complete payload, prompt/input/policy/content hashes, request ID and usage. Include output-token floor/cap boundaries, malformed response handling and the differing observer behavior. Expected values should not simply be recomputed using the same production helper being tested.

**Benefit:** detects silent protocol drift during a mechanical extraction.  
**Cost:** low, deterministic tests with synthetic transport.  
**Simpler adequate alternative to a large matrix:** two adapter-specific request fixtures plus shared parameterized parser/usage/error tests. There is no need to multiply every parser case across every policy and adapter.

Retain focused checks that the caller still forwards remaining time and preserves no-plan, B-disabled and A/A0-withholding paths. These are caller responsibilities, not reasons to exercise every combination through PostgreSQL.

### A2: add one prepared-summary rejection case

The two named SQL suites provide different evidence.

`test_postgres_natural_compaction_packets.py` runs the actual worker, generates synthetic compaction results, reads persisted summaries/source rows, and checks serialized packets and traced request counts. It is meaningful integration coverage, not merely a mocked finalizer assertion.  

`test_postgres_natural_worker_fencing.py` exercises cancellation, lease loss and authoritative readback—but its scenarios create fresh conversations without a prepared compaction summary. Its “before commit” fault also raises before calling the original finalizer; it is not an injected rollback halfway through the success transaction.  

**Consequential gap in the inspected tests:** they do not directly combine a prepared summary with subsequent rejection.

I recommend extending an existing seeded scenario so that compaction completes and a later cancellation or other rejection prevents finalization. Assert that no new summary/source rows, assistant reply or memory changes from that rejected turn escape, and that the previous summary/version remains unchanged. The already-accepted user input should remain; rejection is not deletion of turn acceptance.

**Benefit:** directly protects against accidentally making compaction persistence eager during extraction.  
**Cost:** moderate fixture extension, using the existing SQL setup.  
**Simpler alternative to an expansive gate:** one such case, alongside the existing success packet and fencing tests. Because finalization itself is not being reorganized, I would not require a new comprehensive transaction-fault campaign.

### A4: retain integrated async tests and add controlled lifecycle cases

The existing async tests demonstrate late-acceptance rejection, stale stream/error rejection after selection changes, same-conversation evidence navigation, revisit/resume and obsolete-read rejection. The static view tests instead protect captions and persona/version controls; they do not establish monitoring correctness.   

The plan already calls for missing late-poll, duplicate-terminal and cleanup assertions. Keep those requirements. Add coverage for callback stability under ordinary rerenders and for obsolete asynchronous completion after the selected monitor changes.

Use controlled timers and deferred responses to exercise stream failure with polling still active, simultaneous terminal notifications with one completion operation, terminal-readback failure followed by retry, and disposal on selection change/unmount. Preserve at least one test through `useAgentStudio`; testing only the extracted hook would miss wiring mistakes.

**Benefit:** targets the ordering and ownership risks introduced by extraction.  
**Cost:** a small number of deterministic async scenarios.  
**Simpler alternative:** combine related race assertions in existing fixtures rather than build a new browser orchestration harness.

Do not silently demand stronger scheduling semantics than the baseline currently provides. A newly exposed pre-existing defect should be distinguished from an extraction regression rather than “fixed” invisibly under the cleanup label.

### Reduce redundant gates, not meaningful evidence

For **A1**, the listed six suites are conservative rather than all strictly necessary for changing four import statements. Import/app-composition checks plus relevant worker/event/finalization tests are an adequate slice-level package; the broader runtime checks can be part of the combined final run. A narrowly scoped import-owner assertion is acceptable, but should not grow into architectural lint machinery.

For **A3**, run inventory generation/drift checks and affected renderer tests. Run the entire journey/player/example matrix only when those authored sources or generators are affected. Inspecting the actual generated HTML when labels change is worthwhile, but it can be folded into the bounded browser verification rather than treated as another independent campaign.

For **A2/A4**, retain the synthetic SQL and browser checks. Their role is to verify actual wiring, persistence and lifecycle—not model quality. A skipped dependent check remains pending, not passed. The plan correctly excludes live provider calls and semantic evaluation campaigns; none should be added for this cleanup. 

## 5. A1/A3 correctness and the overall sequence

**A1 is correct and tightly scoped.** The four named worker collaborators import `AttemptResult` through `turn_execution.py`, while `turn_result.py` defines it. Changing those imports clarifies ownership without moving the aggregate or altering its fields. `TurnExecution` imports remain where actually used. There is no basis to describe this as fixing a proven cycle or removing all transitive implementation dependencies.     

**A3 corrects actual overgeneralizations.** CHAR-01 currently describes its output as versioned authored characterization even though active persona content is mutable. MEM-06 and the retention flow also describe the reference-only candidate reply too generally: the natural review path receives it, while typed review does not. Correcting the descriptions and qualifying the edge is preferable to changing code to fit the diagram.    

The proposed order is sensible: remove trivial ownership ambiguity, correct documentation, extract the more mechanical backend protocol, then tackle the more delicate UI lifecycle. A2 and A4 are not architectural prerequisites for one another; keeping independent commits and allowing A4 to be retained/deferred if its interface expands is appropriate. Reconcile source homes afterward without rewriting the historical audit as though it were newly rerun.

**No separate feasibility probe or further consultation round is warranted by the reviewed source.** The remaining uncertainty is whether the concrete A4 implementation stays small and preserves its lifecycle. That can be resolved through the bounded implementation and regression checks already contemplated.

## Inspected scope and evidence limits

I could read the pinned plan, audit, product contract, `AGENTS.md`, development conventions, ADR 0061, relevant inventory sections, the requested backend/frontend source areas and named tests through the GitHub connector. I followed the worker coordination, acceptance/finalization, context/history-admission and persona-authoring/binding paths where they mattered. Large supporting files were inspected in relevant ranges rather than treated as a renewed whole-repository audit.

The GitHub commit comparison from audit baseline `0ec2088ece4bc3b7f539bd56e457a5b69ea02245` to the reviewed revision showed only four documentation-file changes, confirming the supplied documentation-only delta. Anonymous browser availability was **not independently confirmed**: the web route returned a tool-access error, while pinned GitHub connector reads succeeded.

I did not run tests, start services, inspect local state, access private experiment artifacts or investigate either prospective replacement project. Existing tests establish what is asserted in source, not that those assertions passed during this consultation. Historical test results remain reported evidence.

**Overall: this is a worthwhile bounded cleanup, not a replacement-architecture project. Preserve the existing authority boundaries, make A4’s collaboration explicit, and spend the additional verification effort on the few seams that actually move.**