# M3: Usable Profile Memory In Agent Studio

Status: In progress under accepted [ADR 0022](../adr/0022-incumbent-memory-first-product-slice.md).

The real isolated Prompt Center edit → new immutable Agent Studio version →
same-subject conversation journey is now covered by the
[Step 1 UI/API finding](../findings/m3-prompt-center-immutable-version-journey.md).
Its catalog-only router stand-in and synthetic saved fact do not satisfy native
reviewer, embedding, generation, or release acceptance.

## Implementation Checkpoint (2026-09-22)

Correction pass: the generated correction draft was not recognized by the
reviewer's explicit-intent detector, so it could select add mode. The shared
draft fixture and reviewer regression now bind those layers. Run monitoring
previously used the same epoch as evidence refresh, so a read of the cited
message could disable terminal handling; selection, read, and monitor identity
are now separate. Real-hook tests cover same-conversation evidence during a
run, stale cross-conversation callbacks/errors and turn acceptance, revisit,
definition choice, old-page deduplication, and return to latest. Template
previews refresh on focus/manual request; version creation checks for changed
text and pauses for review. See [ADR 0023](../adr/0023-agent-studio-intent-and-async-ownership.md).

A mock-backed browser pass opened an archived source at exact original message
5 without restore/mutation, returned to the archived conversation's latest
page, and continued an active conversation at its latest page. These checks
exercise UI navigation and rendering, not native extraction or reviewer
behavior. The unwaived policy-fingerprint failure and native qualification
gap below remain; M3 is not complete.

The UI/API slice now defaults a new conversation to the selected subject and
definition, distinguishes active from historical facts, resolves citations
through a boundary-checked conversation/message locator, prepares editable
correction/removal turns, and requires a matching run event **and persisted
fact revision** before confirming a change. It exposes Prompt Center content
preview and immutable definition-version creation with the expected current
version. Old conversation bindings remain frozen. The existing acceptance
workflow has an opt-in chronological M3 fixture and a read-only per-turn stage
timeline; the canonical qualification matrix is unchanged.

Focused API/UI tests, an isolated PostgreSQL lifecycle test, web tests/lint/
production build, and mock-backed browser journeys passed. The mock browser
pass covered same-subject/new-subject creation, a citation outside the newest
120 messages and from another conversation, no-op removal, and a new persona
version bound only to a later conversation. It did **not** exercise a live
reviewer, actual persona edit in Prompt Center, or every terminal outcome in a
browser. Archived-source citation was added in the correction pass above. The backend source read allows
archived conversations and is covered by purpose/subject/workspace guards.

The API suite passes with `ADE_REPOSITORY_ROOT` set to this checkout. The
workflow suite's governed manifest/policy fingerprint check still fails after
policy-source changes. That gate is not rebound or waived here. The opt-in
native diagnostic was validated structurally but not
executed: provider, reviewer, and embedding use require separate authority.

## Outcome And Ownership

Deliver four operator journeys for 林小棠's supported saved profile facts:

1. Open an existing conversation, start a new conversation with the same
   person's saved information, or start a new isolated person. Keep subject
   identity when opening a new conversation. Explain that subject facts are
   shared across that person's conversations and are not private character
   relationship history.
2. Inspect current active facts separately from historical, corrected, or
   removed revisions. Open an evidence quote at its original conversation
   and exact message, including archived conversations and older paginated
   messages, without restoring or changing them.
3. Prepare a visible correction or **Remove saved information** request in the
   composer and explicitly send it through the existing turn endpoint and
   reviewer/write path. Show success only after an authoritative committed
   revision is correlated with that request. Acknowledgment, no-op, rejected,
   failed, cancelled, or stale-version runs are not successful changes.
4. Edit persona content through Prompt Center to create an immutable
   definition version, preview the prompt/persona selection, and choose that
   version for a new conversation with an existing subject. Existing
   conversations keep their snapshots and release-mode guards remain intact.

The supported forget action removes a fact from active facts and search input.
Revision evidence, summaries, and earlier conversation context remain; old
context may still contain the information. The UI must use the limited wording
above and must not imply erasure, global suppression, or permanent
non-reintroduction.

## Current Contracts

