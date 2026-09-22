# M3: One Complete Agent Studio Continuity Workflow

Status: Proposed; implementation waits for ADR 0022 sequencing approval.

## Outcome

An operator can use 林小棠 with an explicitly selected memory subject across
conversations, inspect why a fact is remembered, correct or forget it, and
understand what happens when the persona changes. Build on existing contracts;
do not rebuild the runtime or claim all companionship requirements are solved.

## Current Starting Points

- `apps/ade-web/src/features/agent-studio/` already has resource selection,
  session lifecycle, typed fact/revision evidence, and run monitoring.
- `agent_studio_api.py` and `agent_studio_sessions.py` under the API runtime
  feature already bind a conversation to a definition version and a subject.
- `memory_policy.py`, `memory_commit.py`, and `persistence/memory.py` own
  validated writes, lineage, and subject-scoped reads.
- Existing conversations use frozen definition versions. Selecting the same
  subject intentionally shares its facts; this is not character-private memory.

## Delivery Steps

1. Trace one operator journey through the current UI/API and tests. Record only
   concrete gaps: creating a conversation with an existing subject, inspecting
   a source from an earlier conversation, distinguishing active/corrected/
   forgotten facts, and understanding definition/persona version selection.
   Reuse working controls; do not start with a replacement screen design.
2. Add failing contract/UI tests for confirmed gaps, then implement the smallest
   cohesive change. Prefer the existing conversational correction/forget path;
   do not add manual memory CRUD unless the journey proves it necessary and its
   provenance/authorization contract is separately specified.
3. Make source inspection understandable across conversations. Verify that a
   source reference resolves to the original message and that historical
   revisions cannot be mistaken for current remembered facts.
4. Verify persona changes through the existing immutable version model. A new
   conversation may bind a new version to the same subject; existing
   conversations and facts must not be silently migrated or reset. Establish
   actual API support before promising an editing control.
5. Run browser acceptance for supported flows, then native model acceptance
   when authorized generation/reviewer/embedding routes are available. Keep
   these two evidence layers separate in the tracker.

## Checks

- Same subject, second conversation: committed facts remain accessible.
- Different subjects with simultaneously active facts: queries and UI selection
  do not cross boundaries, including after rapid selection changes.
- Correction: only the latest value is active; prior source/revision remains
  inspectable. Forget: tombstone remains auditable but not active recall input.
- Reload/reopen retains selected identities and authoritative state; failed or
  cancelled runs never display an uncommitted memory write as successful.
- Persona/version changes preserve subject identity and historical snapshots.
- Targeted Python and web tests first; relevant lint/build/OpenAPI checks if
  changed. Browser checks use the built-in browser and an isolated development
  database, never reset production data.
- Actual model-driven extraction and semantic recall require native acceptance;
  fake responses and scripted memory cannot satisfy those checks.

## Boundaries And Finish

No Hindsight installation, new memory taxonomy, generic eval framework,
subscription-to-provider proxy, Spark calls, or production migration in this
slice without a separate justified scope decision. The four-call experiment
is complete; no more calls are budgeted by this plan.

M3 is not complete until the supported journey passes end to end with the
required provider evidence. Concerns, promises, shared experiences, and
long-session relevance remain named open work. Release qualification and
operator acceptance remain required; do not merge governed code using stale
policy hashes. Use checkpoint commits on the existing isolated branch and
preserve ignored research captures until their retention is resolved.
