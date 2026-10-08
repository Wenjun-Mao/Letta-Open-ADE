## Recommendation

**Proceed with A1, A3 and A2. Revise A4’s ownership description, then proceed with it as the final bounded slice.** The proposed order is sensible, and no replacement architecture, new domain interface or additional consultation is needed first.

The plan’s central choice is sound: separate a demonstrably distinct protocol and a cohesive monitoring lifecycle while retaining runtime coordination and atomic persistence. My recommended changes are narrower than a redesign: make A4’s callback authority explicit, strengthen one consequential compaction-persistence test, and make verification of unchanged documentation assets conditional.

| Candidate | Disposition | What should change |
|---|---|---|
| **A1 — direct `AttemptResult` imports** | **Proceed** | Verify consumer imports, not merely that the defining module can be imported. Do not turn this into an architectural-lint project. |
| **A3 — responsibility descriptions** | **Proceed, with a small wording extension** | Make the proposed authoring/policy distinctions. Also clarify that eligible compaction precedes generation and that request assembly combines independently bound persona content with Memory evidence. |
| **A2 — compaction dispatch extraction** | **Proceed** | The seam is justified. Keep shared response helpers strictly mechanical. Strengthen fixed-input characterization and add one compaction-bearing transaction-failure case. |
| **A4 — focused run monitor** | **Revise, then proceed** | Distinguish monitoring lifetime from selected-state read arbitration and visible UI state. Preserve stable lifecycle callbacks, post-await guards and terminal retry/deduplication behavior. Retain the controller if extraction requires distributing those authorities. |

**Reviewed revision:** `74e993a9b4d50cc367778392aab71937f5b541ff`.

Below, backend filenames are under `services/ade-api/src/ade_api/features/agent_runtime/`; frontend filenames are under `apps/ade-web/src/features/agent-studio/`, unless otherwise stated.

## 1. A2 is a worthwhile protocol extraction

### What the source establishes

`ConversationExecutor.execute` owns conversation requests, enabled-tool validation, finite tool execution, request authorization, observational capture and candidate production. `ConversationExecutor.compact` instead owns a separate system prompt, response schema, provider-specific payload, summary parser and provenance result. These are different protocols, not merely two steps that happen to have different capability labels.  

The surrounding source already supports the split:

- `TurnExecution.execute` constructs separate conversation- and compaction-traced executor instances.
- `compact_turn` uses only `.compact`, retaining eligibility, A/A0 withholding, B disabling and remaining-deadline calculation.
- `compaction.py` already owns planning, parsing, hashes and `ModelCompaction`.
- `RunFinalizer.commit_success` persists the summary and source references inside the runtime-owned success transaction.    

**Assessment:** extracting compaction dispatch reduces the change surface for a future conversation-execution replacement and makes summary-protocol maintenance easier to locate. That is sufficient justification without a runtime defect, file-size threshold or maintenance benchmark.

A focused concrete executor is reasonable. A module-level function would also be adequate; the class itself is not the architectural achievement. Retaining the existing method would remain correct, but I prefer the extraction because the protocol, result and orchestration boundaries already exist.

### The shared helper would not merely relocate the problematic coupling

The proposed shared `_first_choice` and `_merge_usage` mechanics are genuinely common. The former validates the response envelope and returns a copied message plus finish reason; the latter accumulates integer usage values while excluding booleans. A small feature-local `model_response.py` is a legitimate common dependency. It need not own a transport, deployment, retry policy, observer or domain result. 

The important limit is **not to expand “shared response handling” into shared dispatch policy**. In particular:

`execute` awaits authorization and suppresses ordinary observer exceptions. `compact` directly calls its observer, allowing its exception to propagate. Those differences are observable today. Preserve them at their callers rather than introducing a generalized dispatch helper that silently standardizes them. The existing executor test explicitly distinguishes authorization from observation.   

Likewise, leave `initial_conversation_request` shared by admission and execution. `history_admission.admit_history` measures that actual request and preflights the reviewer. Replacing this dependency with a supposedly cleaner duplicate serializer would weaken the capacity boundary. 

**Untested expectation:** the extraction will improve maintenance locality. Source inspection supports that expectation; it does not measure future developer effort or prove behavioral equivalence.

