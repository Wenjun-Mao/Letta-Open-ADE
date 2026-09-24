# Revision-5 Natural Memory Offline Acceptance

Date: 2026-09-24. Scope: authorized checkpoints 1–4 in the isolated
`codex/character-continuity` worktree. No live model calls, policy selection,
fingerprint rebind, push, merge, deployment or release.
This records offline evidence for director review, not release acceptance.

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

## Director Review Correction

The first checkpoint-3 implementation checked inherited uncertainty, no-save
and withdrawal only in `resolve_user`. An assistant endorsement of `Do you like
coffee?` followed by `Yes` could therefore save coffee after the earlier user
said `I like coffee. Do not save that.` A direct value fragment could also change
mode to bypass the restriction. The restriction belonged to the identified claim
in the admitted exchange, not to the selected evidence mode. The revised
authority module evaluates it for every non-removal write before the complete
review is accepted. Fresh self-contained current assertions can replace earlier
uncertainty or withdrawal; inherited no-save requires explicit, claim-bound
permission inside the cited current span. Unrelated Toronto writes remain valid.
An anaphoric save permission must attach to the nearest cited claim or to a
current assent for the selected assistant proposition; an intervening tea claim
cannot authorize saving coffee.
An explicitly named restriction such as `Do not save that tea claim` does not
attach to a preceding coffee claim merely because it contains `that`.
The regression is covered by complete-delta tests and an isolated PostgreSQL
attempt in both item orders: the prohibited coffee proposal aborts the entire
review with no fact or generation change, while a separate residence-only
review commits once.

The conflict guard formerly compared the whole candidate quote for string
equality with an F/E snapshot value. It now recognizes a plainly stated value
inside a complete answer. `Your dog is Rocky.` can still produce a grounded
read-only conflict against `pet.name=Roxy`; `Your dog is Roxy.` and `Roxy. What
else is new?` cannot be validated as conflicts. An invalid conflict review
still fails semantically; an explicit empty review permits the correct reply.
The F/E reference, current query/context and exact candidate span remain the
conflict interface. This guard covers named contrasts, not general entailment.

## Isolated Browser Replay

The in-app browser used a local web app, API, worker, PostgreSQL database
`ade_m2_memory_test_01a0d527`, and loopback scripted fake router. The private
receipt is `workflows/evals/character_memory_dev/outputs/natural-browser-20260924-v3/browser-evidence.json`.
This replay was captured before the director-review correction above. The
follow-up changes were checked in unit and isolated PostgreSQL tests, not a new
browser replay.

| Journey | UI and PostgreSQL readback |
| --- | --- |
| Toronto add and exact removal | Add succeeded with source citation. Archived old-policy conversation read the shared subject and had a disabled composer. Citation navigated to the original message. Removal was cancelled once, then confirmed; generation 3, forgotten v2, prior add and operator revision retained. |
| Scoped preference and user antecedent | Morning coffee add and morning tea correction succeeded as one v2 chain. An unresolved dog assertion deferred without writing. `Roxy` created name and Husky breed; the breed UI showed “Earlier user context” and “Current answer”. Database readback: generation 4, three active facts, distinct provenance roles. |
| Bare-name endorsement | Assistant asked “Is Roxy a Husky?” and the current user replied “Roxy”. The fake reviewer attempted an identity sibling and assistant-derived breed. The run failed atomically; generation remained 1 with no facts. |

These scripted choices establish API, worker, storage and UI behavior only. They
do not measure natural reviewer reliability, useful replies, recall quality or
release qualification.

## Verification And Remaining Gate

The latest repository suite ran with separate disposable test and migration
URLs. It reported 778 passed, one skipped, and the single known failure below.
The separately named M2 Luna database module passed eight tests on its own
disposable URL.
Before this correction, the API runtime PostgreSQL suite passed 341 tests and
web tests passed 78; web lint and production build passed. The follow-up changed
only API source, tests and documentation. Ruff, changed-file formatting and diff
whitespace checks passed again. OpenAPI drift and Compose rendering passed at
the prior checkpoint. Historical fixture and ledger files have no source diff.

The full suite still has one unwaived positive release-policy freshness failure:
`test_selected_candidates_use_current_policy_without_rebinding_history`.
Its selected candidate hashes are historical and differ from current policy.
No rebind or waiver was performed. Checkpoint 5 live diagnostic remains a
separate authorization gate.
