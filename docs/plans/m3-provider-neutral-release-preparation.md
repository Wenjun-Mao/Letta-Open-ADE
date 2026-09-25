# M3 Provider-Neutral Release Preparation

Status: Historical staged preparation; release qualification remains pending.

The selected-route design in [ADR 0027](../adr/0027-provider-neutral-release-and-embedding-space.md)
remains current. The spend-ledger dependency and request-cap execution contract
below are retired by [ADR 0035](../adr/0035-compact-natural-review-and-observational-dispatch.md).
The single Stage A attempt failed ([finding](../findings/stage-a-provider-neutral-preflight-2026-09-23.md));
its unused budget does not authorize another campaign. Consult the
[tracker](../project-tracker.md) for current work rather than executing these old stages.

1. Trace schema-v3 evidence, promotion, native qualification configuration,
   router source resolution, and stored vector lookup. Preserve the historical
   ledger and immutable definitions.
2. Introduce a versioned selected-role evidence contract and conditional
   compatibility validation. Bind the current unqualified DeepSeek + Qwen
   candidate without carrying forward DGX or llama passing evidence.
3. Separate Qwen vector-space identity from endpoint provenance for new
   bindings, with explicit semantic validation and legacy-vector continuity.
   Make the embedding endpoint configurable; require fresh deployment and
   compatibility review for relocation.
4. Add fail-closed tests for stale/missing roles, failed configured
   compatibility, old schema semantics, provider selection, embedding semantic
   mismatch, and preserved legacy vectors. Run proportional Python, web,
   OpenAPI, formatting, and compose checks.
5. Leave generation, qualification, promotion, production deployment, merge,
   and private-data use to the director's separately reviewed next stage.

End state: a clean source checkpoint with exact candidate routes and a bounded
synthetic qualification request budget estimate, not a release claim.

## Stage gates and request caps

The M3 `RequestLedger` and `BudgetedTransport` design now lives in the shared
Agent Runtime transport construction path; the historical M3 host reuses it.
A fresh, ignored SQLite ledger with immutable stage limits must be shared by
the clean API and worker: reserve and commit one slot **before** every
outbound `chat_completion` or `embeddings` request.
That boundary covers conversation continuations, reviewer, compaction,
automatic and tool retrieval, and fact-document embedding; cap exceptions
fail the turn and stop the stage. Record failed/time-out requests as spent.
The standard API/worker builders now use the same configurable ledger path;
Compose mounts the runtime directory into both services. API/worker health
compatibility includes stage and limits, and the full canonical runner fails
preflight without a matching budget and zero requested retries. Tests cover
concurrent cross-process reservations, restart persistence, real builders,
traced call paths, and cap exhaustion with fake providers. A cap only in the
black-box runner would not constrain a worker's internal requests. The
existing M3 host is development-mode and marks its source dirty; it cannot
be used unchanged as a clean qualification or release-mode host. No actual
qualification host or Stage B approval exists yet. Stage A was separately
approved and attempted once with the 32/32 caps; it failed a required-tool
turn after 7 generation and 7 embedding requests. The retained ledger and
failed artifacts are linked in the finding. No reroll or Stage B call followed.
Direct origin/candidate canary requests are outside the canonical runner;
their caller must reserve through the same stage ledger before sending.

| Stage | Exact synthetic work | Proposed hard stage cap | Stop condition |
| --- | --- | --- | --- |
| A — small preflight | One diagnostic round of canonical `correction_chain` and `old_memory_deep_search`: two correction turns, one initial-fact setup turn, one scored tool/retrieval turn; no proposal. | 32 DeepSeek, 32 Qwen requests | Any failed assertion, route/source mismatch, cap hit, or provider failure stops before B. No reroll. |
| B — qualification | Exactly three full, unmodified canonical 10-case rounds on one clean source/build; required conformance and independent review remain separate. If Qwen has relocated, collect paired synthetic query/document canaries from origin and candidate before promoting the space. | 1,464 DeepSeek, 1,281 Qwen at origin; 1,285 Qwen if four relocation canary calls are needed | A failed turn, cap hit, missing receipt, or incomplete round stops; no partial matrix or diagnostic case substitutes for a full round. |
| C — later release-mode acceptance | Only after separate promotion approval: clean release-mode API and worker in a disposable database, an actual synthetic Agent Studio definition/subject/conversation, then `我现在住在北京。` followed by `更正一下，我现在住在多伦多。`; verify completed runs, committed correction lineage, Toronto active, Beijing inactive, and API/worker source identity. | 16 DeepSeek, 16 Qwen requests | Any gate or behavior failure stops without changing production or reusing the stage as a reroll. |

Each stage gets one fixed ledger and one planned attempt; retaining the ledgers
prevents restart from resetting spend. The proposed campaign ceiling is
**1,512 DeepSeek requests and 1,329 Qwen requests at the original endpoint**,
or **1,333 Qwen with relocation canaries**, conditional on all three stages
being separately approved. A stage never borrows unused calls from another.
Zero requested worker retries, zero reviewer repairs, no automatic rerolls or
provider fallback, and 180-second request caps remain mandatory. An exhausted
cap is a failed/incomplete qualification, not authority to raise the cap.

These caps are proposals, not predicted usage. The canonical matrix contains
20 scored turns, one initial-fact setup turn, and 40 real prelude turns per
round: 183 turns across three rounds. Its DeepSeek ceiling follows six
conversation + one reviewer + at most one compaction request per turn
(1,098 + 183 + 183 = 1,464). The 1,281 Qwen planning figure assumes one
search request per conversation continuation (183 automatic queries + at
most 183 fact-write batches + 915 tool searches); a response can contain
multiple tool calls, so **that figure is not an intrinsic runtime upper
bound**. The ledger's 1,281/1,285 limit is the proposed enforceable bound:
if actual tool use exceeds it, stop and request a new decision rather than
weakening cases or silently expanding spend. The director must separately
approve later-stage caps and clean-host invocation before those calls. The
transport's 180-second
limit applies to each request; the worker also supplies its remaining turn
deadline, so continuations do not each receive a fresh 180-second turn.
