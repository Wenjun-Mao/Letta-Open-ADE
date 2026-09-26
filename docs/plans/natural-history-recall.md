# Natural Historical Recall: Bounded Design And Plan

Status: **Revision 3, approved for bounded H1-H5 implementation and probe**,
2026-09-26, following the user's "agreed, go" and the two conditional-go reviews.
Freeze settings/fixtures and pass relevant offline checks before planned live
DeepSeek/Qwen-embedding work. No production default change or release promotion.
Runtime source inspected: `cece5bedd6032da3ebc3802c7be604eb505967e6`; subsequent
checkpoints through `2be2c7f` changed documentation only.
Product authority: [PC-01 through PC-10](../product-contract.md).
Review basis: [independent reports and source-checked assessment](../findings/natural-memory-consultation/history-recall-review-assessment.md).
Final conditions: [revision-2 review assessment](../findings/natural-memory-consultation/history-recall-r2-review-assessment.md).

This is the single follow-on plan for historical source recovery. The
[compact-reviewer plan](natural-memory-implementation.md) excludes transcript
search; its evidence and open reliability work remain intact. Revision 2 replaces
this plan's initial three-arm scope, not the historical reports or current product
agreements. Revision 3 incorporates the approved final conditions below; acceptance
of this isolated probe is not selection of a production memory policy.

## Outcome And Smaller Scope

Test whether **one automatically admitted historical packet improves natural
continuity over a matched empty-history control**. Lin Xiaotang should recall
relevant dialogue across chats/persona versions without commands, invented shared
experiences or repetitive callbacks. This is a feasibility probe, not selection
of the best retrieval trigger or a production rollout.

ADE already persists messages, definition roots/versions, summaries and fact
provenance. `search_memory` retrieves facts, not transcripts. Reuse PostgreSQL and
the existing one-reviewer/atomic-finalization path. Add one bounded reader and one
history admission path; do not expose a new model tool or public history API.

**Deferred:** discretionary/iterative retrieval, a search-preview/read protocol,
production indexes/backfill, writable notes, episodes, another reviewer or memory
service. If discretion is later justified, start with one combined
`recall_history(query)` operation rather than two stateful operations.

Fact-extraction reliability is a separate limitation: scope loss and truncation
were observed; two low-effort reviewer-only contrasts did not qualify a native
default. Do not change reviewer settings mid-comparison to conceal a failure.
Reader tests and ranking feasibility do not depend on solving general extraction.

## Proposed Read Contract

### 1. Scope And One Coherent Snapshot

Use `load_turn_state()`'s existing short repeatable-read, read-only transaction.
Materialize bounded historical exchanges and their annotations through the same
connection as local messages, facts, entities and summaries. Check accepted subject
generation as today; close the transaction before embedding or generation calls.
No snapshot service, global commit counter or provider-duration transaction.

ADE binds workspace, subject, purpose and character definition root from the run.
The transcript query joins conversation -> immutable definition version -> root;
ordinary persona versions share the root. Do not infer identity from persona text.
Archived conversations remain eligible without restoration. Other roots' transcripts
are excluded; **shared subject facts are not restricted to this character root**.
Enforce scope on materialization and source revalidation, not model-selected IDs.
Evaluation cases use independent subjects/roots as needed to avoid cross-case leakage.

Only successful committed exchanges visible in that snapshot are eligible.
A persisted user message alone is not a completed exchange. Exclude in-flight runs,
rejected candidates and unfinished turns. Local sequence orders one conversation;
timestamps and history handles do not establish global commit order. Readable old
policy bindings need not be executable to supply historical dialogue.

For the bounded probe, retain attempt-local exchange IDs, roles, content hashes,
source times, exact text and annotations. H1 freezes corpus coverage, maximum
exchanges and whole-window selection rules without consulting expected answers.
Record omissions; a relevant exchange outside that scope is a coverage miss.
This does not propose loading every production conversation into memory.

All fixture inputs are target-time state: messages, facts, revisions, annotations,
summaries, query construction and ranking indexes must exclude future turns.
Revalidation checks integrity/existence, not a silent refresh with later content.
Normal memory-generation fencing still handles concurrent fact mutations.

### 2. Source-Relative Lifecycle Meaning

