# Verdict: revise the design, not the foundation

**Keep ADE’s PostgreSQL foundation and the natural-reconciliation direction. Do not adopt composed preference values as the default mutation unit, and do not commit to continuity tables before comparing them with a bounded source-history baseline.**

The largest problem is not insufficient storage. It is that **the unit being updated, the evidence supporting it, and the information actually supplied to the character do not always line up**. Adding broader reconciliation on top of those mismatches would make the system more capable of changing memory without necessarily making it more correct.

The baseline does contain valuable protections: current-fact search filters by subject, active status, and current revision; revisions use expected versions; successful finalization writes memory and the assistant message within one transaction. These are reasons to preserve it, not proof of conversational quality.

## Revisions and evidence inspected

| Scope                             | Exact revision                                                                            |
| --------------------------------- | ----------------------------------------------------------------------------------------- |
| Documentation and proposed design | `243d8d0b4e850aca304eea2699e58ec24d45479b`                                                |
| Implementation and tests          | `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`                                                |
| Discovery branch                  | `codex/character-continuity` resolved to the documentation revision above when inspected. |

I inspected the review brief, complete proposed design, all twelve worked conversations, source map, consultation assessment, relevant imported-report sections, ADRs 0022/0026, and the Stage A offline diagnosis.

Implementation inspection covered the fact registry, review schemas, intent detection, reviewer, policy preparation, memory commits, turn execution, finalization, context construction, compaction, search/tool execution, and relevant memory/source/definition repositories and metadata. Tests inspected included policy, reviewer, context, finalization, repository contracts, PostgreSQL memory lifecycle, relevant executor sections, and selected M1/M2 fixture content.

**Tests were read, not executed.** I accessed no database, running service, credentials, or ignored captures, and did not substitute `main`. Below, *source-demonstrated* means established by the inspected code path—not reproduced against the deployed application. Constructed counterexamples are identified as such. The exact failed Stage A wire request and reply were not available; the repository itself says it cannot establish their contents or whether the museum fact reached the actual prompt.

Runtime filenames below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.

# Prioritized findings

## 1. P1 — Composed preferences are the wrong unit for target-specific revision and removal

**Status: structural design conflict, not merely an unmeasured model-quality risk.**

Design §3 acknowledges lossy rewriting but proposes one composed preference value per category until preservation fails. The registry currently enforces that category-level identity through `fact_key()` and `one_per_entity_per_qualifier`.

Consider:

> “I like coffee in the morning and tea in the evening.”
> Later: “Remove just the morning-coffee preference. Keep the tea preference.”

With one `drink` fact, neither existing operation expresses the request cleanly. Forgetting removes both clauses. Revising to retain tea leaves the coffee clause in the same non-forgotten revision chain, which the proposed historical search may expose. Marking the entire predecessor disputed when only one clause was erroneous similarly loses clause-level historical meaning.

This is more than “the model might paraphrase badly.” **Independent claims require independent lifecycle control.**

**Smallest sufficient correction:** allow multiple preference records within a category, using the existing fact/revision/source tables. Each record should contain one independently revisable, scoped assertion—such as “prefers coffee in the morning”—with an ADE-owned stable ID. Keep singleton semantics for actual singletons.

This does not require a general assertion ontology or model-invented canonical keys. Matching still needs evaluation, but a matching mistake no longer forces unrelated clauses through the same correction/removal operation. Preserve legacy composite records as legacy records; do not invent their decomposition through automatic backfill.

## 2. P1 — Change-versus-error semantics need an “unknown relationship to history” case and a historical correction target

**Status: incomplete design contract.**

The proposed reasons are `enrich`, `supersede`, and `correct`. Supersession makes the predecessor historical; correction makes it disputed. The current policy, meanwhile, permits correction only against an active fact and derives its identity from that target.

Two cases do not fit.

**Present known, history unclear:**

> Saved: Beijing.
> User: “Actually, I live in Toronto.”

Toronto may be sufficiently clear to become current, while the utterance does not establish whether Beijing was formerly correct or always erroneous. Rejecting the whole update preserves a stale present; choosing either historical interpretation invents information.

