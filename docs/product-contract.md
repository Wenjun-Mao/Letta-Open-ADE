# ADE Current Product Contract

Updated: 2026-10-19. This is the single entrypoint for **current agreed product
intent**, not a claim that every agreement is implemented or release-qualified.
It consolidates existing decisions; it does not authorize implementation, live
experiments, deployment, or a change to release evidence.

## Product Direction

ADE is a local-first workspace for configuring, testing, and improving agents.
The current character goal is natural conversational continuity with Lin Xiaotang
(林小棠): meaningful factual updates and relevant recall without memory commands,
repetitive personalization, or invented shared experiences.

## Settled Agreements

IDs remain stable when wording is clarified. Change a decision explicitly rather
than silently changing its meaning. Status below describes evidence on the
retained development branch, not the deployed production revision.

| ID | Current agreement | Implementation / evidence status | Source |
| --- | --- | --- | --- |
| PC-01 | Natural dialogue is the primary interface. Users should not need to say "search memory" or phrase ordinary changes as storage commands. | Phrase-based tool forcing removed; natural tool selection and recall have bounded live observations, not general qualification. | [Design goal](architecture/natural-memory-design.md#1-product-goal-and-revised-recommendation), [ADR 0036](adr/0036-discretionary-curated-tools-and-structured-requirements.md) |
| PC-02 | All learned conversational memories, including user facts and preferences, belong to `(workspace, subject, character root)`. Reusing the same subject and character preserves continuity across chats and ordinary persona-version updates. A different subject or character does not inherit them. | Character-local ownership has real SQL and representative native subject/character/workspace negative-access evidence, plus browser scope switching. Broader boundary and semantic qualification remain pending. | [ADR 0068](adr/0068-hindsight-default-memory.md#character-local-learned-memory), [superseded ADR 0022 scope](adr/0022-incumbent-memory-first-product-slice.md) |
| PC-03 | Shared conversational experiences belong to the same user and the same character across chats and ordinary persona-version updates. Definition root identifies that character; a different character needs a distinct root, not a similarity guess. Neither learned facts nor experiences transfer to another character (PC-02). | Same-bank continuity across fresh chats is observed in six scoped captures; ordinary-version/root mechanics have SQL coverage. General historical/semantic recall remains unqualified. | [ADR 0068](adr/0068-hindsight-default-memory.md#character-local-learned-memory), [historical design section 3](architecture/natural-memory-design.md#3-fact-identity-scope-and-time) |
| PC-04 | Persona edits create immutable versions. New conversations can use the new version; previous conversations retain their original binding. An ordinary version edit does not create a different character. | Version creation and retained bindings have isolated UI/API evidence. | [M3 version journey](findings/m3-prompt-center-immutable-version-journey.md), PC-03 |
| PC-05 | Memory interprets natural factual meaning, scope, uncertainty, corrections and supported lifecycle operations. ADE enforces source integrity, structural ownership and truthful outcomes. The Hindsight path follows PC-14's separate persistence authorities, not a duplicate ADE reviewer or native fact-version transaction. Valid attribution is not proof of correct interpretation. | The incumbent is unchanged. The development Hindsight reply/delivery/inspection replacement is implemented with scoped real-product evidence, not general semantic qualification; no second ADE reviewer executes in that path. | [ADR 0068](adr/0068-hindsight-default-memory.md#separate-product-records-and-learned-memory), [incumbent ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md), [live findings](findings/natural-memory-factual-followup-2026-09-24.md) |
| PC-06 | Do not implement conversational privacy/no-save/consent policy features or phrase-specific semantic rules, including equivalent keyword tables. This is removal, not dormant configuration. Structural subject/character isolation, credential handling and syntactic validation remain. | Natural and typed memory rules and phrase-based tool routing removed in the development branch. | User direction 2026-09-24, [ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md), [ADR 0036](adr/0036-discretionary-curated-tools-and-structured-requirements.md) |
| PC-07 | Manual memory removal is deferred for the first Hindsight integration. Hindsight handles ordinary updates/corrections from conversation; neither a deletion control nor guaranteed conversational deletion is required. Preserve original chat and report outcomes truthfully. | The development Hindsight path omits manual-removal/reset APIs and controls. Incumbent removal and historical lifecycle/atomicity evidence remain unchanged, not requirements to restore; no erasure or topic-suppression guarantee. | [ADR 0068](adr/0068-hindsight-default-memory.md#defer-manual-removal-use-native-updates), [incumbent ADR 0026](adr/0026-memory-removal-reply-boundary.md) |
| PC-08 | Keep ADE-owned PostgreSQL product records and one product API/runtime. Hindsight owns learned-memory state under PC-14, with a separate persistence boundary. Model Router separates model/provider identity from product behavior. Embedding identity must not depend on deployment on Spark specifically. | The isolated development candidate uses separate ADE/Hindsight PostgreSQL authorities and one product API/runtime. No production transition or paired-restore qualification is established. | [ADR 0068](adr/0068-hindsight-default-memory.md#separate-product-records-and-learned-memory), [ADR 0019](adr/0019-ade-steady-state-runtime.md), [ADR 0027](adr/0027-provider-neutral-release-and-embedding-space.md) |
| PC-09 | Prefer minimum code and direct ownership. No speculative memory service, episode store, second reviewer, or generic framework. Count provider requests observationally, without spending gates; retain execution timeouts, explicit retry semantics and finite tool loops. | Spending controls removed; new architectural additions require a demonstrated need and explicit decision. | User direction 2026-09-24, [ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md), [conventions](development-conventions.md) |

## Archived Conversations

**PC-10 (agreed 2026-09-25):** Archived conversations remain eligible for natural
historical recall within PC-03's same-user/same-character boundary, including
ordinary persona-version updates. Archiving changes conversation-list visibility;
it does not erase history or reset character continuity. Retrieval must not restore
the conversation merely to read it. Eligibility does not require mentioning every
archived conversation or make its historical statements current facts.

This is an agreed product contract, not implemented historical-retrieval behavior.
Reconcile recovered source text with later corrections rather than treating old
statements as current facts. PC-07 defers manual removal from the first Hindsight
integration; incumbent removed-fact recovery requirements remain historical.

## Improvised Character History

**PC-11 (agreed 2026-09-30):** Xiaotang may invent solo past experiences as part
of her fictional life. Users should expect those stories to remain consistent
later, rather than being disposable conversational decoration. Permission to
create her own history does not authorize invented user facts, past user
statements or shared user-character experiences (PC-03/05).

Authored biography remains the common foundation, subject to immutable persona
version bindings (PC-04). Improvised stories belong to the same user/subject's
continuing relationship with the same character within the workspace (PC-03),
not to a universal biography shared across users. Their continuity spans chats
and ordinary persona-version updates; archived chats remain eligible under
PC-10. These stories do not transfer to another user/subject or character root.

Ordinary conversation preserves established history while allowing compatible
elaboration and genuine error correction. It is not a co-authoring interface for
deliberately rewriting established episodes to match a new suggestion. New details
must not be presented as details already told to, or experienced with, the user.

Clarification agreed 2026-10-02: when recalling an established episode, incomplete
evidence should remain uncertain rather than invite an invented missing detail.
Natural wording belongs to the answering model; no fixed uncertainty phrase is
required. This does not withdraw permission to create new solo fictional stories.

This is accepted product intent, not a claim that current history retrieval or
review implements reliable character-story continuity. It selects neither a new
store nor an expanded reviewer mandate (PC-09). Story admission and correction
semantics, and sufficient implementation remain open below.
See [ADR 0050](adr/0050-consistent-improvised-character-history.md) for rationale
and the distinction between new fiction and faithful recollection. The
[continuity-probe plan](plans/character-story-continuity.md) records the separately
approved bounded diagnostic and its evidence limits; PC-11 itself is not a
standing live-run authorization or release qualification.

## Character Specification And Assessment

**PC-12 (agreed 2026-10-04):** Persona Definition owns authored, versioned
characterization, including behavioral tendencies. Conversation Behavior applies
that characterization to the present exchange, interpreting available context
and choosing and expressing a response. The boundary is authored intent versus
contextual application, not static facts versus all behavioral instructions.
ADE-wide requirements remain independent of persona-specific expectations.
Traits are tendencies, not mandatory actions in every reply.

Assess **grounding**, **conversational judgment**, and **character fidelity**
separately as overlapping properties of observable responses. They are not
independent causal diagnoses, internal phases, emitted planning objects, or scores
to average into one character-quality result. Subjective assessments identify the
relevant persona intention, response passage and contextual reason; multiple
acceptable responses and genuinely indeterminate cases remain possible.
Grounding respects PC-11's permitted new solo fiction without authorizing invented
user/shared history or unsupported recollection. Story-admission mechanics remain
open. Diagnostic comparisons verify actual inputs and semantic sufficiency;
source identity alone proves neither sufficiency nor reliable behavior.

This records agreed responsibility and assessment vocabulary, not a new subsystem,
agent, reviewer, model phase, persona edit, live run or behavioral qualification.
See [ADR 0061's clarification](adr/0061-capability-responsibility-map.md#character-clarification-2026-10-04)
and the [assessment guide](architecture/capability-map/character-assessment.md).

Clarification, 2026-10-10: Character receives relevant memories and their context
alongside characterization and dialogue, not a packet it must adjudicate. Memory
categories, attribution and time remain useful context. Evidence terminology can
remain appropriate for ingestion diagnostics and evaluation. This changes no
grounding agreement or requirement to assess observable responses separately.

Clarification, 2026-10-12: useful continuity reduces unnecessary repetition,
improves a relevant response or creates appropriate recognition; recalling more
facts is not itself better. Assess corrections, genuine changes, temporary
choices and unresolved ambiguity according to their meaning, not merely the
latest stated value. Apply these distinctions when relevant to the exchange,
without requiring history recitals or fixed wording. The assessment guide's
[continuity calibration](architecture/capability-map/character-assessment.md#continuity-calibration)
records agreed examples, not behavioral qualification or a completed test suite.

Clarification, 2026-10-13: repeatable assessment freezes the conversation case
before observing an answer and preserves the actual run separately from its
review. Report each lens as meets, partly meets, fails or cannot assess, with a
response passage and contextual reason. Calibrate with human review; AI judging
may assist but is not the sole authority. Retain all attempts and report by
promise/lens with denominators, uncertainty and repeat consistency, not an overall
average. Mechanical failures remain visible separately. This selects no numerical
release threshold, runtime schema or execution authority. See the guide's
[review method](architecture/capability-map/character-assessment.md#repeatable-review-method)
and [ADR 0061](adr/0061-capability-responsibility-map.md#repeatable-assessment-clarification-2026-10-13).
Implementation status: the [kit](../workflows/evals/hindsight_integration/README.md)
now includes six source-bound real-product captures and scoped safety observations.
Character judgments remain UNREVIEWED; human calibration, the full assessment
baseline and general Memory reliability remain unqualified.

## Hindsight Hosting

**PC-13 (agreed 2026-10-10):** Use self-hosted Hindsight, not Hindsight Cloud,
for the planned experimentation and any subsequent adoption under this direction.
The user rejected Cloud's usage pricing for repeated tests and re-ingestion.
Do not reopen Cloud as the default next step. Self-hosting does not eliminate
model/infrastructure costs or require every model to run locally.

The first experiment must remain isolated from native memory, as explicitly
requested during setup planning. Reusing model infrastructure must not change
native persistence or the running ADE/trial services. The user subsequently
selected the existing OCI ARM host instead of the Mac for this experiment, to
avoid extra Mac memory/swap pressure. At that time the announced 4-core/24 GB
upgrade was unverified, so the first experiment targeted the then-current
2-core/approximately 12 GB host. The later upgrade verification is recorded
under PC-14; it does not change the first experiment's historical resource evidence.
The [setup plan](plans/hindsight-self-hosted-experiment.md) records this placement
and preparation through OCI deployment, iterative replay, recovery and shutdown.

Clarification, 2026-10-11: expand this into an approximately ten-hour autonomous
campaign, with the user starting Goal mode after the plan is settled. Routine
diagnosis, repairs, configuration choices and justified retests must not require
renewed approval or stop at an arbitrary replay/generation count. Preserve prior
evidence, product expectations, resource safety and the experiment's isolation;
the plan distinguishes routine decisions from genuine authority/risk changes.

The user explicitly started Goal mode on 2026-10-11, authorizing the plan's P0-P4
campaign with a ten-hour target, twelve-hour hard cap and separate Codex tasks.
Planning alone granted no live authority; activation grants bounded operational
authority, not production adoption, migration or cutover.
Clarification, 2026-10-11 12:47:46 UTC: the user authorized extending the
campaign time limits at the operator's judgment to finish the goal. This
supersedes the plan's earlier prohibition on extending campaign time. In this
execution, work continued beyond the ten-hour target and all live work and the
sealed archive finished by the original twelve-hour hard stop and cutoff; the
original activation/target/hard-stop timestamps remain immutable records and no
previously admitted operation deadline was changed. The time clarification did
not expand product, safety, deployment, or adoption authority.
PC-05/08/09 continue governing the incumbent; no runtime spending gate is added.
See [ADR 0062](adr/0062-self-hosted-hindsight.md) for rationale and guardrails.

Clarification, 2026-10-11: after reviewing the completed campaign, the user
approved a five-hour-target/six-hour-cap semantic diagnosis-and-repair follow-up
through Relay Direct. The existing setup plan's revision 5 records fresh clocks,
controls, execution permissions and closure requirements. This authorizes
isolated synthetic candidate work and the existing inference routes, not native
integration/adoption, a native model-default change or a weakening of PC-02/03/07/
11/12. Earlier failures and revision-4 evidence remain immutable historical
results. Direct approval does not itself create or resume native Goal mode.

Status, 2026-10-11: revision 5 is closed at tested runtime source
`d2a27c338d71d90ef2fa8ad7a7085682a7aa4e06`. Its
[finding](findings/hindsight-semantic-follow-up-2026-10-11.md) records verified
Character context/request mechanics, mixed semantic results, stopped candidate
services and a sealed archive. No fresh restart/restore or lifecycle qualification
was performed; revision-4 proof remains historical. This changes no product
agreement and authorizes neither another activation nor native adoption.

## Default Memory Implementation

**PC-14 (agreed 2026-10-12):** Adopt self-hosted Hindsight as ADE's default
Memory implementation. The user selected adoption after reviewing the completed
experiments and separating Memory findings from Character behavior. The next
planning activity is integration and transition, not another vendor-selection
gate. [ADR 0068](adr/0068-hindsight-default-memory.md) records this decision.

The domain remains Memory: Retention & Updates, Organization & Maintenance, and
Recall & Context. ADE preserves its product ownership and scope/continuity
contracts while using Hindsight's concrete capabilities. Character continues to
own interpretation and response behavior; Interface owns user-facing use,
configuration and inspection. Adoption neither transfers those responsibilities
to Hindsight nor qualifies them through Memory tests (PC-11/12, ADR 0061).

This supersedes the earlier assessment-only/adoption-deferred direction, not
historical findings or the requirement for an integration design. PC-13's
self-hosting choice and PC-01/02/03/04/06/07/10/11/12 remain in force. Incumbent
reviewer and atomic-memory-write mechanisms in PC-05/08/09 are not requirements
to duplicate inside Hindsight; the integration design must explicitly replace
conflicting transaction and service assumptions while retaining one ADE-owned
product API, source integrity, ownership boundaries and truthful outcomes.
No generic Memory framework or second semantic reviewer is implied.

Ownership correction, 2026-10-12: the user rejected making a preference told to
Xiaotang available to another character. PC-02/03 now scope all learned memories
to the same subject and character root, including ordinary user facts. The
previous portable/shared-profile exception is superseded. There is no
cross-character shared-profile pool or automatic propagation of learned facts.
Same-character continuity across chats, versions and archive state remains.
This is structural Memory ownership, not a new consent/no-save policy or a
sharing-feature request (PC-06). Prior experiment fixtures and outcomes retain
their historical meaning; their cross-root profile-sharing cases do not qualify
the new contract. Bank layout must implement this boundary rather than adopt
the experiment's subject-wide sharing policy by default.

Clarification, 2026-10-12: start the integration with a fresh workspace/subject
and leave all existing data untouched. Historical migration/backfill is outside
this scope, not a required later phase. Backward compatibility is not a design
goal: replace incumbent contracts where needed rather than adding legacy
adapters, dual writes, fallback execution or compatibility-only abstractions.
Preserving existing data does not require the new runtime to open or resume
legacy conversations. This permits breaking code/API changes in the eventual
approved implementation; it does not authorize deleting or rewriting retained
data or changing live services now. Scope and continuity agreements apply within
the new workspace/subject; a fresh start must not silently reset an existing one.

Ingestion agreement, 2026-10-12: deliver accepted user messages and committed
Character replies to Hindsight with explicit speaker, time and conversation
attribution. Exclude uncommitted reply candidates. An accepted user message
remains eligible if reply generation later fails. Preserve utterance attribution;
delivery does not declare every proposition a true shared event (PC-03/11).
Use durable asynchronous delivery with visible progress and failure status.
Conversation success, delivery acceptance and retention completion are distinct;
queued work must not be presented as completed memory. Exact source units and
ordering/retry mechanics remain integration design decisions.

Freshness agreement, 2026-10-12: replies do not wait for pending retention to
finish. Perform normal scoped recall against available Memory and supply the
current input and bounded recent dialogue independently of retention completion.
Recent turns already present in the current conversation context do not need a
second copy from Hindsight. This does not imply that other chats or all older
messages are in context; recall of those sources may lag while ingestion is
pending. Interface shows retention progress/failures. No retention catch-up
barrier is required, and pending work must remain distinguishable from completed
processing. This does not skip the normal recall call.

Recall-failure agreement, 2026-10-12: if a Hindsight memory lookup fails, pause
that reply and offer Retry in Interface. Preserve the accepted user message;
do not continue Character generation with an empty-memory substitute or report
that nothing was remembered. The interface explains the service failure rather
than generating a Character apology. Retry attempts the reply for the saved
message, including a fresh scoped lookup, without appending the user's message
again. A successful lookup with no relevant memories is a valid empty result,
not a failure. Pending retention alone still does not block a reply. Detailed
attempt/idempotency mechanics remain integration work.

Scope amendment, 2026-10-12: defer manual memory removal from the first Hindsight
integration and cancel the unstarted removal-preservation probe. This supersedes
the earlier native-invalidation requirement and removal-specific ingestion gate
recorded in [ADR 0068](adr/0068-hindsight-default-memory.md#remove-saved-memory-without-erasing-chat).
Let Hindsight handle ordinary factual updates/corrections through retention and
consolidation; ADE does not add a second semantic reviewer, manual update commands
or keyword rules. Verify corrections through native state and subsequent recall,
not manual fact repair. This is no promise of perfect correction, conversational
deletion or erasure of original chat. Isolation, source attribution, delivery
integrity and recovery requirements remain; old-source rebuild remains excluded.

Storage agreement, 2026-10-12: ADE remains authoritative for original conversation
messages, character definitions/bindings, run state and durable delivery status.
Hindsight owns extracted memories, organization, recall and memory curation; it
may retain source copies for processing without replacing ADE's chat record.
Do not maintain a second ADE fact store or semantic reviewer alongside it.
Source delivery and its bookkeeping are not another Memory engine. ADE product
commits and Hindsight retention are separate persistence operations, not one
cross-service transaction. Protect both stores in backup/recovery planning;
replaying chats is not an equivalent restore of Hindsight's learned state.
Exact backup coordination and restore procedures remain integration work. This
amends PC-05/08's incumbent reviewer and single-authority
assumptions for the new path, not Character responsibility or PC-02/03 isolation.

Planning placement, 2026-10-12: the user selected a new isolated stack on the
existing OCI host for the first live ADE + Hindsight integration checks. Preserve
current ADE/trial services and archived experiment evidence. The completed host upgrade
was confirmed read-only as four cores and 23.4 GiB RAM; measure full-stack resource
use before qualification. The [three-stage plan](plans/hindsight-integration.md)
covers the complete flow, boundary/failure verification, and recovery/fresh-start readiness.
This selects a test location, not implementation or live-operation permission.

Separate cleanup, 2026-10-12: the user explicitly authorized retiring the old
OCI test stack and synthetic database/cache while preserving archives, with the
unverified revision-5 restore limitation disclosed. The
[teardown record](findings/hindsight-semantic-follow-up-2026-10-11.md#subsequent-authorized-teardown)
confirms removal and unchanged unrelated services. This narrow exception to
test-data preservation does not authorize deleting ADE/trial data, modifying
historical evidence or activating the new integration.

Status, 2026-10-19: product direction adopted. The user approved Stage 1 M0-M6
and A1-A6 on 2026-10-18, authorizing scoped implementation, isolated OCI/provider
checks and repair under the [integration plan](plans/hindsight-integration.md),
with GitHub Actions excluded. The [native source/recovery boundary](findings/hindsight-native-boundary-2026-10-19.md)
has scoped evidence. The development persistence/runtime/UI and collector are
implemented; [six actual-product captures, eight representative safety cases,
native browser mechanics and paired archives](findings/hindsight-product-flow-2026-10-19.md)
have source-bound observations. All isolated activations are closed/stopped and
the baseline services unchanged. Final private indexing is being reconciled;
Character remains UNREVIEWED. Existing
ADE/trial services and retained data remain
untouched. This is not production cutover, release qualification, broader Stage 2/3
acceptance or authority to remove the incumbent's retained data.
Known consolidation defects and Character failures remain separate work items;
adoption does not turn the experiments into an M2 quality-winner claim.

## Open Decisions, Not Agreements

Historical-native investigations below are evidence limitations, not authority
to restore retired reviewer/history-trial behavior in the Hindsight path.

- Remaining Hindsight integration work under PC-14 includes broader qualification
  of native updates/corrections, logical paired restore and later fresh-scope
  readiness. Stage-1 representative fault/isolation and paired-archive mechanics
  have scoped observations, not general qualification.
  [ADR 0070](adr/0070-hindsight-message-delivery.md)
  selects bank/source/recovery identities and [ADR 0072](adr/0072-hindsight-outbox-and-saved-input-retry.md)
  selects outbox and saved-input Retry mechanics; their bounded product checks
  are recorded in the Stage-1 finding. These are integration decisions, not a reopened choice of the
  default Memory implementation. The
  [source-pinned assessment](findings/hindsight-integration-assessment-2026-10-10.md)
  and [consultation synthesis](findings/hindsight-consultation/assessment.md)
  supply candidate seams and tradeoffs, not approved implementation mechanics.
  Earlier requirements for another experiment before deciding adoption are
  superseded by PC-14; their observations and unresolved defects remain valid
  historical evidence. PC-05/08/09 continue governing the running incumbent
  until an explicitly designed and authorized transition.
- Historical source recovery: retrieval strategy, bounded evidence supplied to the
  reviewer, reconciliation with corrected or removed facts, and failure behavior.
  PC-03's character boundary and PC-10's archive eligibility are settled;
  production mechanics are not. On 2026-10-02 the user agreed to investigate bounded
  model-assisted source selection, compared with retrieval-only context expansion,
  before answering. [ADR 0057](adr/0057-model-assisted-evidence-selection-investigation.md)
  records the design direction, not implementation or live-run authorization.
  In the subsequent recovery planning, the user selected retaining four windows
  while comparing joint source selection methods. The
  [bounded recovery plan](plans/character-evidence-recovery.md) prepares that design;
  its whole-packet admission contract remains proposed rather than adopted.
  Candidate retrieval at larger scale remains a separate question.
  The [historical-recall plan](plans/natural-history-recall.md)
  revision 3 is approved for a bounded automatic-versus-empty-history probe, including
  read-only historical evidence and the final review conditions. This selects no
  production retrieval policy, default, or release-qualified behavior.
- Whether existing dialogue/history access suffices for habits, concerns and
  shared experiences before adding fact types or episode records. A drinking
  habit must not silently become a preference merely to fit today's registry.
- PC-11 implementation: what makes an utterance an established episode rather
  than a joke, hypothetical or error;
  how corrections and authored-persona conflicts are resolved; and whether the
  existing dialogue/history path suffices. Permission to improvise solo episodes,
  expected later consistency, per-user/per-character scope and ordinary-chat
  stability rather than deliberate co-authoring are settled, not questions to
  reopen.
- Reviewer settings: two low-effort replays produced correct proposed deltas,
  but no coherent native low-effort sequence or default change is qualified.
- Final context policy and release qualification. Historical release evidence
  does not qualify changed policy hashes.

The Codex context-management report is advisory input for historical recovery,
not approval to implement it or to reintroduce excluded privacy features.

## Where Each Record Belongs

- **This contract:** current product intent, exclusions and open decisions.
- **ADRs:** rationale, technical contracts and explicit supersession history.
- **Roadmap:** ordered outcomes; **tracker:** present work, blockers and evidence.
- **Plans:** bounded delivery steps referencing the relevant PC IDs.
- **Capability inventory:** source-backed responsibility and measurement map using
  Domain/Subsystem/Module (L1/L2/L3), agreed 2026-10-04; not competing product intent,
  runtime redesign or qualification. See [ADR 0061](adr/0061-capability-responsibility-map.md)
  and the [inventory entrypoint](architecture/capability-map/README.md).
- **Findings:** observed results and limits, never automatic product decisions.

When an older design, plan or historical ADR conflicts with a current product
agreement, do not silently revive it. Follow the current agreement for planning;
explicitly amend affected technical contracts before implementation. Surface a
genuine unresolved conflict rather than inventing user intent.

## Keeping Agreements Followed

For product-affecting plans and reviews, list the relevant PC IDs, any intentional
changes, and the evidence needed to verify behavior. Routine fixes need no new
ceremony or mandatory full-document reading.

When the user changes a settled direction, update this contract in the same
documentation/change checkpoint, link the rationale or ADR, and label superseded
requirements at their old entrypoint. Keep historical findings unchanged. Do not
mark an agreement implemented or verified solely because a plan or mock test says
so. Reconcile existing decisions before asking the user to choose them again.
