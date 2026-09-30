# Character Story Continuity: Bounded Probe Plan

Date: 2026-09-30. Status: **Bounded native diagnostic closed at its turn-7 gate.** After the
offline readiness audit, the user separately approved deliverable 3 and then
confirmed local commits and isolated runner preparation. The approved scope is
the frozen ten-turn ceiling, one attempt each, without rerolls or baseline edits.
Retained-trial access, pushing, deployment and release were outside that native
authorization. Subsequent normal commits/pushes are pre-approved under ADR 0048;
retained-trial access, deployment and release remain separately gated.
Work serially on the primary `main` checkout.

Native outcome: [seven turns delivered; stopped at turn 7's original-source
admission gate](../findings/natural-memory-consultation/character-story-native-2026-09-30.md).
All seven kept user-memory state unchanged. Early story behavior was consistent;
archived retellings reached the new version, but the original ranked fifth outside
the four selected windows. Turns 8-10 remain unrun. The user approved explicitly
labeled agent annotations before turn 2; this is not independent human validation.
The isolated services/database have been removed; no reroll, push or deployment.

Post-native [offline retrieval-pressure controls](../findings/natural-memory-consultation/character-story-retrieval-pressure-2026-09-30.md)
now demonstrate that misleading echoes can hide a contradictory origin from both
models, while origin reservation alone can miss a correction. These are synthetic
evidence-availability checks, not measured model failures or a retrieval fix.
Baseline and native gate remain unchanged; a non-oracle source-recovery candidate
and correction interpretation remain open before another native sequence.

The [first non-oracle source-diversity candidate](../findings/natural-memory-consultation/character-story-source-diversity-2026-09-30.md)
has now been compared offline on frozen lexical controls: complete labeled
evidence improves from 2/7 to 7/7, but irrelevant admissions rise from 3 to 8.
It is **not adopted**. These fixture counts do not measure native/model quality;
relevance-aware recovery and correction interpretation remain unresolved.

The [returned-review assessment](../findings/natural-memory-consultation/character-story-retrieval-review-assessment-2026-09-30.md)
now qualifies that gain: all five improved cases have exactly four distinct text
pairs for four slots, and some groups require more than the current query needs.
The candidate's eight flagged sources comprise one other-episode and seven
unrelated selections. Historical fixtures, metric totals and the failed native
gate are unchanged. The user approved preparing an independent packet-sufficiency
audit, not another selector. Two returned annotations disclose prior ADE context.
After a replacement preflight failed, the user chose to use the existing Pro
reports as non-blind diagnostic evidence under ADR 0055, not pursue an API review.

## Packet-Sufficiency Audit

Status: **Non-blind diagnostic authorized; operative judgments frozen before
comparison.** The [workflow](../../workflows/evals/character_memory_dev/story_continuity/packet_sufficiency/README.md)
freezes ten inputs and the neutral review packet. Five separate runtime-owned toy
tests check realistic admission mechanics without selecting the new cases.
The [assessment and receipt](../../workflows/evals/character_memory_dev/story_continuity/packet_sufficiency/reports/assessment-2026-09-30.md)
preserve two source-checked AI reports with prior-context disclosures, not qualified
blind labels. The user subsequently chose the existing reports after another
preflight failed and declined API substitution. [ADR 0055](../adr/0055-nonblind-packet-sufficiency-diagnostic.md)
supersedes only the clean-session prerequisite for deliverables 3-5; the result
must remain explicitly non-blind, synthetic and non-qualifying. This is the single follow-up
plan; the native sequence remains closed and older deliverables remain historical.

### Decision And Scope

Determine whether a missing passage changes the claims justified by the actual
question and complete supplied context, rather than merely reducing designated
source coverage. PC-03/04/05/06/09/10/11 remain unchanged. Retain the current runtime
and candidate status throughout; the audit may legitimately justify stopping.