History establishes what was said, not that it was true then or remains true now.
Lifecycle transitions describe changes to saved fact representations, not proof
that the user retracted or misstated the original utterance. A known `correct`
code can still have unspecified meaning for the testimony. Repairing an extraction
that dropped "morning" must not imply the user originally said "all day."
The scope/content of a user correction requires admitted dialogue; codes cannot
supply missing details such as a corrected city or reason for travel. Freeze both
extraction-repair and actual user-retraction contrasts in H1.

| Evidence | Appropriate interpretation | Must not happen |
| --- | --- | --- |
| Explicit old morning-coffee preference; current morning-tea preference | Tea is latest; coffee was an earlier report. | Treat old coffee as current or a drinking habit as preference. |
| Report corrected/invalidated, followed later by the original value | Preserve the intervening dispute; later agreement does not validate the original report. | Infer continuous truth from the matching latest value. |
| Ended state | Describe the supported ending. | Invent an opposite preference or attitude. |
| Removed fact; raw conversation retained | Relevant historical quotation remains possible; removal is not erasure. | Treat the removed chain as active or recreate it from retrieval alone. |
| No usable fact linkage | Attribute source/time and qualify unknown currency. | Treat missing current memory as proof of continued truth. |

Resolve links from the recovered message span to its originating revision, then
through recorded predecessor relationships to the current fact. Looking only at
the latest revision's sources misses operator removal, which can have no message
source. Preserve source authority roles: antecedent/referent support is not itself
an assertion of every sentence in the exchange.

The bounded annotation envelope identifies the linked span, origin, recorded
transitions on its source-to-current path (operation/reason/status and ordering),
and eligible current descriptor. Preserve correction/invalidation even if a later
value matches the origin. Do not replace this with a latest-status label or a
model-written timeline. Unknown/legacy transition meaning stays unknown.
Where provenance branches, preserve the relevant recorded paths rather than
inventing one linear history. Omit the optional window if its required envelope
cannot fit; never silently trim away a material transition.
Use deduplicated bounded revision records and predecessor edges, not enumerated
path timelines or a graph framework.

Apply annotations only to linked claims, not all clauses in a message. Read the
existing revision metadata without exposing forgotten revision values; the retained
transcript is the separate permitted source. Annotations are not write handles.
Do not invent semantic links with regexes, keyword rules or another model call.
Unlinked cross-chat corrections/resolutions remain a retrieval/interpretation
problem, not grounds for a new semantic linkage system.

Freeze minimum sufficient evidence sets for correction/resolution cases: a topic
hit without its needed qualification is not sufficient recall. If later resolution
is absent, past attribution remains possible; a current-state claim is unsupported.
These are semantic evaluation expectations, not a promise of comprehensive
historical truth repair.

### 3. One Combined Internal Read And Ranking Probe

An internal reader ranks the frozen corpus and returns complete, bounded,
role-labelled exchange windows with source identity/time and annotations. There
are no model-visible previews, arbitrary-ID reads or extra expansion protocol.
Source text is attributed data, not executable archived instructions/tool calls.
Whole-window omission is explicit; do not clip away negation or corrections.
Existing summaries may aid location only if captured at target time; they cannot
substitute for exact dialogue or require a new summarization call.

Compare simple literal ranking with semantic ranking on **ranking-development
fixtures separate from scored dialogue cases**. Reuse the embedding client/route
and model artifact, not the fact-space recipe, fact-query instruction, vector table
or fact distance threshold. Keep transcript vectors in the bounded probe, with
identity covering corpus hashes, document/query formatting, model/artifact,
dimensions and normalization/comparison. No permanent transcript schema is needed.
Record corpus-embedding cost separately from per-turn cost. Regenerate any
probe-local vectors when their recipe or corpus changes; never mutate fact vectors.

Measure ranks and sufficient-evidence coverage for Mandarin paraphrases. Freeze
selection/tie-breaking, query formatting, limits and any no-match cutoff before
dialogue scoring; do not tune them on held-out answers. If neither ranker supplies
needed evidence, report that feasibility limit before runtime comparison.
No hybrid framework or extra query-rewrite model call is assumed.

### 4. Admission And Narrow Read-Only Review

Use one admission path against actual serialized generation and projected reviewer
requests, including schemas, escaping, annotation metadata and output/candidate
reserves. Preserve mandatory prompt/persona/current turn, existing local evidence
and lifecycle rules. Optional history uses remaining capacity; it must not displace
the matched control's local/fact context or bypass A/A0's narrative-withholding rule.
Admit fewer whole annotated windows or record omission. No rolling eviction system.

