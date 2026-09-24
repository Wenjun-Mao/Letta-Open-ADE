# Third Pro Review: Planning-Readiness Assessment

Status: recommendations for discussion, not a design amendment, accepted ADR,
implementation plan, or authority to run experiments.
Reviewed design: `c01f45a045eb0fdd0fc6b3e18add82f2dbb57024`.
Unchanged implementation: `4905ce15dbda6466b12f2d1ed7908eb3d03995a0`.

## Reports And Evidence

- [Round 3 A](reports/pro-round3-a.md), attachment
  `0220959c-b8d2-4978-ab7a-fbf8f475e961`.
  SHA-256: `994ab40ac70c56b790b1df39fd9be332d8a67592d4086bec2534647c03e8a88c`.
- [Round 3 B](reports/pro-round3-b.md), attachment
  `47408a4b-4d5a-4cdf-8acb-2d23228642b3`.
  SHA-256: `2e5bc37c6c160334e0ee21deab2ea261b7a9403dbd4b2a83ed6a58acf1e19250`.

Both report static inspection of the same pinned documents/source, not execution
or live validation. Originals are preserved unchanged. This assessment checks
the consequential claims against local design/source; no model, database, or
runtime tests were run. Neither reviewer agreement nor this review is release evidence.

## Verdict

Both reviewers support bounded implementation planning and retaining the foundation.
Their findings are complementary: A emphasizes same-turn no-save precedence and
reply/write consistency; B identifies selective recall of terminal lifecycle state.
Both warn that the full-snapshot prerequisite can undermine immediate conversation.

Keep one lifecycle view, one subject-memory generation, one shared clarification
bundle, and one atomic mutation boundary. Close the narrow contract gaps before
freezing affected implementation work. Do not restart framework research or adopt
another storage layer. Revision 3 is a coherent basis, not an unchanged production
context policy that has earned acceptance.

## Verified Findings And Disposition

`Use` means recommend a contract clarification, not silently adopt it.

| Finding | Local check and evidence limit | Disposition |
| --- | --- | --- |
| Same-turn removal/no-save must dominate saving the same assertion | `memory_policy.py:83-134` tracks forgotten normalized keys; the named regression at `test_memory_policy.py:228` covers forget-then-add. Independent preference IDs make intent-level matching broader than key equality. No new runtime failure reproduced. | Use: assertion-scoped no-save eligibility, independent of proposal order; unrelated writes remain eligible. |
| Atomic reply and memory can disagree semantically | Design section 5 addresses a reply seeking clarification, not an explicit contrary interpretation. `worker_finalization.py:64-90` commits prepared writes and assistant text but does not establish semantic agreement. | Use: detected explicit contradiction fails the atomic attempt; unresolved reference defers only its dependent write. |
| Selective recall is active-only despite new inactive views | Section 8 explicitly says active-fact fallback. `persistence/memory.py:386-426` requires active status and an embedding of the current revision. | Use: current lifecycle selection may return active or inactive descriptors, never forgotten chains or arbitrary revisions. |
| Unrelated memory pressure can remove the immediately preceding exchange | Section 8 requires the complete lifecycle snapshot before any prior narrative, including clarification. The capacity threshold follows from the proposed rule; its real frequency is unmeasured. | Use/Test: provisional bounded control, not permanent production necessity; compare a genuinely different recent-dialogue-first candidate. |
| No-summary alone does not isolate that admission rule | Removing a summary while retaining the prerequisite still discards the tiny interview/dog exchange when guards cannot fit. | Use: distinguish summary ablation from admission-policy comparison. |
| Full-snapshot retrieval can duplicate already supplied evidence | `turn_execution.py:182-204` embeds/searches before context construction unconditionally. The proposed complete packet already contains all eligible current facts from its snapshot. | Use: skip redundant automatic retrieval in that mode; retain selection/search where it adds evidence and separate required-tool conformance. |
| Optional compaction can become a needless failure dependency | `turn_execution.py:162-179` compacts before final context construction. A summary later withheld by admission cannot help that response. | Use: determine eligibility before optional compaction solely for that response; do not claim this removes all legitimate compaction work. |
| Reviewer must reserve for the not-yet-generated reply | Section 5 selects a shared bundle before generating its candidate reply. `reviewer.py:198-249` has no candidate-reply input today. | Use: reserve the permitted reply allowance in reviewer input budgeting; never trim one stage's evidence or clip a contradictory clause to fit. |
| Acceptance-time conflicts affect queued no-op turns too | `run_service.py:76-89,122-136` replays existing runs and excludes concurrent active turns per conversation, not per subject. The proposed fence can fail a different conversation before classifying its writes. | Use: terminal conflict, same-key historical outcome, explicit fresh resubmission; Test queued/in-flight/no-op outcomes separately. |
| End, forget, and old-history admission compose surprisingly | Excluding the ending descriptor is required by Option A, while old messages remain. Removal may also shrink guards enough to readmit a previously withheld summary. | Test: end -> forget -> resume old conversation; do not secretly retain a forgotten guard or promise global nonuse. |
| Replayed removal success is not current absence | Design section 6 returns the original action result. Later restatement may create a different record. | Use: distinguish action receipt from fresh current-state readback in API/UI wording. |
| Endorsement and clarification require claim-level semantics | The proposal allows explicit assent but rejects generic multi-claim acknowledgment; shared messages do not prove complete discourse framing. | Test: explicit partial yes/no, missing roleplay framing, unrelated follow-up questions, direct statements needing no confirmation, and mixed independent writes. |