## 2. A4 has a real seam, but its ownership contract needs sharper wording

### The seam is resource lifecycle—not ownership of every run-related value

The coherent unit is the stream/poll lifetime: `eventSourceRef`, `pollRef`, `activeMonitorRunRef`, terminal deduplication, guarded monitoring callbacks and terminal completion sequencing.

However, visible `run` state is also updated by acceptance, cancellation and selected-session refresh. `refreshSelected` updates conversation, memories, activity, bindings and other selected-workspace state. Moving all “run-related” state into a monitor would cross the proposed boundary rather than clarify it.  

I would revise the plan to describe these responsibilities explicitly:

| Responsibility | Owner after extraction |
|---|---|
| Stream/poll resources, currently monitored run identity, terminal in-flight/deduplication state | **Run monitor** |
| Conversation selection, selection epochs, selected-read epochs, pagination/evidence read arbitration | **Existing controller** |
| Acceptance/cancellation policy, visible workspace state, interpretation of committed memory-action outcomes | **Existing controller**, receiving guarded monitor updates |

This does not require another epoch system. The monitor may capture a guard for the current selection lifetime; only the controller advances selection/read epochs.

### Callback checks are not duplicate authority—but callbacks can hide mutations

Today `finishRun` checks ownership before terminal reads, after those reads, and after `refreshSelected`. That sequencing is consequential. An extracted monitor checking ownership only *after* an awaited completion callback returns is insufficient if the callback has already changed controller state while obsolete. 

A narrow completion callback is therefore reasonable, provided that:

**The monitor checks its own lifetime around asynchronous work, while the controller callback checks the supplied ownership guard before its own consequential mutations.** Repeated checks at asynchronous boundaries are not competing lifecycle authorities.

The selected-read epoch must remain separate. Opening evidence in the same conversation advances read arbitration without changing the selected conversation lifetime; that should not invalidate the monitor. Conversely, A → B → A must not make callbacks from the first visit to A current merely because the conversation and run IDs match again. The existing captured selection epoch is what distinguishes those lifetimes.  

There is also an existing return-value subtlety worth preserving rather than redesigning: `refreshSelected` returns `null` for obsolete reads and caught read errors. The monitor must not reinterpret that as verified memory persistence. `memoryActionOutcome` currently requires both a matching committed event and a matching persisted revision before reporting a confirmed change. Keep that interpretation with its existing owner.  

### Preserve callback stability and terminal recovery

One concrete extraction risk is callback identity. The controller’s selection-reset effect depends on `stopMonitoring`. Returning a newly changing stop function from the extracted hook could rerun that effect and clear selected state on unrelated renders. This is a **prospective refactoring risk, not a diagnosed existing bug**. Preserve a stable lifecycle API and verify that ordinary rerenders do not restart monitoring. 

Keep terminal authority in one place as well. Currently terminal handling deduplicates before fetching; errors caught by `finishRun` clear the terminal marker so a later attempt can retry. `event-stream.ts` closes its transport on a terminal event, but polling and application completion are managed separately. Transport closure is not a second owner of terminal readback.  

**Assessment:** proceed with this focused extraction after clarifying those points. Do not extract selected-state readback into another independent hook, add an event bus, or expose a broad collection of controller setters merely to make the file shorter.

The plan’s retain-current-controller escape condition is appropriate. It should be exercised during the ordinary bounded change, not turned into a separate feasibility project or another consultation round.

## 3. Replacement options are preserved, not implemented

The plan correctly distinguishes avoiding new coupling from making Character and Memory interchangeable.

### Clarify the current composition boundary now

I recommend one small addition to the boundary sketch:

> Runtime request assembly combines immutable authored characterization, ADE-wide requirements and scoped Memory evidence, using the actual consumer serialization and capacity rules. Memory evidence delivery does not confer ownership of persona authoring or the Character implementation.

This is a documentation clarification, not a proposed interface. `DefinitionService.prepare` captures prompt/persona content and hashes alongside deployment and policy configuration; `context.py` then combines persona content with mandatory instructions and memory/context material. The resulting definition snapshot is therefore not simply a portable personality document.  

Also state that **compaction currently uses the conversation deployment and provider adapter**. A2 separates implementation ownership without creating independently selectable compaction configuration. That coupling is deliberate enough to retain now; adding another model role solely to anticipate replacement would be premature. 