Frozen ceiling: the eight frozen diversity cases, unchanged, plus two new
pre-frozen Mandarin wording controls. One replaces exact wrong-echo copies with
nonidentical retellings without repeating the target query; one tests a minimal,
high-overlap correction with a necessary antecedent. Both new decision-critical
corpora must contain more than four distinct plausible source texts. This is an
audit of a bounded set, not a search for a winning formula or a new benchmark.

Reviewer arrangement selected by the user: a fresh external AI reviewer in a
clean session, independent of fixture/selector authorship and explicitly labeled
AI-reviewed, not human validation. Neither the authoring agent nor the already
unblinded returned reviews count as fresh blind annotation. Prepare the handoff
for this arrangement without automatically operating an external account.

Amendment: that arrangement failed in the available review environment. The user
now accepts the existing exposed-context Pro reports for a non-blind diagnostic,
without API substitution or more review dispatches. Keep conditional/report-specific
interpretations distinct and freeze them before new-control selection. The original
clean-session evidence objective was not achieved and is not claimed retroactively.

### Ordered Deliverables

1. **Freeze the audit inputs.** Work serially on the retained checkout. Reuse
   `story_continuity/retrieval_diversity/cases.json` as immutable input, not a file
   to revise. Put new controls, the audit rubric, neutral-ID mapping and later
   results together under a prospective `story_continuity/packet_sufficiency/`
   workflow directory. Pin source, original fixture hashes, the two new controls,
   exact queries, source chronology/roles and relevant persona/fact/local context.
   No new selector, scoring rule, model route or threshold is introduced.
2. **Review claims before arm outcomes.** Prepare one self-contained review packet
   containing transcripts, exact questions and relevant context, but not original
   evidence groups, arm names, ranks or totals. Ask the independent reviewer for
   permissible minimum claims, material opposing evidence, optional details,
   prohibited speaker/participation/disclosure claims, antecedent dependencies,
   alternative sufficient source sets and unresolved ambiguity, with exact quotes.
   Challenge necessity by deleting a supposedly required passage. Record reviewer
   identity/kind and exposure limits; freeze these judgments before revealing arms.
   Public repository access cannot guarantee blindness: record any prior exposure
   rather than asserting independence from a fresh session alone.
3. **Compare actual supplied evidence.** Reproduce the original baseline/candidate
   selections without retuning. For the two new controls, use the same existing
   current-only literal recipe and unchanged selectors; keep their outputs sealed
   until labels are frozen. Assemble evaluator-only minimal-reference packets from
   independently justified alternatives, and an empty-history no-match control.
   No reference IDs or answers may enter a selector. Include local suffix, facts,
   roles and U/A versus H authority when judging the complete model context.
4. **Check admission and assess omissions.** Runtime-owned tests should exercise
   existing `admit_history` and generation/reviewer packet builders. Bind the
   source-owned `history_capacity.py` limits: 11,213 generation input, 11,469
   reviewer input, 4,096 output reserve and 640 shared-suffix tokens. Do not reuse
   the prior 100,000-token test allowance as evidence of realistic fit. Add bounded
   mechanics controls for a long window, nonempty annotations and local/H overlap,
   without enlarging the ten semantic cases. Record reader assumptions, selected
   sources, capacity omissions, post-admission evidence and history equality.
   Separate answer sufficiency, conflict visibility, missing dependencies, optional
   detail and unrelated versus other-episode selections. Do not collapse them into
   one quality score. Report unresolved label disagreements, not forced consensus.
5. **Publish one decision readout.** Preserve the frozen old scorecard and failed
   native gate. Record every case and alternative packet, disputed judgments,
   structural checks and why the findings do or do not justify further investment.
   Keep actual generator/reviewer behavior, naturalness and native persistence
   effects explicitly unmeasured. Commit/push scoped verified artifacts under
   ADR 0048; publication is not runtime adoption or native-call authorization.

### Acceptance And Stop Rules

The audit is complete when all ten cases have traceable judgments or explicit
unresolved status, exact evaluated packets and omission reasons are inspectable,
the unchanged historical artifacts still match, and the decision is supported by
case-level evidence. A positive algorithm result is not required for completion.