**Earlier history corrected without changing the present:**

> Beijing → Toronto was previously recorded as a move.
> Later: “Beijing was my sister’s city. I lived in Ottawa before Toronto.”

The current residence remains Toronto. Correcting the immediate current value is the wrong operation; the historical Beijing assertion is the target.

**Smallest sufficient correction:** separate current-value replacement from the relationship asserted about history. Permit an `unspecified` historical relationship when necessary. For retrospective corrections, either add an append-only reference disputing a specifically identified earlier revision while preserving current state, or explicitly exclude that capability from increment A and abstain on affected historical answers.

Also label history as **previously reported state**, not independently verified historical truth. The design’s own definition of a fact as a user report should govern its temporal labels.

## 3. P1 — Context integrity must precede retrieval-ranking experiments

**Status: source-demonstrated defects; the proposal already states several correct principles, but their implementation belongs in the first increment.**

In `context.py`:

* The concatenated system prompt, persona, and memory-control instructions are truncated together. Sufficiently long preceding content can remove the memory rules.
* Profile lines are concatenated and then truncated as text.
* Retrieval deduplication uses **all supplied profile IDs**, not only records that survived packing.
* `retrieved_fact_ids` includes candidates whose text may subsequently be truncated away.

A concrete constructed case: a long first preference consumes the profile budget. A later location record is absent from the rendered profile, but its ID remains in `active_ids`. Automatic retrieval finds that location, and deduplication discards the retrieved copy. **The database and retriever can be correct while the model never receives the answer.**

There is also a revision issue: state loading and search occur separately, while deduplication is by fact ID. A newer retrieved revision can be suppressed by an older profile copy.

**Smallest sufficient correction:** pack complete records, deduplicate against records actually packed, resolve version differences explicitly, and produce a manifest of exactly supplied IDs/revisions. Keep mandatory policy nontruncatable. Check the full request after tool policy, schemas, and continuations are added—not merely the initial context.

Design §5 already calls for nontruncated policy, revision-aware deduplication, and full-request accounting. Move these correctness repairs into A; leave ranking comparisons in B.

## 4. P1 — An ended fact disappearing from active memory does not neutralize a stale summary

**Status: design gap supported by the existing read path.**

Compaction summarizes the previous summary plus incremental messages. Its prompt preserves preferences, commitments, unresolved questions, and relevant assistant responses. The turn path then supplies the conversation’s summary alongside active facts; it does not reconcile summary assertions against lifecycle changes made in other conversations.

Constructed example:

> Conversation A’s summary: “小王 is the user’s partner.”
> Conversation B: “小王和我分手了。” → proposed `end`.
> Resume A: “Help me think about weekend plans.”

The active partner fact is now absent, but A’s summary still supplies the old relationship. **Absence is not an overriding statement that this relationship ended.** Dating the summary helps attribution but does not supply the missing update.

**Smallest sufficient correction:** when selecting historical context, supply relevant lifecycle information from existing revisions—ended relationships and disputed assertions as well as replacement values. For this example, the necessary information is “the relationship with 小王 ended,” not the stronger inference “the user has no partner.”

Do not build another independently maintained truth summary. Derive these status annotations from the existing records, and prevent selected narrative context from silently outranking them.

A related omission: once `end` removes a record from the active reviewer set, **how does the user subsequently remove that saved historical information?** Explicit target discovery must be able to find eligible inactive records. Otherwise “end, then forget” becomes less capable than “forget while active.” This is target-specific saved-memory removal, not a demand for global erasure.

## 5. P1 — Entity labels form an unversioned side channel for stale or unsupported information

**Status: source-demonstrated stale-data delivery; downstream model error remains untested.**

`_stage_identity_entities()` accepts `new_entity_label`, falling back to the proposed value. That label is persisted separately. Correcting or forgetting a name fact does not revise the label, while `MemoryReviewer.review()` continues supplying non-subject entity labels.

