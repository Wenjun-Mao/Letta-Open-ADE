# ADE Current Product Contract

Updated: 2026-09-25. This is the single entrypoint for **current agreed product
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
| PC-02 | Shared profile facts belong to the user/subject within a workspace. Reusing the subject preserves those facts across conversations and persona versions; a new subject is isolated. | Storage and UI paths implemented; bounded cross-conversation recall observed. | [ADR 0022](adr/0022-incumbent-memory-first-product-slice.md), [M3 plan](plans/m3-agent-studio-continuity.md) |
| PC-03 | Shared conversational experiences belong to the same user and the same character across chats and ordinary persona-version updates. Definition root identifies that character; a different character needs a distinct root, not a similarity guess. Shared factual knowledge does not imply participation in another character's conversation. | Agreed design, reconfirmed by user 2026-09-25. General historical-recall behavior is not implemented/qualified. | [Design section 3](architecture/natural-memory-design.md#3-fact-identity-scope-and-time) |
| PC-04 | Persona edits create immutable versions. New conversations can use the new version; previous conversations retain their original binding. An ordinary version edit does not create a different character. | Version creation and retained bindings have isolated UI/API evidence. | [M3 version journey](findings/m3-prompt-center-immutable-version-journey.md), PC-03 |
| PC-05 | The reviewer interprets natural factual meaning, scope, uncertainty, corrections and requested lifecycle operations. ADE enforces schema, source integrity, ownership, versions and atomic persistence. A valid citation is not proof of correct interpretation. | Compact reviewer and structural checks implemented; live scope omission and output exhaustion remain evidence of limitations. | [ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md), [live findings](findings/natural-memory-factual-followup-2026-09-24.md) |
| PC-06 | Do not implement conversational privacy/no-save/consent policy features or phrase-specific semantic rules, including equivalent keyword tables. This is removal, not dormant configuration. Structural subject isolation, credential handling and syntactic validation remain. | Natural and typed memory rules and phrase-based tool routing removed in the development branch. | User direction 2026-09-24, [ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md), [ADR 0036](adr/0036-discretionary-curated-tools-and-structured-requirements.md) |
| PC-07 | Explicit operator fact removal remains available. Historical messages/revisions are not thereby erased. Factual ending, correction and removal are distinct; report committed outcomes truthfully. | Lifecycle and atomicity checks implemented; no general data-erasure or topic-suppression feature is promised. | [ADR 0022](adr/0022-incumbent-memory-first-product-slice.md), [ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md) |
| PC-08 | Keep ADE-owned PostgreSQL persistence and one product API/runtime. Model Router separates model/provider identity from product behavior. Embedding identity must not depend on deployment on Spark specifically. | Native foundation implemented; current policy changes are not release-qualified. | [ADR 0019](adr/0019-ade-steady-state-runtime.md), [ADR 0027](adr/0027-provider-neutral-release-and-embedding-space.md) |
| PC-09 | Prefer minimum code and direct ownership. No speculative memory service, episode store, second reviewer, or generic framework. Count provider requests observationally, without spending gates; retain execution timeouts, explicit retry semantics and finite tool loops. | Spending controls removed; new architectural additions require a demonstrated need and explicit decision. | User direction 2026-09-24, [ADR 0035](adr/0035-compact-natural-review-and-observational-dispatch.md), [conventions](development-conventions.md) |

## Archived Conversations

**PC-10 (agreed 2026-09-25):** Archived conversations remain eligible for natural
historical recall within PC-03's same-user/same-character boundary, including
ordinary persona-version updates. Archiving changes conversation-list visibility;
it does not erase history or reset character continuity. Retrieval must not restore
the conversation merely to read it. Eligibility does not require mentioning every
archived conversation or make its historical statements current facts.

This is an agreed product contract, not implemented historical-retrieval behavior.
Explicit fact removal remains governed by PC-07; reconciling recovered source text
with corrected or removed facts must be specified in the historical-recovery plan.

## Open Decisions, Not Agreements

- Historical source recovery: retrieval strategy, bounded evidence supplied to the
  reviewer, reconciliation with corrected or removed facts, and failure behavior.
  PC-03's character boundary and PC-10's archive eligibility are settled;
  these mechanics are not.
- Whether existing dialogue/history access suffices for habits, concerns and
  shared experiences before adding fact types or episode records. A drinking
  habit must not silently become a preference merely to fit today's registry.
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