Both arms use the same immutable `H`-capable reviewer binding, model settings and
limits. Baseline receives empty history; automatic receives the admitted packet.
Expose identical history text, roles and annotations to generation and review,
using a request-local `H` map separate from `U/A` support and `F/E` targets.
Do not append cross-chat records to `source_messages`: those become write support
and use conversation-local sequence comparisons.

Extend only the existing conflict decision to cite an exact candidate span and
held `H` source span. ADE checks identity/scope, role, hash and unambiguous quote;
the reviewer judges semantic contradiction and attribution. Historical difference
alone is not conflict: a current tea assertion may differ from old coffee, and an
attributed old-coffee answer may differ from current tea. Existing atomic rejection
remains; no conflict is not proof that an answer is correct.

History cannot become a current anchor, mutation target, earlier writable support,
or fourth write-evidence mode. Independently admitted local messages retain their
ordinary authority even if also present in history. No catch-up extraction.

Freeze these natural multi-turn contrasts, with complete expected deltas:
- Old removed preference -> historical quotation -> "yes, you remembered correctly":
  zero preference mutation; acknowledgment of recall is not necessarily current truth.
- "I currently prefer oolong again": a supported new fact may be added while the
  removed chain stays forgotten.
- A local question explicitly asking about current preference -> genuine affirmative
  answer: existing assistant-supported authority remains available; no short-answer ban.
- "I like that tea from before again", referent available only in `H`: defer mutation
  rather than disguise the referent as direct current evidence. Natural local
  clarification can establish it through existing modes on a subsequent turn.

The reviewer, not phrase code, interprets these meanings. Namespace enforcement
does not guarantee prevention of semantic laundering through a real current quote.
Measure all resulting writes across the follow-up, not just the retrieval turn.

The automatic packet is fixed before generation and persists through any existing
tool continuations. Check actual continuation size; do not reset its allowance,
silently strip evidence from review, or add a history retrieval loop.
Review failure, truncation or contradiction retains existing atomic behavior.

### 5. Availability, Purge Races And Error Ownership

Empty retrieval is successful empty evidence, not proof that history never existed.
Ordinary optional-history unavailability before first exposure may produce an
explicit unavailable result and an existing-context answer/clarification. This
cannot soften mandatory fact retrieval, review or persistence errors.

Before each outbound model packet containing history, validate source existence
and held identity/integrity using a fresh database read, not the original snapshot.
Before first exposure, omit legitimately purged windows and rebuild both packets.
After exposure, discovered source loss or inability to establish required integrity
aborts the attempt; do not silently remove history only from the reviewer.
Also check admitted-source existence during finalization before committing.
Archive changes alone do not invalidate eligibility.

Carry the successful attempt's absolute monotonic deadline to the new finalization
history check and bound that check by remaining time. Expiry/failed validation
prevents success commit; it does not schedule another provider attempt. Do not
move `commit_success()` into generation retries or change acknowledgment-loss
semantics. This bounds the new read, not every pre-existing finalizer operation.
Keep admitted history identities separately from mutation sources and check them
whenever nonempty, including a successful `decisions: []` review.

Required authorization is an awaited fatal guard, never a best-effort observation
callback. Apply it to source-bearing corpus embedding requests too; unused ranking
candidates are not finalization dependencies. If optional history reading fails,
preserve the existing mandatory snapshot rather than reloading newer state.

The guarantee is bounded by each check: a purge after authorization cannot unsend
an already authorized request, and this probe does not promise continuous freshness
or introduce long-held source locks. Test loss visible before each boundary, not
an impossible zero-race guarantee. Existing cancellation, lease, conversation-version
and subject-generation fences still own atomic commit.

Scope/hash mismatch, stale generation, deadline and cancellation stay fatal;
the reader adds no retry, fallback or repair. Timeout uses the existing attempt
deadline. Request observations are non-vetoing; required evidence integrity is not.

No history tool is exposed in this revision. If a discretionary tool is later
approved, first address `executor._execute_tool()`'s ordinary-handler-exception
wrapper so integrity/version/timeout errors cannot become optional unavailability.
Argument validation already fails outside the handler catch; do not claim all
cancellation is swallowed. That future prerequisite is not a broad executor rewrite
required for the automatic-only experiment.

