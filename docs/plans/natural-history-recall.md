# Natural Historical Recall: Bounded Design And Plan

Status: **Revision 2, proposed for Pro review**, 2026-09-25. No implementation,
model calls, default change, or release promotion is authorized by this document.
Runtime source inspected: `cece5bedd6032da3ebc3802c7be604eb505967e6`; subsequent
checkpoints through `2be2c7f` changed documentation only.
Product authority: [PC-01 through PC-10](../product-contract.md).
Review basis: [independent reports and source-checked assessment](../findings/natural-memory-consultation/history-recall-review-assessment.md).

This is the single follow-on plan for historical source recovery. The
[compact-reviewer plan](natural-memory-implementation.md) excludes transcript
search; its evidence and open reliability work remain intact. Revision 2 replaces
this plan's initial three-arm scope, not the historical reports or current product
agreements. Proposed read semantics below still require approval.

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

### H2: Reader And Ranking Feasibility

Use a helper within the existing state-load transaction. PostgreSQL tests cover:
scope/root joins and shared-fact scope; archived/versioned sources; overlapping local
sequences; and an exchange transaction started before capture but committed after,
which must remain absent from this attempt. Freeze annotations and all local state
in the same snapshot. Verify source-span chains, source-less operator removal,
mixed corrected/unaffected claims, branches and bounded-envelope omission.

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

## Revision 2 Coverage And Remaining Review

[Assessment dispositions](../findings/natural-memory-consultation/history-recall-review-assessment.md)
map to sections 1/2 (snapshot and source-relative lineage), 3 (distinct transcript
recipe), 4 (fresh authority, temporal conflict and capacity), 5 (delivery races and
errors), and H4/H5 (control fairness and stage-level outcomes).
The original reports remain unchanged. This draft adds no accepted product decision.

Review the source-relative envelope, historical acknowledgment versus fresh assertion,
bounded purge guarantees and automatic-only comparison before implementation approval.
Unlinked semantic corrections and reviewer quality remain empirical, not missing
permission to add phrase rules. No privacy subsystem, spending gates, new fact types,
extra reviewers, writable notes, episodes or general memory framework.
