# Second Plan Review: Implementation Readiness

Status: source-checked recommendations, not implementation authorization or a plan
amendment. Reviewed packet: `f786007f7d03b375ed0d9b36bf3c2ae0f9e947b6`.
Unchanged implementation: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.

## Reports And Evidence

- [Plan round 2 A](reports/pro-plan-round2-a.md), attachment
  `6d4a0efb-a2b2-4b7b-b1d9-50d056a39588`.
  SHA-256: `6fd570b5d81c595f88a9a756bbefb1e374bf09134780824316f67ec6d65323cf`.
- [Plan round 2 B](reports/pro-plan-round2-b.md), attachment
  `5f783d99-4530-4d5e-9a40-2b4d802552d3`.
  SHA-256: `48d53d96232353d8426f2c4a42cba8ae35b10df7993e01b10e54f55c372fbf2b`.

Originals are preserved byte-for-byte. Both report static public-GitHub inspection,
not executed tests. Local checks below were source inspection only: no deadlock,
commit-acknowledgment failure, or retrieval fault was reproduced, and no provider or
database calls were made. Reviewer recommendations are not user authorization.

## Verdict

Both reviewers now recommend bounded implementation of checkpoints 1-5, without
another architecture round. The previous paired-evidence, symmetric-usefulness,
failed-diagnostic, cleanup and capability blockers are closed in the specification,
not proven in code. Their new requirements fit the existing affected components.

Recommend folding four engineering checks and one positive-compaction assertion
into the existing checkpoints when implementation is authorized. Do not select A
or B, run checkpoint 6, or treat this review as product/release acceptance.

## Verified Findings And Disposition

Paths below are relative to `services/ade-api/src/ade_api/features/agent_runtime/`.
`Use/Test` means recommend the requirement and its regression, not claim it is fixed.

| Requirement | Source check and limit | Disposition / checkpoint |
| --- | --- | --- |
| Consistent transaction lock order | `run_service.py:accept_turn` locks conversation then subject before checking active runs. `worker_finalization.py:_lock_conversation_and_subject` sorts their IDs, sometimes reversing that order. A cycle is possible; no database reproduction here. | Use/Test, 2-3: establish one order across touched writers/cleanup and a real two-connection admission/finalization regression. |
| Deferral removes dependent staged effects | `memory_policy.py:prepare_memory_review` stages identity entities separately; `memory_commit.py:commit_memory_review` inserts all `new_entities` before fact operations. The future per-claim filter must not leave identities behind. This is an integration risk, not an existing demonstrated deferral bug. | Use/Test, 2-3: finalize the effective write set before embeddings/commit; test mixed and all-deferred cases. |
| An exception does not prove rollback | `worker.py` routes finalization exceptions to `commit_failure`; the latter rereads the run and does not overwrite an already-terminal result. Preserve this protection in new capture/UI paths. | Use/Test, 2-3/5: authoritative committed/rejected/unconfirmed observations; inject failures before commit, after commit, and during artifact retention. |
| Compatible indexes must not consume duplicate result slots | `persistence/metadata.py` allows one embedding per fact/revision/model/policy tuple; `persistence/memory.py:search_active_facts` limits joined embedding rows. Multiple compatible policy versions could duplicate facts if introduced naively. Today's single-policy reader is not shown faulty. | Use/Test, 2/4, conditional on multi-version reads: choose one eligible representation before the distinct-fact limit. |
| Actual compaction must retain useful meaning | `compaction.py:parse_compaction_response` checks schema, nonempty text and size. Checkpoint 6 requires real compaction on two stale-state arcs but does not explicitly require a detail recoverable only from the summary. | Use/Test, 1/4/6: add a positive retention assertion inside an existing compaction arc. |

### Transaction And Effective-Write Details

The lock-order fix needs an audit of the full touched transaction order, including
run/lease and other row locks, not just a local swap of two calls. Reproduce the
subject-ID-before-conversation-ID case with coordinated independent connections.
Keep locks outside provider computation; do not mask database deadlocks with extra
model attempts. This complements the single generation fence rather than replacing it.

After permitted deferrals/no-save exclusions, retain only entities justified by
surviving operations. An empty effective memory write set means no entities, facts,
indexes or generation advance. A mixed deferred-pet/valid-residence case must still
commit the valid residence without the pet identity. Generate and align embeddings
against final effective operations. Invalid proposals or contradictions must retain
their specified failure behavior, not be silently filtered as optional claims.

### Outcome Recovery And Retrieval Details

Distinguish confirmed rejection, confirmed commit, and an outcome not yet confirmed.
An artifact-write failure cannot undo a database commit; it makes evidence incomplete.
Read the authoritative run/action receipt or recover using the same idempotency key.
Never automatically use a fresh key, generation or target set. Unconfirmed is an
observation status, not a new memory lifecycle value or distributed transaction.
If outcome/evidence remains unresolved, the cell is unscorable and follows the
existing infrastructure-stop rule; do not label a committed reply uncommitted.

If compatible-version reads are chosen, test F1 indexed twice, F2 once, a terminal
descriptor and a forgotten chain. Assert distinct eligible fact coverage before
the result limit. No additional ranking service or mandatory multi-version feature
is implied; a simpler compatible format/read policy may avoid overlap entirely.

### Positive Compaction And Pressure Semantics

Within an already-required actual-compaction arc, predeclare one useful detail,
such as which interview opening the user chose. Keep its source outside the admitted
raw suffix and its answer absent from facts, the new question and other model input.
Require the real generated summary to preserve the meaning, that exact summary to
reach A, and the downstream reply to use it appropriately. No exact-wording gate or
extra evaluator is needed. A vague but harmless summary must not pass this requirement.

This is a component-specific gate for summary-enabled A. A0 may correctly abstain
without the summary; B must not acquire a hidden older-history requirement. Retain
the symmetric common product envelope separately. Reused evidence remains one actual
attempt supporting multiple proven-equivalent cells, never independent replication.

The mandatory pressure point can disqualify A structurally: if A withholds the only
permitted antecedent, it cannot correctly resolve it by guessing. That is valid when
the load/continuity requirement is genuine and frozen in advance; it is not broad
empirical proof that selective retrieval is better, nor evidence that B passes.
In checkpoint 1, distinguish a comparison cell's mechanically correct no-write
(which may fail product usefulness) from a required-mutation cell's incorrect state
(which stops the campaign). Freeze that classification before responses.

Avoid spending live requests solely to rediscover an offline capacity consequence.
Any planned offline screen or reduced live schedule must be explicit in the frozen
matrix before approval, without weakening required coverage or counting skipped
calls as executed evidence. The proposed 96/160 request ceilings remain unapproved
and unchanged; completion within them is not yet established.

## Next Step And Boundaries

Recommend user authorization for checkpoints 1-5 with these focused completion
requirements recorded in the existing plan, starting with fixture/contract tests.
No new framework, alternate plan, pending-claim store, semantic lock system, or broad
external review is needed on the evidence available. Park those expansions.

Provider accuracy, useful recall, false-veto frequency, actual compression quality,
cost and policy selection remain empirical. Checkpoint 6 requires separate approval
of the frozen matrix and live budget; deployment/promotion remain separate again.
The design and plan are unchanged in this assessment checkpoint. No runtime changes,
tests, provider calls, commit, push, merge or release promotion occurred.