## Checkpoints And Observable Completion

### H1: Freeze The Bounded Contract

After approval, amend the relevant ADR and create an isolated evaluation binding;
do not rewrite old definitions/fixtures or release hashes. Freeze corpus selection,
window/capacity limits, models/settings, ranking-development versus held-out cases,
expected evidence sets, complete deltas and human scoring rules.
Record anticipated turn latency and the criterion for an unacceptable regression
before scoring, not after seeing results; these are evaluation criteria, not spend caps.
Current source scope and archive eligibility remain settled.
Choose one recipe/target setup without fresh target-turn compaction, or freeze
equivalent existing summaries, so paired base packets genuinely match. B is an
allowed experimental choice, not a production-default selection.

### H2: Reader And Ranking Feasibility

Use a helper within the existing state-load transaction. PostgreSQL tests cover:
scope/root joins and shared-fact scope; archived/versioned sources; overlapping local
sequences; and an exchange transaction started before capture but committed after,
which must remain absent from this attempt. Freeze annotations and all local state
in the same snapshot. Verify source-span chains, source-less operator removal,
mixed corrected/unaffected claims, branches and bounded-envelope omission.
Use a concurrently committed exchange with no fact mutation to prove membership
isolation independently of subject-generation fencing.

Run the separate ranker feasibility probe after authorization. Distinguish corpus
miss, ranking miss and insufficient qualification/resolution evidence. Retain exact
ranked IDs/scores/recipe and source hashes. Reader tests need no live native baseline;
ranking calls establish retrieval behavior only, not delivered-dialogue quality.

### H3: Automatic Packet And Reviewer Integration

Add the automatic-only evaluation path and shared `H` reviewer binding; no tool
allowlist or public-route expansion. Extend existing packet/finalization tests,
not a second runtime harness. Verify `H` write references fail and `H` conflict
plus a valid write rejects atomically in either order. Unknown handles and
ambiguous source quotes fail binding, not semantic fallback.

Test serialized Chinese/escaped text, long annotations, output reserves and existing
tool continuation pressure. Both models receive the same admitted evidence.
Pause before generation, continuation, review and finalization to exercise visible
purge, ordinary unavailability, scope/hash errors, timeout and cancellation.
Use committed PostgreSQL readback; no assistant/fact commit after fatal rejection.
Historical instructions remain source data, never system authority.
Include deadline expiry and purge after review on a no-write success candidate;
neither reply nor new revision may commit, and no provider rerun is allowed.
Preserve post-commit acknowledgment-loss tests. Observation failures remain
non-vetoing, unlike authorization failures. Compare actual paired base packets
after removing only history and consistently normalizing fixture identities.
Keep the final actual reviewer capacity check; its projected reply reserve is
not a guarantee, and overflow is not permission to strip already exposed evidence.

### H4: Paired Targets And Short Semantic Sequences

Before scoring delivered dialogue, establish a traceable short native control for
scope, correction, habit/no-write and isolation under the exact frozen binding.
Disclose its failures rather than demanding general model qualification. Invalid
setup cannot count as a scored retrieval success; unaffected independent cases may
still be reported. Do not repair settings midrun or relabel candidate-only results
as successful delivery.

First compare empty-history versus automatic history on independently reseeded,
identical target-time prefixes. Query formatting uses current text and the same
admitted local context, never future metadata or expected answers. The reviewer
binding is identical; only admitted history differs. Keep input/output limits fixed;
do not pad baseline, enlarge automatic limits or equalize actual request counts.

Separately run short chronological follow-ups for acknowledgment/restatement,
ambiguity and repetitive callbacks. Once arm replies/writes diverge, label subsequent
differences as trajectory effects, not isolated retrieval effects. Failed dependencies
leave continuations unrun; preserve every failed/unrun result without success rerolls.

Required cases cover: distant/archived same-root recall across persona versions;
other root/subject/workspace/purpose exclusion; correction then return to the original
value; invalidation and ending; source-less removal, recall acknowledgment and fresh
restatement; `H`-only referent clarification; habit versus preference; resolved
concern with distant resolution; ambiguous antecedents; and an unrelated follow-up.
No callback or tool call is required merely because history exists.

