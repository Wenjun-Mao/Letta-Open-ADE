# Natural Conversational Memory: Proposed Design

Date: 2026-09-23. **Status: proposed for independent critique, not accepted.**
No runtime, schema, provider budget, deployment, or release-policy change is
authorized by this document. Existing accepted ADRs remain authoritative.

Read alongside the [source map](../findings/natural-memory-consultation/source-map.md),
[worked conversations](../findings/natural-memory-consultation/design-scenarios.md),
and [research assessment](../findings/natural-memory-consultation/README.md).
Current-code statements refer to `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.

## 1. Recommendation And Product Contract

Keep ADE's PostgreSQL store, reviewer, versioned evidence, and bounded context.
Change their semantics around **natural updates and appropriate recall**, rather
than replace them with a memory framework or require users to operate tools.

The character is Lin Xiaotang (林小棠). A successful conversation feels attentive
and coherent: she responds to what matters now, uses relevant prior information
without reciting a dossier, and does not invent intimacy or shared experiences.
Warm character dialogue does not require pretending to have a physical body,
turning roleplay into biography, or falsely claiming a completed memory operation.

The proposed target has three understandable parts:

1. **Current understanding:** supported facts and a few meaningful ongoing topics.
2. **Evidence:** immutable messages and revisions explaining that understanding.
3. **Working context:** a bounded selection for this reply, not another authority.

This resembles a memory hierarchy in purpose, not a literal human-memory model.
Recent turns and summaries are working context; durable records survive sessions.
The model proposes meaning and writes dialogue. ADE owns identities, validation,
selection, persistence, and observable outcomes.

No user must say "search your memory" or "update my profile." "I moved to Toronto"
should naturally update a prior Beijing residence. "I'm thinking of moving"
must not. Memory success is not equivalent to calling `search_memory`.

## 2. What Exists And What Actually Needs Changing

| Concern | Current implementation | Proposed delta |
| --- | --- | --- |
| Storage | Subject-bound facts, revisions, source spans, embeddings | Reuse; no replacement ledger |
| Updating | Regex chooses add-only, correction-only, or forgetting-only review | General evidence-bound reconciliation of natural statements |
| History semantics | A `correct` revision replaces the current value | Distinguish change over time from correction of an error |
| Preferences | One text value per entity/category | Preserve compatible scoped preferences within that value initially |
| Ongoing context | Concerns/plans/events have no supported durable type | Small continuity-entry extension, separate from profile facts |
| Recall | Automatic vector lookup plus optional fact-search tool | Relevance-first context; optional deeper lookup, not a product prerequisite |
| Removal | Active saved fact excluded; history remains | Preserve this limited contract, not global suppression/erasure |
| Scope | A subject shares facts across characters/versions | Preserve fact sharing; explicitly scope new conversational continuity |

Root cause: the current product model treats useful memory mainly as a small
profile edited through narrow operations. The regex-mode gate and fixed slots
are consistent with that earlier scope, but not sufficient for natural change
and ongoing conversation. Prompt patches alone cannot supply missing lifecycle,
scope, or retrieval contracts. Conversely, the Stage A failure alone does not
prove we need new storage: it exposed a separate tool/evaluation misalignment.

## 3. Ownership And Representation

### Existing profile facts

Keep `MemorySubject`, entities, fact IDs, revision chains, and exact source spans.
The existing supported types remain the first implementation scope. A fact means
"the user explicitly reported this," not independently verified world truth.
Persona templates are not user facts. Quoted third-party speech and fictional
scenes are not automatically autobiographical evidence.

Retain a single `person.preference` value per category initially. Compatible
information is composed without erasing scope: "coffee in the morning; tea in the
evening," not a global switch to tea. This saves a new assertion/key ontology,
but creates a measurable risk of lossy rewriting. If clause preservation fails,
revisit atomic scoped assertions before adding more prompt exceptions.

New semantics on the existing revision path:

| Proposed operation | Meaning | Current projection |
| --- | --- | --- |
| `add` | New supported fact, no matching slot | Active new fact |
| `revise` + `enrich` | Compatible detail; preserve earlier supported clauses | Active next version |
| `revise` + `supersede` | A once-true state has changed | Active next version; predecessor historical |
| `revise` + `correct` | Earlier content was erroneous | Active next version; predecessor disputed |
| `end` | Explicitly no longer true, with no replacement | Inactive; historical, not forgotten |
| `forget` | Explicit removal of saved information | Forgotten; excluded from active recall |

`revise` is one proposal shape with a closed reason, not three executors. Existing
`correct` revisions remain historically labeled; do not reinterpret them in a
backfill. No-op is an empty proposal list. Ambiguity is no write with a diagnostic
reason, not a speculative permanent memory. No confidence-number threshold.

Keep recorded time from ADE. Optionally store the user's exact time phrase on a
new revision ("last Tuesday"); do not fabricate a calendar interval. Completed
change can supersede without an exact date. A historical statement by itself
does not overwrite current state. No bitemporal engine in this proposal.

### Proposed continuity entries, not a second biography

Add these only in the second implementation increment, after fact semantics.
They cover important user-reported plans, concerns, and events that are awkward
as permanent profile slots: Rocky's recovery or an upcoming interview.

Proposed logical shape:

```text
ContinuityEntry
  id, workspace_id, subject_id, definition_root_id
  kind: plan | concern | event
  phase: open | resolved | recorded
  status: active | forgotten
  text, version, current_revision_id, recorded_at, updated_at
