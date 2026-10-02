# External Direction Review: Model-Assisted History Selection

Prepared 2026-10-02 for one external reviewer. This is the complete handoff prompt.
Preparation/publication is not external dispatch or authorization to use an account.

## Purpose

Critique ADE's proposed character-history retrieval direction before we implement
its experiment harness. Help us decide whether to proceed, revise the experiment,
or reframe the problem. Being wrong could add a costly, fallible model phase that
overfits synthetic cases without improving continuity. Do not manufacture a
recommendation if the evidence supports only a conditional judgment or open question.

## Access And Evidence Anchor

GitHub-only, read-only access. You cannot inspect our local checkout, services,
databases, ignored native traces, accounts or conversation history. Do not implement,
make provider calls, start services, post issues or change repository state.

Repository discovery: https://github.com/Wenjun-Mao/Letta-Open-ADE
Review source commit: 1a5336acbd34bc3bf0adde544ff2502b8875a07a
Discovery branch: main; use the pinned commit, not whatever main later contains.
Public raw-file base: https://raw.githubusercontent.com/Wenjun-Mao/Letta-Open-ADE/1a5336acbd34bc3bf0adde544ff2502b8875a07a/

Inspect these paths at that base, in priority order:

1. `docs/product-contract.md` and `docs/adr/0057-model-assisted-evidence-selection-investigation.md`.
2. `workflows/evals/character_memory_dev/story_continuity/evidence_selection/PROTOCOL.md`.
3. `workflows/evals/character_memory_dev/story_continuity/correction_dependencies/READOUT.md`, `cases.json` and `judgments.json` in that same directory.
4. `services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py`, `persistence/history.py` in that feature directory, and `services/ade-api/tests/agent_runtime/story_packet_builder.py` for the current mechanical boundaries.

These files were publicly fetched without credentials and matched local bytes at
preparation. If you cannot access them, disclose that and limit yourself to the
summary below; do not substitute another revision or claim repository inspection.
State the actual commit/files inspected and any prior ADE context. Prior exposure
does not invalidate a useful critique, but do not present it as blind validation.

## Self-Contained Context

ADE's fictional character may improvise solo past experiences, then should recall
them consistently within the same user/character relationship across chats, normal
persona versions and archives. Genuine correction and compatible elaboration are
allowed; invented user facts/shared experiences and deliberate user-requested
retcons are not. Incomplete recall should preserve uncertainty, without mandatory
phrases. PC-05/06/09 separate semantic interpretation from structural enforcement
and reject phrase rules, speculative episode stores and a second factual reviewer.

Our reported evidence is narrower than this goal: six exposed, author-labeled
Mandarin cases use three matched episode pairs and one correction template. Each
has eight eligible exchanges. Both literal top-four selection and a novelty
candidate always admit the correction; when it merely refers back, the named
antecedent is missing in three baseline pairs and two candidate pairs. All packets
fit. This is evidence availability, not an observed generator/reviewer failure,
independent replication or production reliability. Verify the report against its
sources rather than treating this summary as independent evidence.

Proposed direction: a separate bounded model pass sees a broader eligible pool and
returns zero to four original source IDs that jointly help answer the question.
It returns no answer, rewritten history or memory update. Fresh answer-generation
and reviewer requests receive the same final admitted sources, with none of the
selector's extra context, reasoning or summaries. Structural validity is not proof
of semantic sufficiency. The baseline remains; no runtime change is implemented.

The draft protocol proposes ten cases: the six reused development cases, three
new controls for ambiguous references, genuinely corrected originals and no-history
questions, plus a D02 variant withholding its antecedent. The new controls,
labels and harness do not yet exist. Three arms share the pool: unchanged literal
top four; highest-ranked anchor plus its immediate same-chat predecessor/successor,
then literal fill to four; and semantic selection of up to four IDs. Pools contain
eight exchanges, or seven for the withheld case. Future labels/inputs precede runs.

The proposed selector uses the existing DeepSeek route, high thinking, JSON-only
IDs, 11,469 estimated input tokens, 4,096 output reserve and a 180-second deadline.
It permits one attempt per case, at most ten selector calls, without repairs or
rerolls. Generation/reviewer packets are built but not dispatched. Candidate
retrieval at larger scale, downstream answer quality and live execution approval
are separate. No model outcome for this proposed protocol exists.

## Questions Worth Challenging

1. Is a separate semantic selector the smallest justified next investment, or are
   we overengineering around a probe's four-window limit or weak retrieval baseline?
2. Can this comparison distinguish useful joint-evidence selection from fixture
   artifacts, answer/source-position leakage or unequal abstention/cardinality?
3. Are source IDs alone enough to preserve ambiguity and important qualifications?
   Where might fresh shared packets still lose meaning or mislead the reviewer?
4. Which candidate-availability, scope, cost or failure-mode assumptions could make
   a positive toy result irrelevant to actual continuity? Which matter now, and
   which can reasonably wait rather than expanding this into a broad benchmark?

Challenge the direction, not merely the implementation details. Four windows,
eight candidates, the model/settings and one-shot design are proposed experimental
choices, not universal product laws. If a better option requires revisiting an
agreed investigation boundary, identify that explicitly rather than silently
waiving it. Preserve product intent unless arguing for a separately named change.
No literature survey or endorsement of our preferred mechanism is required.

## Requested Report

Lead with your assessment and the few insights that would change our next action.
For consequential findings, cite the reviewed commit plus exact paths and symbols
or passages; distinguish direct observations, inferences and hypotheses. Explain
the consequence and the smallest counterexample or test needed to resolve it.
Propose only the minimum experiment/design changes justified by your critique,
including a simpler alternative if warranted. Name what this evidence cannot
decide. Include inspected sources, access gaps and prior-context disclosure.

Be concise where possible and detailed where the reasoning needs it. Your report
will be preserved unchanged; our verification and integration will be separate.
Consultant agreement is not implementation acceptance or release evidence.