For example, Rocky is saved as both a name fact and entity label. A typo correction changes the fact to Roxy, but the reviewer still receives Rocky as the entity label. Removing the name fact likewise does not remove that label from reviewer input.

This is not the accepted retention of an old transcript. It is a **current operational identity hint that bypasses the fact lifecycle**. Additionally, the separate label is not bound to evidence in the same way as the fact value.

**Smallest sufficient correction:** derive generation/reviewer-facing labels from current eligible identity facts. Use an opaque neutral identifier when no current label is available. Retain old names only as explicitly historical evidence or aliases with a defined lifecycle—not as an apparently canonical label.

The semantic validator also deserves modest claims: `_value_supported()` uses substring/token-set overlap, including individual Chinese characters. It cannot establish scope, polarity, ownership, or clause entailment. The proposal correctly acknowledges this limitation. Treat the check as lexical validation, not proof that a rewritten assertion is supported; add adversarial semantic cases rather than another judge presented as certainty.

## 6. P1 — Replace obsolete evaluation contracts rather than accumulating tests around them

**Status: demonstrated test-contract mismatch; the new evaluation direction is sound.**

`test_reviewer.py` explicitly asserts add-only, correct-only, and forget-only schemas. Those tests protect the behavior this proposal intends to remove. They must change alongside the reviewer—not remain as competing obligations.

The PostgreSQL lifecycle test supplies hand-authored proposals and synthetic vectors. It tests persistence, lineage, current-revision filtering, and subject isolation—not extraction quality or semantic retrieval. The context removal/follow-up tests assert that instruction strings reach the prompt, not that a model obeys them.

There are also fixture migration hazards. The older forgetting fixture preloads an assistant promise not to bring up the information again. Preserve that as historical fixture content where useful, but do not promote it into a desired response under Option A.

**Smallest sufficient correction:** maintain separate results for proposed writes, committed state, actually supplied evidence, and reply behavior. An always-abstaining reviewer must not “win” merely by avoiding false writes.

Two hard checks in §7 need qualification: cross-root prohibition applies to character-private continuity, **not intentionally shared subject facts**; stale-answer checks must distinguish sequential turns from the explicitly allowed in-flight stale-snapshot case. Otherwise the acceptance criteria contradict the ownership and concurrency contracts.

## 7. P2 — Root ownership is reasonable for conversational history, but not sufficient to define current world state

**Status: product-contract question and future read-path risk, not demonstrated cross-character leakage.**

The proposal deliberately shares profile facts across characters while keeping continuity entries root-specific. That is coherent for “what this character discussed with this user.” It is less straightforward for plans and concerns presented as current circumstances.

Constructed example: Lin hears that Rocky’s surgery is tomorrow; another character later hears that Rocky recovered. Lin’s private entry can remain open. Root isolation and universally current world-state knowledge cannot both be inferred from those private records.

**Smallest sufficient correction:** define private continuity as **what was reported in that character’s conversations, with dates**, not a second authoritative biography. Shared supported facts can override it; otherwise the character should avoid presuming an old situation still holds.

There are two additional ownership boundaries:

A shared fact licenses using Toronto as the user’s city; it does not automatically license “I remember when you told me about moving” in a character that never had that conversation. Carry enough provenance to distinguish shared-profile knowledge from this character’s discussion.

Likewise, a message may contain both a shared fact and character-private material. Future model-facing source retrieval must not expand a shared fact’s evidence link into unrestricted access to that whole message. The existing operator source reader checks workspace/subject/purpose, not the proposed character-private boundary.

Finally, enforce the distinction between editing an existing character and creating a genuinely different one. `create_next()` versions by definition key; it does not establish semantic character identity. This needs an explicit workflow and tests, not a persona-similarity classifier.

## 8. P2 — Continuity entries have not yet earned a second persistence lifecycle

**Status: unproven architectural hypothesis.**

Three tables are not inherently excessive. The larger cost is the additional concept set: topic matching, kind/phase compatibility, resolution, reopening, removal, root ownership, provenance, capacity, selection, and concurrency.

