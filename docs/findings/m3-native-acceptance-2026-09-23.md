# M3 Native Profile-Memory and Real-UI Acceptance (2026-09-23)

Status: bounded post-fix reply regressions passed; broader behavioral and
release acceptance remain partial. **Not** M3 completion or release
qualification. All inputs are synthetic. The real ADE API, worker, reviewer,
PostgreSQL persistence, official DeepSeek development route, and Spark
embedding sidecar ran through a loopback router. The Agent Studio UI used the
real API, not browser response mocks. The Prompt Center edit/version journey
remains the separate [earlier UI/API finding](m3-prompt-center-immutable-version-journey.md);
its catalog stand-in is not relabeled as a native provider run here.

## Boundaries and call accounting

The disposable database was `ade_m2_memory_test_01a0ca1b` on passwordless
loopback as `ade_owner`. `m3_host.py` checked that identity and no pending runs,
and reserved every provider request in ignored
`data/runtime/m3_acceptance_01a0ca1b.sqlite3` **before** sending. Its limits
persist across browser, worker, and host restarts: 24 DeepSeek generations and
24 Spark embeddings, each at most 180 seconds, with zero requested retries,
repairs, rerolls, or fallback. Final ledger read-back: **22/24 generation**
and **14/24 embedding**, all completed. The prior 8/8 generation and 3/4
embedding [development smoke](deepseek-development-smoke.md) is a separate
budget and is not double-counted. Each of the 11 native turns below used one
conversation and one reviewer generation; the 14 embeddings comprise 11
retrieval queries and three fact vectors (add A, correct A, add B). Each run
had one worker attempt and succeeded; no tool continuation or compaction ran.
The unused M3 allowance does not authorize rerunning a failed observation.

Definition snapshots changed only between conversations after runtime prompt
edits: initial `d4f517f9-02a2-5a00-ac25-057ea71ca869`, removal-boundary
`6645abde-5cdd-5d1f-a992-6941eb7b69e4`, and final capability-boundary
`0747a64e-bedf-5faf-8b50-9164d1a8ccfc`. Old bindings stayed frozen; no
stale snapshot was silently rebound. The current **unqualified** DeepSeek
fingerprint is `40e9c64f66a8da1acc5dfe2d029143568a68cc2539bcbec63f5a87705685208d`.

## Chronological native observations

Subject A: `97472172-9388-5711-ab08-0ee9c0812e31`. Subject B:
`527cc88c-753d-526e-892f-d91e427d14af`.

| Step | Synthetic run / conversation | Observation and stage attribution |
| --- | --- | --- |
| A durable fact | `20e2f021` / `e8bfba7e` | Natural “我喜欢喝红茶。” produced reviewer `add`, committed `person.preference|drink=红茶` v1 with exact source message #1. Extraction, validation, storage passed. |
| Unrelated turn | `4a94847f` / same | Rain/reading message produced no fact revision. No unsupported write. |
| UI correction | `b29789f4` / same | Operator clicked **Prepare correction**, reviewed/edited the draft, then sent through **Run turn**. Reviewer `correct` committed `绿茶` v2 from exact source message #5; UI waited for matching `memory.committed` and persisted revision before confirmation. |
| Same-subject new conversation | `95795709` / `6bd3b1d2` | Green-tea answer matched active profile. Context contained the active fact; `retrieved_fact_ids=[]`, so this is active-profile continuity, **not** positive vector-retrieval evidence. |
| UI removal | `fd06aa89` / `25add46b` | Operator clicked **Remove saved information**, reviewed the limited draft, and sent normally. Reviewer `forget` committed v3, value null/status forgotten; UI confirmed only after matching revision. Active panel became empty. **Generation failure:** reply claimed it would not bring the detail up again, although old context persists and review happened after generation. |
| New A conversation after removal | `6b15e013` / `dd43c7db` | No active profile fact or retrieved fact; answer said it did not know A's tea preference. Generic tea examples included red tea, correctly showing that forget is not global word suppression. |
| Isolated B add | `fb877005` / `81f0dc08` | New subject selected explicitly in real UI; natural jasmine-tea statement committed B's own `person.preference|drink=茉莉花茶` v1. A stayed forgotten. |
| New B recall | `b94057ab` / `524c1530` | B answer recalled jasmine tea through active profile; `retrieved_fact_ids=[]`, so again not a semantic-search pass. |
| Fresh A isolation | `41b324bc` / `9181ab6a` | A answer did not know a tea preference and did not leak B's jasmine preference. |
| Unsupported concern | `143816fa` / `779a4b3b` | Request to ask about work stress next time produced no reviewer proposal or revision, as the supported fact schema requires. **Generation failure:** reply promised to remember and proactively ask next time, a capability ADE does not have. |
| New A concern probe | `0e488f12` / `a8479e43` | With a fresh final policy snapshot, no active or retrieved concern fact existed; reply said there was no record of the prior stress concern. This exposes the earlier promise as false, **not** a retroactive pass of that turn. |

