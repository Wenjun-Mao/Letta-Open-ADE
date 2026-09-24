# A Simple Memory Architecture for Natural Conversational Continuity

## Executive answer

**The smallest coherent architecture is not a graph, a reflection agent, a vector database, or a framework. It is an evidence-preserving memory ledger with two retrieval paths.**

For the ADE design described in the brief, I recommend keeping PostgreSQL and the existing subject/message ownership model, then making one conceptual change: treat durable memory as **versioned assertions derived from evidence**, not as a mutable bag of “facts.” Keep recent dialogue as working context; maintain a compact **current-state view** over those assertions; and add a second, sparse retrieval path for **episodes/source conversation** that covers memorable experiences which do not fit a fixed fact schema. Use the existing reviewer call to propose state transitions rather than adding another agent or another model call.

The resulting logical architecture is:

| Layer | Responsibility | What it must *not* become |
|---|---|---|
| **Working context** | Persona, recent dialogue, bounded current-state profile, a small automatically retrieved set | The source of durable truth |
| **Memory ledger** | Current and historical assertions, uncertainty, changes, corrections, provenance, event/observation time | A destructively updated “latest facts” table |
| **Episode/source retrieval** | Recover old shared conversations and experiences that were not promoted into the current profile | Another always-in-context summary |
| **Original transcript** | Authoritative evidence, reprocessing, auditing, deletion lineage | Unfiltered fallback that can resurrect forgotten material |

These can all remain **logical layers inside ADE-owned PostgreSQL**; they do not require four databases or a framework replacement.

The key record should be approximately:

`memory_subject + content + kind + state + observed_at + valid_from/valid_to + certainty + source_message_ids + revision/supersession links`

The `kind` can remain partly typed but should allow a narrative fallback. The `state` should distinguish at least current, uncertain/pending, resolved, superseded, retracted/corrected, and forgotten. The critical distinction is that **“changed” is not the same as “was false.”** “I moved from Ottawa to Montreal” should preserve Ottawa as formerly true; “I never lived in Ottawa—that was my sister” should mark the old assertion as erroneous. Hindsight’s explicit separation of occurrence time from mention time is the strongest published mechanism here, but its full four-network graph architecture is not required to obtain that benefit. citeturn21view3turn21view4

For ordinary conversation, the existing reviewer should be changed from “is this an explicit correction/removal?” to a broader reconciliation operation:

**NEW · ENRICH · SUPERSEDE · CORRECT · RESOLVE · UNCERTAIN · NO-OP**

That directly addresses the brief’s stated weakness: natural changes are often expressed without correction language. The application, not the model, should remain responsible for validating subject scope, source existence, allowable transitions, and destructive operations. Mem0’s 2025 paper is useful evidence for having an LLM compare a candidate against relevant existing memories and select among operations, but its current open-source implementation is actually moving in a different direction: as of public commit `47a69e1e72dc562b6fdd49a9ef892229afc7508a`, its active extraction path uses a single additive extraction call, and the V3 prompt is explicitly “ADD-only with memory linking.” citeturn20view0 fileciteturn2file1 fileciteturn3file0 The current Mem0 changelog likewise describes the single-pass OSS pipeline as accumulating memories with no UPDATE/DELETE events and says the former external graph-store integration was removed from OSS in favor of entity linking. citeturn12search4

For retrieval, start simpler than Hindsight. Use a fixed token budget and combine:

**subject-scoped PostgreSQL full-text/keyword retrieval + the embedding retrieval ADE already has + cheap metadata filters for currentness/entity/time.**

Automatic retrieval should serve common continuity cases. Keep model-directed `search_memory` as a second chance when the user explicitly invokes the past, automatic retrieval is weak, or the model recognizes that context is missing. Do **not** add graph traversal, a cross-encoder reranker, or a separate query-rewrite model until ablations show a specific retrieval failure they solve. Hindsight demonstrates that semantic, BM25, graph, and temporal channels plus fusion/reranking can be highly effective, but its published results evaluate the bundle rather than isolating which of those components is necessary for a system of ADE’s scale. citeturn21view2turn21view1 Letta’s filesystem experiment points in the opposite—and valuable—direction: with GPT-4o-mini, simple semantic/file search plus grep and iterative tool use reportedly reached 74.0% on LoCoMo, leading Letta itself to warn that cross-framework memory comparisons are difficult and that model/tool behavior can matter as much as specialized storage. citeturn24search0

**My design recommendation is therefore Option A below: versioned ADE-owned assertions plus an episodic/source fallback.** It is the smallest change that directly improves natural change handling, historical truth, old-conversation recall, provenance, and safe forgetting while retaining ADE’s isolation and auditable storage model.

The research does **not** support replacing ADE wholesale with MemGPT/Letta, Hindsight, or Mem0. Each contributes useful mechanisms; none demonstrates that its complete architecture is necessary for the problem as stated.

## Evidence base and architectural evolution

This report treats the project-context bullets as a **maintainer-supplied description**, not repository evidence. I did not inspect an ADE repository, local services, private configuration, credentials, user data, or deployed infrastructure.

For original MemGPT, I inspected the public arXiv v2 paper dated February 12, 2024. Its central contribution is virtual context management: a hierarchy in which the finite LLM context contains system instructions, a read/write working context, and a FIFO message queue, while external recall and archival storage hold material outside the immediate prompt. Incoming/user-visible messages are persisted into recall storage, and the model can use functions to search or move information between tiers; retrieval is paginated to respect context limits. citeturn18search0turn19view0 This is fundamentally a **context-management architecture**, not a complete theory of mutable personal truth.

MemGPT’s conversational evaluation is consequently strongest as evidence for deep retrieval. Its Deep Memory Retrieval task asks questions about prior multi-session conversations, compares MemGPT against a lossy conversation-summary baseline, and uses an LLM judge; the appendix shows that questions themselves were generated to require participation in an old conversation. citeturn19view0 That demonstrates the value of retaining searchable conversation history beyond a rolling summary, but it does not establish a solution for subtle changes, corrections, uncertainty, deletion, or privacy.