The proposal also defers persisted dialogue events. Consequently, its new tables do not directly solve “what did we discuss about my museum visit?”—one of the clearest conversational-continuity requirements. The underlying transcript already records that exchange.

**Smallest sufficient correction:** move the bounded source-excerpt comparison ahead of commitment to C’s schema. The design already recognizes this competitor, but C/D’s ordering should not let tables become the default before their simpler alternative is tested.

A concrete case where the simpler design is sufficient:

> “The interview finished. I’ll hear next week.”
> Later: “Still no news.”

A relevant dated excerpt preserves exactly what is known without deciding whether to create an event, revise a plan, resolve a concern, or maintain multiple entries. Within the recent conversation, existing history can already supply it. Across conversations, a bounded same-subject/same-root source lookup is a plausible baseline.

That is a **logical simplicity advantage, not a measured retrieval win**. Source retrieval may miss paraphrases or distant events and may retrieve stale material. Compare those failures under the same budget and eligibility rules.

If entries subsequently win, introduce the smallest topic representation justified by the failures. Do not add a general event catalogue merely because an entry schema makes it convenient.

## 9. P2 — Target-version checks protect writes, not every dependency of a concurrent turn

**Status: partly an explicitly accepted tradeoff; additional race cases remain untested.**

The finalizer revalidates proposed operations against locked current state. That protects targeted changes and active-key collisions. It does not check every fact used to generate the reply, and an empty proposal has no target version to check. The design explicitly permits already-running replies to use older snapshots.

For example, A reads Toronto and generates a reply while B changes the city to Montreal. A can subsequently commit a no-op reply based on Toronto. **Under the proposed contract, this is not automatically a lost-update bug.** Do not accidentally require linearizable dialogue in its tests.

A different case deserves investigation: two conversations both first introduce “my dog Rocky.” Each reviewer can allocate a new entity. Because the keys contain different entity IDs, ordinary active-key uniqueness does not identify the semantic duplicate. Conversely, two pets genuinely can share a name, so automatic name-based merging is unsafe.

**Smallest sufficient correction:** test both cases explicitly. Preserve the documented snapshot contract. For new-entity plans based on an absence assumption, detect relevant concurrent identity changes and fail stale plans rather than silently merging them. Add broader read-dependency checks only when a defined user-visible requirement needs them. Do not serialize provider calls under database locks.

## 10. P2 — Atomic post-response review is defensible, but capacity exhaustion needs an escape path

**Status: intentional failure tradeoff plus an unresolved capacity risk.**

Keeping the synchronous reviewer avoids a pending-memory queue, catch-up ordering, and another consistency model. I would retain it initially.

However, failed review or embedding can discard an otherwise completed generated reply. That consequence is real in the execution/finalization structure and explicitly accepted by the proposal. Measure it as a conversational failure, not merely a memory subsystem error.

The capacity risk is sharper: the reviewer currently receives all active facts; the proposal adds a checked budget and potentially continuity entries. If “eligible active” includes an accumulating set of resolved/recorded entries, ordinary turns eventually risk capacity failure. Moreover, a removal request routed through that same full-set reviewer could fail before it can reduce the set.

**Smallest sufficient correction:** check capacity before expensive generation where possible, define eligibility precisely, and preserve a target-specific correction/removal path that does not require fitting every memory into the reviewer. Do not silently truncate possible conflicts.

Keep failed-run user messages as attributed user evidence where allowed, but do not treat them as proof of a completed discussion or perform hidden catch-up extraction. Preserve explicit committed-status feedback; an empathetic reply or empty proposal list is not confirmation that something was saved.

# Recommended simplified design

I recommend **small independently editable facts, explicit lifecycle history, and one carefully assembled context**, with source retrieval as the next experiment—not a new memory subsystem.

### Durable state

Retain subjects, entities, immutable messages, fact IDs, revisions, source spans, and compatible embeddings. Change preference cardinality so independently revisable claims do not share one lifecycle.