### H5: Interpret Before Expanding

Produce one outcome record per turn with these distinct stages:

| Stage | Required evidence |
| --- | --- |
| Corpus | Eligibility, scope, target-time state and declared coverage/omissions. |
| Retrieval | Topic hit versus minimum sufficient evidence set and rank. |
| Admission | Actual generator/reviewer source packets, sizes and omissions. |
| Candidate | Relevance, attribution, time/scope and repetition given that packet. |
| Review | Complete proposed delta and correct/missed/false conflict, including no decision. |
| Delivery/persistence | Delivered reply and committed full delta, rejection, unavailable or unrun. |

Structural tests gate isolation/provenance/atomicity. Semantic scoring inspects all
values, qualifiers, lifecycle effects and source authority, not just intended targets.
A caught bad candidate is not a delivered success; a false reviewer veto is not a
retrieval failure. Blind arm labels for human review, retain quotes/disagreements;
a model judge is optional/advisory. Keep observations and interpretation separate.
Safe incompleteness and sufficient historical recall are distinct scores. Reuse
the existing harness, not mutation-only scoring that requires new revision IDs:
zero-revision recall can pass, unintended additions fail, and required fresh
updates must not be rewarded for doing nothing. Retain each follow-up's actual
history packet to distinguish repeated history support from local-only continuity.

Report every case, counts, actual latency and context costs. Recommend continuing
only when automatic recovery adds demonstrated useful dialogue without structural
violations, unauthorized writes, stale-current claims or unacceptable distraction/
latency on the frozen criteria. A small clean sample is feasibility, not reliability.
If results are mixed, identify the bottleneck; do not add episodes or a third arm
to manufacture a winner. Retain baseline if value is unproven.

A later discretionary proposal must name a demonstrated need (such as unnecessary
automatic callbacks or query-selection misses) and use the same reader/admission.
Production delivery requires a separate decision on scale, indexing/freshness,
source UI, immutable bindings/defaults and release qualification. This probe does
not close M3/M4, promote evidence or authorize deployment.

## Owners And Verification

- `agent_runtime/turn_memory_snapshot.py` and `persistence/`: bounded reader within
  existing snapshot, root/source joins and revision metadata. No new persistence service.
- `natural_context.py`, `turn_execution.py`: automatic admission and evidence propagation;
  split touched oversized responsibilities rather than growing monoliths.
- `natural_memory_reviewer.py`, `natural_memory_binding.py`, `natural_memory_review.py`
  and structural policy binder: read-only conflict extension and actual packet preflight.
- `executor.py`, worker control/finalization: existing continuations, deadlines,
  cancellation and atomic commit; no discretionary history tool in this scope.
- `workflows/evals/character_memory_dev/`: fixtures, runner, stage results and ignored
  captures; reuse native diagnostics. Tests live in the existing runtime/workflow suites.

Run focused tests, isolated PostgreSQL tests, full Python tests, Ruff/changed-file
formatting and OpenAPI drift. Run web tests/build if shared types or UI change;
none is required merely to conduct the probe. Verify populated/fresh migrations
if schema changes become necessary rather than assumed. Keep the known policy
freshness failure unwaived. No live calls or tests have been run for this revision.

## Revision Coverage And Approval Boundary

### Checkpoint state, 2026-09-26

H1/H2 reader and frozen ranking mechanics have an accepted offline checkpoint.
H3 has an isolated evaluation-only packet and commit fence. Director first
verified 43 focused tests and 15 worker fault cases. The initial combined
PostgreSQL run collided with pending reader fixture runs; the worker suite
passed on its own fresh database, now documented in the README. The H3 follow-up
joined annotation links to H handles, added shared lifecycle guidance and kept
ordinary reviewer packets unchanged. It passed 61 focused tests, 11 evidence/
finalization tests, six reader/lineage/guard PostgreSQL tests and 15 worker
cases. Director then independently verified 46 focused tests and accepted the
H3 follow-up as offline evidence.