Letta is important because **“MemGPT/Letta” is no longer one architecture**. The May 2025 Letta Leaderboard still describes the classic two-tier design: core memory inside context, arranged in memory blocks, and archival memory outside context accessed through search. Its benchmark separately tests read, write, and update behavior with synthetic fictional facts; a prompted GPT-4.1 grades answers, and extraneous memory operations are penalized. citeturn23view0 That benchmark is useful evidence that model capability strongly affects agent-controlled memory operations, but its explicit contradictory-fact update task is much cleaner than natural utterances such as “things have settled down now” or “we may be moving again.” citeturn23view0

Current Letta product direction is materially different. In February 2026, Letta introduced Context Repositories/MemFS: git-backed memory exposed as ordinary files, with a file tree providing progressive disclosure and a `system/` directory for material pinned into every prompt. Its background memory/reflection process can review recent conversations and modify this repository. citeturn16search0 In March, Letta explicitly described this as a move away from specialized server-side memory tools toward filesystem operations, git-backed context repositories, client-side subagents and skills. citeturn16search1 The public Letta Code source shows that shift continuing as of commit `3d45a4f68bab7c43bd8b2184dcb1fd929c49e8de` on September 23, 2026: incidental memory upkeep is routed to a background memory worker, while direct memory tasks remain foreground operations. The same source text says a MemFS edit does not change the already-compiled current turn and takes effect on a later prompt refresh. fileciteturn4file0L3-L7 This is a useful scheduling design, not evidence that ADE needs Git.

Letta’s harness is publicly documented as open source, and its current self-hosting documentation distinguishes local/on-device and self-hosted operation from cloud-hosted agents. citeturn14search3turn14search35 Therefore I treat **MemFS, progressive disclosure, background memory workers, and ordinary file search as mechanisms**, while Letta Cloud persistence/hosting is a deployment choice rather than evidence for the memory architecture.

Hindsight’s December 2025 paper is the most architecturally ambitious system in the requested set. It separates memory into world facts, agent experiences, opinions, and synthesized observations; retains conversational input as self-contained narrative facts; assigns occurrence ranges and a separate mention timestamp; resolves entities; builds several kinds of links; retrieves via semantic, BM25, graph, and temporal channels; combines candidates with Reciprocal Rank Fusion; reranks with a cross-encoder; and provides a `reflect` operation that reasons over retrieved memory and can update opinions. citeturn19view1turn21view2turn21view3 Its current public documentation exposes retain, recall, and reflect through isolated memory banks, and allows raw source text retention to be disabled independently of extracted memories. citeturn13search0turn13search2 I treat those core mechanisms as the relevant open/public architecture; Hindsight Cloud account/OAuth/connectors are managed-service concerns and are not needed to evaluate the design. citeturn13search9

Hindsight reports striking results: with an open-source 20B model, 83.6% on LongMemEval versus 39.0% for a full-context baseline using the same backbone; larger backbones reportedly reach 91.4%, with especially large gains on temporal and multi-session questions. citeturn21view1 These are **authors’ reported system-level results**, not evidence that a graph, four epistemic networks, cross-encoder reranking, and reflection agent are individually responsible. The reported experimental pipeline uses all four retrieval channels, RRF, neural reranking, narrative extraction, graph construction, and a reasoning stage together. citeturn21view2 The v1 paper sections inspected do not provide the kind of clean graph-vs-no-graph, reranker-vs-no-reranker, or reflect-vs-direct-answer ablation that would justify importing those pieces independently into ADE.

Mem0 also has an important historical/current distinction. The April 2025 paper describes an extraction phase followed by reconciliation: for each extracted candidate memory, it retrieves semantically similar existing memories and asks an LLM to select ADD, UPDATE, DELETE, or NOOP. It reports using ten recent messages and ten similar memories with GPT-4o-mini in its evaluation. citeturn20view0 Its graph variant preserves conflicts by marking relationships invalid instead of physically removing them, which is conceptually useful for historical truth. citeturn20view0 The paper reports a 26% relative LLM-judge improvement over its OpenAI comparison, roughly 2% additional overall score from the graph variant, 91% lower p95 latency than full-context processing, and more than 90% lower token cost; all of these are authors’ benchmark results on LoCoMo, not universal production measurements. citeturn19view2turn20view0

Current Mem0 OSS should not be described as the 2025 paper implementation. I inspected `mem0/memory/main.py` and `mem0/configs/prompts.py` at public commit `47a69e1e72dc562b6fdd49a9ef892229afc7508a`, the commit associated with its September 23, 2026 release. The active path labels extraction as a single LLM call and invokes `ADDITIVE_EXTRACTION_PROMPT`; the prompt itself says ADD-only, uses existing memories for deduplication/linking, and explicitly links changed preferences, continuations, and contradictions rather than overwriting them. citeturn12search2 fileciteturn2file1 fileciteturn3file0 fileciteturn3file1 This is a significant product-direction change. Mem0’s current public changelog also says the OSS single-pass extraction pipeline accumulates memories with no UPDATE/DELETE events and that the external graph store was removed from OSS. citeturn12search4 Separately, Mem0’s current repository warns that its published current benchmark scores can reflect managed-platform proprietary optimizations not present in OSS, so managed and open-source performance claims should not be conflated. citeturn14search5

The strongest transferable lesson from this evolution is that **the industry is not converging on one storage structure**. MemGPT demonstrated tiering and model-directed retrieval; Letta has moved toward files and background self-curation; Hindsight emphasizes temporal/entity structure and multi-channel retrieval; Mem0 has moved its OSS write path from destructive reconciliation toward additive, linked memories. citeturn18search0turn16search1turn21view2turn12search4 The durable common idea is much simpler: keep evidence outside the finite prompt, select a bounded amount of it, preserve enough structure to understand changes, and make memory operations inspectable.

## Mechanism-level comparison

### Responsibilities belong in different layers

The original MemGPT split remains a very good conceptual starting point even though its exact implementation need not be copied. Working context is scarce and immediately actionable; external memory is larger and searchable. citeturn19view0 Letta’s newer “progressive disclosure” reaches the same conclusion with a filesystem rather than dedicated memory tools: a small set of files is pinned while other material stays out of prompt until needed. citeturn16search0 Hindsight formalizes the external store much more deeply, while Mem0 focuses primarily on producing compact memories that are later retrieved. citeturn19view1turn20view0

For ADE, the clean responsibility split should be:

