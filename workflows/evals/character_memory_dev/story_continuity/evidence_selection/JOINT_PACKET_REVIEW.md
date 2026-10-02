# External Design Review: Joint Evidence Packets

Prepared 2026-10-02 for one **Pro** reviewer, at the user's request. This is the
detailed assignment accompanying the self-contained handoff prompt. Publication
does not dispatch a consultant or authorize external-account use.

## Purpose And Mode

Independently challenge the four-window recovery design before implementation.
Decide whether its next offline slice is worth doing as written, needs a smaller
revision, or should be reframed. Being wrong could add a fallible model request,
unnecessary all-or-nothing failures, or misleading success claims from toy cases.

**Mode recommendation: Pro.** The unresolved need is source-grounded reasoning
about admission semantics, failure paths and a discriminating comparison. Deep
Research adds no necessary contribution now: the immediate research shortlist is
already source-checked, and broad candidate retrieval is outside this slice.
Challenge our framing rather than seek endorsement; a conditional judgment or
named open question may be more useful than a forced recommendation.

## Access And Immutable Evidence

GitHub-only, read-only access. No local checkout, worktrees, services, databases,
ignored captures, accounts or conversation history is available. Do not implement,
call providers, start services, post issues or change repository state.

Repository discovery: https://github.com/Wenjun-Mao/Letta-Open-ADE
Discovery branch: main. Review source commit: **48db1ca339cbcc7c7f47a3f7af89b654f14aaebc**.
Pinned source tree: https://github.com/Wenjun-Mao/Letta-Open-ADE/tree/48db1ca339cbcc7c7f47a3f7af89b654f14aaebc
Public raw-file base: https://raw.githubusercontent.com/Wenjun-Mao/Letta-Open-ADE/48db1ca339cbcc7c7f47a3f7af89b654f14aaebc/

All 18 required files listed below were fetched publicly without credentials and
matched the pinned source bytes before preparing this brief. This brief is
published in a later documentation-only commit; its immutable permalink is in
the handoff. Use the source anchor above, not moving `main` or the brief's revision,
for source/design claims. State the commit and files actually inspected, access
gaps and any prior ADE context. If access fails, use only this supplied summary;
do not silently substitute another revision or claim source inspection.

## Self-Contained Context

ADE's character may invent solo fictional history, then should recall it
consistently within the same user/character relationship across chats, ordinary
persona versions and archives (PC-03/04/10/11). New solo fiction and compatible
elaboration remain allowed; missing recollection is not permission to invent
previously established details, user facts or shared experiences. Genuine error
correction is allowed; deliberate ordinary-chat retcons are not. Natural uncertainty
has no mandated phrase. The reviewer interprets meaning; ADE enforces source,
scope, versions and persistence (PC-05). Retained history cannot independently
restore a removed fact or authorize a write (PC-07). PC-06/09 exclude semantic
keyword rules, speculative episode/graph services and a second factual reviewer.

Completed D04 evidence is narrow. In an eight-exchange Mandarin fixture, literal
top four selected E07, E02, E05, E04. E07 rejects a mistaken teahouse retelling and
refers to the originally stated location; absent E01 names the old-bookstore
entrance. Literal generation correctly expressed uncertainty. Evaluator-repaired
four (E07, E02, E05, E01) and all eight sources produced supported naming, one
witness each. Those are not working recovery methods or reliability estimates.
All eight fit both existing input budgets with full reply reserves, so four is a
policy choice, not measured necessity. The literal reviewer returned a source-bound
conflict about a tentative optional aside; its semantic interpretation remains
open. The other two returned valid no-change, not truth/persistence certificates.
No native delivery or persistence was tested; native turn 7 remains stopped.

The user chose retaining four windows while comparing joint source selection.
The plan, ADR 0060 and protocol v2 are proposals; new controls, harness and model
results do not exist. Three methods use the same eligible pool: unchanged literal
top four; its highest-ranked anchor with immediate same-chat predecessor/successor,
then baseline fill to four; and one model pass selecting zero to four distinct
original IDs. The model sees at most eight complete exchanges and the question,
not labels, expected answers or another arm's output. It supplies no answer,
summary, canonical episode, dependency graph or memory update.

Every new arm uses the same proposed admission rule: the entire selected set,
in presentation order, reaches fresh generation and reviewer H unchanged, or
returns `packet_unadmittable` with no dispatchable packet. Neither consumer sees
the selector's wider pool or reasoning. Existing budgets/reserves and source
bindings stay intact. The initial builder belongs in service-owned tests beside
`story_packet_builder.py`, uses real binders/serializers, and preserves the legacy
builder for frozen studies. Validating a greedily trimmed result is not sufficient.

The observed D04 gap is selection. Current greedy `admit_history` and individual
source omission in `HistoryAttempt.omit_before_exposure` are separate code-backed
hazards for a joint packet, not observed D04 causes. Proposed later native adoption
would invalidate the whole proposal on selected-source loss, authorize the full
pool before broader model exposure, and preserve source/scope/hash/annotation and
accepted-generation checks at exposure and commit. No automatic reselection or
empty-history fallback is proposed. This may reject a useful subset because one
optional selected exchange is oversized or lost; question that tradeoff directly.