H2 now has a source-guarded native embedding path and finite synthetic fixture
runner. The offline integration passed 66 focused tests, four native PostgreSQL
guard tests and 16 worker cases on a separate freshly migrated database; one
worker case exercises the native Qwen recipe with fake embeddings. Its first
worker run failed because `history_ranking` was absent from the trace-stage
allowlist. The trace contract now includes that stage, and the 16-case rerun
passed. The path uses fresh source and subject-generation guards before each
embedding dispatch. Synthetic fixture ranking is explicitly fixture-owned and
makes no native source claim. The frozen live H2 schedule completed: Qwen
cosine recovered both positive development evidence sets where literal missed,
and the adequacy rule selected Qwen. Four held-out cases then retained every
required exchange; their one-to-three-exchange corpora did not pressure the
top-four rank. Both recipes admitted four irrelevant windows on the unrelated
development case. Full scores, hashes, omissions, receipts and latency are
recorded in [the H2 finding](../findings/natural-memory-consultation/history-h2-ranking-feasibility-2026-09-26.md).
Director approved the narrow H4 reviewer-only amendment after the offline
preflight diagnosis. The original H2-hashed contract remains unchanged; the
evaluation-only H4 overlay sets reviewer context to 16,384 and input to 11,469
while retaining 4,096 output and the 5% safety rule. Both arms and controls use
the same envelope. Long follow-up replies may omit optional older windows;
record that as capacity loss. The amended one-shot run subsequently completed
four controls and three paired targets before the empty-arm `user_retraction`
turn exhausted the unchanged two-request conversation tool-step ceiling. It
preserved one failed and 15 unrun top-level cells; all six follow-ups were
also unrun, with no retry. See the [partial H4/H5 finding](../findings/natural-memory-consultation/history-h4-h5-partial-live-2026-09-26.md).
Blind director scoring and any production decision remain pending.

The [offline review correction](../findings/natural-memory-consultation/history-h4-offline-review-correction-2026-09-26.md)
keeps that one-shot result immutable while classifying the failed turn as a
verified bounded rejection rather than an observed integrity violation. The
15 unrun top-level cells plus six dependent follow-ups are 21 unrun native
turns. Future H4 transport counts dispatches without campaign-wide spend
gates, and its scheduler may continue independent cells after this specific
fully evidenced rejection; the two-request per-turn ceiling remains frozen.

[Assessment dispositions](../findings/natural-memory-consultation/history-recall-review-assessment.md)
map to sections 1/2 (snapshot and source-relative lineage), 3 (distinct transcript
recipe), 4 (fresh authority, temporal conflict and capacity), 5 (delivery races and
errors), and H4/H5 (control fairness and stage-level outcomes).
The original reports remain unchanged. Revision 3 adds the accepted H1 testimony
clarification, H3 deadline handoff and the final bounded checkpoint tests. Approval
covers the isolated probe, not production policy/defaults or release qualification.
Unlinked semantic corrections and reviewer quality remain empirical, not missing
permission to add phrase rules. No privacy subsystem, spending gates, new fact types,
extra reviewers, writable notes, episodes or general memory framework.

## Proposed Follow-up: Native Generation Contract Alignment

Status: approved by user for implementation, 2026-09-26. Checkpoint 0 records
the serial offline implementation in the retained isolated checkout before code
edits. Director review remains the gate before the fresh live diagnostic in
checkpoint 4. This is the single plan for this follow-up, not an amendment to
the immutable H4 fixtures, captures, or historical results.

Checkpoints 1–3 passed offline director review. The
[instruction audit](../findings/natural-memory-consultation/native-generation-contract-offline-2026-09-26.md)
records the assembled packet review, binding and proportional checks.
Checkpoint 4 completed one fresh seven-turn candidate diagnostic; the
[source-bound finding](../findings/natural-memory-consultation/native-generation-candidate-live-2026-09-26.md)
records checkpoint 5's bounded dialogue/persistence review and adoption
recommendation. No default or release decision follows from it.

### Outcome and Evidence

Align the generator's description of memory with ADE's actual runtime while
preserving Lin Xiaotang's persona and natural dialogue. Relevant agreements:
PC-01/03/04/05/07/09/10. No product direction is changed.

H4 execution is complete across three campaigns: nine comparable target pairs,
one confounded pair, and one one-sided case. The independent Pro review is AI
advice, not human acceptance. Under the later ADR 0043 reviewer correction, both
ambiguous dog turns deferred writes, explicit updates worked, but one reply
asserted the wrong dog and the removed-tea reply denied admitted testimony.
See the [source-bound diagnostic and offline diagnosis](../findings/natural-memory-consultation/history-target-attribution-diagnostic-2026-09-26.md).
These observations supersede the earlier progress notes above as current status;
they do not establish a production winner or general reliability.