| Responsibility | Recommended home | Why |
|---|---|---|
| Persona/character contract | Working context, versioned separately | Always needed; should not depend on retrieval |
| Last few conversational turns | Working context | Resolves local pronouns, tone and immediate continuity without durable-memory latency |
| “What is true/current now?” | Bounded active-memory view | Fast personalization and current state |
| “What used to be true?” | Versioned memory ledger | Needed for changing circumstances and temporal questions |
| “What happened between us?” | Episode/source retrieval | Experiences often do not reduce cleanly to predicates |
| Verbatim evidence | Original transcript | Required to verify, re-extract, audit, and erase derived artifacts |
| Long summaries | Derived cache only | Useful for compression; never authoritative over source |

A summary is therefore **not another source of truth**. It is a cache with lineage. This matters for both false-memory prevention and deletion: if a summary says something that its source messages no longer permit the system to use, that summary has to be invalidated or rebuilt.

### Extraction should classify the relationship to existing memory

Mem0’s 2025 ADD/UPDATE/DELETE/NOOP mechanism usefully demonstrates that reconciliation improves when the model sees both a new candidate and related existing memories. citeturn20view0 But those four verbs conflate several semantically different events.

A more conversationally faithful operation set is:

| Situation | Ledger operation | Example |
|---|---|---|
| New independent information | **NEW** | “My sister is Maya.” |
| Same truth, more detail | **ENRICH** | “Maya is my younger sister.” |
| Circumstance changed | **SUPERSEDE** | “I moved from Ottawa to Montreal.” |
| Previous memory was wrong | **CORRECT/RETRACT** | “I never lived in Ottawa; that was Maya.” |
| Temporary state ended | **RESOLVE** | “The contract issue is sorted now.” |
| Hedged/possible state | **UNCERTAIN/PENDING** | “I might move again.” |
| Duplicate or irrelevant | **NO-OP** | Same preference restated |

This classification can be emitted by the **existing reviewer call**. Nothing in the research shows that a second “reflection” model is necessary for it. Hindsight’s retention pipeline does considerably more—coreference resolution, temporal normalization, participant attribution and entity extraction—but those are stages of one retention mechanism, not proof that each must be a separately hosted agent. citeturn21view4

The application should then enforce invariants. A model proposal cannot change `memory_subject_id`; cannot cite a nonexistent source; cannot hard-delete a transcript as a side effect of a normal update; cannot mark a current residence superseded from “I might move”; and cannot silently turn an assistant-generated suggestion into a fact about the user.

That last rule is especially important for a recurring character. Hindsight’s distinction among external facts, agent experiences and opinions is a useful **epistemic principle**: not every sentence entering memory has the same authority. citeturn19view1 ADE does not need four networks to capture the benefit. A much smaller field such as `evidence_kind = user_assertion | delivered_agent_experience | tool_observation | inference` is enough to prevent an assistant’s own hallucinated statement from recursively becoming “known truth.”

### Time needs two clocks, not a graph

Hindsight’s clearest transferable mechanism is the separate occurrence interval and mention timestamp. A stored unit includes `τs`/`τe` for when the event or state was true and `τm` for when it was mentioned. citeturn21view3turn21view4

That should become, in ordinary database language:

`observed_at` — when ADE received the evidence  
`valid_from` / `valid_to` — when the described state/event applies  
`time_precision` — exact / day / month / approximate / unknown

This alone handles many cases that otherwise tempt developers toward a temporal graph.

Suppose a user says on September 24, “We moved to Montreal last month.” The source was observed on September 24; `residence=Montreal` is valid from approximately August; the former Ottawa record ends approximately then. If the user instead says, “Actually, I never lived in Ottawa,” the Ottawa assertion is retracted rather than given a historical validity interval.

Likewise, changing relationships should be represented as versions. “Alex is my boyfriend” followed a year later by “Alex and I broke up” should leave a historical relationship with an end date and a current status of not-partners. That can be represented with ordinary rows and indexes; Hindsight’s entity/temporal graph demonstrates one way to exploit such relationships for retrieval, but the temporal information itself does not require graph traversal. citeturn21view4

Reference resolution should also stay deliberately conservative. Hindsight uses participant attribution plus canonical entity resolution drawing on string, co-occurrence and temporal signals. citeturn21view4 For ADE, recent dialogue plus a subject-scoped alias/entity table is probably sufficient until measured otherwise. “He got promoted” should update John only when recent context makes John sufficiently unambiguous; otherwise the reviewer can emit UNCERTAIN rather than manufacturing an identity.

### Retrieval should have an automatic lane and a deliberate lane

The systems studied reveal two viable retrieval philosophies.

MemGPT is strongly **model-directed**: the model recognizes a need for old information, calls search, can paginate and continue searching, and brings results into its limited context. citeturn19view0 Letta’s 2025 filesystem experiment goes further in that direction: the agent can reformulate queries and search repeatedly with familiar tools; Letta argues that this behavior can matter more than whether the underlying store is a graph or vector index. citeturn24search0

Hindsight is predominantly **retriever-directed**: semantic, BM25, graph and temporal channels run in parallel, RRF merges them, a cross-encoder reranks, and a token budget determines how many facts reach the model. citeturn21view2

For a small conversational system, neither extreme is necessary. The minimal design is:

**Automatic lane:** every user turn gets a cheap, subject-scoped search over current assertions and episodes. Use keyword/full-text and the already-available semantic signal; boost explicitly matched entities and relevant time ranges. Return only a bounded number of tokens.

**Deliberate lane:** expose `search_memory` to the generation model when it needs more. It should be allowed to reformulate the query itself and make another search, without an extra query-rewriter model.

The deliberate lane is important for sentences such as “remember that ridiculous café after the rainstorm?” where the search terms the user provides may not look like a stable “fact.” The automatic lane is important because a model cannot choose to search for context it does not realize exists.

A graph should remain an ablation, not a default. Hindsight provides a plausible mechanism for indirect multi-hop discovery, while Mem0’s 2025 graph variant reported only a modest overall gain over base Mem0 and current Mem0 OSS has removed its external graph store. citeturn20view0turn12search4 Letta’s simple-search result is an additional reason to test before adding graph-specific operational and cognitive burden. citeturn24search0