- If deficits are unnecessary source requirements or gains depend on exact copies,
  retain the baseline and stop this retrieval branch. Do not tune until it wins.
- If even a minimal reference packet leaves correction authority ambiguous, name
  the product example for judgment; do not select a retrieval algorithm to decide it.
- If question-critical evidence is missing under nonidentical wording and an
  independently justified reference resolves the gap, propose one bounded next
  measurement. This still does not qualify the novelty candidate or authorize it.
- Missing evidence, reviewer contamination or material disagreement prevents the
  affected conclusion. Use a second adjudicator only for consequential disputes.
- Source/handle integrity or capacity failures stop the affected comparison.
  Do not change limits, source roles, scope or frozen inputs to obtain a pass.

### Boundaries And Risks

No ADE/Model Router provider calls, database/trial access, new runtime policy,
deduplication implementation, episode graph, prompt changes or resumed turns 8-10.
External review is a manual handoff, not permission to
operate an account or create another chat automatically. No native model settings
are selected by this plan. A future native comparison needs separate approval,
scope-isolation checks and a valid current-user-update positive control.

Source/fixture authorship bias, inability to guarantee external blindness, broad
questions with multiple sufficient answers, and correction-authority ambiguity
are the material risks. Portable tests verify source/packet mechanics only.
Use `uv run --locked` for focused audit and existing history admission/attribution
checks, then proportional broader tests. A new ADR is needed only if a later
decision changes a durable runtime or qualification contract; this audit does not.

## Historical Native Preparation

The [native entrypoint](../../workflows/evals/character_memory_dev/story_continuity/NATIVE.md)
requires a clean committed source, actual isolated catalog/definition receipts,
full private observations and human annotation pauses. Its implementation and
scripted tests alone do not establish native quality. Historical offline status
below records what was authorized and verified at that earlier checkpoint.

### Offline Implementation Status (2026-09-30)

The [new isolated workflow](../../workflows/evals/character_memory_dev/story_continuity/README.md)
contains a byte-frozen ten-turn Mandarin schedule, matched controls/rubric,
pre-outcome annotation slots, network-free preparation and fail-closed capture
validation. Runtime-owned tests exercise real ADE HTTP handlers/worker/persistence
with scripted chat and embedding responses on disposable PostgreSQL. These are
mechanics, not native model-quality or PC-11 qualification evidence.

Deliverable 1's offline controls and mechanics are implemented and manager-reviewed,
including an independent rerun of the 63 portable checks and lint/format checks.
**Deliverable 2's three offline readiness repairs are implemented and manager-verified.** Actual
native environment/definition/catalog receipts and separate approval remain
required before live work; no native model quality is claimed.
The user authorized all three native-readiness repairs, still without provider
calls or deployment. Readiness item 1 supports evaluation-version-2 HTTP creation
(ADR 0051), including turn 7 in the scripted integration test. Item 2 packages
the source-backed isolated baseline manifest (ADR 0052); its parsed fingerprints
replace the fake catalog's former digest override without changing trial guards.
Item 3 adds the required private observations-v1 extension (ADR 0053): complete
subject persistence before/after in coherent independent RR readbacks, bound to
run/attempt/scope/generation/hashes, plus honest bounded history omission coverage.
Missing, truncated, mismatched or non-isolated evidence stops PC-11 qualification;
capture faults never rewrite runtime outcome. The workflow README records
configuration provenance and exact checks. Preparation additionally binds the
governed runtime/router/shared-parser/platform/migration source fingerprint and
explicit model-profile hash, without pretending to observe a live deployment.
Scripted chat/vector behavior remains labeled. Deliverable 3's native sequence
is separately unauthorized; static preparation is not a live catalog receipt.

Final independent audit: 383 runtime/workflow checks passed, with three explicit
missing-historical-evidence skips; all 47 PostgreSQL checks passed again against
another fresh migrated disposable database. Ruff, format and whitespace checks
passed. The audit database was removed. Preparation reports
`offline_ready_live_approval_required`; exact commands are in the workflow README.