Keep the proposed small operation family, but make historical meaning precise: replacement can leave the past relationship unspecified; ending is distinct from forgetting; correcting older history must not accidentally replace the present. Existing ambiguous legacy revisions remain ambiguous.

Entity labels and summaries remain derivatives. They must not become alternate routes around the fact lifecycle.

### Turn processing

Retain one conversation-generation path and one post-response reviewer, followed by atomic finalization. Remove whole-message add/correct/forget gating so a normal message can contain different justified operations.

The application continues owning IDs, scope, target versions, evidence binding, and allowed transitions. The model handles semantic proposals; neither lexical validation nor an additional judge turns those proposals into proven truth.

### Context

Assemble complete, source-labelled records within the total budget. Separate mandatory instructions from quoted memory/history data. Record what actually reached the model.

Use current facts and relevant lifecycle annotations to interpret older summaries. Keep automatic semantic retrieval as the baseline; test exact-match additions separately. A successful natural reply does not require a ceremonial `search_memory` call.

### Continuity

Use existing recent dialogue and summaries first. Compare a bounded, dated, character-scoped source-excerpt path for cross-conversation gaps. Define source/removal/archive eligibility before enabling it.

Only add durable topic entries when that comparison shows a specific recurring failure they solve.

| Keep                                              | Change now                                                 | Defer                                                     |
| ------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------- |
| PostgreSQL, explicit subjects, immutable evidence | Independently editable preference claims                   | Continuity tables                                         |
| Versioned facts and atomic finalization           | Natural mixed-operation reconciliation                     | Broad transcript retrieval                                |
| Current-revision vector filtering                 | Historical targeting and relevant end/dispute context      | Background extraction and catch-up                        |
| Optional memory search                            | Whole-record context packing and actual-evidence tracing   | Graphs, rerankers, reflection agents                      |
| Option A saved-record removal                     | Lifecycle-safe entity labels and truthful outcome feedback | Global suppression/erasure as a separate product contract |

This does **not** make all history disappear after removal. It preserves the specified limitation while preventing active derivatives from pretending to have stronger currentness or attribution than their sources support.

# Short validation sequence

**1. Settle the small semantic contract with deterministic counterexamples.**
Extend the twelve arcs with partial preference removal; known present/unknown past relationship; correction of an older revision while current state stays unchanged; end-then-forget; stale entity labels; and a shared fact beside character-private text. Annotate expected state and permissible abstention after each turn. No provider calls are needed for this step.

**2. Verify policy, packing, and persistence independently.**
Use hand-authored proposals and fake transports for accepted/rejected operations. Exercise long personas, oversized values, hidden profile records, competing revisions, and exact supplied-evidence manifests. Separately run disposable PostgreSQL tests for populated-schema migration, lifecycle transitions, cancellation, rollback, and concurrent writes. These tests establish mechanics, not extraction quality.

**3. Compare reviewer policies in shadow mode.**
Replay chronological user turns against controlled prior state. Measure false writes, missed updates, wrong targets, wrong historical relationships, and justified versus unjustified abstention separately. Include mixed statements and Chinese paraphrases. Preserve failures and actual request counts rather than repairing the score through rerolls.

**4. Separate retrieval from response quality.**
For retrieval, score the necessary evidence that actually fits the final context—not candidate hits. Compare existing selection, corrected packing/selection, and the bounded source baseline under the same total budget. For response quality, supply identical correct evidence and judge factuality, attribution, restraint, repetition, and warmth, allowing ties and multiple acceptable phrasings.

**5. Run a small end-to-end continuity and failure sequence.**
Test immediate follow-ups, new conversations, two subjects, two roots, compatible persona revisions, concurrent updates, and reviewer/embedding failure. Score committed state, supplied evidence, user-visible outcome, and cost per successful turn together. Keep required-tool conformance separate from natural recall.

**Bottom line:** the proposal’s restraint about frameworks, background work, and graphs is justified. Its weak shortcut is composed preferences; its largest missing read contract is how historical changes constrain stale context. Fix those and the demonstrated context/label problems first. Then require continuity entries to show an advantage over attributed source history before giving them a permanent schema.