### Scheduling should distinguish explicit memory operations from incidental learning

Current Letta Code has made this distinction explicit: ordinary incidental memory upkeep can go to a background worker, while a task whose primary purpose is to modify memory is handled directly; the current compiled turn does not retroactively change when memory files are edited. fileciteturn4file0L3-L7 Hindsight likewise supports background processing for synthesized observations, and its current service exposes separate retention/recall operations with configurable processing behavior. citeturn19view1turn13search0 Mem0’s 2025 paper asynchronously refreshed its global conversation summary so that summary construction did not block the main extraction path. citeturn20view0

A useful small-team policy is:

**Explicit memory intent**—“remember this,” “that’s wrong,” “forget that,” “we moved”—gets synchronous or strongly ordered handling when correctness requires an immediate durable result.

**Incidental learnable detail** can be processed after response generation. Within the same conversation, the recent-dialogue window already contains the statement, so the model does not need the durable write to finish in order to remember what was said one turn ago.

To close the cross-session gap, the context builder should include **durable-but-unprocessed user messages** for that subject until the reviewer has processed them. That gives read-after-write behavior without forcing every ordinary turn to wait for a memory-model call.

A failed assistant generation should not create “agent experience” from text the user never received. User evidence can be keyed independently to the already-durable user message; an assistant-derived memory should require a delivered assistant message or an independently successful tool/action event.

### Privacy requires lineage, not merely deletion APIs

Hindsight’s bank abstraction is a strong example of enforcing an isolation unit: all operations target one bank and the public docs describe banks as isolated from one another. citeturn13search2turn13search7 Current Letta Code similarly has a cross-agent memory guard that denies access to another agent’s memory directory before normal permission handling. citeturn14search15 Mem0’s current OSS code also explicitly treats user/agent/run identifiers as scope fields rather than freeform metadata and prevents caller metadata from mutating identity scope. fileciteturn2file0 The common principle is stronger than any particular API: **isolation must be enforced by the storage/retrieval boundary, not merely by instructions in the prompt.**

For ADE, every memory query should therefore require the bound memory subject at the database predicate level. Embedding/vector retrieval should not return a global candidate set and filter afterward.

“Forget” is harder than “delete a fact.” Hindsight can be configured not to persist original document text, demonstrating that source retention is a separate policy choice from retaining derived memories. citeturn13search0 But for an application that *does* retain transcripts, deleting one active fact while leaving an old summary or searchable message intact does not make the system forget it.

ADE should define at least two semantics:

**Forget / stop using:** the material may remain in an audit/evidence store if policy permits, but it is excluded from every generation-facing retrieval path. All derived assertions, embeddings, episode summaries, current-profile entries and cached contexts carrying that source are invalidated.

**Erase / delete:** remove or cryptographically destroy the source evidence itself as required, then cascade invalidation/deletion through every derived representation.

This is why `source_message_ids` or equivalent lineage is not just debugging metadata; it is a privacy primitive. A forgotten message needs a tombstone or exclusion policy that is checked by **both fact retrieval and transcript/episode retrieval**, and summaries whose lineage contains the forgotten source must be regenerated or removed. Otherwise the fact will eventually reappear from a layer other than the one that was “forgotten.”

That also exposes one genuine unresolved product-policy question in the maintainer summary: an “immutable messages” design and a promise of irreversible erasure cannot both be absolute. ADE needs an explicit definition such as **append-only under normal operation, deletable under an erase workflow**, or an encrypted-erasure equivalent.

## Architecture options and tradeoffs

### Recommended: ADE-owned versioned ledger plus episode fallback

This option keeps the supplied architecture almost entirely intact: PostgreSQL remains authoritative; subjects remain explicit; messages and source provenance remain ADE-owned; the existing reviewer remains the only dedicated memory-model call.

The main change is to replace “active typed fact plus revision” as the whole memory abstraction with a more general **versioned assertion/episode ledger**. Existing typed facts can migrate into this representation without being discarded.

A minimal logical record might be:

```text
memory_id
memory_subject_id
kind                  # preference, identity, relationship, state, plan, episode, ...
content               # self-contained natural-language assertion
canonical_key         # optional; e.g. residence.current
state                 # current, uncertain, resolved, superseded, retracted, forgotten
observed_at
valid_from
valid_to
time_precision
confidence             # optional; do not pretend precision the source did not provide
source_message_ids
supersedes_memory_id   # optional
corrects_memory_id     # optional
entity_ids             # optional, ordinary relational join
revision_metadata
```

The fixed schema does **not** have to disappear. High-value slots such as name, current location or important relationship can still have `canonical_key`s and efficiently populate the active profile. The escape hatch is that experiences and unusual conversational information can remain narrative memories rather than being dropped because there is no matching fact type.

The reviewer sees the current user message, recent user turns, candidate related memories, and candidate entities, as the maintainer summary says it already does. Its output changes from tightly correction-gated mutation proposals to the broader transition vocabulary above. Application policy remains in control.

Retrieval uses three priority bands:

1. current high-value profile, already compact and always supplied;
2. automatic subject-scoped keyword/semantic retrieval over current assertions plus episodes;
3. deliberate `search_memory` for deeper or iterative recall.

The original transcript is a final evidence/fallback tier and should not automatically dump raw historical text into every turn.

This option borrows MemGPT’s separation of context from external evidence, Mem0-paper-style comparison against related memories, Hindsight’s temporal/provenance discipline, and Letta’s lesson that retrieval primitives can stay simple. citeturn19view0turn20view0turn21view3turn24search0 It does **not** import any of those frameworks.

### Baseline alternative: transcript-first plus a tiny current profile

The smallest architecture in terms of memory-writing logic is even more radical: persist almost no extracted long-term memories. Keep only a deliberately small current profile for identity, stable preferences and high-value current state; index the actual conversation history with PostgreSQL FTS and existing embeddings; retrieve raw/source conversation when needed.

This resembles the lesson from Letta’s filesystem LoCoMo experiment more than classic MemGPT. Letta reported strong retrieval performance from conversation files using semantic search, grep and iterative model queries, even without specialized memory representations. citeturn24search0

Its major virtue is **false-memory resistance**. There are fewer model-generated abstractions capable of becoming wrong. Old shared experiences are especially well served: the system searches what was actually said.

