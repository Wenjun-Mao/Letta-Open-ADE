# ADR 0057: Model-Assisted Evidence Selection Investigation

Status: Accepted investigation design direction, 2026-10-02. No implementation,
model/provider call, production adoption or native continuation is authorized.

2026-10-02 amendment: [ADR 0058](0058-offline-packet-capacity-and-qualifications.md)
authorizes a separate D04 eight-source offline capacity diagnostic and prospective
packet rubric. Only that diagnostic supersedes the extra-slot rejection below;
the selector design and runtime remain limited to four final sources.

2026-10-02 planning follow-on: the user selected keeping four windows while
comparing joint source selection methods. The [bounded recovery plan](../plans/character-evidence-recovery.md)
and proposed [ADR 0060](0060-joint-history-packet-admission.md) refine the prospective
packet contract. Atomic admission remains proposed; no runtime decision or new
execution follows from this planning choice.

## Problem And Evidence

The [matched correction study](../../workflows/evals/character_memory_dev/story_continuity/correction_dependencies/READOUT.md)
admitted referential corrections without the passages naming their referents in
three baseline pairs and two novelty-candidate pairs. All packets fit. The missing
evidence was available in the controlled corpus, locating this failure at source
selection rather than capacity or downstream answer construction. These are
non-blind synthetic availability results, not observed model-answer failures.

The user agreed to investigate model-assisted evidence selection, with a simpler
retrieval-only comparison, and then agreed to the bounded design below. This
records that direction without treating discussion as implementation approval.

## Candidate Evidence Flow

1. Build a bounded eligible candidate pool with complete exchanges, source IDs,
   roles and chronology. Preserve PC-03/04/10 scope across chats, ordinary versions
   and archives. Chronology helps locate a referent; it does not establish truth.
2. A bounded semantic selection pass proposes up to four source IDs that jointly
   support the question, including passages needed to interpret references. It
   selects evidence, not an answer, canonical story, memory delta or rewritten
   source. Zero sources is a valid selection when historical evidence is unneeded.
   Evaluator labels and answer keys never enter its input.
3. ADE enforces source identity, scope, integrity and output limits. Selecting a
   valid source does not prove the model understood it. No earliest/latest/majority
   authority rule, correction keyword table or reserved-origin slot is introduced.
4. Construct fresh answer-generation and reviewer requests using the same final
   admitted history, at most four whole windows under existing capacity checks.
   Do not forward the selector's broader context, reasoning, summaries or proposed
   answer, including through hidden conversation state. Keep selection omissions
   distinct from admission drops; a dropped dependency is not silently resolved.
5. For recollection with incomplete evidence, preserve uncertainty rather than
   inventing the missing detail. Natural wording remains the answering model's
   responsibility, not a phrase rule or a claim of verified behavior.

The selector is an additional fallible model phase with latency and request cost,
not a second factual reviewer or authority for persistence. Any future source-
bearing selector call requires integrity/scope checks and its own finite context
and output budget; the four-window final limit does not bound its larger input.
Keep observational request accounting, explicit timeout/retry semantics and
direct ownership under PC-05/06/09. No new service, episode store or generic
framework is selected. The follow-on
[protocol proposal](../../workflows/evals/character_memory_dev/story_continuity/evidence_selection/PROTOCOL.md)
specifies a source-backed route, settings and prompt for review; they are not a
runtime default, executed comparison or provider-verified configuration.

## Alternatives And Consequences

Keep retrieval-only context expansion as the simpler comparison: it can make
earlier or surrounding passages available without a semantic model call, but
proximity alone does not identify a distant reference. Neither approach is yet
shown to improve production behavior. Keep the current baseline; the prior
novelty candidate remains unadopted.

Reject automatic origin authority, phrase-specific correction handling, extra
final slots and downstream invented answers. The bounded selection investigation
does not solve larger-history candidate retrieval: absent passages cannot be
selected. Do not silently extend the reader's existing corpus boundary.

## Investigation Guardrails

The [existing continuity plan](../plans/character-story-continuity.md#model-assisted-evidence-selection)
remains the delivery entrypoint. Before any model run, define and freeze a finite
protocol: candidate/input/output limits, source-only response schema, prompt,
model/settings, comparison recipe, attempt policy and handling of invalid outputs.
Do not confuse a malformed response or transport failure with a valid empty
selection. Implementation and any live/provider use need separate authorization.

First isolate selection with necessary passages available. Reuse existing cases
as exposed development checks, not a held-out or independent benchmark. Include
ambiguous references, genuinely corrected originals and questions needing no
history; freeze new source-quoted labels before outcomes. Inspect missing-source
behavior separately. An ambiguous referent must not be forced into one authority
label, and a valid empty selection alone does not demonstrate natural abstention.

Verify exact source membership, whole-window limits, integrity and fresh shared
generation/reviewer history independently of semantic quality. Assess named-answer
availability, dependencies, competing/qualifying evidence and irrelevant admissions
separately. Model selection observations are not generated-answer, reviewer or
persistence qualification. No aggregate adoption claim follows from development
fixtures; larger-history retrieval and downstream behavior remain later questions.

PC-01/03/04/05/06/09/10/11 boundaries remain in force, with the agreed PC-11 recall
uncertainty clarification. ADR 0056's completed measurement and all frozen artifacts
remain historical evidence; this decision supersedes no runtime policy and does
not reopen the native turn-7 stop or authorize turns 8-10.
