# M3 Prompt Center → Immutable Agent Studio Version: Isolated UI/API Check

Status: Step 1 journey passed on 2026-09-22 (local time). This is UI/API and
persistence evidence, not native model or release qualification.

## Boundary And Fixture

- Real production-build ADE Web at `http://localhost:3121`, real ADE API at
  `http://127.0.0.1:3120`, and real PostgreSQL persistence in the verified
  disposable container `ade-m2-memory-it-01a0ca1b`. The separate database
  `ade_m3_prompt_journey_01a0ca1b` was created and migrated to
  `20260902_0006`; no pre-existing test database was reset.
- `ADE_REPOSITORY_ROOT=/tmp/ade-m3-step1.hunxJr` holds copied `config/` and
  `content/`. Prompt Center writes only the synthetic
  `chat_m3_step1_01a0ca1b` prompt and `chat_m3_persona_01a0ca1b` persona
  there, including the persona's separate SQLite database. No repository
  prompt/persona file or production database was edited.
- The **only mocked application boundary** was the Model Router catalog
  transport at `127.0.0.1:3122`: GET `/v1/router/model-catalog` returned the
  copied deployment manifest through its normal catalog serializer. Every
  non-catalog route rejected requests. Its log recorded three catalog GETs
  and zero generation/embedding POSTs. The ADE API, Prompt Center routes,
  definition/session routes, and persistence were not mocked.
- One baseline fact, `person.preference: synthetic red tea`, was seeded in the
  disposable database through the existing `prepare_memory_review` and
  `commit_memory_review` path, with a synthetic run/message and vector. It is
  a fixture for testing cross-version subject sharing, **not** evidence of
  native extraction, reviewer, or embedding behavior.

## Browser And Read-Back Evidence

The retained in-app browser handoff tabs are Prompt Center tab `3` at
`http://localhost:3121/prompt-center` and Agent Studio tab `4` at
`http://localhost:3121/agent-studio?conversation=96994d41-db03-5b06-bbf9-003368adbc78`.
The latter currently shows the original conversation; the new conversation
can be selected from its conversation list or opened at
`http://localhost:3121/agent-studio?conversation=3205b1f0-f387-584e-9c68-5379380a64ac`.

1. Prompt Center UI created the synthetic prompt and persona. A real Agent
   Studio definition v1 (`7b9ac81f-3fef-41be-9057-ddcb0ca7aec3`) and
   baseline conversation were created with subject
   `3d2bb297-8df6-5257-956b-65bd41d9caa7`. The UI showed the seeded
   active fact after reload.
2. Prompt Center UI saved an edit changing the persona from “version one” to
   “version two” (`Persona Prompts: Update OK`). Agent Studio still displayed
   the old preview; its first Create version click returned “Templates changed
   in Prompt Center. Review the refreshed previews before creating a version”
   and refreshed the displayed persona text. API read-back still found only v1.
3. A second Create version click created v2
   (`99e9892b-b5bd-411e-b1dc-c25a4d15218c`) and selected it for the next
   conversation. The new conversation used that version and the **same**
   subject; its UI showed the same active fact and original-message citation.
   Returning to the old conversation still showed v1 and its original
   message/fact. API and PostgreSQL reads confirmed immutable persona content:

| Conversation | Version | Subject | Persona SHA-256 |
| --- | ---: | --- | --- |
| `96994d41-db03-5b06-bbf9-003368adbc78` | 1 | `3d2bb297-8df6-5257-956b-65bd41d9caa7` | `1cd7213909bcb0c55525f89f3b83199cafb5faa8d2df7da75dbc12703c82307d` |
| `3205b1f0-f387-584e-9c68-5379380a64ac` | 2 | `3d2bb297-8df6-5257-956b-65bd41d9caa7` | `9b205918a9342bf5269dce2d049c4ec29be45030bc61441b1cf60c365ee5f2ff` |

Both versions retained prompt SHA-256
`56bd0286c879aa85f38ce5c9aaf4865cebfe0397e5a52ee1d17ed7b86dcbc66a`.
The shared fact remained active at version 1. A real API create request using
stale `expected_current_version=1` after v2 existed returned HTTP 409
`agent definition current version does not match` and created no v3.

Focused guardrails passed: 8 API resource/release-policy tests and 9 web hook
tests. Release mode was not reconfigured or bypassed; this journey used the
existing development mode. The remaining preview-to-snapshot race between
the final read and concurrent edit is documented in [ADR 0023](../adr/0023-agent-studio-intent-and-async-ownership.md).