Its weakness is **state reconciliation**. Searching a transcript about “where do I live?” may retrieve both the old Ottawa discussion and the newer Montreal discussion. A current profile or recency/currentness layer still has to decide which statement governs now. Forgetting also becomes demanding because transcript search itself must honor deletion/tombstones.

I would implement this option as an experimental baseline even if it is not selected, because it tells the team how much complexity extraction is actually buying. If transcript-first retrieval performs within a few points of a sophisticated derived-memory layer on real continuity cases, the simpler method deserves serious consideration.

### Upper-complexity option: temporal narrative memory with multi-signal retrieval

A third option takes the parts of Hindsight most relevant to conversational continuity but stops well before full Hindsight.

Retain 1–3 self-contained **narrative memory units** from a conversational episode. Give each occurrence and observation times. Resolve named entities into ordinary relational identifiers. Search them using:

- full-text/BM25-like ranking;
- vectors;
- entity match;
- temporal filter/boost.

The results can be combined with a simple rank-fusion method if needed. Hindsight demonstrates the complete version of this design, including four retrieval channels, RRF and a reranker. citeturn21view2 But there is no reason to begin with its graph edges, opinion network, cross-encoder or reflect loop.

This option is attractive if the evaluation shows that old shared experiences and temporally phrased questions dominate failures. It has better representational coverage than a tightly typed fact store, but more write-time inference and more things to debug.

### Explicit tradeoff comparison

| Dimension | Versioned ledger + episode fallback | Transcript-first + tiny profile | Temporal narrative memory |
|---|---|---|---|
| **Current-state correctness** | **High** if transition policy is good | Medium–high; profile must override stale transcript hits | High |
| **False-memory risk** | Low–medium; derived assertions require provenance | **Lowest**; most recall comes from source | Medium; more LLM-derived narrative |
| **Natural-change coverage** | **High** | Medium; relies heavily on retrieval/reasoning | High |
| **Old shared-conversation coverage** | High with episode fallback | **High** if search succeeds | **High** |
| **Temporal reasoning** | High for explicit state changes | Medium without extra temporal normalization | **Highest** |
| **Write-path latency** | Existing reviewer cost; can background incidental writes | **Lowest** | Highest of the three |
| **Read latency** | Low–medium | Medium; more source search/tool use | Medium–high |
| **Model-call cost** | Roughly existing memory-review cost | **Lowest on writes**, potentially higher on recall | Higher on writes; reranking/reflection would raise it further |
| **Operational burden** | **Low–medium**; mostly schema/query changes | Low | Medium–high |
| **Cognitive complexity for small team** | **Low–medium** | **Low** | Medium |
| **Deletion/forgetting complexity** | Medium; lineage makes it tractable | High because source is the principal memory | Medium–high |
| **Best role** | **Recommended production direction** | Required simple baseline | Conditional follow-up |

The most consequential tradeoff is between **derived-state correctness and source fidelity**. Option A explicitly models “what is current?” while still falling back to episodes. Option B avoids many extraction errors but asks retrieval/generation to infer currentness from contradictory history. Option C increases retrieval coverage but also increases the surface area on which extraction and normalization can fail.

## Natural-dialogue walkthroughs

The important cases are not benchmark-style statements such as “My favorite color is green / now it is blue.” Ordinary conversation mixes event history, affect, implication, hedging and references. The following walkthroughs show the actual difference among the options.

### A move

Earlier memory:

> “We live in Ottawa.”

Later, casually:

> “The last few weeks have been chaos, but we’re finally unpacked in Montreal. I think the cats are happier than we are.”

**Versioned ledger + episode fallback.** The reviewer retrieves the Ottawa residence candidate. It proposes `SUPERSEDE`: Ottawa remains historically valid; Montreal becomes current, with `valid_from` approximated from “last few weeks” rather than fabricated as an exact date. A separate episode memory can preserve the moving/unpacking experience if it appears conversationally significant. The source message is attached to both. On the next question, “Any ideas for something nearby this weekend?”, Montreal appears in the active profile without requiring a memory tool call.

This is the direct payoff from distinguishing occurrence time from observation time, a distinction formalized in Hindsight. citeturn21view3turn21view4

**Transcript-first.** Update only the tiny `current_location=Montreal` profile. The original Ottawa and Montreal conversations remain searchable. This is simple and robust, but historical queries depend on the model retrieving the right source snippets.

**Temporal narrative memory.** Store a narrative event such as “The user recently completed a move from Ottawa to Montreal and is unpacking with their cats,” with approximate occurrence interval and Montreal/Ottawa entities. Current residence may still be separately materialized for fast profile use. This gives excellent future recall for “how was that move?” but involves more model-created prose than Option A.

Crucially, none of the options should interpret the sentence as “correcting an erroneous Ottawa fact.” It is a changed circumstance.

### A concern that has been resolved

Earlier:

> “I’m really worried they might not renew my contract.”

Several weeks later:

> “They renewed me through next year, so I can finally stop stressing about that.”

**Versioned ledger + episode fallback.** The previous concern is not deleted. It transitions to `RESOLVED`, and a new event records the renewal. Current context should no longer tell the character that the user is presently worried about renewal, but an old-conversation question can still recover the period when they were worried.

This is where a simple active/deleted bit is insufficient. Deleting the old concern loses shared history; leaving it active causes an emotionally jarring false continuity.

**Transcript-first.** Remove “contract renewal concern” from the tiny current profile, while retaining both conversations. Retrieval should prefer recent evidence for a present-tense question. This has minimal write logic but creates a stale-retrieval hazard: an old worry can still rank highly for “How is work going?” unless current-profile evidence has precedence.

**Temporal narrative memory.** Preserve two temporal events: the earlier uncertainty and the later renewal/resolution, perhaps linked only by a shared employment/contract entity or topic. A graph edge is not necessary to recognize the sequence.

### An old shared conversation

Six months later:

> “Remember that ridiculous café we found after the rainstorm in Quebec City? What was the dessert I couldn’t pronounce?”

This is the failure mode a fact-only system is most likely to miss. The café episode may never have produced a schema-shaped “fact” important enough to enter an active profile.