Semantic sufficiency is not mechanical validity. A self-contained correction may
suffice alone; an original-only route can suffice when omitted material does not
change the warranted answer. Admitting a referring passage creates its conditional
antecedent need; not every question needs an original-plus-correction pair.
Ambiguous/partial evidence can remain useful without justifying a settled answer.

Exactly ten prospective cases: six exposed D01-D06 restoration cases; new N01
ambiguous reference, N02 genuinely corrected original, N03 no-history request;
and M01, D02 with E01 withheld from every candidate pool. Inputs, source-quoted
alternative sufficient routes, qualifications and deletion challenges must be
reviewed/frozen before scoring. All controls are author-labeled, not blind.
Case-level assessment separates availability, selection, admission, qualification,
uncertainty, irrelevance and request cost; there is no aggregate quality score.
An empty N03 response is conformance, not superiority over always-fill methods.
Gains confined to exposed restoration cases warrant only limited follow-up.

The next proposed implementation slice is offline control preparation and packet
mechanics only. A separately approved campaign would permit ten one-attempt
selector calls, no repairs/rerolls and zero generation, reviewer, embedding or
native calls. It cannot establish actual reply quality. Later answer/reviewer
comparison and native integration need separate design, authorization and evidence.
The existing reader's newest-128 scoped-exchange boundary is not widened here.

## Questions To Resolve

1. Is the whole selected set the right preservation unit, or does it impose
   avoidable failure beyond real dependencies? Give a minimal overflow/source-loss
   counterexample and the smallest defensible alternative, without silently
   converting selection to greedy salvage or requiring speculative infrastructure.
2. Can the three-arm comparison justify its extra semantic-model request under
   the retained cap? Challenge asymmetries in cardinality, uncertainty, ordering,
   admission and cost. Four is the user's current study choice; if changing it is
   better, identify a separate policy decision rather than quietly waive it.
3. Can the proposed ten cases and source-quoted judgments detect false clarity,
   omitted genuine corrections, ambiguous referents and known-template overfitting?
   Identify the smallest pre-outcome revision needed, if any; do not grow a broad
   benchmark or use answer-string inclusion as a semantic oracle.
4. Are source-only output, identical final H and the proposed failure states enough
   for this offline slice? Separate defects that block it now from pool-exposure,
   race, lifecycle or persistence requirements that must precede native adoption.
5. What should change our next action? Recommend proceeding, revising or reframing
   only as far as the evidence allows. A cheaper method or a conditional stop is
   welcome. Distinguish a useful packet gain from downstream product qualification.

## Required Reading At The Pinned Source

Append each repository-relative path to the raw-file base above. Start with the
design and observed evidence; inspect only code needed for consequential findings.

1. `docs/product-contract.md`, `docs/plans/character-evidence-recovery.md`, and
   `docs/adr/0060-joint-history-packet-admission.md`.
2. `workflows/evals/character_memory_dev/story_continuity/evidence_selection/`:
   `PROTOCOL.md`, `READOUT.md`, `behavioral/READOUT.md`, `behavioral/results.json`.
3. `workflows/evals/character_memory_dev/story_continuity/correction_dependencies/`:
   `cases.json` and `judgments.json`, the unchanged original ledger/author labels.
4. `services/ade-api/src/ade_api/features/agent_runtime/`: `history_ranking.py`
   (`rank_windows`), `history_admission.py` (`admit_history`), `history_attempt.py`
   (`omit_before_exposure`, `authorize_ranking_sources`, `authorize_request`),
   `persistence/history.py` (`read_history_corpus`), `persistence/history_guard.py`
   (`validate_admitted_history`, dispatch/commit guards), `natural_memory_binding.py`
   (`build_natural_binding_map`). Also inspect
   `services/ade-api/tests/agent_runtime/story_packet_builder.py` (`build_history_packet`).
5. `workflows/evals/character_memory_dev/story_continuity/evidence_selection/`:
   `REVIEW_ASSESSMENT.md` and `RESEARCH_REVIEW.md` for reviewed historical input,
   not an independent validation of this proposal. No new literature survey needed.

Private raw router bodies/reasoning, service/configuration receipts and ignored
native traces are unavailable. Published synthetic results retain visible outputs
and reviewed metadata, not an independently repeatable private-capture audit.
Original reports and old protocols are historical; do not revive their superseded
next steps or treat AI-manager review as human/blind validation.

## Requested Report

Lead with the few consequential insights and their effect on our next action.
For each relied-upon finding, cite the source commit, exact path and symbol/passage,
separate observed facts from inference/hypotheses, and provide the smallest
counterexample or test. Explain the minimum recommended design/experiment change
and what can wait. State access gaps, inspected files, prior context and what the
evidence cannot decide. Be concise where possible and detailed where needed.

Your report will be preserved unchanged; our factual verification, insight-level
integration and decisions will be recorded separately. Consultation is not
implementation acceptance, execution approval or release evidence.