ContinuityRevision
  entry_id, version, operation: add | revise | forget
  phase, text, run_id, predecessor_revision_id, recorded_at
ContinuityRevisionSource
  revision_id, message_id, exact span, message hash
```

Plans/concerns use open/resolved; events use recorded. Resolution requires an
explicit update about the same topic. "The interview happened" is an event,
not proof that anxiety or job uncertainty ended. One entry describes one topic;
no generic graph, personality inference, relationship score, or autonomous goal.
Uniqueness is entry ID, not an invented global topic key. Ambiguous matching
does not close an old entry. Provenance and optimistic versions apply exactly
as for facts; a second generic repository framework is not needed.
Forget writes a tombstone with null current text; earlier revision text remains.
Reopening a resolved topic requires an explicit new user update, not passage of
time. Initial extraction records reported plans as plans, never predicted outcomes.

These are three small additive tables, not a rewrite of existing fact tables.
Foreign keys must bind workspace/subject/root, revision parent, and source message
ownership, with checks for allowed kind/phase combinations. IDs alone do not prove
authorization; reads and writes enforce the same scope at the application boundary.
Start with bounded text selection over eligible entries; do not create an
independent vector store or LLM summarizer for every entry. Whether this extension
is justified over retrieving source excerpts is a central external-review question.

Scope is `(workspace, subject, definition root)`, across conversations and persona
versions of that root. Another character sharing the subject gets shared profile
facts, not that character's conversational continuity. A root means a continuing
character; a genuinely different character uses a different root. This is a
**proposed new scope for new entries**, not a reinterpretation of existing subjects.
No user/model-provided tool argument can choose a subject or root.

Do not persist assistant claims as user facts, fulfilled promises, or real shared
events. "We discussed your museum visit" is a transcript-backed conversation
event, not "we visited together." Persisting dialogue events or fictional story
memory is deferred; raw conversation evidence already records the discussion.

## 4. Write Path And Consistency

Keep the current synchronous, post-response reviewer for the first increments.
Do not add a background worker, pre-response extraction call, or pending-memory
bridge without measured latency/consistency need. The current user message is
already available to the conversation model and takes precedence over stale
context when it clearly reports a change; persistence is not yet confirmed.

Proposed successful turn:

1. Accept one immutable user message through existing idempotent run admission.
2. Load the bound subject/character state and assemble reply context.
3. Generate a reply; optionally use curated read-only search. No write claim.
4. Run one reviewer over the current user, reference-only recent users, active
   facts, and eligible continuity entries. Remove the regex-selected add-only
   schema. Explicit removal still needs its own affirmative evidence.
5. Bind new evidence to the current message. References to existing records
   must include expected versions. Preserve predecessor sources for retained
   clauses; older messages help reference resolution, not new unsupported facts.
6. Validate scope, type, evidence span, operation, matching entity, and versions.
   Build embeddings for changed facts through the configured embedding route.
7. Revalidate against locked state; atomically commit memory, final assistant
   message, summary when needed, events, and successful run status.

The same review can add Rocky's breed and update a residence. It must not remove
unrelated facts. "Maybe a Husky" is uncertainty about breed, not the dog's name.
An explicit *plan* can be stored as a plan later; uncertainty about a location
cannot become a location fact. Current uncertainty regexes need type-aware review,
not global disabling of the no-inference boundary.

Exact quotes and lexical overlap are not proof of semantic entailment. ADE can
enforce mechanical invariants; extraction meaning remains model-dependent and
must be evaluated. Do not add a second judge and call that proof. For absent or
ambiguous evidence, the reviewer should return no proposal. An invalid proposal
remains a failed review, not silently dropped successful memory.

Keep the present atomic failure boundary initially: failed generation/review/
embedding/commit leaves the accepted user message and run evidence, but no new
assistant reply or memory writes. This means a reviewer outage can fail a chat
turn. It is a deliberate simplicity tradeoff for critique, not a claim that every
received message is remembered. No automatic catch-up extraction from failed turns.

Conversation leases serialize a conversation. Different conversations sharing a
subject can compute concurrently; finalization locks and rechecks the subject
and relevant versions. A conflict fails rather than silently overwriting or
rerunning a successful generation. Do not hold SQL locks during provider calls.
Reads begun after success see committed state; already-running replies may use
older snapshots. Do not promise linearizable dialogue across simultaneous chats.

Keep ADE-owned `retry_count`, whole-attempt deadlines, cancellation checks, and
budget accounting. Reviewer repair is distinct from a retry and remains zero for
the selected DeepSeek lane. No extra calls or fallback providers are hidden here.

## 5. Recall And Context Construction

Retrieval happens automatically; users need not know its name. The proposed order
is policy/persona, compact profile, relevant continuity/current facts, clearly
dated summary, recent raw turns, then the current message. Memory and historical
text are data, not instructions. Current updates outrank stale summaries for
current-state questions; historical questions need historical attribution.

Preserve the current context-window/reserve policy as the starting budget. Within
the existing 1,500-token profile allowance reserve stable identity facts first,
then relevant current facts. Within the 1,500-token retrieval allowance select
remaining facts and (later) continuity entries together, not 1,500 per new layer.
Keep the current 1,500 summary and 3,000 recent-turn targets as comparison values,
not evidence these are optimal. Full serialized request plus tool schemas and
output/safety reserves must fit the selected model; approximate token counting
needs conservative headroom and boundary tests. Never truncate mandatory policy.

Proposed first selection policy: existing semantic fact search with its calibrated
cutoff, plus deterministic exact known-entity/value matches. Deduplicate by ID and
revision; rank explicit matches before semantic candidates, recency only as a
tie-breaker. Pin only available subject name and current location in the compact
profile, not every recently edited preference. Measure against current recency-first
profile selection before changing defaults. Chinese substring matching is a
bounded exact-match signal, not claims of BM25 or full Chinese lexical search.

For entries, select a bounded candidate set by same subject/root, explicit entity
matches, and most recent updates. Admit relevant open topics first; resolved/event
entries require a matching topic rather than automatic callbacks. This may miss
paraphrases: record misses and compare source retrieval before adding entry
embeddings. "Open" never proves the topic remains emotionally urgent.

The reviewer initially sees the complete eligible active set within a separately
checked input budget. If that cannot fit, report capacity exceeded; do not silently
truncate potential conflicts and invent duplicates. Candidate-only reconciliation
is deferred until scale demands it and exact-target lookup covers omitted slots.

Keep optional `search_memory` for an absent relevant fact, but natural replies do
not fail merely because the model answered from adequate supplied context. Stop
deriving mandatory search from ordinary free-form wording in the proposed product
path. Explicitly required tools belong to declared action/conformance contracts;
unsupported provider contracts fail before generation, not after an optional call.
No provider thinking-mode change is chosen by this memory proposal.

Historical fact recall needs a deliberate extension to the same read tool:
`time_scope=current|history`, default current, with query and bounded limit only.
History searches eligible revision values and returns temporal/attribution labels
and source IDs, never silently substitutes an old value as current. Superseded or
ended values are historical; corrected predecessors are explicitly disputed, not
once-true facts. Forgotten fact chains stay excluded from model-facing search,
even though the operator can inspect retained evidence. Existing revision
embeddings may be reused only for the compatible embedding space; no broad
transcript lookup is implied. Include this contract with increment A's historical
tests, or mark historical-answer capability incomplete rather than guessing.

Do not ship broad transcript search in the first increment. A subsequent bounded
experiment compares fact/entry recall against source excerpts. Eligible sources
must share subject and definition root, precede the current turn, carry speaker/
conversation/time/source IDs, and be treated as untrusted quoted evidence. Archived
source readability is not automatically permission for model retrieval. Decide
archive eligibility and removal implications before enabling this path. No tool
accepts arbitrary SQL, conversation IDs from another subject, or unrestricted URLs.

Memory relevance and conversational use are separate. Even when a fact is supplied,
Lin Xiaotang need not mention it. Recent replies help avoid repeated callbacks;
do not add a persistent "mention score" or novelty scheduler yet. No evidence means
no invented recollection. Recommendations may introduce new ideas without falsely
claiming the user previously preferred them.

## 6. Removal, Nonmention, And Privacy

Preserve ADRs 0022/0026 (Option A): **Remove saved information** excludes the saved
record from active profile/search; messages, summaries, revisions, and backups
remain. It does not promise global nonuse, suppression, or erasure. The same limit
must apply to continuity entries if added. Removal is explicit and target-specific.

"Don't bring this up now" is conversational intent, not a delete command. Honor it
in the current reply using current context; do not promise durable topic blocking.
Ambiguous "forget it" must not trigger data destruction. Use a brief clarification
when necessary; the operator UI can provide unambiguous removal and readback.

Existing forgotten records are not automatically resurrected by background replay.
A new explicit statement may be saved again under Option A; any sticky nonuse
policy would be a separate material product decision. No automatic historical
backfill. Ended/resolved facts are not forgotten and can support historical answers.

Global nonmention/nonuse and actual erasure are deferred, **not implemented through
prompts**. They would need controls across raw turns, summaries, search, derived
records, logs, exports, and backup retention. This proposal does not weaken the
scope of a user's future erasure request or claim that retained history is erased.
Provider calls still disclose selected context externally; evidence and diagnostic
retention should stay minimal, access-controlled, and explicit.

## 7. Delivery, Cost, And Acceptance

| Increment | Deliverable after design approval | What remains unclaimed |
| --- | --- | --- |
| A | Natural fact reconciliation, distinct revision reasons, scoped-value preservation; fixed-evidence reply tests | Concerns, episodic recall, full companion quality |
| B | Bounded automatic context-selection comparison; align natural vs mandatory-tool tests | Source search and unlimited memory scale |
| C | Continuity entries if retained after critique and smaller baseline comparison | Graphs, autonomous outreach, fictional world memory |
| D | Optional source-retrieval experiment only if measured misses justify it | Permission to ingest all history or widen deletion promises |

Record accepted contracts in a concise ADR only after external review and user
decision. Migrations must be additive, preserve all existing facts/revisions and
embedding identities, and label legacy revision semantics unknown where necessary.
Do not replay old user conversations or mutate immutable agent definitions. New
behavior requires freshly bound policies and qualification; old evidence stays old.
Migration tests cover both fresh and populated PostgreSQL. Rollback compatibility
must be checked before deploy, not assumed because columns were additive.

No new generation call per normal turn is proposed for A/B: conversation plus
existing reviewer, with existing optional compaction/tool continuations. Reviewer
input and context tokens can grow; measure request counts, token counts, p50/p95
latency, and cost per successful turn. C reuses that reviewer but expands payload;
D may add retrieval/embedding work and requires a separately approved budget.

Tests must independently inspect **write state**, **selected evidence**, and
**reply claims/quality**. Use the twelve worked arcs as an initial specification,
not a benchmark already passed. Replay chronologically, include two subjects and
two character roots, and never preload future turns. Assert versions, source
links, current/historical status, exclusion after removal, cancellation, races,
and exact attempts. Preserve failures and abstentions; do not reroll for a pass.

Hard checks: no cross-subject/root disclosure, no unsupported committed assertion,
no stale current-state answer in annotated cases, no erased-history promise,
and no fake tool success. Human review judges relevance, restraint, repetition,
and warmth separately, with access to the same source evidence. Fixed-evidence
reply tests cannot establish retrieval or persistence quality. Required-tool tests
explicitly force a supported contract; natural recall tests score meaning instead.

Acceptance thresholds, exact call caps, and migration execution are a later
implementation plan. All currently failed qualification evidence remains intact.
No M3 completion, Stage B/C unblock, main merge, or release promotion follows
from approval of this document alone.

## 8. Alternatives And Questions For Scrutiny

- Reintroduce Letta or adopt Hindsight now: no demonstrated benefit on ADE cases
  yet; operational and contract costs precede evidence. Keep comparison possible.
- Store everything as a narrative: simpler write shape, harder source attribution,
  precise correction/removal, and current-vs-historical enforcement.
- Generic temporal assertion graph: expressive, but much larger than present need.
- Transcript-first with only a tiny profile: credible smaller competitor to C;
  compare relevance, stale facts, scope, token cost, and removal semantics.
- Pre-response review or background review: may improve consistency or latency,
  respectively, but changes failure/commit semantics; defer pending measurement.

Ask Pro particularly whether composite preference values are an unstable shortcut,
whether continuity entries earn three tables, whether root-level scope matches
the product, and whether atomic post-response review is tolerable. Challenge the
design, not only its implementation details. Any simpler design meeting the same
cases and safeguards is preferable. These are proposed defaults for scrutiny,
not questions the user must settle before receiving the critique.