**Versioned ledger + episode fallback.** Automatic memory retrieval first searches compact memories. If it finds nothing strong, episode/source retrieval searches subject-scoped conversation summaries/messages using “café,” “rainstorm,” “Quebec City,” and related semantic terms. The generation model can invoke `search_memory` with a reformulation if needed. The retrieved result contains source pointers so the answer can be grounded in the original exchange.

This is exactly the kind of deep conversational recall that motivated MemGPT’s searchable recall storage. citeturn19view0 Letta’s filesystem experiment provides additional evidence that iterative keyword/semantic search over historical conversation can be surprisingly competitive without first turning everything into a knowledge graph. citeturn24search0

**Transcript-first.** This is its strongest case. Search source conversation directly. A lexical hit on “Quebec City” or “rainstorm,” combined with semantic ranking, may retrieve the passage with essentially no extraction error.

**Temporal narrative memory.** The café outing would likely already exist as a self-contained episodic memory, so retrieval may be direct. Hindsight’s narrative extraction explicitly favors self-contained facts that preserve cross-turn context rather than sentence fragments. citeturn21view3 The tradeoff is that the exact dessert name still may require source retrieval if the narrative abstraction omitted it—another reason not to discard original evidence.

### An ambiguous update

Current state:

> “We live in Montreal.”

New statement:

> “I might be moving again. Nothing decided yet.”

**Versioned ledger + episode fallback.** The reviewer emits `UNCERTAIN/PENDING`, perhaps “User may move again; no destination or decision established.” It does **not** supersede Montreal. The current profile may include the pending plan only if relevant, but current residence remains Montreal.

If the next sentence is “My partner is leaning toward Vancouver,” the system can enrich the pending plan without asserting that the user is moving to Vancouver.

**Transcript-first.** Keep the source statement; current location profile remains unchanged. Optionally record a tiny hedged plan entry. This is naturally conservative.

**Temporal narrative memory.** Record the possible future move as an intention with low certainty/future temporal scope. Do not convert it into a residence relationship.

This case illustrates why a separate binary “correction intent” gate is a poor abstraction. The statement is meaningful memory even though it is neither a correction nor a new settled fact. Mem0’s current OSS additive/linking approach explicitly recognizes updated preferences, continuations and contradictions as linkable new memories rather than requiring destructive replacement; that direction is useful evidence for preserving ambiguous evolution, even though ADE should retain a stronger explicit current-state view. fileciteturn3file1

### A true correction, for contrast

Suppose the user later says:

> “Wait, I need to correct something I told you ages ago. I never lived in Ottawa—my sister did. I was in Kingston before Montreal.”

Now the Ottawa record should be `RETRACTED/CORRECTED`, not historical truth. Kingston becomes the predecessor residence if the statement is unambiguous. Any compact summary saying the user formerly lived in Ottawa must be invalidated. An episode containing “the time you lived in Ottawa” should not remain independently retrievable as established fact.

This distinction—**superseded truth versus retracted error**—is one of the highest-value changes the project can make. A system that stores only “latest fact” loses the distinction; an append-only system without status preserves both statements but may retrieve the wrong one. A versioned ledger gives both history and current correctness.

## Experiment plan

The experiment should discriminate mechanisms without installing or migrating to any of the researched frameworks. It should use public/synthetic data and newly authored synthetic conversations; the assignment provides no authorization to disclose private conversations to new vendors or run paid/private-data experiments.

### Build an ADE-specific continuity set before changing architecture

Create a compact replay suite centered on actual design failures rather than generic QA. Each scenario should contain multiple sessions and a gold ledger state after every relevant turn.

The core categories should include:

| Category | What the gold annotation tests |
|---|---|
| New information | Should a memory be created? |
| Enrichment | Preserve identity while adding detail |
| Changed circumstances | Old state stays historically true; new state becomes current |
| Correction | Old assertion becomes false/retracted |
| Resolved transient state | Historical experience remains; no longer current |
| Contradiction | Keep evidence and avoid arbitrary resolution |
| Hedging | Do not upgrade “maybe” into truth |
| Pronoun/entity resolution | Correct person without cross-entity leakage |
| Temporal references | “last month,” “back when,” future plans |
| Old shared episodes | Recall details that were never active-profile facts |
| Subject collision | Similar names/facts in two memory subjects never cross |
| Forget/delete | No resurrection through fact, summary, embedding or transcript retrieval |

The four walkthroughs above should become mandatory seed cases, then be paraphrased into less explicit natural language.

### Compare simple baselines before richer machinery

Run the same generation model and fixed context/token budget across these conditions:

**Recent-only baseline.** Persona plus recent dialogue, no durable retrieval. This measures how much memory is helping at all.

**Current ADE-like baseline.** The maintainer-described active typed-fact profile, existing reviewer/gating, and current semantic retrieval.

**Transcript FTS baseline.** Search original messages only with PostgreSQL full-text/keyword retrieval.

**Transcript vector baseline.** Existing embeddings only.

**Hybrid source baseline.** FTS + vectors, no extracted long-term memories except the current profile.

**Recommended ledger.** Versioned assertions + current view + episode/source fallback.

**Temporal enhancement.** Recommended ledger plus event/observation time filtering.

Only after these should the experiment add entity boosting, rank fusion, a cross-encoder reranker or graph traversal. Hindsight’s strong system-level results make those reasonable later ablations; they do not make them reasonable defaults. citeturn21view1turn21view2

### Measure the write path separately from retrieval

A memory system can answer benchmark questions correctly while maintaining a bad internal state. Letta’s 2025 Leaderboard usefully separates memory reading, writing and updating for exactly this reason, although its data are synthetic. citeturn23view0 ADE’s evaluation should go further and score the ledger itself.

For each turn measure:

**False-write rate:** durable memory created without adequate source evidence.

**Missed-change rate:** a changed or resolved state left active.

**Wrong-transition rate:** changed circumstance mislabeled as correction, uncertainty promoted to fact, etc.

**Provenance completeness:** every durable assertion has valid source lineage.

**Current-view accuracy:** the exact set of assertions considered current after each turn.

**Historical-truth accuracy:** old-but-once-true versus corrected-false facts are distinguishable.

**Entity error rate:** fact attached to the wrong person/subject.

These are more directly relevant to “avoid false memories” than an end-answer judge alone.

### Measure retrieval under a fixed context budget