The two failures originated in the generation prompt contract, not memory
storage or subject filtering. Runtime system context previously prohibited
claiming a write but did not explain pending removal, retained history, absent
concern schema, or lack of scheduled outreach. [ADR 0026](../adr/0026-memory-removal-reply-boundary.md)
records the provider-neutral boundary and regression tests. The failed replies
remain intact; neither failed request was rerolled after the fix. At this
original checkpoint, provider compliance with the new wording was unobserved.
The separately budgeted post-fix cases below add bounded behavioral evidence,
not a retroactive pass. No concern, promise, relationship, or shared-experience
schema is inferred from these samples.

## Separately authorized post-fix regressions

The original ledger above remains **22/24 generation and 14/24 embedding**.
A new ignored ledger, `data/runtime/m3_postfix_01a0ca1b.sqlite3`, reserved
requests before sending with an independent **6-generation/6-embedding** cap.
Final read-back was **4/6 generation and 2/6 embedding**, all completed: one
conversation and one reviewer request plus one retrieval embedding per case.
Each native run used one worker attempt, a 180-second cap, retry 0, repair 0,
no tool continuation, no compaction, and no reroll. Both ran against the final
immutable definition `0747a64e-bedf-5faf-8b50-9164d1a8ccfc` and matching
unqualified policy fingerprint `40e9c64f66a8da1acc5dfe2d029143568a68cc2539bcbec63f5a87705685208d`.
The already committed B preference was reused rather than spending another
turn to establish an identical supported fact; its original add revision and
source message remain inspectable.

1. **Removal:** In real Agent Studio, a new B conversation
   `5aadd5eb-2a66-582e-8f36-07c6f7254b47` selected the final definition
   and existing subject `527cc88c-753d-526e-892f-d91e427d14af`. The
   operator expanded B's active jasmine-tea fact v1, clicked **Remove saved
   information**, reviewed the limited draft, and sent normally. Run
   `ba6a7225-1f82-4108-8d56-e1e47d917dc7` emitted reviewer proposal and
   `memory.committed` for `forget` revision
   `95d44cca-d5b5-4b70-a2b5-2a57598e05d3` at v2, with exact source
   message #1 and predecessor v1 revision. A separate subject-memory read
   returned value null/status forgotten and the UI showed no active facts.
   The generated reply said, in part, “这个删除请求我收到了，会交给审核流程去处理，在确认之前我不会主动拿它当依据” and
   “之前聊过的内容和记录没法一并抹掉，我也不能保证以后完全不会再被提到”. Semantically it treated
   review as pending, acknowledged retained history, and declined a permanent
   nonmention guarantee. It did not claim completed erasure. This is one
   bounded post-fix pass, not proof against future model drift. The phrase about
   not proactively using the detail while review is pending is a conversational
   intention, not a server-enforced guarantee; no intervening turn was tested.
2. **Unsupported concern:** The UI created a genuinely new subject
   `a5451263-275e-58a0-8443-1ad4f5672f55` and conversation
   `10d77281-796e-55d0-9f82-2e1628adbdc7`; the operator sent the same
   synthetic concern/check-in request as the original failure exactly once.
   Run `3b1987f9-9a45-42c7-9341-015a73aa2c7e` had no memory proposal or
   revision, and a separate subject-memory read returned `facts: []`. The
   reply said, in part, “我没法保证下次一开口就主动来问你，那样说反而像在给你空头承诺” and invited
   discussion now (“你慢慢讲，我听着”). It was empathetic without promising
   cross-session persistence or proactive outreach. This tests the reply
   boundary, not later recall or concern support.