The [source map](source-map.md) supplies pinned implementation links. The claims
above were checked by inspection, not by rerunning the named tests. New lifecycle,
generation, and shared-bundle behavior is still proposed.

## Recommended Contract Closure

### Saving, Removal, And Reply Agreement

"I still like morning coffee, but remove that saved preference" must not forget
one ID then save a new equivalent assertion. "Yes, Roxy is a Husky, but don't save
that" authorizes conversation understanding, not a durable write. Apply this rule
to the same assertion regardless of operation order, including identification and
endorsement clauses; keep unrelated additions eligible. Do not turn it into a
whole-message forget-only mode or lasting suppression. A later fresh assertion
can still be stored under Option A. A no-new-save instruction alone need not imply
deletion of a pre-existing record unless the removal intent is clear.

The existing reviewer can classify a detected conflict without an extra judge:
"Rocky is the Husky" in the candidate reply versus a Roxy breed write cannot
commit as success. Unresolved breed reference defers that write, not an independent
Toronto move; "How old is she?" is not a breed-uncertainty veto. Detection is fallible:
test both missed contradictions and false vetoes. Deferral is an observable no-write
on this turn, not a pending job or silent later catch-up.

### Selective Reads And Context Admission

Ended/invalidated state is current lifecycle information, not generic historical
search. A relevant descriptor can answer "did I report that relationship ended?"
without asserting no partner or replaying arbitrary prior values. Preserve source
attribution: a fact shared from another character is not evidence that the user
told this character. Do not merely remove the SQL active filter: terminal revisions
need an eligible current descriptor/index representation, with revision, subject,
and embedding-space checks retained. That detail belongs in the bounded plan.

The full-packet rule was our conservative response to the summary-freshness flaw.
Its downside is real at the contract level: unrelated memory can make ADE unable
to follow its own last question. Recommend keeping it only as a provisional,
small-memory control with a measured operating envelope, not a universal truth rule.

The plan should compare it against a recent-dialogue-first candidate at equal total
budgets, using selected active and terminal evidence. The candidate must reserve
the shared local exchange and explicitly define what it omits; it is not yet a
chosen or equally safe replacement. Test stale breakup/correction narratives as
well as unrelated-memory pressure. Keep complete reviewer target visibility unless
that separate write-side contract is explicitly changed. Generation improvement
alone does not solve full-reviewer capacity. No summary-dependency graph is proposed.

Count useful answerability, false current-state claims, unnecessary clarification,
withholding, capacity failures, cost, and latency separately. Safety through always
abstaining is not success. Set measurable bounds and acceptance criteria in the
plan before execution; do not retrospectively choose thresholds to favor a candidate.

### Operational Clarifications

Memory-generation conflict should be terminal for the accepted run: no spending
retry allowance against an immutable stale generation and no automatic clone with
a new key. Same-key replay returns the recorded result; a deliberate new submission
is different authority, especially after removal. Preserve accepted message/failure
evidence and the existing distinction between no writes and committed writes.

Reserve candidate-reply input space before bundle selection and validate final
requests as a backstop. Skip duplicate automatic query embeddings when a complete
bound snapshot already supplies the records. This does not waive embeddings for
actual writes/selective retrieval, provider qualification, or explicit tool tests.

## Next Step And Boundaries

Recommend one bounded contract amendment followed by implementation planning,
not another broad architecture investigation. User approval is still needed to
advance that phase. The read-admission comparison is a validation decision inside
that plan, not permission to run models now or a claim that either candidate won.

Park continuity tables, generic history repair/search, stronger forgetting,
background review, graphs, new frameworks, and fine-grained concurrency read sets.
No runtime/design amendment, accepted ADR, provider calls, commit, push, merge,
or release promotion occurred in this assessment checkpoint. Stage B/C remain blocked.
