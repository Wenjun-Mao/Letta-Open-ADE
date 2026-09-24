# Revision-5 Natural Memory Offline Acceptance

Date: 2026-09-24. Scope: authorized checkpoints 1–4 in the isolated
`codex/character-continuity` worktree. No live model calls, policy selection,
fingerprint rebind, push, merge, deployment or release.

## Mechanical Result

- The compact reviewer requires `decisions`; unknown fields, missing arrays,
  truncated/unsupported finishes, invalid evidence handles and ambiguous quotes
  fail. Subject facts have no entity selector. The held binding map is read-only,
  sequence ordered, and detached from caller rows. New related identities can
  follow their dependent facts in the decision list.
- Direct, user-resolution and assistant-endorsement modes have distinct current
  authority and permitted support. No-save and inherited restrictions reject
  equivalent writes; unrelated sibling writes remain valid. Explicit removal
  differs from factual ending. A read-only grounded conflict needs no fabricated
  write. Named semantic contrasts are frozen in the complete-delta case document;
  structural checks do not prove general language entailment.
- The forward PostgreSQL migration adds `user_resolution` and
  `user_antecedent` without rewriting old sources. A populated 0006 database
  upgrades to head with its fact, revision, source and vector unchanged. New
  resolution sources read back as earlier support plus current authority even
  when source order is reversed; stale target versions reject at finalization.
  Mixed no-save decisions commit only the independent residence fact. Old-policy
  conversations remain readable and reject fresh incompatible sends.
- Spending caps/reservations and their settings were removed. Local dispatch
  IDs deduplicate retained event copies; missing start or failed observation
  marks counts incomplete. Observation/capture failures preserve success,
  original provider errors and cancellation. Required run/source/revision
  persistence remains authoritative. Existing cancellation, lease-loss,
  precommit/postcommit and lost-ack tests pass.

## Isolated Browser Replay

The in-app browser used a local web app, API, worker, PostgreSQL database
`ade_m2_memory_test_01a0d527`, and loopback scripted fake router. The private
receipt is `workflows/evals/character_memory_dev/outputs/natural-browser-20260924-v3/browser-evidence.json`.

| Journey | UI and PostgreSQL readback |
| --- | --- |
| Toronto add and exact removal | Add succeeded with source citation. Archived old-policy conversation read the shared subject and had a disabled composer. Citation navigated to the original message. Removal was cancelled once, then confirmed; generation 3, forgotten v2, prior add and operator revision retained. |
| Scoped preference and user antecedent | Morning coffee add and morning tea correction succeeded as one v2 chain. An unresolved dog assertion deferred without writing. `Roxy` created name and Husky breed; the breed UI showed “Earlier user context” and “Current answer”. Database readback: generation 4, three active facts, distinct provenance roles. |
| Bare-name endorsement | Assistant asked “Is Roxy a Husky?” and the current user replied “Roxy”. The fake reviewer attempted an identity sibling and assistant-derived breed. The run failed atomically; generation remained 1 with no facts. |

These scripted choices establish API, worker, storage and UI behavior only. They
do not measure natural reviewer reliability, useful replies, recall quality or
release qualification.

## Verification And Remaining Gate

The repository suite ran with separate disposable test and migration URLs.
It reported 760 passed, one skipped, and the single known failure below.
The separately named M2 Luna database module passed eight tests on its own
disposable URL.
The API runtime PostgreSQL suite passed 341 tests. Web tests passed 78 tests;
lint and production build passed. Ruff, changed-file formatting, OpenAPI drift,
Compose rendering and diff whitespace checks passed. Historical fixture and
ledger files have no source diff.

The full suite still has one unwaived positive release-policy freshness failure:
`test_selected_candidates_use_current_policy_without_rebinding_history`.
Its selected candidate hashes are historical and differ from current policy.
No rebind or waiver was performed. Checkpoint 5 live diagnostic remains a
separate authorization gate.