Inspection confirms obsolete editable-memory-block and searchable-transcript
claims in `content/prompts/system/chat/chat_v20260516.py`. Separately,
`context.py` says "Use only committed facts shown in context," without clearly
distinguishing current profile facts from admitted historical testimony. These
are observable instruction conflicts; their causal contribution to a particular
model answer remains unproven.

### Design and Boundaries

Create `content/prompts/system/chat/chat_v20260926.py` as an explicitly selected
candidate, preserving the old template byte-for-byte. Preserve persona, Chinese
dialogue style and output rules; do not redesign character identity or style.
Replace obsolete memory capabilities, rather than append a competing override.
The generator speaks; the existing reviewer interprets writes; ADE validates and
commits. Do not claim a write already succeeded. `search_memory` searches saved
fact descriptors, not transcripts, and lifecycle status remains meaningful.

Teach two general generation rules at their existing owners:

- Where materially plausible alternative referents remain, ask which entity the
  user means without first asserting one. Clear references remain answerable.
- Use admitted, attributed dialogue to answer what was said. Past testimony is
  not automatically current truth. An empty fact search does not negate supplied
  dialogue; unavailable history must not be invented. Operator removal neither
  erases testimony nor authorizes restoring a removed fact.

Audit the assembled base prompt, persona, `context.py`, `natural_context.py`,
`history_admission.py`, tool descriptions in `executor.py`, and `tool_policy.py`.
Clarify conflicting shared wording at its owner; avoid duplicating rules across
every layer. Preserve ordinary no-history behavior and read-only H authority.
Do not change reviewer instructions/schema, validators, retrieval/ranking, tools,
timeouts, retry policy, model profiles, or memory lifecycle semantics.

Shared generation-instruction changes affect assembly beyond the new template;
they must be explicitly recorded and tested, not disguised as a prompt-only
contrast. Existing definition/conversation prompt and persona bindings remain
unchanged. No default switch, migration of existing agents, deployment, release
rebind, or adoption is included. No phrase matching, privacy features, second
reviewer, new retrieval tool, new evaluator framework, or unrelated refactoring.

### Ordered Checkpoints

1. Implement the candidate and minimal owner-level instruction alignment. Record
   a concise ADR with the actual affected paths and supersession scope; link it
   from this plan and the tracker. Keep historical prompt snapshots intact.
   [ADR 0044](../adr/0044-native-generation-memory-contract-candidate.md)
   records the selected candidate and shared generation-instruction effects.
2. Test discovery and explicit candidate selection, old/new immutable bindings,
   and actual assembled native packets with and without H. Cover empty saved-fact
   tool continuation beside admitted testimony, ambiguous alternatives, and clear
   references. Static/fake tests prove wire contracts and persistence mechanics,
   not semantic compliance. Run focused tests, disposable PostgreSQL checks where
   bindings are exercised, Ruff, and OpenAPI drift; run the broader runtime suite
   proportionally. Do not waive the known stale release-policy gate.
3. Adapt the existing `history_target_diagnostic.py` and
   `history_target_diagnostic_run.py` minimally to select the candidate explicitly.
   Preserve the original frozen schedule and captures. A separate diagnostic
   binding records the new prompt and generation-instruction hashes, prior source
   anchors, unchanged reviewer/schema hashes, and provider identities. Reuse the
   seven semantic turns in four isolated subjects; no copied runner or generic
   configuration framework. Check capacity before live dispatch: changed prompt
   size may change H admission even with identical limits. Record actual admitted
   evidence and do not claim matched context if it differs.
4. After implementation approval and offline director review, execute one fresh
   seven-turn diagnostic using pinned DeepSeek/Qwen routes, original per-turn
   ceilings and zero retries/repairs. Use observational request counts, fresh
   disposable PostgreSQL and a separate output directory. Commit/freeze source
   first. No midrun changes or rerolls; stop integrity/setup faults. Independently
   record semantic failures and continue safe independent trajectories. Retain
   each attempt, complete deltas, exact sources and independent DB readback.
5. Review dialogue and persistence separately and document adoption recommendation.
   No automatic default change follows a successful sample. Repeated failures
   warrant a new diagnosis, not an open-ended prompt-patching loop. Any production
   history adoption or release qualification remains a separate decision.