These clarifications help both replacement directions without assigning a future Character controller to either “guidance only” or full generation ownership.

### Keep the remaining deliberate coupling visible

`AttemptResult` contains concrete context, generation, reviewer, prepared-review, embedding and compaction types. A1 does not remove those dependencies. Likewise, finalization branches on prepared review type, performs source/version checks and coordinates the complete result on one database connection. These are real integration constraints, not defects that cleaner imports solve.  

For **Memory replacement**, changing retrieval or selection while retaining authoritative local state may fit the current contract. Moving authoritative writes into an independently committing external store raises a different consistency and authority decision. The present all-or-nothing success contract cannot simply be assumed to survive behind an adapter.

For **Character replacement**, retain the distinction between authored intent and contextual behavior, plus the current separation between an uncommitted candidate and the persisted reply. Do not freeze a new character-state schema, planning object, tool-loop allocation or additional model phase now. PC-04, PC-05, PC-08, PC-09 and PC-12 already provide the relevant constraints. 

Defer vendor interfaces, migration mechanics, portable persona schemas and revised transaction arrangements until a concrete integration supplies requirements. I have treated Hindsight and `persona_generators` only as supplied product direction, not evidence of compatibility or readiness.

**No product-contract amendment is needed for these cleanups.** A future change to persistence authority or accepted Character behavior would require a separate explicit decision.

## 4. Verification is mostly appropriate, with two material refinements

### A2: characterize the protocol, not merely the existence of hashes

The inspected `test_compaction.py` is useful: it covers contiguous-prefix planning, incremental extension, both provider branches, input-budget rejection and summary-budget rejection. But several provenance checks only establish 64-character hashes; the tests do not fully freeze both payloads or cover malformed response envelopes and compaction-observer failures. 

Before extraction, add two fixed-input expected-request/result fixtures—one per provider branch—and small parameterized edge cases. Expected values should come from pinned literal inputs or independently specified expected payloads, not exclusively from the same helpers under test. Cover the token floor/caps, forwarded timeout, usage filtering, malformed choice/message/summary responses and observer exception behavior.

**Benefit:** catches changes that otherwise look like harmless serialization or helper cleanup.  
**Cost:** low, test-only work using the existing synthetic transport.  
**Simpler adequate alternative to a larger campaign:** these fixtures plus the existing executor tests; no live provider replay or semantic summary evaluation.

The acceptance wording should mean “each branch preserves its own pre-cleanup request,” not that the two intentionally different branches become identical.

### A2: add one failure case that actually contains compaction

The PostgreSQL packet test is strong integration evidence *when run*: it constructs the real worker, triggers A/A0 compaction, checks summary content and sources, checks a compaction trace stage, and verifies B has no compaction dispatch. It can also host a few additional assertions matching persisted provenance fields to the prepared result or captured expected values.  

The inspected fencing tests do something different. They use fresh conversations and assert that cancellation/lease loss prevents assistant and memory-revision persistence. Their commit-fault cases raise before `commit_success`, after it, or during artifact retention. They do **not** exercise summary-bearing rollback after writes have begun inside the success transaction.  

Add **one real-worker, compaction-bearing late transaction failure**, for example a synthetic persistence failure after `create_compaction` has executed but before the success transaction completes. Assert that the attempted success leaves no new assistant, summary/source bundle or successful run/version advancement.

**Benefit:** directly protects the plan’s “prepared before generation, durable only with success” promise.  
**Cost:** a small-to-moderate extension using the existing long-history seed and synthetic transport.  
**Simpler alternative:** a unit spy can show that a rejected attempt does not invoke success persistence, but cannot establish rollback of already-staged SQL writes. There is no need to multiply this into every fault type × every memory policy.

The existing packet test already checks real construction and the compaction trace stage. A second elaborate mocked `TurnExecution` construction harness is unnecessary unless it covers a specific gap that this integration test cannot.

### A4: use deterministic race tests, with a small browser smoke

The async suite actually asserts late-acceptance rejection, obsolete stream callbacks, same-conversation evidence navigation, monitor resumption and obsolete-read error rejection. Its stream is mocked. The view tests inspect static markup and configuration controls; they do not establish asynchronous monitoring correctness.   

