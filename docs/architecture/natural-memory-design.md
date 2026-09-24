# Natural Conversational Memory: Proposed Design

Revision 2, 2026-09-23. **Proposed for a second independent review, not accepted.**
This is a design, not an implementation plan or authorization to change runtime,
schema, providers, budgets, deployment, or release evidence. Accepted ADRs still
govern the running product. No replacement memory framework is proposed.

Implementation anchor: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0` (unchanged).
Revision 1 remains at documentation commit
`243d8d0b4e850aca304eea2699e58ec24d45479b`. See the
[review assessment](../findings/natural-memory-consultation/pro-review-assessment.md),
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

Changes from revision 1:

- Independently mutable preferences get separate records, not composed values.
- Lifecycle distinguishes unknown historical meaning, error without replacement,
  ending, removal of inactive information, and reassertion.
- A current user clarification may bind narrowly to earlier user evidence.
- Correct context packing, provenance, and lifecycle-safe derivatives come before
  ranking experiments. Name/location pinning is not a chosen default.
- Continuity tables and generic historical-fact search are deferred. Compare
  bounded source windows before adopting another durable semantic lifecycle.

## 2. Current Foundation And Required Contract Changes

| Area | Current source | Proposed direction |
| --- | --- | --- |
| Facts | Subject-owned typed records, revisions, source spans, embeddings | Reuse; change only required identity/lifecycle contracts |
| Preferences | One record per category | Multiple independently editable preferences within a category |
| Reviewer | Regex selects add-only/correct-only/forget-only schema | Mixed evidence-bound operations from natural speech |
| Evidence | Exact current user span; recent users reference-only | Current anchor plus bounded supporting user spans |
| Context | String truncation, candidate-ID dedup, limited provenance | Complete records, actual supplied-evidence manifest, protected policy |
| Derivatives | Independent entity labels and narrative summaries | Eligible current identity and explicit lifecycle guards |
| Commit | Post-generation reviewer, atomic assistant/memory success | Retain, with explicit capacity/recovery and concurrency limits |
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

Target discovery must include eligible inactive records, not just active profile
facts. The same scope/version validation applies to both. Intent classification
must not silently turn "forget it" or "don't discuss this now" into removal.

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

Every model proposal requires a **current user anchor**. Direct assertions use current
spans. A clarification may also cite exact spans from up to the preceding eight
user messages in the same conversation, plus the intervening assistant exchanges
for reference resolution. ADE supplies this bounded window; the model cannot fetch
arbitrary past messages or choose another subject/conversation as write evidence.

Example: "One of my dogs is a Husky" / "Rocky or Roxy?" / "Roxy."
The breed revision cites both user spans. The assistant question identifies the
reference, but is not evidence for Husky. If only the assistant introduced Husky,
the same short answer does not authorize importing that unsupported proposition.
This is current clarification, not catch-up extraction of unrelated earlier facts.

The proposal identifies the source-span set and current anchor; ADE resolves
message IDs, exact offsets/hashes, roles, chronology, ownership, and target versions.
Persist all directly relied-on user spans in the existing multi-source revision
relationship. Retained content from an existing assertion carries predecessor
source lineage; it is not silently reattributed to the latest short reply.

Former failed/cancelled-turn text is not automatically replayed. It is eligible
as supporting user evidence only if this current turn explicitly resolves that
specific earlier claim within the window; it never proves a completed exchange.
Quotes, hypotheticals, negation, and uncertain identity must remain uncertainty.
Outside the bounded window, ask naturally rather than invent evidence or widen it.

Exact spans and lexical overlap establish mechanical support, not entailment.
Model meaning can still be wrong. Keep adversarial evidence tests and separate
false writes from missed writes; adding another judge does not prove truth.

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

Preflight the review packet budget before expensive conversation generation where
possible. Initially include all active and inactive nonforgotten subject records
within a checked budget; no unmeasured candidate selector silently hides possible
targets. Ambiguous matching abstains. Packet overflow is an explicit capacity
failure, not truncation of potential conflicts. No claim of unlimited memory scale.

**Capacity recovery:** the operator can select exact fact IDs and versions for
removal, including inactive records. A separately declared, explicitly confirmed
saved-memory removal command validates bound scope and versions and writes the same
tombstone/source audit transaction without model generation, embeddings, or the
full reviewer packet. Its source is a typed operator action, never a fabricated
user-message quote. This is a proposed product control, not a privileged test bypass;
it requires a durable action record linked to the revision, authorized under the
existing local-only access boundary, not a claim of multi-user authentication. Bind
workspace/subject on the server and record action ID, targets/versions, request hash,
local-operator origin, and result. Idempotent replay cannot remove a newer version.
Natural-language removal continues through the reviewer. No broad purge/erasure is added.
Targeted correction at capacity is deferred; removal provides the recovery path.

Conversation leases serialize a conversation. Cross-conversation provider work can
overlap; finalization locks and revalidates targeted changes. This protects stale
mutations, not every read dependency: a no-op reply may use an older snapshot.
Reads begun after a successful commit see the new state; already-running replies
are not promised linearizability. Do not add hidden reruns on a conflict.
New-entity and preference-add proposals depend on absence assumptions. Bind their
relevant entity/identity-revision or preference-category ID/version read sets; reject
stale add plans when those sets change before commit. This can reject harmless
concurrency but avoids silently creating duplicates from stale matching input.
Do not merge same-named pets automatically. No database locks during model calls.

## 7. Context Integrity Before Selection Quality

Normative instructions have a protected, nontruncatable allocation. Persona and
policy validation must fail explicitly if mandatory content cannot fit. Evidence
is clearly marked untrusted data, not concatenated as new normative instructions;
delimiters do not constitute a proof against prompt injection.

Pack **whole records**, never partial fact strings. Resolve candidate conflicts
by current revision before packing; refresh a disputed version or fail context
assembly rather than suppressing a newer retrieved revision with an older profile
copy. Deduplicate against records actually included, not all profile candidates.
Do not require a globally atomic read snapshot across provider work.

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

Natural recall succeeds when the reply has appropriate evidence, whether automatic
retrieval or optional `search_memory` supplied it. Ordinary wording must not create
a hidden mandatory-tool obligation. Explicit required actions use declared supported
provider contracts and separate conformance tests. No DeepSeek thinking-mode switch
is selected by this design; the existing conformance blocker still needs resolution.

## 8. Stale Narrative And Bounded Conversation Evidence

A dated summary is still capable of supplying stale current facts. Relevant endings
and invalidations must reach the context as derived lifecycle guards, not disappear
with the active record. Current user updates and committed state/guards outrank an
older narrative for present-state claims. Guards state the specific change, not a
broader inferred negative (ended relationship with X does not mean no partner).

Proposed conservative baseline: attach a subject-memory watermark when committing
a summary. When the summary predates memory changes, include the intervening
nonforgotten current-state changes/endings/invalidations as bounded guards. A legacy
summary with no watermark is treated as stale. If its dependencies cannot be
covered within budget, omit that summary from generation and mark the evidence gap;
do not silently summarize over it or present it as current. Raw recent messages
remain attributed historical dialogue, not a replacement source of current truth.
An omitted summary does not imply known prior context or successful deep recall.
Apply the guard-or-withhold rule to selected older raw evidence too, not just
summaries. If relevance of a terminal state is unclear, conservatively supply it or
withhold the optional older narrative. Never drop the current user message or
mandatory policy. Expose withheld-history gaps instead of claiming complete context.
This deliberately changes the current fail-on-unsummarized-omission behavior for
optional history only: the reply must acknowledge insufficient evidence when its
answer depends on the withheld material. It cannot masquerade as complete recall.

This conservative policy may over-invalidate summaries. It is preferable to guessing
which free-text clauses changed, but needs scrutiny against a simpler no-summary
baseline. The watermark describes the summary's memory snapshot, not all possible
changes to world truth. It must be captured/rechecked with the source snapshot;
do not stamp a concurrent newer commit onto an older generated summary.

Forgotten values are not emitted as lifecycle guards. Option A still permits old
messages/summary text to contain removed information; this is not global suppression.
Do not use a stale operational identity label as an excuse to bypass removal.

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
Review the expanded chronological arcs before an implementation plan. Separate
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
where required. Operator-action provenance and summary watermarks are proposed
additions with explicit ownership, not pre-existing capabilities. Preserve old
rows, source links, ambiguous legacy semantics, and embedding-space identity.
No historical extraction replay or immutable-definition mutation. New behavior
requires a new policy binding and qualification; additive SQL alone does not prove
rollback compatibility. Fresh/populated migration tests belong in the later plan.

Normal turns retain one conversation path and one reviewer; compaction/tool work
and requested retries are separately visible. Larger packets, evidence guards,
and scoped history can increase tokens/latency. Measure cost and p50/p95 latency
per successful turn, including reviewer-induced chat failures and capacity rejects.
No new calls or source-index construction are authorized by this revision.

Still challengeable: atomic post-response availability; natural-scope matching for
preferences; conservative summary invalidation; the limited multi-turn evidence
window; operator removal's typed-action provenance; and deferring retrospective
fact-history correction. These are explicit proposed choices, not hidden tasks.
Continuity tables, generic history search, stronger subject-wide ordering, graphs,
background review, and external memory services must earn their added complexity.

Only after the second critique and user review should accepted decisions become
an ADR and implementation plan. No M3 completion, Stage B/C unblock, release-gate
waiver, main merge, or promotion follows from this document.