For every test question, annotate the smallest evidence set needed to answer correctly. Then measure:

**Evidence Recall@budget**, not just Recall@K: did the context composer supply the needed evidence within the same token budget?

**Stale intrusion:** did the supplied context contain an obsolete assertion that could plausibly mislead the model?

**Current-vs-historical accuracy:** particularly for present-tense versus “back then” questions.

**Episode recall:** can the system recover shared experiences that never became facts?

**No-memory precision:** when there is no relevant past information, does retrieval stay quiet?

Hindsight’s use of token-bounded recall is a particularly transferable design principle: the downstream constraint is tokens, not an arbitrary fixed number of memories. citeturn21view2

### Measure end-to-end behavior and operations

End-to-end prompts should be judged against explicit factual criteria first, with blind human review for conversational naturalness where feasible. LLM judging can be secondary, because all of the major vendor benchmarks here use model-dependent evaluation or synthetic data to some degree: MemGPT’s DMR uses an LLM judge and generated questions; the Letta Leaderboard uses synthetic facts/questions and GPT-4.1 grading; Mem0 uses LoCoMo and repeated LLM-as-a-Judge runs; Hindsight also uses a separate LLM judge for its experiments. citeturn19view0turn23view0turn20view0turn21view2

Operationally track p50/p95 added response latency, reviewer latency, memory jobs queued per turn, model calls per conversational turn, generation/reviewer tokens, embedding calls, retrieval queries, retrieved tokens, storage growth, background-job lag, and failure/retry rate.

The key read-after-write test should deliberately issue a follow-up immediately after a change, then repeat it from a newly opened conversation. This will tell the team whether incidental background extraction plus the pending-message bridge is sufficient or whether more writes must be synchronous.

### Run the ablations in an order that can stop early

A useful order is:

`FTS only → vector only → FTS+vector → +currentness/time → +entity boost → +episode summaries → +reranker → graph`

Stop when the quality curve flattens.

Similarly, for writes:

`current correction gate → broader transition classifier → +uncertainty → +temporal interval → richer narrative memory`

The graph question should only survive if a meaningful cluster of failures genuinely requires traversing indirect relations after hybrid retrieval and entity/time filtering. The reranker should only survive if it produces enough evidence-recall or stale-intrusion improvement to justify another model and its latency. A reflection agent should not even enter the experiment unless ordinary extraction plus deterministic state views cannot handle the desired character continuity.

This is the core methodological lesson from the vendor evidence. Hindsight’s integrated stack performs extremely well but does not tell ADE which component caused each gain. citeturn21view1turn21view2 Letta’s simple filesystem result shows that surprisingly simple retrieval can perform well under a capable agent. citeturn24search0 Mem0’s own architecture has substantially changed since its paper, which is further evidence against treating a published framework shape as a fixed optimum. citeturn20view0turn12search4

## Recommendation matrix and unresolved questions

### Adopt as a principle

| Recommendation | Why | Evidence that would change it |
|---|---|---|
| **Separate evidence from derived memory.** Original messages are evidence; facts/summaries are revisable interpretations. | Prevents an extractor’s wording from becoming more authoritative than the conversation; enables reprocessing and deletion lineage. Hindsight explicitly separates evidence-like memory from synthesized observations/opinions, while MemGPT preserves searchable message history outside immediate context. citeturn19view1turn19view0 | Only a design that can provide equivalent audit/retraction/deletion guarantees without source lineage would justify dropping it. |
| **Represent changes by version/state, not destructive overwrite.** | Required to distinguish “used to be true” from “was never true.” Mem0’s paper preserves invalidated graph relationships for temporal reasoning; current Mem0 OSS has moved further toward additive linked history. citeturn20view0turn12search4 | Evidence that historical state is never user-visible or relevant—which contradicts the recurring-character goal. |
| **Store event/valid time separately from observation time.** | Small schema cost; directly solves moves, past relationships and “last month” statements. This is explicit in Hindsight’s memory tuple. citeturn21view3turn21view4 | If an ADE-specific eval shows temporal/current-state questions are negligible and date extraction creates more errors than benefit, keep only `observed_at` plus optional free-text timing. |
| **Use a broader reconciliation vocabulary than correction/removal intent.** | Natural conversation contains enrichment, resolution, uncertain plans and ordinary changes that are not “corrections.” Mem0’s historical reconcile design and Hindsight’s temporal extraction both support reasoning relative to existing state. citeturn20view0turn21view4 | If shadow evaluation shows the existing gate already captures natural changes with very low miss rate. |
| **Keep application policy authoritative over model proposals.** | Model reasoning is useful for semantic classification, but isolation, deletion and legal/state invariants are deterministic application responsibilities. Current Hindsight banks, Letta memory guards and Mem0 scope enforcement all illustrate hard boundaries outside prompting. citeturn13search2turn14search15 fileciteturn2file0 | Nothing in the reviewed evidence supports delegating tenant/subject isolation or destructive authorization to an LLM. |
| **Treat working context as a bounded cache, not the durable store.** | This is the common principle spanning MemGPT’s memory hierarchy, Letta’s progressive disclosure and Hindsight’s token-budgeted recall. citeturn19view0turn16search0turn21view2 | A future model/context regime where the complete authorized history can be supplied cheaply and reliably without context degradation. |
| **Make forgetting apply to every retrieval surface.** | Deleting a current fact is ineffective if summaries or transcripts can reintroduce it. | Only a product definition explicitly saying “forget” does not mean “stop using this information” would alter this, and that would need to be made clear to users. |

### Test before adopting

**Narrative episodic memories alongside typed facts.** The project brief specifically identifies a likely gap in the fixed fact schema. Hindsight’s narrative-fact approach and MemGPT/Letta’s retrieval of old conversation suggest that this gap matters. citeturn21view3turn19view0turn24search0 Test whether narrative episodes materially improve old-conversation recall before expanding the entire schema.

**Hybrid lexical + vector retrieval.** Hindsight intentionally combines semantic and keyword search, and Letta’s filesystem experiment combines semantic search with grep. citeturn21view2turn24search0 This is a low-complexity test because PostgreSQL FTS can coexist with the embedding path ADE already has. Keep lexical-only if hybrid retrieval does not provide measurable coverage.

