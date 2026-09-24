# Verdict: targeted corrections, then authorize bounded implementation

**The plan is substantially executable. I would authorize its bounded implementation after tightening the comparison contract, making policy-selection criteria symmetric, and specifying evidence retention for failed reviews.** A further index-compatibility requirement should be added to checkpoint 2’s tests.

The PostgreSQL, lifecycle, provenance, generation-fence, and operator-removal directions no longer require a new architectural decision. The main remaining risk is **implementing the planned experiment correctly but drawing a stronger—or more favorable—conclusion than its evidence supports**.

In particular, **A0/B removes summarization as an explanation for differences, but the recipes do not yet fully specify an admission-only comparison.** And although the design rejects safe-but-unhelpful abstention, checkpoint 6 states its explicit answerability requirement for B, not equally for every selectable policy. Those are correctable specification gaps, not reasons to reopen framework selection.

## Inspected revisions and evidence boundary

| Scope                                                                                                                                                                            | Exact revision                             |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| Implementation plan, revision-4 design/amendment, all 22 scenarios, brief, source map, third-round assessment and both preserved third-round reports; required M3 plans and ADRs | `1a3181c133b7404d6159dbb55468c0a53bb857bd` |
| Previous design: contrasting generation, context and narrative-admission sections                                                                                                | `c01f45a045eb0fdd0fc6b3e18add82f2dbb57024` |
| Implementation and selected relevant tests                                                                                                                                       | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` |

Implementation inspection included turn admission/execution/finalization, memory retrieval, response contracts, source/readback presentation, operator authorization, request budgeting, failure tracing, evaluation cleanup, and the existing UI memory-action logic. I also inspected relevant test portions, including reviewer mechanics and terminal-failure tracing.

**This was static public-GitHub inspection, not test execution or runtime validation.** The required public documents were accessible. I did not inspect local databases, services, credentials, ignored captures, or actual provider requests. The source map’s unavailable operational evidence—including the earlier failed Stage A reply and exact request—remains unavailable; I have not inferred its contents.

Below, checkpoint numbers refer to `docs/plans/natural-memory-implementation.md`. Runtime filenames are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.

# Prioritized findings

## 1. P1 — Freeze the paired recipes more precisely before claiming that they isolate admission or summarization

**Classification:** underdetermined experimental contract, not a demonstrated failed experiment.
**Affected checkpoints:** **1, 4 and 6**.

The three-arm structure is a good improvement. Checkpoint 4 specifies:

* A: complete lifecycle snapshot before prior dialogue/summary.
* A0: the same prerequisite and budget, without a summary.
* B: local suffix first, selected lifecycle records afterward, without a summary or older raw windows.

It also holds models, policies, reviewer visibility, output caps and total limits constant. That is a sound starting point.

However, three details remain capable of changing the interpretation.

### A0’s eligible raw history is not explicitly the same as B’s

A0 inherits A’s behavior except for summaries; B explicitly excludes older raw windows. The previous control contract permits clarification bundles, older raw dialogue and summaries. Consequently, two reasonable implementations could differ on whether A0 includes material outside the shared local suffix.

**Counterexample:** an interview antecedent sits just outside the shared suffix. A0 admits an older same-conversation message; B does not. A0 answers better. That result concerns source availability, not merely the global lifecycle-snapshot prerequisite.

**Smallest correction:** for the A0/B admission probes, explicitly give both variants the same eligible local-message pool and exclude older raw windows from both. Record any intended difference separately.

### Removing a summary can change other included evidence

“Same budget” does not necessarily mean “same non-summary input.” If A0 reallocates the space saved by removing a summary, it may retain more messages or facts.

**Counterexample:** the relevant clarification is omitted in A but fits in A0 because the summary allocation is reclaimed. The result shows the practical effect of that resource-allocation policy; it does not isolate the quality of summarization itself.

**Smallest correction:** name the contrast being measured. For a summary-presence probe, freeze the non-summary sections and their ordering. For a resource-allocation probe, allow repacking but label it as such. No fourth production strategy is necessary.

### B changes a policy package, not just one Boolean prerequisite

B introduces selected lifecycle retrieval and its associated query work, while full-snapshot A/A0 skip redundant retrieval. That is a sensible implementation difference—not something to undo merely for experimental purity. It does mean A0/B measures **full-snapshot admission versus selective, local-dialogue-first admission**, including their selection and cost consequences.

**My recommendation:** retain the three variants and narrow the causal claims. A0/B is a useful no-summary comparison of those admission packages. A/A0 is a conditional summary comparison under a specified common recipe. Neither contrast, by itself, establishes how summaries would behave under B.

The existing final-input manifests can enforce these distinctions. Add assertions about the intended similarities and differences between paired manifests; do not add a strategy framework.

## 2. P1 — Apply the same usefulness gate to every selectable policy, and do not substitute A0 evidence for A without proving equivalence

**Classification:** acceptance-specification gap.
**Affected checkpoints:** **1 and 6**.

Checkpoint 6 requires zero observed hard-boundary violations, correct lifecycle outcomes and absence of forbidden reply claims. It then specifically requires **B** to preserve answerability under unrelated-memory pressure. The surrounding design correctly says missed updates and unjustified abstention must be scored, but the executable selection wording is asymmetric.

### Safety and usefulness must be separate pass conditions

**Counterexample:**

* A withholds the dog-clarification exchange and asks the user to repeat it.
* B preserves the exchange but produces a prohibited stale claim in another case.
* A has no forbidden claims; B fails a factual requirement.

The conclusion cannot be “A passes, therefore choose A” unless A independently meets the required continuity standard. It may instead be **neither meets the agreed product target**.

**Smallest correction:** apply the predeclared answerability requirement to every selectable policy within a common, predeclared operating envelope. Define required task completion independently of what that policy happened to retain.

For example, when policy and current input fit, the full reviewer packet fits, and the short eligible exchange contains the answer, a policy-induced omission is a continuity failure—not a newly “unanswerable” case. Conversely, exceeding the declared reviewer-capacity limit should remain a capacity failure rather than an unfair factual-answer requirement.

Do not redefine the supported envelope after seeing which variant wins.

### Count failed and vetoed turns in the outcome, not only delivered answers

A terminal contradiction veto prevents a bad answer from being committed. That is a valuable protection, but it is not successful conversational continuity.

An implementation that vetoes every difficult turn must not achieve perfect “delivered-answer accuracy.” Report both the correctness of delivered replies and the proportion of scheduled probes that successfully deliver a useful, permitted reply. The plan already intends to record false vetoes and abstentions; this makes their consequence explicit.

### The proposed live campaign does not automatically test A wherever it tests A0

The six paired probes are A0/B. A receives the additional summary comparisons, not explicitly the same six-probe campaign. A0 may stand in for A **where the resulting requests and relevant processing are demonstrably equivalent**, such as a probe in which A would have no summary. It cannot stand in for A simply because both use the full-snapshot prerequisite.

**Smallest correction:** either demonstrate that equivalence per probe or evaluate the actual selectable policy. This need not increase calls where manifest equivalence permits evidence reuse.

### Scripted summaries cannot establish production summarizer quality

The plan explicitly labels this limitation, which is good. But actual compaction is optional in the live campaign. If the selected policy uses generated summaries, the final acceptance record must either include bounded actual-compaction evidence or explicitly leave that capability unaccepted.

**Counterexample:** hand-authored summaries preserve every relevant correction, so A performs well; the actual compactor drops the correction. Testing only interpretation would miss the production failure.

The baseline compaction path is a real additional model operation before dialogue generation, not an inert formatting step.

Finally, preserve the existing stop rules. A stopped or budget-exhausted campaign yields incomplete evidence, not a winner from whichever arm ran first. Where a control limitation is expected, distinguish disqualifying that policy from a hard infrastructure/privacy failure requiring the entire campaign to stop.

## 3. P1 — The planned false-veto and contradiction evaluation needs evidence that survives failed finalization

**Classification:** source-proven observability limitation; engineering/acceptance blocker, not a new memory-model decision.
**Affected checkpoints:** **3, 4 and 6**.

The plan requires the reviewer to return claim-specific permit/defer/contradiction outcomes, and it requires recording false vetoes. A contradiction fails the atomic attempt. Those semantics are coherent. The existing failure evidence path is not yet sufficient to evaluate them.

In the baseline:

* `worker_events.py:append_success_events()` emits `context.built` and `memory.proposed` from a successful `AttemptResult`.
* `provider_tracing.py:_safe_response_shape()` preserves response structure, counts and usage—not candidate reply content or the typed reviewer decision.
* Terminal-failure tests deliberately verify redaction of provider-derived exception text.

### Counterexample

The dialogue model correctly says that Roxy is the Husky. The reviewer incorrectly reports a contradiction and the run fails before success finalization.

If the retained artifacts contain only a validation detail code and response-shape metadata, the evaluator cannot distinguish:

1. a correct veto of an inconsistent candidate reply;
2. a false veto;
3. a malformed reviewer result; or
4. missing evidence in one of the two model inputs.

Counting that run as a generic failure is possible. Measuring the specified false-veto rate is not.

### Smallest sufficient correction

Make diagnostic evidence independent of successful assistant/memory commit.

For the authorized synthetic campaign, retain the actual serialized input manifests, candidate user-visible reply, typed reviewer outcome, affected proposal references and terminal result even when the turn fails. For normal runtime events, preserve bounded structured reason codes and references under the existing privacy boundary.

This is **not** permission to save rejected candidate replies as conversation messages, retrieve diagnostic text as memory, or retain private reasoning. Nor should raw provider exception text become the logging mechanism.

Add a failure-path test proving that the evaluator can classify a deliberately injected false veto while the assistant message, memory mutations and generation advance remain absent.

## 4. P2 — Preserving vector-space identity is not enough to preserve legacy retrieval coverage

**Classification:** concrete migration/integration hazard that should become an explicit test; no proposed implementation has yet demonstrated the failure.
**Affected checkpoints:** **2 and 4**, before live policy comparison.

Checkpoint 2 correctly requires current-revision terminal descriptors and embeddings, and prohibits using an old active embedding as though it represented an ended assertion. It also preserves existing embedding-space identity.

The baseline lookup additionally filters by **`retrieval_policy_version`**, as well as embedding fingerprint, subject, active status and current revision. Preserving rows and vector-space identity alone therefore does not guarantee that the new read path can still select them.

### Counterexample

A populated subject has valid active facts indexed under the old retrieval policy. The new lifecycle selector queries only a new policy identifier.

A’s full-snapshot read still exposes those facts. B’s vector query returns none. The comparison then appears to show that selective admission is inferior, although the problem is index compatibility.

The plan does not require making that mistake. It should explicitly prevent it.

### Smallest sufficient correction

Extend populated-store tests to demonstrate that:

* compatible legacy active records remain selectable under the new reader;
* newly inactive records are retrieved through their terminal descriptors, not predecessor active values;
* forgotten records remain excluded;
* index-format/read-policy compatibility is distinguished from semantic vector-space identity.

The engineering choice may be to retain a compatible active-document format, support explicitly compatible index versions, or perform a separately budgeted reindex. Do not silently relabel incompatible vectors or make SQL migration perform unapproved provider calls.

Use the same coherent populated state for the A/A0/B comparison. Otherwise migration coverage becomes an unrecognized experimental variable.

# Disposition of third-round findings

The following maps the material criticisms in the two preserved third-round reports. **“Addressed” means the amendment and plan now specify the behavior; it does not mean the implementation or model reliability has been validated.**

| Third-round finding                                                                           | Disposition                                        | Assessment                                                                                                                      |
| --------------------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Same-turn no-save/removal must dominate equivalent additions, independent of IDs and ordering | **Addressed**                                      | Assertion-scoped precedence and staging all proposals before conflict checking close the contract.                              |
| Reply/write disagreement needs an explicit outcome                                            | **Addressed semantically; partial operationally**  | Claim-specific outcomes and terminal contradiction behavior are specified. Failed-review evidence needs finding 3’s correction. |
| Inactive information must participate in selective recall                                     | **Addressed**                                      | One lifecycle view and terminal indexing are specified. Add the populated-index compatibility test above.                       |
| Complete-state admission can destroy useful local continuity under unrelated pressure         | **Partial**                                        | It is now a control, not a preselected production rule. A fair, symmetric comparison remains to be completed.                   |
| Removing summaries alone does not remove the global admission prerequisite                    | **Addressed structurally; partial experimentally** | A0 and B now separate the concepts, but paired input recipes need tightening.                                                   |
| Full-snapshot turns perform redundant automatic retrieval                                     | **Addressed**                                      | Checkpoint 4 explicitly skips it without fabricating a search-tool execution.                                                   |
| Compaction can run before deciding whether its result will be admitted                        | **Addressed**                                      | Admission now precedes optional compaction.                                                                                     |
| Reviewer capacity must reserve the candidate reply, not only the shared dialogue              | **Addressed**                                      | Separate reviewer estimation, maximum candidate-reply reservation and actual-request checks are explicit.                       |
| Queued generation conflicts and same-key replay need defined outcomes                         | **Addressed**                                      | Initial/final fences, terminal conflict, immutable replay and deliberate fresh submission are specified.                        |
| End → forget → old narrative can re-expose an unsupported current-state premise               | **Explicitly bounded; behavior untested**          | Option A remains limited removal. This combination is included rather than silently converted into global suppression.          |
| Replaying a successful removal does not prove current absence                                 | **Addressed**                                      | Historical receipt and current readback are distinguished.                                                                      |
| Partial assent and assistant-origin framing must be claim-specific                            | **Addressed as a contract; empirical unknown**     | The planned source roles and negative cases are appropriate; model accuracy remains to be measured.                             |

The source map also continues to mark generic historical repair/search, cross-conversation raw retrieval and continuity tables as unimplemented or deferred. Those are legitimate scope boundaries, not failures to satisfy a capability secretly assumed by this plan.

# Other scrutiny: what is sound, and what belongs in checkpoint verification

## Migration and provenance: the plan now acknowledges the actual schema change

The existing API contract requires a run origin for memory revisions and represents evidence as message spans. Operator removal is therefore a genuine causation extension, not merely another way to call the old endpoint. The plan correctly specifies exactly one run or operator-action origin and role-labelled source evidence rather than fake conversation runs or invented quotes.

I would preserve this approach. The checkpoint-2 tests should enforce origin ownership and source roles at both the application and persistence boundaries. Existing evidence must remain readable without retroactively claiming that ambiguous legacy corrections were known supersessions or errors.

No additional universal provenance framework is necessary. A small explicit origin distinction and the existing revision/source relationships are sufficient for the stated scope.

## Concurrency: retain the single generation fence

Capturing memory generation at accepted input, checking a coherent initial snapshot, and rejecting stale nonempty decisions at finalization is executable. It deliberately rejects some harmless work and even some queued turns that might eventually have produced no write. The plan now states terminal conflict and deliberate resubmission, so this is a product tradeoff rather than a hidden retry policy.

The baseline already centralizes successful finalization inside a transaction and revalidates proposed mutations there. Extending that boundary is preferable to adding semantic absence-read sets or holding locks during provider computation.

The important engineering invariant is that **every effective writer participates**, including operator actions and identity changes. Same-key replay must return the original result without advancing generation or reissuing provider work. Do not let a generic retry wrapper reinterpret a generation conflict as transient.

## Operator API/UI: the authority exists, but update the outcome model—not just the display strings

`require_operator` is a real repository boundary backed by the existing role mechanism. When authentication is disabled, the baseline deliberately treats the local caller as admin; the proposed action-origin field does not change that trust model. The plan correctly calls for reuse and reader-denied tests instead of inventing multi-user authentication.

One concrete integration trap deserves a checkpoint-5 test: the existing UI memory-action code identifies success by a matching **run**, exact `"correct"`/`"forget"` operation and next fact version. That logic cannot simply be reused unchanged for operator-origin receipts or the new revise/reason semantics.

Use the new typed outcomes as the shared contract. Distinguish committed mutation, deferred/no-write claim, terminal failure, replayed historical action and newer current state. In particular, a restatement racing with post-removal readback must not turn an accurately committed receipt into either a false absence claim or a false corruption warning.

This is an engineering integration requirement, not a reason to add another mutation path.

## Cleanup: the plan’s stronger rule is necessary and should be preserved

The baseline evaluation purge deletes source links associated with messages being removed, even where those links belong to another surviving revision. It also removes run-owned revision/predecessor material. A mere reordering of deletes would not preserve a shared multi-conversation evidence chain.

Checkpoint 2 explicitly requires whole-case timing and preservation of sources needed by surviving shared revisions. That addresses the issue at the correct level. The implementation can reject an unsafe individual purge or clean up a complete case-owned dependency set atomically; it need not invent general production erasure.

The exit test should inspect surviving evidence and current pointers, not merely verify that foreign-key exceptions disappeared.

## Rollback and cutover: appropriately honest, with a consequential user-visible limitation

The plan correctly rejects “additive SQL means old binaries are safe.” It requires matched backup restoration or a tested forward fix, drained writers, and an explicitly authorized recovery point/data-loss window. That is a sufficient planning contract; the exact restore procedure belongs to deployment verification.

The proposed old-policy cutover is intentionally disruptive: old conversations remain readable, while new semantics require a newly bound conversation. Retaining the subject transfers eligible saved facts, **not automatically the old conversation’s unsaved interview discussion, summary or clarification context**, because cross-conversation raw retrieval is excluded.

Checkpoint 5 should make that distinction visible and test fresh-send rejection versus historical replay/read access. Do not call the new session seamless continuation or silently copy history to avoid explaining the boundary.

## Budgets: the mechanism is credible; the numerical envelope remains empirical

The current `RequestLedger` reserves before sending, retains interrupted/failed reservations, and binds immutable limits and build/stage identity. `BudgetedTransport` covers generation and embedding calls. This is an appropriate foundation for the proposed shared 96-generation/160-embedding ceiling.

The plan correctly includes setup, indexing, tool continuations, compaction and reviewer calls, and correctly says the ceiling does not guarantee completion. I would not demand a fabricated exact spend prediction now. Require the frozen campaign and fake-transport coverage before separate live approval, and leave an exhausted campaign incomplete rather than borrowing unused historical qualification allowance.

# Simplification recommendation

**Keep one lifecycle representation, one mutation boundary and one assembler.** The proposed architecture largely achieves that.

For this review’s remaining issues, simplification means adding precise contracts—not additional machinery:

* Treat A0 as a diagnostic control unless it is explicitly made a selectable policy.
* Describe A0/B as the declared full-versus-selective admission comparison rather than claiming a stronger one-variable result.
* Reuse final-input manifests to verify paired equivalence.
* Add failure-capable evidence capture to the existing tracing/artifact path, not another review service.
* Preserve one memory-generation rule instead of reintroducing specialized semantic dependency tracking.

I would also soften the blanket instruction to split oversized modules *before* adding code. Extract cohesive responsibilities where the change requires it, but do not turn module-length cleanup into an unrelated prerequisite. The plan already excludes unrelated refactoring; the implementation should follow that narrower intent.

# Authorization recommendation

**Yes—bounded implementation can be authorized after the named corrections.** No competing plan or further framework research is necessary.

Before runtime edits, freeze the paired input recipes and the symmetric usefulness/selection gate in checkpoint 1. Make failure-path evidence capture an explicit checkpoint-3/4 deliverable, and add legacy retrieval compatibility to checkpoint 2’s populated-store tests.

The remaining distinctions are:

| Category                                                   | Treatment                                                                                                                                                                             |
| ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Blocking contract corrections**                          | Paired comparison invariants; equal usefulness requirements and valid evidence transfer between A/A0; acceptance of summary-bearing behavior only on appropriately labelled evidence. |
| **Engineering requirements within authorized checkpoints** | Failed-review observability, compatible lifecycle indexes, origin constraints, complete-case cleanup, typed UI outcomes, cutover/replay tests.                                        |
| **Empirical unknowns**                                     | Which candidate wins, false-veto rate, semantic matching, unnecessary withholding, actual compactor behavior, conflict frequency, latency and cost within the supported envelope.     |

Authorization of checkpoints 1–5 should not preselect A or B. Checkpoint 6’s provider use, subsequent product-policy acceptance, deployment, and release qualification remain separate decisions.

**The plan is close enough to implement after these corrections. Its acceptance process must be equally capable of concluding “A works,” “B works,” or “neither provides useful, trustworthy continuity within the agreed envelope.”**
