# Natural Conversational Memory: Proposed Design

Historical design: consult the [current product contract](../product-contract.md)
for settled intent and later exclusions. Section 3's character-root boundary is
retained as PC-03; later privacy-policy and phrase-rule removals supersede the
corresponding proposals here. This document is not the current status summary.

Revision 4, 2026-09-23. **Amended proposal accompanying an implementation plan for review.**
This is a design, not an implementation plan or authorization to change runtime,
schema, providers, budgets, deployment, or release evidence. Accepted ADRs still
govern the running product. No replacement memory framework is proposed.

Implementation anchor: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` (unchanged).
Revision 3 remains at documentation commit
`c01f45a045eb0fdd0fc6b3e18add82f2dbb57024`. See the
[third-round assessment](../findings/natural-memory-consultation/pro-round3-assessment.md),
[source map](../findings/natural-memory-consultation/source-map.md), and
[worked conversations](../findings/natural-memory-consultation/design-scenarios.md).

## 1. Product Goal And Revised Recommendation

Lin Xiaotang (林小棠) should respond like an attentive conversational character:
understand ordinary factual changes, recall relevant details, and avoid repetitive
callbacks or fabricated experiences. Users should not need "search memory" or
"edit profile" commands. Warmth does not require false physical co-presence,
invented biography, or claims that an uncommitted operation succeeded.

Keep **one durable fact system, ordinary conversation evidence, and one bounded
context assembler**. Current understanding is a projection; immutable messages
and revisions explain it. Recent dialogue and summaries supply working context,
not another source of factual authority. Model proposals remain fallible; ADE
owns identities, scope, lifecycle, evidence binding, and transaction outcomes.

This amendment closes same-turn no-save, reply/write agreement, selective lifecycle
recall, and budget/recovery contracts. Full-snapshot admission becomes an experimental
control, not a chosen production requirement. Keep one lifecycle view, one mutation
generation, one shared clarification bundle, and atomic post-response review.
The [bounded plan](../plans/natural-memory-implementation.md) awaits Pro/user review;
no continuity table, background reviewer, or additional normal-turn model call is added.

## 2. Current Foundation And Required Contract Changes

| Area | Current source | Proposed direction |
| --- | --- | --- |
| Facts | Subject-owned typed records, revisions, source spans, embeddings | Reuse; change only required identity/lifecycle contracts |
| Preferences | One record per category | Multiple independently editable preferences within a category |
| Reviewer | Regex selects add-only/correct-only/forget-only schema | Mixed evidence-bound operations from natural speech |
| Evidence | Exact current user span; recent users reference-only | Shared bounded exchange; user assertions/endorsements with role-labeled references |
| Context | String truncation, candidate-ID dedup, limited provenance | Complete records, actual supplied-evidence manifest, protected policy |
| Derivatives | Independent entity labels and narrative summaries | Eligible current identity and explicit lifecycle guards |
| Commit | Post-generation reviewer, atomic assistant/memory success | Retain; memory-generation conflict check and explicit operator-action provenance |
| Continuity | No concern/event schema or transcript-search tool | Existing history first; bounded source experiment before new tables |

Root cause is a mismatch between the unit of meaning, mutation, evidence, and
context inclusion. More permissive prompts cannot fix these contracts. The six
synthetic counterexamples in the assessment establish source-level limitations,
not live dialogue quality. The failed Stage A tool contract remains a separate
conformance issue; neither failure establishes a need to replace PostgreSQL.

## 3. Fact Identity, Scope, And Time

Keep existing subject/entity/fact/revision/source identities. A fact means a
supported **user report**, not verified world truth. Persona content, assistant
claims, quoted third-party speech, and roleplay are not automatically user facts.

Keep singleton identity for the existing singleton types. For preferences, use
an application-generated fact ID as stable assertion identity, alongside existing
entity/category and a bounded user-supported statement including its scope.
"Prefers coffee in the morning" and "prefers tea in the evening" are two records.
Do not generate a universal taxonomy of natural-language scopes or let the model
choose database keys. The same category does not imply replacement.

The reviewer selects an existing ID/version only when the claim and scope clearly
match. Equivalent repetition is no-op; compatible independent claims add records;
an ambiguous match abstains rather than merging or multiplying records. Matching
is a semantic evaluation problem, not guaranteed by UUIDs. An enrichment may
refine one assertion but cannot hide an independently removable assertion in it.

Legacy composite preferences remain explicitly legacy. Do not infer a decomposition
or backfill evidence. Partial removal of a legacy composite is unsupported until
the user explicitly identifies retained assertions: a reviewed atomic replacement
can forget the old record and add the restated independent records. Without that
clarification, offer whole-record removal, not silent clause surgery. No old
composite revision becomes model-searchable through the replacement records.

Shared profile facts remain owned by `(workspace, subject)`. Character dialogue
evidence is additionally bounded by definition root; persona versions retain that
root. A different character requires a new root through an explicit workflow, not
a similarity classifier. Shared knowledge licenses "you live in Toronto," not
"you told me during our conversation" when it came from another character.

Define `person.current_location` for new writes as **reported current residence**,
not a temporary visit. "In Paris for the weekend" does not supersede residence.
Legacy values retain unspecified location meaning unless their existing user
evidence unambiguously establishes residence; never silently relabel a visit.
No stable profile pin should assume otherwise.

Record ADE observation time and, when relevant, the user's exact time phrase.
Do not manufacture exact event dates or validity intervals. A completed move can
update residence without an exact date; a past-tense statement alone cannot replace
the present. Old "tomorrow" remains relative to its source date, not to today.

## 4. Lifecycle: One Record, Explicit Transitions

Proposed projection status: `active`, `inactive`, or `forgotten`. Inactivity records
`ended` or `invalidated`; it is not equivalent to forgotten. Revisions retain the
proposed operation, change reason, expected version, source spans, and predecessor.
The following is a semantic contract, not a new public API schema.

| Operation | Eligible target | Result and historical meaning |
| --- | --- | --- |
| `add` | No matching eligible record | New active record with user evidence |
| `revise(enrich)` | Active | Same assertion refined; do not dispute or erase supported earlier scope |
| `revise(supersede)` | Active | New current value; prior value was reported to have ceased applying |
| `revise(correct)` | Active | New value or null; previous current claim disputed. Null makes projection inactive/invalidated |
| `revise(unspecified)` | Active | New current value; relationship to the old report remains unknown |
| `end` | Active | Inactive/ended; prior report no longer applies, not retracted as an error |
| `reassert` | Inactive | New active revision supported by fresh user evidence; do not turn the gap into continuous truth |
| `forget` | Active or inactive | Forgotten tombstone, null projection; whole fact chain excluded from model fact retrieval |

`revise` is one proposal shape with a closed reason. Null is allowed only for
invalidation/removal/end, never a guessed new value. "Actually I live in Toronto"
can replace Beijing with `unspecified`; no need to infer whether Beijing was once
correct. "Beijing was wrong; I won't say where I live" invalidates without inventing
removal intent. "We broke up" ends the particular relationship, not "has no partner."

No-op applies to equivalent repetition and already-completed targeted removal;
diagnostics distinguish no change, ambiguous target, and unsupported request. An
empty proposal list is not confirmation that something was saved or removed.
Each record changes at most once in a review. A forgotten record is never silently
reactivated. A fresh explicit restatement may create a new record under Option A,
with new evidence, not revival of the excluded chain. Ended records use reassertion
only when identity is clear; otherwise abstain on matching.

Explicit same-turn removal or no-save intent excludes saving that same assertion,
regardless of operation order, restatement, or endorsement: do not forget one ID
and recreate equivalent information under another. Unrelated assertions remain
eligible. No-save alone need not delete an existing record unless removal intent
is clear. This is current-turn eligibility, not lasting suppression or automatic
forget-only mode. A later fresh assertion remains eligible under Option A.

Target discovery must include eligible inactive records, not just active profile
facts. The same scope/version validation applies to both. Intent classification
must not silently turn "forget it" or "don't discuss this now" into removal.

Use one **derived lifecycle view** for reviewer targeting, context guards, and
operator display and selective recall: ID/version, type/entity/category, identifying assertion and scope,
status/reason, and source/revision references. For a null inactive projection,
derive its last identifying assertion from the revision chain: "withdrawn report:
prefers morning coffee; invalidated, not a current preference." This distinguishes
it from withdrawn evening tea without asserting either as true. Do not maintain
another mutable description or expose arbitrary prior revisions. Forgotten chains
are excluded from model-facing views; operator audit access remains separate.
Selective search may return an ended/invalidated current descriptor, not just active
facts: "latest report: this relationship ended," not "has no partner." Bind the
index and result to the current revision, subject, and embedding space. Null terminal
values require the descriptor representation, not reuse of an old active embedding.

**Historical boundary:** correcting an arbitrary earlier revision while preserving
today's value is not included in this first target. It needs a separately specified
append-only historical-dispute contract. Do not implement that as revision of the
present. Accordingly, defer revision 1's generic `time_scope=history` tool and do
not feed old fact chains to the model as historical truth. Operator evidence/history
views remain available. Historical dialogue must qualify source claims or abstain
when current context does not establish their accuracy; retrospective corrections
are visible in raw dialogue but are not claimed as durable historical repairs.
Legacy `correct` revisions are not retroactively classified as supersession/error.

## 5. Evidence For Natural Reconciliation

Every model proposal requires a **current user anchor**. Direct assertions use
current spans. Select one local clarification bundle before generation: current
user message and a contiguous suffix containing at most eight preceding user
messages and intervening committed assistant messages in this conversation.
Use complete messages/exchanges, not excerpts that can hide negation or correction.
Choose the longest suffix that fits both stages after reserving reviewer input for
the permitted candidate reply and all instructions/schemas/output/tool allowances.
Use section 8's selected experimental admission policy. Eight messages is a ceiling,
not a fit guarantee; never shrink only the reviewer's bundle after generation.

Supply the identical selected bundle to both stages and record its IDs in both
manifests. The reviewer may not independently reach back further. Omitted messages
are an explicit gap. A mutation needing a missing antecedent is ineligible; ask
naturally for restatement instead. Current self-contained assertions remain eligible.
If no antecedent fits the chosen admission policy, use current-only dialogue; never drop the current
message or policy. If those cannot fit, fail explicitly. Supply the candidate reply
to review as reference-only, never new user evidence. Defer a dependent mutation
when that reply asks to clarify the same unresolved claim. A detected explicit
contradiction between reply and write interpretation fails the atomic attempt;
do not silently rewrite the reply or add a judge/call. Unrelated questions are not
vetoes. Deferral means no dependent write this turn, not a pending catch-up job.
Shared input does not guarantee agreement; score missed contradictions and false vetoes.

"One of my dogs is a Husky" / "Rocky or Roxy?" / "Roxy" binds two user spans;
the assistant question identifies the referent, not the breed's truth. If only
the assistant introduced Husky, a bare name does not endorse it. By contrast,
"Is Roxy a Husky?" / "Yes, she is" may be a new user endorsement of that one
unambiguous proposition. Current assent supplies authority; the question supplies
its meaning. A generic acknowledgment cannot endorse several unrelated claims,
upgrade "might be," or turn a hypothetical, quotation, or story into biography.
Explicit "yes to the first, no to the second" can resolve separate propositions.
Missing discourse framing remains a limitation; ordinary direct assertions do not
need a new confirmation ritual merely because endorsement is supported.

Proposals distinguish direct assertion, reference resolution, and endorsement.
Validate message IDs, exact offsets/hashes, roles, chronology, ownership, and target
versions. Persist the current user anchor, relied-on earlier user spans, and any
assistant referent as **role-labeled source links**, not fake user quotations.
Assistant links alone never authorize a write. This is an explicit extension of
the current user-only validation contract, reusing message/source identities.
Retained assertion content keeps predecessor lineage, not attribution to a short yes.

Failed/cancelled-turn user text may support only a current explicit resolution
within this same supplied bundle; label its outcome and never imply a completed
exchange. No unrelated catch-up extraction or arbitrary historical fetch is allowed.
Exact spans prove binding, not entailment; semantic tests must count false writes,
missed writes, and unjustified clarification separately. No extra judge proves truth.

## 6. Turn Processing, Failure, And Capacity

Retain: accepted immutable user message -> bounded context -> conversation model
-> one post-response reviewer -> validation/embeddings -> atomic finalization.
The reviewer can propose different justified operations in one message without
regex-selected global modes. The conversation can acknowledge a clear current
user change before persistence but must not claim a committed memory operation.

Generation/review/embedding/commit failure leaves the accepted user message and
failure trace, not a committed new assistant reply or memory writes. Measure this
as chat availability/latency, not merely memory quality. Keep existing cancellation,
leases, idempotency, ADE-owned retry count/deadlines, and request accounting.
Reviewer repair is separately budgeted and remains zero for the selected DeepSeek
lane. No background queue, hidden catch-up, or new normal-turn generation call.

Preflight review capacity before conversation generation where possible. Include
all active and inactive nonforgotten lifecycle views; do not hide possible targets
with an unmeasured selector. Include only entities required by these records or
the selected exchange, not orphan historical metadata or forgotten identity labels.
Record whether failure is fact/descriptor, dialogue, persona/policy, tool-result,
or total-request capacity. No silent target truncation or unlimited-scale claim.

**Operator removal remains available when ordinary review is unavailable.** An
explicitly confirmed command selects exact fact IDs/versions and the displayed
memory generation, including inactive targets. Server-bind workspace/subject;
enforce the existing local-only access boundary, not invented multi-user auth.
Use the same mutation validation, tombstone, and concurrency boundary as review,
without generation, embeddings, or the full packet. Model proposals cannot select
operator authority. All targets validate before any changes: multi-target removal
is all-or-nothing, with action outcome and tombstones in the same transaction.
Persist action ID, request hash, targets/versions, generation, origin, and outcome.
Same-key/same-request replay returns the recorded outcome without reapplying it;
different content conflicts. Failure records cannot coexist with partial effects.
That receipt describes the earlier action, not current absence after a later fresh
restatement. Show a separate current-state readback instead of overclaiming replay.
Typed operator action is a distinct causal origin, not a dummy run or message quote:
current required run/message provenance needs an explicit alternative. This amends
ADR 0022's composer/reviewer route, not a hidden optimization. Removal can reduce
fact pressure, not cure every capacity cause. Direct correction/purge stays deferred.

**One monotonic subject-memory generation protects every nonempty write decision.**
Capture it at user-message acceptance, before provider work. Build the fact/entity/
lifecycle input in one coherent database snapshot with that same generation;
if it has advanced, conflict rather than silently rebasing the accepted turn.
Review uses this snapshot too. A changed generation at finalization rejects the
entire nonempty proposal, even when target versions or final eligible sets match.
Retain ownership and exact target-version checks. Every effective fact lifecycle
or identity mutation, including operator removal, advances generation once in the
same locked transaction as its effects; all mutation entrypoints share this rule.
It is not the existing subject-name metadata version. No-op and idempotent replay
do not advance it. Operator actions bind their selected snapshot in the same way.

This catches changed identity dependencies and add-then-forget (empty-again) races,
at the cost of rejecting some harmless concurrency. No automatic model rerun or
reinterpretation against newer tool results. Conversation leases remain; no locks
span provider calls. Empty/no-op replies may reflect older snapshots, so dialogue
is not linearizable. Fresh reads see commits; a post-removal explicit restatement
can add a new fact, but an in-flight pre-removal proposal cannot resurrect it.
Names are not unique entity keys. The counter is not a summary truth certificate.
Generation conflicts are terminal for that accepted run, including before packet
construction when it might otherwise have been a no-op. Same-key replay returns
the original outcome; do not spend retries on a stale generation or automatically
clone the request. Reconsideration requires a deliberate new user submission.

## 7. Context Integrity Before Selection Quality

Normative instructions have a protected, nontruncatable allocation. Persona and
policy validation must fail explicitly if mandatory content cannot fit. Evidence
is clearly marked untrusted data, not concatenated as new normative instructions;
delimiters do not constitute a proof against prompt injection.

Pack **whole records**, never partial fact strings. Resolve candidate conflicts
against the bound coherent snapshot before packing; refresh stale candidates to
that version or fail. A newer generation requires failure, not a silent initial
snapshot rebase. Never suppress a newer retrieved revision merely because its ID
appeared in profile candidates. Deduplicate against records actually included.
Do not require a globally atomic read snapshot across provider work. Tool results
carry their own versions; newer results do not silently rebase the write snapshot.

Each included record carries fact/revision ID, version, user attribution,
observation time, lifecycle meaning, and shared-profile versus this-character
evidence origin. Source references are not permission to expand another root's
whole message. Derive model-facing entity names from eligible current identity
facts; absent/removed identity uses a neutral opaque reference. Unversioned stored
labels are not alternate current memory. Historical aliases are not silently active.

Record a manifest of exactly serialized IDs/versions/source spans, sections,
omissions, and size estimates. It must describe the final model input, including
tool-returned evidence, not merely search candidates. Check each complete provider
request after policy/schema/tool-result additions and reserve output/safety space.
If a complete mandatory request cannot fit, fail before sending; no silent clipping.
Conservative estimates remain estimates and need model-boundary tests.

Use existing profile/retrieval/summary/recent-turn budgets as experimental baselines,
not fixed quality claims. Correct packing first. Then compare current semantic
retrieval with bounded exact-entity expansion and relevance-based selection at
equal total budgets. Entity-name hits can bring eligible breed/name facts together;
do not assume embedding the word Husky alone solves a query about Rocky.
Do not pin current location universally or claim substring matching is Chinese BM25.
When a complete bound lifecycle snapshot is supplied, skip redundant automatic
embedding/search of that same set. Retain selective retrieval and explicit-tool
conformance. Determine narrative admission before optional compaction solely for
that response, avoiding a provider dependency on a summary that will be withheld.

Natural recall succeeds when the reply has appropriate evidence, whether automatic
retrieval or optional `search_memory` supplied it. Ordinary wording must not create
a hidden mandatory-tool obligation. Explicit required actions use declared supported
provider contracts and separate conformance tests. No DeepSeek thinking-mode switch
is selected by this design; the existing conformance blocker still needs resolution.

## 8. Stale Narrative And Bounded Conversation Evidence

A summary is historical narrative, never certified current by its creation time,
memory generation, or recompaction. Example: A describes partner X; B commits a
breakup; A is first compacted afterwards from old dialogue. Its brand-new summary
can still be stale. Supply current replacements/endings/invalidations independently
of summaries. **No delta-watermark optimization or summary-dependency graph.**

**Control A, full snapshot (provisional):** before admitting prior narrative
(clarification bundle, older raw dialogue, summary, or experimental source window),
include a complete snapshot of the subject's eligible active and inactive lifecycle
views from section 4. Reuse those records across sections without duplicating them;
do not select a supposedly sufficient guard subset by semantic relevance. Active
records state current reports; inactive descriptors identify withdrawn assertions,
not current preferences or verified past truth. Forgotten chains are absent.
No old values from superseded revisions need be replayed to assert the current one.

If the complete snapshot cannot fit, omit optional prior narrative and record the
capacity cause/evidence gap. Dependent clarifications then become ineligible under
section 5; the reviewer cannot privately keep their antecedents. Never omit the
current message or mandatory policy. Without prior narrative, budgeted current
lifecycle selection, including terminal descriptors, may support an answer. Review still requires its
full lifecycle packet; if that fails, the turn fails rather than skipping review.
This intentionally relaxes fail-on-unsummarized-omission only for optional history,
not policy, current input, write evidence, or truthful claims about recall.

**Candidate B, recent-dialogue first (not yet selected):** reserve the shared local
exchange before optional memory, then select relevant current active/terminal views
within the remaining allocation. No summary or older/cross-conversation raw window
in this first comparison. It drops A's global prerequisite for immediate dialogue,
not subject/root boundaries, evidence authority, or full reviewer target visibility.
Missing relevant terminal state may make B worse on stale-state cases; do not call
it equally safe in advance. Neither candidate changes the write contract.

Compare A with and without supplied summaries (diagnostic-only A0) using fixed
nonsummary evidence; compare A0/B as full-versus-selective recent-first admission
packages, not a one-variable causal claim. The [implementation plan](../plans/natural-memory-implementation.md)
defines paired input controls, symmetric usefulness gates for selectable A/B, and
actual-compaction evidence before summary-enabled acceptance. Predeclare the common
operating envelope and whole-record overflow behavior. More saved records, including
inactive ones, must not silently turn a quality failure into a passed abstention.
Adopt neither as universal policy before the plan's evidence/selection gate.

Precedence compares the **same subject, attribute, scope, and relevant time**:
current explicit user updates guide this turn, and committed current state/terminal
guards constrain older narrative. Toronto residence and a Paris weekend visit do
not conflict; Paris can ground "nearby" without replacing residence. Ending the
relationship with X does not imply no partner. Persistence is not universal authority.

This baseline is intentionally over-conservative, not proof of semantic freshness.
Historical corrections without a fact mutation, and unavailable later updates,
can escape the ledger. Dialogue establishes what was reported, not completeness
or verified history. Qualify claims or abstain when the supplied sequence cannot
support them; never widen root/archive boundaries to resolve uncertainty. Option A
still permits forgotten information in raw messages/summaries, not fact guards or
entity labels. End -> forget -> resume old dialogue removes the saved ending guard;
absence does not prove the relationship resumed. Shrinking memory can also readmit
old narrative containing removed information. These Option A limits need explicit
tests and honest copy. Score unnecessary withholding and missed answerability,
including unrelated-memory pressure; safe abstention alone is not continuity.

**Source-window comparison, not production rollout:** first supply fixed eligible
windows to test representation adequacy, then test their retrieval under equal
budgets. Only same-workspace/subject/root, nonarchived conversations, chronological
user messages and committed assistant replies qualify. Include the relevant later
updates before judging an older episode; inability to establish them is an evidence
gap, not permission to present the episode as current. Window/source IDs, speaker,
time, and provenance remain attached. Exclude failed-run exchanges from this baseline.

Exclude other roots' full messages even if a shared fact cites them. Archive removes
a conversation from this experimental source pool, not its already committed shared
facts; operator citation access is separate. Retained raw text may contain forgotten
facts under Option A, so fixtures must expose and test that limit explicitly.
No arbitrary transcript-search endpoint or continuity table is approved here.
If dated excerpts cannot meet the agreed cases at acceptable cost, consider the
smallest source-linked topic representation proven useful; no assumed event catalog.

## 9. Removal, Attribution, And Product Limits

Preserve Option A: remove saved information from active fact selection/search;
messages, summaries, revision evidence, and backups remain. The proposed extension
also permits inactive-record removal. It does not promise erasure or durable nonuse.
An operator command confirms a committed result; a conversational acknowledgment
before reviewer commit does not. Do not promise future autonomous check-ins.

"Don't mention this now" is current conversational intent, not automatic deletion
or a durable topic block. Ambiguous removal needs clarification. A new explicit
restatement can be saved again; no background resurrection from old messages.
Global nonmention/nonuse, physical erasure, fictional world state, inferred
psychological profiles, autonomous outreach, and relationship scores remain out.

Sources are observations with attribution: shared user knowledge is not shared
experience; discussing a museum trip is not visiting together. Important concerns
can inform dialogue from supplied evidence without being declared a new durable
fact type. No source means no invented recollection. Memory can help silently;
not every supported detail should be mentioned. Recommendations may be novel
without pretending they are remembered preferences.

## 10. Review Criteria, Compatibility, And Open Tradeoffs

This revision supplies design boundaries, not implementation steps or live budgets.
Review the expanded chronological arcs alongside the proposed plan. Separate
proposal accuracy, committed state, actually supplied evidence, and reply quality.
Score missed updates and unjustified abstention as well as false writes. Preserve
old fixtures as historical evidence; do not import their unsupported promises as
new expected answers. Require real prior assistant turns for repetition tests.

Deterministic checks cover transition closure, multi-source ownership, labels,
packing/version conflicts, request bounds, removal at capacity, cancellation,
rollback, and races. Model trials remain separately budgeted. Hard boundary checks
prohibit cross-subject access and unauthorized private-root evidence, not permitted
shared facts. Sequential stale-state tests and allowed in-flight stale snapshots
are separate. Human review scores warmth/relevance/restraint with ties and multiple
valid phrasings. A zero-failure finite suite is not universal reliability proof.

Reuse fact/revision/source/embedding storage, extending identity and lifecycle only
where required. Operator-action provenance, role-labeled endorsement references,
and subject-memory generation are proposed additions, not pre-existing capabilities.
Preserve old rows, source links, ambiguous legacy semantics, and embedding-space identity.
No historical extraction replay or immutable-definition mutation. New behavior
requires a new policy binding and qualification; additive SQL alone does not prove
rollback compatibility. Fresh/populated migration tests are specified in the plan.

Normal turns retain one conversation path and one reviewer; compaction/tool work
and requested retries are separately visible. Larger packets, evidence guards,
and scoped history can increase tokens/latency. Measure cost and p50/p95 latency
per successful turn, including reviewer-induced chat failures and capacity rejects.
No new calls or source-index construction are authorized by this revision.

Still challengeable: atomic post-response availability; natural-scope matching for
preferences; complete-guard capacity and unnecessary withholding; the shared
clarification window; harmless mutation conflicts; and deferring retrospective
fact-history correction. These are explicit proposed choices, not hidden tasks.
Continuity tables, generic history search, stronger subject-wide ordering, graphs,
background review, and external memory services must earn their added complexity.

The implementation plan now accompanies this amendment for Pro/user review. Record
an accepted ADR only after approval; no implementation authority, M3 completion,
Stage B/C unblock, release-gate waiver, main merge, or promotion follows from it.