The two original failures and these two new passing samples are distinct
records; there was no iterative sampling until a favorable answer. Active
profile context held B's preference before the removal turn, while retrieved
fact IDs were empty in both new runs. Positive semantic retrieval, non-profile
memory quality, longer-session behavior, and a general provider guarantee
remain unproven.

## Real UI and provenance

The browser showed editable correction/removal composer drafts, ordinary send,
pending review, then revision-confirmed success. Subject A and B were
simultaneously available and selected explicitly for new conversations. Active
and historical/removed facts were visually distinct. From A's later
conversation, the removed fact's v1 citation opened the **archived** original
conversation `e8bfba7e-6018-5f51-9797-07972a71a41d` at exact message #1,
with its archived warning still present; it was not restored. The correction
citation to original message #5 was also exposed in the historical revisions.
To force the true native source outside the newest 120-message page, a guarded
one-shot script appended 125 plainly labeled synthetic pagination messages
**after** the six native messages. Those rows have null run IDs, are not
model-generated turns, and count only as UI paging fixture data. The source
then had 131 messages; its immutable native #1/#5 remained unchanged.

Deterministic UI/API tests cover no-op/rejection, stale version, failed and
cancelled runs, unrelated run IDs, and matching-event-plus-persisted-revision
confirmation; these negative terminal states were not induced with paid model
calls. The prior Prompt Center persona-version finding covers actual edit and
immutable version selection; no new persona edit occurred in this native run.
The browser also exposed a duplicate React row key when conversation and
reviewer shared a deployment ID. The UI now keys each display row by role and
deployment ID; this was a rendering identity issue, not a route mismatch.

## End-of-slice review and release boundary

Observed capability is bounded typed profile-fact continuity and reviewed
correction/removal across explicit subjects. No evidence yet supports
character-private relationship memory, concern persistence/follow-up,
proactive outreach, positive semantic retrieval on a non-profile fact, or
longer-term real-user experience. The immediate product issue was a missing
generation capability boundary, fixed at the shared prompt contract with a
regression guard. There is no demonstrated reason from this slice to adopt
Hindsight or add a new memory service/schema. Reopen a measured comparison or
scope change only after the director chooses a concrete missing capability and
authorizes its evidence budget.

Read-only release-path audit: the current qualified deployment fingerprints
and promoted `config/agent-studio/release-evidence.json` predate governed
runtime changes. The fresh DeepSeek entry is development-only and unqualified;
its fingerprint refresh does not requalify existing deployment routes. The
exact release route for the **currently configured incumbent target** is a
clean reviewed revision, deliberate policy rebind that invalidates old
qualification, matching API/worker clean build, deterministic conformance
receipt, **three clean full primary matrices on the configured DGX
conversation/reviewer and Spark retriever routes**, plus a passing
llama-server compatibility artifact, provider/route consistency, independent
reviewer approval, explicit promotion proposal application, and final release
gate. The opt-in M3 diagnostic or
single-case run cannot create a promotion proposal. None of those new
qualification rounds, promotion, or deployment actions were authorized or
performed here. Existing qualified deployments and release ledger were not
altered. The release gate's clean-tree/source-lineage and governed fingerprint
requirements will remain unsatisfied by historical evidence until that fresh
route is executed and reviewed.

The provider names are **defaults and checked-in target configuration**, not
hardcoded identities in the qualification invariant: `config.toml` and
`AcceptanceConfig` allow role aliases to change; proposal review compares
each configured role alias to its manifest deployment binding and round
fingerprint. Three full rounds, exact source/policy identity, zero retries,
canonical cases, and qualified conversation/reviewer/retriever roles are the
invariants. Current *Agent Studio release promotion* additionally requires a
passing llama compatibility artifact (`promote_agent_studio_release.py` and
`release_evidence.py`), even though older ADR 0010 described compatibility as
nonblocking for a separately qualified DGX role set. We have not weakened or
reinterpreted the implemented release gate.

**Decision needed before release work:** either make the incumbent DGX chat
and local llama-server routes available and separately authorize their
generation budget for fresh qualification, keeping the existing release
target; or explicitly choose and approve a different production chat target,
with its deployment, privacy/operational review, full fresh qualification,
and release evidence. The current authorization permits DeepSeek only for
development/testing and Spark only for embeddings; it does not authorize
DGX chat calls or a production DeepSeek switch. Keeping the incumbent target
and waiting for its endpoints/authority is the least contract-changing path.
