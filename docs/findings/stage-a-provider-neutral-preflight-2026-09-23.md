# Stage A Provider-Neutral Preflight — One Attempt

Status: **failed diagnostic; Stage B is blocked.** This is not release
qualification or a promotion proposal. No reroll was made.

## Bound attempt

- Run ID: `agent-runtime-20260923t173320z-2877d4ea`.
- Clean source revision: `f87838f02743a5202af4df3fc167b933035edda5`;
  governed source fingerprint:
  `5abb74c3fd1dd926bef724b5c00e88920e7d867d4ef9b673a9188c45efa90e5a`.
  API and worker health matched this identity with `source_dirty=false`.
- Isolated Compose project: `ade-stage-a-01a0ca1b`, with a worktree-local
  disposable PostgreSQL directory and shared runtime-data mount. The main
  checkout's running stack was not restarted or modified.
- Router catalog identified `deepseek::deepseek-flash` at the official
  `https://api.deepseek.com` route and
  `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B` at the existing Spark
  `http://dgx-spark:8001/v1` route. The main checkout's `.env` selected a
  missing `sources.local.json` in this worktree; before any provider call, an
  ignored, isolated Compose override selected the checked-in `sources.json`.
  The router then reported both selected sources healthy. No source code or
  manifest binding was changed for this attempt.
- One diagnostic round selected the canonical `correction_chain` and
  `old_memory_deep_search` cases. It used zero requested retries, zero
  reviewer repairs, no compatibility round, and no fallback.
- The retained SQLite ledger
  `data/runtime/stage-a-preflight-f87838f-20260923.sqlite3` binds this source,
  `development` mode, `preflight` stage, and immutable caps of 32 generation
  and 32 embedding reservations. API and worker used the same file. It records
  **7 DeepSeek generation and 7 Qwen embedding requests**, all with completed
  transport outcomes. No reservation was left pending or failed; the unused
  balance is not authorization for a second attempt.

## Turn-level result

| Synthetic turn | Outcome | Evidence |
| --- | --- | --- |
| `correction_chain` — Beijing | Succeeded; reviewer committed `person.current_location` fact version 1 (`add`). | Run `316e8ced-ee03-4cac-b7cc-5834b2132015`; events 10–13. |
| `correction_chain` — Toronto correction | Succeeded; same fact ID reached version 2 (`correct`). Final active fact projection contained Toronto and not Beijing. | Run `83c87c97-d279-44a9-b097-2d3c4e87c629`; events 10–13 and round fact observation. |
| `old_memory_deep_search` — 13-fact setup | Succeeded; reviewer committed all 13 synthetic facts in the auxiliary no-tool session. | Run `b6cd1344-83e2-4a21-953c-c9378e54c035`; events 10–37. |
| `old_memory_deep_search` — scored museum query | **Failed.** Runtime resolved an explicit `search_memory` requirement, but the DeepSeek conversation response ended with `finish_reason=stop`, `tool_call_count=0`, and `tool_calls_state=missing_or_null`. Runtime emitted `conversation_required_tool_missing` and failed the run. No `search_memory` execution or tool-result retrieval occurred; the assistant did not provide the museum answer. | Run `aa44465b-adc1-447d-a5cf-518dc6bfe096`; events 9–14. |

The scored query did issue one automatic Qwen `retrieval_query` embedding
request. That is **not** evidence of an explicit `search_memory` tool call or
successful deep retrieval. The observed root cause is the missing required
tool call in the provider response, correctly rejected at the runtime
contract boundary. The trace does not establish *why* the model omitted it;
that requires a separately authorized diagnosis before changing prompts,
tool wiring, provider behavior, or another live attempt. The runner retained
failed evidence and did not start Stage B or Stage C.

## Retained evidence and limits

The ignored run directory is
`workflows/evals/agent_runtime_acceptance/outputs/agent-runtime-20260923t173320z-2877d4ea/`:

- `preflight.json`: matching API/worker health and budget preflight passed.
- `diagnostic-round-001/round.json`: case scores, turn outcomes, typed facts,
  and deployment snapshots.
- `diagnostic-round-001/events.jsonl`: ordered model, memory, tool-requirement,
  and terminal events; SHA-256
  `fcac3a3a24e6b20daa30a2f169dc07d0bddc7d7daa37513f6cf31b6f5d1ef6dc`.
- `provenance.json`: clean source/config and artifact linkage.

The workflow purged its synthetic evaluation sessions after artifact capture;
three sampled session-state reads returned HTTP 404. The ignored ledger,
artifacts, Compose override, and disposable database remain for independent
review. Stage A passing status is not claimed, and the unqualified candidate
and historical release ledger remain unchanged.
