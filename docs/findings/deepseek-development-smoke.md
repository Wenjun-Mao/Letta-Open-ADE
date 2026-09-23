# DeepSeek Development Smoke (2026-09-23)

This is a bounded synthetic development check for ADR 0025, not native release
qualification. No private conversation or retained user memory is an input.

## Budget reservation before live generation

| Request group | DeepSeek generation requests reserved | Spark embeddings reserved | Rerolls |
| --- | ---: | ---: | ---: |
| Synthetic dialogue, native tool continuation, typed reviewer, Comment Lab, Label Lab | 8 maximum, counting each tool continuation | 4 maximum | 0 |

Each request has a 180-second cap. Read-only `/models` discovery is outside the
generation/embedding caps. Stop on contract failure. A reservation is not a
claim that calls were spent; the observed counts and outcomes are recorded
below after execution.

## Observed calls

1. Direct official DeepSeek API synthetic arithmetic dialogue: one generation
   request; HTTP 200; response model `deepseek-flash`; final content `4`,
   `finish_reason=stop`; reasoning field present but not displayed; 59 prompt,
   29 completion tokens (27 reasoning), 88 total. No retry or fallback.
2. Native ADE `search_memory` through loopback Model Router: two generation
   requests (initial tool call and continuation), one validated synthetic tool
   event, required-tool condition satisfied, provider reasoning received and
   replayed only in the assistant tool-call message. Final answer identifies
   the synthetic older tea preference as oolong. Combined usage: 1,142 prompt,
   148 completion, 1,290 total tokens. No retry or fallback.
3. Native ADE memory reviewer through loopback Model Router: one generation
   request, no repair. Locally typed and policy-validated `forget` proposal,
   exact synthetic fact ID and expected version 2, JSON null value. Provider
   reasoning was present but not output as a proposal. Usage: 1,510 prompt,
   135 completion, 1,645 total tokens. No retry or fallback.
4. Comment Lab through loopback Model Router: one generation request with
   `json_object`, zero retries; Chinese synthetic community comment accepted
   from assistant content. Provider reasoning was absent from the returned raw
   lab reply. Usage: 134 prompt, 76 completion, 210 total tokens.
5. Label Lab through loopback Model Router: one generation request with
   `json_object`, zero repair; locally validated exact-substring extraction
   returned `Messi`, `Inter Miami`, and `Orlando City` on the primary attempt.
   Provider reasoning was absent from the returned raw lab reply. Usage: 274
   prompt, 77 completion, 351 total tokens.
6. Spark Qwen3-Embedding-0.6B sidecar: one synthetic embedding request; HTTP
   200, one vector, 1,024 dimensions, matching the existing retriever
   fingerprint. The vector values were not printed or retained.
7. Agent Studio development binding on disposable, passwordless loopback
   PostgreSQL `ade_m2_memory_test_01a0ca1b` at migration head
   `20260902_0006`: created synthetic subject
   `26e641e3-16a1-5f57-8eb6-2268c0841865` and conversation
   `521b5875-8420-5223-8f07-8a5563b68f35`. A separate SQL connection read
   back `purpose=agent_studio`, DeepSeek conversation/reviewer route aliases,
   Spark retriever alias, and overall `unqualified` status. Only read-only
   discovery occurred during the bind; no model generation, embedding, memory
   turn, release-ledger write, or promotion occurred. The synthetic database
   rows remain for inspection. This first binding's DeepSeek fingerprint was
   superseded by the subsequently tightened thinking/high lane contract.
8. Repeated only the no-generation binding after that contract change:
   synthetic conversation `79d990f5-6871-59c1-9795-c178e55f5dbb` and
   subject `d3e9cc27-3e40-5623-8a73-55aab4fc2877` were persisted in the
   same disposable database. A separate SQL connection read back
   `purpose=agent_studio`, `unqualified`, and conversation fingerprint
   `d4756a2637ab02aa666b72d46c560d1e827f24ec4dba1f3b1e7a83831555ed86`,
   matching that development manifest at the time. This second binding was
   superseded by the final official-host guard.
9. Final no-generation binding after the official-host guard: synthetic
   conversation `7ee779cc-6eba-5cd5-8cfd-e947b285a654` and subject
   `d04d067f-f146-5c0d-afec-9219cdff2545`. Independent SQL read-back
   confirmed `purpose=agent_studio`, `unqualified`, and conversation
   fingerprint `e0a682a85211679031f1d85f6ec7a630658c2a90bcd73bcd3cf2d1b0c7e4b33a`,
   exactly matching that checked-in unqualified manifest at the time. The
   subsequent caller-override and reviewer-budget correction produced a new
   development fingerprint for the native turn. All three
   synthetic sessions remain available for inspection; no production data was
   touched.
10. After preserving explicit supported caller overrides and naming a zero-repair
    reviewer budget, one synthetic native Agent Studio turn ran through the
    `/api/v3/agent-studio/sessions` and `/api/v3/conversations/{id}/turns` HTTP
    endpoints, one real worker attempt, and the disposable database. A separate
    database connection read back `run_status=succeeded`, one active
    `person.current_location=Toronto` fact at version 1, one memory revision,
    and `memory.committed`/`run.completed` events. Conversation
    `1eab6fbc-dc86-56c9-ad54-228ac48b2ac3`, subject
    `8986c374-8e70-5f0f-ba1e-4a0e94999263`, run
    `c32c2352-cf58-4e5d-8668-97c646f6af2b` remain in the disposable DB.
    The turn reserved and used exactly two DeepSeek generation requests
    (conversation and reviewer) and two Spark embedding requests (retrieval
    query and fact vector). It had zero tools, zero retries, zero reviewer
    repairs, and no compaction. Two preflight harness failures occurred before
    session creation and before any provider call; they corrected source
    provenance setup and Python module loading, then this single authorized
    turn completed. No private history was used.

Final generation count: **8 of 8** (none unspent). Spark embedding count:
**3 of 4** (one unspent). No rerolls. This establishes one synthetic native
development turn, not model quality, private-data approval, or release
qualification.

## Verification and remaining gate

The repository test run excluding only the intentional checked-in-manifest
policy-freshness gate passed: 619 Python tests, 7 skipped. The web suite passed
73 tests; lint, TypeScript/production build, Ruff, formatting, OpenAPI artifact
check, and `git diff --check` passed. The full Python run still fails the
checked-in-manifest policy-freshness test because the pre-existing qualified
deployments retain their older governed hashes. They were not rebound or
promoted; the release ledger remains untouched. This is a release gate, not a
development-lane test failure.

Read-only official DeepSeek `/models` returned
`deepseek-flash` and `deepseek-v4-pro`; only `deepseek-flash` is selectable in
ADE. Read-only Spark `/v1/models` returned `Qwen/Qwen3-Embedding-0.6B`.