The plan’s late-poll, duplicate-terminal and cleanup additions are justified. Make them specifically exercise:

- Deferred poll/terminal results across A → B → A, including selection changes during terminal readback.
- Competing terminal notifications and a failed terminal fetch followed by successful retry.
- Resource closure and timer removal, stream failure with polling retained, and unrelated rerenders without monitor restart.

These are best expressed with deferred promises and fake timers. Preserve the existing same-conversation evidence test and strengthen its resource-count assertions.

**Benefit:** protects the ownership boundary rather than merely testing the new filename.  
**Cost:** moderate focused test work, without services or model calls.  
**Simpler adequate browser requirement:** one synthetic walk for actual hook/stream/view wiring. Repeating every deterministic race manually in a browser is unnecessary.

### Make broad checks conditional rather than removing useful tests

The existing lock-order SQL test is a genuine multi-connection regression for the unchanged lock helper. It is useful to run when the environment is available, but it neither fills the compaction rollback gap nor justifies expanding lock-order testing for this extraction. 

For A3, run the canonical renderer checks and tests governing changed artifacts. Make the journey/example/player suite conditional on those authored sources or generated outputs being affected. Running a cheap broader documentation suite once is reasonable; making every unchanged asset a blocking prerequisite is not necessary.

Keep “skipped is not passed.” But do not make unrelated SQL/browser resources prerequisites for independently verified A1 or documentation work—the plan already allows those slices to proceed separately. 

## 5. A1/A3 correctness and sequencing

**A1 is correctly scoped.** The defining module is `turn_result.py`, while the four named worker collaborators import through `turn_execution.py`. Changing their imports addresses incidental ownership/navigation coupling without changing the result.     

A direct-import test alone would already pass before cleanup. Conversely, requiring `turn_execution` to have no `AttemptResult` attribute would be inappropriate because it still imports the type for its own use. A targeted consumer-import check—simple source inspection or a tiny existing-test assertion—is sufficient.

**A3 is also correct.** Active persona storage updates existing rows; immutable runtime definition creation is separate. The inventory currently obscures that distinction and describes candidate-reply input too generally, whereas `TurnExecution` passes a candidate to natural review but not typed review.    

The retention-flow step also places “Generate candidate reply” before mentioning compaction in the same sentence. Reword it to make optional pre-generation compaction clear without changing topology, statuses or capability IDs. 

**Keep A1 → A3 → A2 → A4.** A1 and A3 provide inexpensive clarity; A2 has the stronger extraction case; A4 carries more lifecycle risk and is independent of the backend improvement. Update moved source-home references with the relevant implementation slices, leaving final reconciliation to catch omissions rather than repair deliberately stale navigation.

No replacement-design milestone should gate this sequence, and A4 should not become a prerequisite for retaining the earlier wins.

## Inspected scope and evidence limits

GitHub reads successfully returned the pinned plan, audit, product contract, `AGENTS.md`, development conventions, ADR 0061 and relevant inventory entries/flows. I inspected the named backend execution/compaction files, focused worker and finalization paths, acceptance, context/admission, relevant definition/authoring code, the requested backend test areas and the three discussed SQL suites. Frontend inspection covered the controller, stream/API helpers, memory-action interpretation, relevant view code and the async/static-view tests.

The [GitHub comparison from the audit baseline to the reviewed commit](https://github.com/Wenjun-Mao/Letta-Open-ADE/compare/0ec2088ece4bc3b7f539bd56e457a5b69ea02245...74e993a9b4d50cc367778392aab71937f5b541ff) confirms that the intervening changes are documentation-only.

Direct anonymous raw-web fetches failed through the web tool; therefore, I confirm pinned source access through the GitHub connector, **not an independently successful anonymous-access check**. No local files, services, credentials, private experiment artifacts, prior conversation history or `persona_generators` source were inspected.

No tests, browser interactions or provider calls were run. Historical test results remain reported evidence, not results reproduced here.

**Bottom line:** the cleanup is worth doing with the narrow revisions above. It improves ownership and maintenance locality while preserving meaningful replacement options—but it does not establish replaceability, behavioral qualification or release readiness. This is an advisory recommendation, not implementation approval.