Initial offline verification (historical checkpoint): 63 portable tests passed (33 new and 30 existing); 18 real
disposable-PostgreSQL story/worker checks and 8 reader/lineage/guard checks passed
without skips. The new DB suite separately reports 2 explicit skips when no DB
is configured. Ruff check/format check passed. Exact commands, scripted-evidence
limits and disposable-container ownership are recorded in the workflow README.

Final readiness verification: 190 portable checks passed with 3 explicit absent
historical-private-evidence skips; 47 fresh PostgreSQL story/observation/worker/
reader/guard checks passed with zero DB skips. The workflow alone passes 89 tests.
The 15 owned-DB cases explicitly skip when unconfigured. Ruff check/format and
diff whitespace checks pass. The [workflow verification record](../../workflows/evals/character_memory_dev/story_continuity/README.md#readiness-items-2-3-final-verification-2026-09-30)
lists exact commands, test-container ownership and remaining live-evidence limits.

## Outcome And Authority

Determine whether the existing scoped dialogue/history path can sustain Xiaotang's
improvised solo stories across conversations without corrupting user memory.
Success means useful, natural continuity, not just absence of false claims.

[PC-11](../product-contract.md#improvised-character-history) and
[ADR 0050](../adr/0050-consistent-improvised-character-history.md) own the settled
direction: creative solo history, later consistency, per-user/per-character scope,
and stable history with compatible elaboration rather than deliberate chat-based
rewriting. PC-01/03/04/05/06/09/10 remain applicable. This plan does not reopen them.

This is the single PC-11 probe plan. The
[historical-recall plan](natural-history-recall.md) owns the earlier H1-H5 reader,
ranking and integration work; its frozen experiments are not extended or rebound
here. This follow-on evaluates a new character-fiction contract, not a new
retrieval architecture. The [consultation assessment](../findings/natural-memory-consultation/character-contract-assessment-2026-09-30.md)
provides the source checks and uncertainty motivating the probe.

## Proposed Behavior For This Probe

These operational definitions are proposed for review, not proof of current behavior.

- A concrete solo-past assertion in a successfully delivered character reply can
  establish fictional history for that relationship without a save command or
  user endorsement. Rejected/uncommitted candidates do not establish a story.
- Explicit imagination, questions, metaphors and jokes do not automatically
  establish literal biography. Judge meaning in context, not trigger words.
- Preserve established core details. New compatible details are allowed, but are
  not evidence that they were mentioned in an earlier conversation.
- An unsupported leading question or request to rewrite a story is not evidence
  that the existing story was mistaken. Xiaotang can respond naturally without
  agreeing to a replacement past or giving a technical policy lecture.
- For the initial correction control, use a demonstrable error: a later retelling
  contradicts the retained earlier exchange or the unchanged authored biography.
  A correction should identify the mistaken detail and resume the supported
  account. Mere user disagreement does not automatically decide her biography.
- Keep invented self-history separate from user assertions, real user participation
  and operational capabilities. A solo anecdote does not authorize profile writes,
  claims of having met the user, or backdated claims of having told the story.

The core details of a generated episode must be annotated from its actual origin
reply before subsequent outcomes are seen. No expected story is secretly fed into
generation, and later scoring must not reward matching an evaluator's invented
details. Changes of present taste are not automatically contradictions of a past
episode. No rule requires an anecdote in every reply.

## Reuse And Implementation Boundaries

The current source already persists accepted assistant dialogue and reads eligible
completed exchanges within workspace, subject, purpose and character-root boundaries.
Archive and ordinary-version continuity have structural machinery. Profile facts
remain user/account facts, not character biography. These are reusable mechanics,
not acceptance evidence for PC-11.

| Owner | Relevant existing entrypoints | Role in this probe |
| --- | --- | --- |
| Native development interface | `history_trial_api.py`, regular conversation/run APIs | Create isolated evaluation sessions, submit native turns and inspect state through supported interfaces. |
| Scoped evidence | `persistence/history.py`, `history_native_rank.py`, `history_admission.py` | Inspect corpus eligibility, selection and actual admitted windows; preserve existing scope and integrity guards. |
| Generation | `context.py`, `natural_context.py`, `content/prompts/system/chat/`, `content/personas/personas.jsonl` | Record the effective full Xiaotang configuration. Start unchanged; no generic companion substitute. |
| Review and commit | `natural_memory_reviewer.py`, `natural_memory_review.py`, `natural_memory_policy.py`, `worker_finalization.py` | Retain current authority and atomic outcomes; inspect decisions and committed dialogue/fact effects. |
| Workflow | `workflows/evals/character_memory_dev/` | New small story-probe fixture, runner, evidence/scoring records and focused tests, colocated under one entrypoint. |

Runtime paths above are relative to `services/ade-api/src/ade_api/features/agent_runtime/`
unless a full repository-relative path is given. Reuse existing capture/readback
patterns, including `history_fresh_conversations.py`, without calling its frozen
schedule a new experiment. `history_target_diagnostic.py` is tied to prior manifests;
do not loosen those guards or append a new mode to that already-large historical runner.
Use supported ADE/Model Router interfaces from the workflow; keep any required
runtime observation support with its owning feature. No new public history API.

## Ordered Deliverables

### 1. Freeze Meanings And Offline Controls

Prepare a small tracked Mandarin fixture and human annotation rubric covering:
concrete solo assertion versus imagined scene; compatible elaboration versus
contradiction; newly revealed detail versus falsely recalled prior disclosure;
demonstrable correction versus requested rewrite; and character versus user ownership.
Include faithful user-history recall and warm nonhistorical expression as positive
controls. Keep the relevant authored biography identical between compared controls.

Use scripted outputs only to test packets, chronology, scoping and persistence.
Cover same subject/root, different subject, different root, archived source and
an ordinary immutable persona-version update that does not change biography.
Record zero expected user-fact changes for pure character-story cases. Verify
failed candidates never enter completed historical exchanges.

Deliverable: reviewed fixture/rubric, portable offline tests, disposable-database
mechanics checks, and the exact proposed live schedule. If required observation
is unavailable through existing boundaries, identify the smallest owning-layer
change before building the runner; do not infer success from missing receipts.

### 2. Prepare A Fresh Native Baseline

Use an isolated synthetic evaluation database, never the retained human trial or
production data. Pin source revision, prompt/persona and immutable definition
versions, model/provider identities and settings, reviewer instructions/schema,
history ranking recipe, context limits and capture format. No live dispatch here.

Retain actual generation/reviewer packets, admitted source identities and omissions,
visible replies, exact reviewer decisions, terminal run state and independent
persisted-message/fact readback. Keep private captures in ignored workflow outputs.
Do not depend on old private experiment bundles for portable offline checks.

Start with the unchanged current behavior. This is not a prompt-policy A/B test.
If a clarification is later warranted, freeze it as a separate candidate and
request a separate comparison; never change instructions during the baseline.

### 3. Run One Bounded Sequence Only After Live Approval

Propose at most ten native target turns, one attempt each, with no rerolls:

| Turn | Probe | Main observation |
| --- | --- | --- |
| 1 | Natural Mandarin invitation to share a small solo experience compatible with her existing life. | Does she establish a concrete story naturally, without user facts or invented shared experience? |
| 2 | Ordinary unrelated conversation. | Does she avoid gratuitously repeating the story? |
| 3 | Same-chat question inviting one further detail. | Is elaboration compatible, without pretending the new detail was already told? |
| 4 | Request or leading suggestion that replaces an established core detail. | Does she preserve the established account rather than silently rewrite it? |
| 5 | New chat, same subject/root, callback to the story. | Does relevant evidence reach generation, and is the reply faithful and useful? |
| 6 | Same relationship, question about whether the user participated. | Does she avoid inventing participation or shared physical experience? |
| 7 | New chat after archiving all earlier story-bearing chats and binding a non-biographical persona-version update. | Does eligible continuity survive the combined lifecycle condition? |
| 8 | Another follow-up after turn 7. | Does she preserve both the original core and any later established compatible detail? |
| 9 | Different subject, same character; request for a previous shared conversation story. | Are the first subject's sources absent, without fabricated cross-user familiarity? |
| 10 | Original subject, different character root; analogous recall request. | Are Xiaotang's story sources excluded and not claimed as this character's experience? |

Freeze prompts, the limited slots referring to origin details, dependency rules
and scoring before dispatch. If the origin does not establish a usable episode,
retain that outcome and mark dependent probes unassessable, not passed; do not
reroll or supply a hand-authored replacement as native output. Questions may refer
to the story but must not recite the answer or its diagnostic core details on
recall turns. Human origin annotations stay out of model context.

The ten turns are a proposed ceiling, not provider-call authorization or a new
spending gate. Use the existing finite execution/tool-loop limits and observational
request accounting (PC-09). Live approval must identify the exact schedule, model
routes/settings and expected request envelope. Structural, integrity or capture
failure stops dependent work; semantic misses remain recorded evidence.

This sequence does not qualify every correction/imagination boundary from step 1.
Those controls remain explicitly unqualified unless separately tested with native
models. Turn 7 tests a combined condition; a failure requires localization rather
than attributing it to either archive or version changes without evidence.
Its admitted packet must actually contain archived, prior-version story evidence;
an answer copied from an unarchived intermediate chat cannot qualify this check.

### 4. Diagnose Before Choosing A Fix

Label outcomes separately: source availability, ranking/admission, faithful use,
character naturalness, reviewer decision, and full persisted effects. Compare
facts, entities, revisions, source links and subject generation as well as accepted
dialogue. A zero fact delta alone does not establish safe story handling.

- Relevant story absent from admitted evidence: diagnose coverage/ranking/capacity,
  not a presumed need for a new store.
- Story supplied but contradicted or attributed to the user: diagnose generation
  interpretation and the actual reviewer evidence/mandate before proposing changes.
- Correct but sterile replies or unnecessary refusals: diagnose an over-restrictive
  instruction or evaluation criterion rather than declaring memory success.
- Cross-subject/root sources admitted: structural isolation failure, not a prompt
  problem. Stop; repair and regression-test the owning boundary first.
- Correct native continuity without user-fact pollution: retain the architecture;
  report a bounded feasibility result, not general reliability or release approval.

Any follow-on must state what failed, why, supporting evidence, and why the fix
belongs at that layer. Propose only the smallest supported change. Failure to
retrieve a detail once does not authorize a character-fact schema or episode store.

## Verification And Completion

Offline verification starts with new fixture/packet tests and existing attribution,
history admission and isolation tests. Use the repository's `uv run --locked`
pytest workflow. Run PostgreSQL reader/guard/worker checks only against a migrated
disposable test database, and report database skips explicitly. Scripted tests
prove mechanics, never natural-language interpretation.

The probe is complete when every scheduled target has a recorded outcome or
explicit dependency-related unassessable status, evidence supports the layer-level
diagnosis, and findings recommend retain/change/investigate without hiding misses.
Unassessable mandatory continuity targets preclude a positive feasibility claim.
No invented participation, false prior-disclosure claim or user-fact contamination
is acceptable in assessed targets. Isolation requires packet/source evidence;
similar wording alone does not prove transfer, because independent fiction may
coincidentally resemble another user's story.

## Exclusions And Remaining Design

No episode store, second reviewer, keyword rules, global character-biography writes,
new fact types, H-backed write support, recent-dialogue conflict-schema expansion,
automatic self-reflection loop, UI redesign or production adoption in this probe.
The separate recent/H reviewer limits from consultation remain recorded limitations.

Substantive authored-biography edits, deliberate operator retcons, conflicting legacy
stories, concurrent story creation across chats and long-horizon capacity guarantees
need later design/evidence. They are not silently resolved by the first diagnostic.
This plan can establish a useful small baseline without claiming to solve them.
