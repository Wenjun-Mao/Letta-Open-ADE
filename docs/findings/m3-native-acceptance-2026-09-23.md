# M3 Native Profile-Memory and Real-UI Acceptance (2026-09-23)

Status: partial behavioral acceptance; **not** M3 completion or release
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
remain intact; neither failed request was rerolled after the fix. Thus provider
compliance with the new wording is still **unobserved**, and M3 native
behavioral acceptance remains partial. No concern, promise, relationship, or
shared-experience schema is inferred from these samples.

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
exact release route is a clean reviewed revision, deliberate policy rebind
that invalidates old qualification, matching API/worker clean build,
deterministic conformance receipt, **three clean full primary DGX matrices**
plus llama-server compatibility from the canonical acceptance workflow,
provider/route consistency, independent reviewer approval, explicit promotion
proposal application, and final release gate. The opt-in M3 diagnostic or
single-case run cannot create a promotion proposal. None of those new
qualification rounds, promotion, or deployment actions were authorized or
performed here. Existing qualified deployments and release ledger were not
altered. The release gate's clean-tree/source-lineage and governed fingerprint
requirements will remain unsatisfied by historical evidence until that fresh
route is executed and reviewed.