- `apps/ade-web/src/features/agent-studio/` owns resource selection, session
  lifecycle, fact/revision evidence, run monitoring, and composer state. Reuse
  working controls and split touched oversized components by responsibility.
- `/api/v3` binds conversations to a subject and an immutable definition
  version. Keep existing APIs except additive source conversation ID and
  message sequence on revision evidence; join authoritatively within workspace
  and purpose boundaries and use existing session/state pagination.
- `memory_policy.py`, `memory_commit.py`, and `persistence/memory.py` own typed
  review validation, revision lineage, and subject-scoped reads. Do not add
  manual fact CRUD, a new service or schema family, or an alternate backend.
- Prompt Center already supplies immutable content revisions. Expose the
  existing definition-version creation contract with
  `expected_current_version`; do not bypass development/release restrictions.

## Implementation Order

1. Trace current UI/API journeys and identify specific gaps. Add focused
   contract and UI tests for those gaps before changing behavior.
2. Make conversation creation retain the chosen subject by default while
   offering an explicit isolated-person action. Prevent stale selection and
   read responses from rendering facts for a different active subject after
   reload or rapid switching.
3. Return authoritative evidence source conversation ID and message sequence
   through repository joins and additive response fields. Navigate the quote
   through existing paginated conversation state, including archived sources,
   with ownership and purpose rejection tests.
4. Add contextual composer actions that prepare an editable request. The
   operator sends normally. Correlate a target fact/version and the returned
   run with a committed revision before reporting success; preserve explicit
   no-op, rejection, stale version, cancellation, and failure states.
5. Expose persona version creation from Prompt Center content and preview the
   version choice. A new conversation may bind the new version to the same
   subject; old conversations and facts remain unchanged.
6. Add one small chronological native diagnostic to the existing character
   memory eval workflow: natural durable fact, natural correction, recall
   after unrelated turns, removal and a new-conversation probe, and an
   unsupported concern/follow-up. Attribute each observation to extraction,
   validation, storage, context, generation, or provider stage. Do not build
   a general evaluation framework or make a new model call.
7. Run focused tests, proportional Python and web verification, OpenAPI
   regeneration, and four UI journeys in the built-in browser against an
   explicitly isolated development database. Label mocks and scripted data.

## Acceptance Layers

**UI/API readiness:** The four journeys work with simultaneous active subjects;
reload and rapid selection retain correct identity; older/archived evidence
opens at the exact original message; correction/removal status reflects the
committed revision rather than a run acknowledgment. Verify no-op, rejection,
stale version, cancellation and failure. Persona edits preserve the subject,
old snapshots, and release guards. The limited removal copy remains visible.

**Native behavioral acceptance:** When conversation, reviewer and embedding
routes are separately authorized and available, execute the chronological
diagnostic and inspect every stage. UI/API readiness and scripted browser
data cannot substitute for this evidence. No new model, Spark, embedding,
API-key fallback, or Hindsight calls are authorized by this plan.

**Release readiness:** Keep fresh governed policy fingerprint, build,
conformance, provider qualification and ledger promotion separate. The known
full-suite production-policy fingerprint failure must be reported and cannot
be rebound or waived here. Do not claim milestone completion or release
promotion while required evidence is missing.

## End-Of-Slice Review And Boundaries

Before substantial new memory machinery, review observed operator behavior
and plainly missing required capabilities, even without a failed benchmark.
Record whether the next gap needs a small ADE contract, a measured service
comparison, or a scope change. Concern, promise, shared-experience and
relationship-history schemas are not inferred from these samples. The
original ADE/Hindsight comparison remains deferred with its historical
evidence intact.

Current review finds no demonstrated need for a new relationship schema or
external memory service. The plainly missing evidence is native extraction,
retrieval, correction/removal, unsupported concern follow-up, and operator
use over time. Run the isolated diagnostic only when the routes are authorized,
then review whether the gap is in extraction, validation, storage, context,
generation, or provider behavior before proposing new machinery. Do not treat
the absence of a failed benchmark as evidence that those capabilities exist.

Use reviewable commits on the existing isolated branch. Preserve production
state, ignored research captures, and the disposable test container. No push,
merge, release promotion, or cleanup belongs to this slice.