### Observable Acceptance and Interpretation

- Each ambiguous dog turn asks a genuine clarification without asserting a chosen
  dog; both saved names remain unchanged before clarification. Opposite later
  clarifications update only the identified entity.
- An explicit Roxy rename is answered directly and committed immediately, without
  unnecessary clarification or suppression of clear updates.
- The historical tea question acknowledges the admitted earlier mention as past
  testimony, without asserting a current preference or writing one. Fresh renewal
  adds a new active preference while the old record remains forgotten.
- Judge entity, temporal meaning, attribution, revision timing and source support,
  not fixed answer phrases or literal citation-substring equality. A later correct
  state does not excuse an earlier unsupported assertion or write.
- Record captured source availability, completed/delivered turns, and quality as
  separate dimensions. Seven committed turns alone do not pass acceptance. This
  small sequential contrast cannot isolate every instruction's causal effect or
  demonstrate general reliability. Preserve adverse and prior evidence unchanged.

Serial implementation should use the retained `codex/character-continuity`
checkout. No parallel writers or new task is authorized by this planning draft.

## Fresh Ordinary-Conversation Candidate Check

Status: offline checkpoint frozen for director review on 2026-09-26; no native
provider calls, live outcome, release qualification, or default decision. This
small check follows the completed seven-turn candidate diagnostic above. It
tests fresh ordinary conversations under PC-01/02/03/05/09/10 without changing
the candidate or its shared instructions. The [fixture](../../workflows/evals/character_memory_dev/fixtures/history_recall/fresh_conversation_generalization.json)
has SHA-256 `a5385bbe24fdeb78421cf9f3618ede3c804a1983a610de09f924dc31a4162e57`
at this checkpoint; its generation binding has SHA-256
`1d703e701e13fa61491d93fa89048b5405fa89d4c340c8523c8870d69001fa75`.
The four independent trajectories contain 13 native user turns, including all
setup turns. No earlier dog, tea, or jasmine target is reused.

The finite schedule covers a current-location introduction and correction with
recall in a separate chat; two sisters with one ambiguous pronoun and two clear
name updates; recall of a cracked pottery bowl from an archived chat without
turning an event into a profile fact; and an unrelated arithmetic question plus
a different-subject boundary check. Every assistant reply and memory transition
must arise from its actual preceding native turn. No scripted reply, fact,
revision, future statement, or expected answer enters the corpus. The fixture
freezes semantic must/must-not criteria before observation, including calibrated
uncertainty if the relevant source is absent. A missing setup fact makes the
later target setup-limited; it is never repaired or silently counted as a pass.
Evaluate full replies and full fact deltas, not selected answer snippets.

For the live adaptation, reuse `history_target_diagnostic.py` for frozen source
and route checks, transport, worker, disposable-PostgreSQL boundary and manifest;
reuse `history_target_diagnostic_run.py` for `fact_state`, `run_revisions`,
`verified_turn_disposition` and per-turn evidence; and reuse the existing
`_execute_turn` path. Replace only `seed_history_case` with chronological calls
through `PurposeSessionService.create`: first chat creates the definition and
subject, later chats bind that same definition version and subject, and the
scope control creates a new subject under the same definition. Archive the event
source chat through `set_archived` after its completed turn. Keep the runner
adaptation small and local; do not copy the existing several-hundred-line
runner or introduce a general campaign framework.

Before dispatch, bind a clean source revision, fixture and generation binding,
actual prompt/persona/reviewer/schema hashes, route fingerprints and unchanged
per-turn limits. Capture each request, attempt, admitted source, delivered reply,
complete delta and independent PostgreSQL readback. Counts remain observational;
zero retries or reviewer repairs. Preserve a failed turn and skip only its
dependent turns after verified bounded rejection; stop on integrity or setup
faults. The offline checkpoint's fixture test checks count, source binding,
configuration and absence of seeded replies. A later runner requires focused
fake-provider and disposable-PostgreSQL checks before any live execution.

These fixtures are new to this candidate's tuning, but are not statistically
independent and cannot be guaranteed unseen to the base model. Thirteen turns
can expose a failure or support a narrow feasibility observation; they cannot
establish reliability, production history adoption, or release readiness.