**Automatic retrieval plus model-directed fallback.** MemGPT and Letta show the value of iterative agent-directed search, while Hindsight shows the value of automatic multi-signal context supply. citeturn19view0turn24search0turn21view2 The hybrid policy should be tested against automatic-only and tool-only modes.

**Background incidental extraction with a pending-message bridge.** Current Letta Code is strong evidence that background memory upkeep is operationally viable, but its exact consistency semantics are Letta-specific. fileciteturn4file0L3-L7 Test immediate follow-ups and immediate new-conversation switches before moving all ordinary writes off the response path.

**A flexible assertion format instead of preserving the current typed-fact schema unchanged.** This should be run in shadow mode first. If free-text/narrative memories improve coverage without raising false-write or stale-intrusion rates, relax the schema. If they mostly create duplication, retain more typing.

### Defer

**Knowledge graph storage/traversal.** Hindsight gives a credible positive case, especially for entity-linked multi-hop questions. citeturn21view4turn21view1 But Mem0’s paper found only a modest overall improvement from its graph variant, current Mem0 OSS removed its external graph-store integration, and Letta reports competitive LoCoMo retrieval with ordinary file search. citeturn20view0turn12search4turn24search0 The case for a graph should come from ADE-specific residual failures, not fashion.

**Cross-encoder reranking.** Hindsight uses it after RRF and achieves strong full-system results, but the inspected paper does not isolate the reranker’s marginal contribution. citeturn21view2 Add it only if the candidate set contains the right evidence but ranking routinely places it outside the token budget.

**A reflection agent or opinion network.** Hindsight’s reflect mechanism is designed partly for coherent evolving agent beliefs/preferences, not merely user-state continuity. citeturn19view1turn21view2 A recurring character might eventually benefit, but ADE’s immediate stated problems—natural updates, schema coverage, retrieval and false memories—do not require it.

**Git/filesystem memory as ADE’s primary store.** Letta’s current design is compelling for coding agents because ordinary file/Git operations give the agent transparent, programmable memory and concurrent subagents can use worktrees. citeturn16search0turn16search1 Those benefits do not obviously outweigh ADE’s existing PostgreSQL provenance, relational isolation and revision model for a conversational character. Treat progressive disclosure and background curation as transferable ideas; defer the storage metaphor.

**A dedicated second query-rewrite model.** Letta’s retrieval experiment shows the acting model can reformulate search terms itself, and MemGPT already lets the main model issue repeated memory searches. citeturn24search0turn19view0 Add another call only if the existing generation model demonstrably fails to formulate searches.

### Reject for the current decision

**Reject wholesale framework replacement.** None of the evidence demonstrates that replacing ADE-owned storage with an entire external framework is necessary. Hindsight’s strongest evidence is for its integrated system; Letta is moving between substantially different memory architectures; Mem0’s current OSS differs materially from its own 2025 paper. citeturn21view1turn16search1turn12search4 Those are reasons to extract mechanisms, not adopt brands.

**Reject destructive “latest fact wins” storage.** It cannot represent historical truth versus correction.

**Reject vector similarity as the sole retrieval mechanism.** Keyword/entity/time cues routinely carry information that semantic similarity need not rank well; both Hindsight and Letta deliberately combine semantic retrieval with non-vector search. citeturn21view2turn24search0

**Reject summaries as independent truth.** They should always have reconstructible lineage.

**Reject automatic promotion of assistant-generated text into user truth.** A character’s own delivered experiences may legitimately have memory, but that is a different evidence class from a user assertion. Hindsight’s epistemic separation is the useful principle here. citeturn19view1

**Reject a “forget” implementation that only deactivates the active fact while leaving the same information eligible for transcript, summary or embedding retrieval.** That satisfies database mutation but not conversational forgetting.

### What remains unresolved

The first unresolved question is **what the product promises when the user says “forget that.”** There are at least three meanings: stop mentioning it; stop using it for personalization; physically erase it. The data model and deletion cascade cannot be finalized until those semantics are explicit.

The second is **what counts as authoritative character self-memory.** If the recurring character says, “I loved our trip conversation,” does that become part of its persistent experiential identity merely because the model generated it? Automatically persisting all assistant output creates a self-reinforcing hallucination channel. A defensible default is to persist user claims, verified tool/action outcomes, and explicitly selected delivered character experiences under separate provenance classes—not treat all generated prose as fact.

The third is **how strong cross-conversation read-after-write must be.** Recent dialogue makes asynchronous incidental learning safe inside one thread, but a user who immediately opens another conversation can expose background lag. The experiment should measure this before choosing synchronous review for every turn.

The fourth is **how far temporal normalization should go.** `observed_at` is nearly free and should exist. Approximate `valid_from/valid_to` is highly useful. Full natural-language temporal normalization for every memory may not earn its error/latency cost unless temporal queries are common; Hindsight demonstrates the sophisticated endpoint but not that ADE needs all of it. citeturn21view4

The fifth is **the privacy boundary of model and embedding providers.** The maintainer summary says generation is router-backed, embeddings are separately hosted, and hosting may move. That means provider location/retention policy should not be encoded into the memory architecture. Minimize extraction payloads to the current evidence plus relevant subject-scoped candidates, record which provider processed a memory operation when audit requirements call for it, and keep durable ownership and deletion lineage inside ADE.

The sixth is **whether the current typed schema is actually the principal recall bottleneck.** The proposed episode fallback makes that empirically testable without deleting or redesigning existing facts. If adding episodic/source retrieval fixes old-shared-conversation failures while transition classification fixes natural changes, there may be no need for a broad schema rewrite.

The decision I would make from the present evidence is therefore deliberately conservative:

**Retain ADE-owned PostgreSQL and the separate reviewer. Expand the reviewer from correction gating into source-grounded state reconciliation. Make facts versioned/temporal rather than destructively current. Add a provenance-preserving episodic/source retrieval lane. Use PostgreSQL lexical search plus the existing embedding signal under a fixed token budget. Make explicit corrections/forgetting strongly ordered, move incidental learning toward background processing only with a pending-evidence bridge, and instrument every failure.**

That architecture captures the strongest ideas demonstrated across MemGPT, Letta, Hindsight and Mem0 while avoiding the parts for which the evidence does not yet justify their cost.