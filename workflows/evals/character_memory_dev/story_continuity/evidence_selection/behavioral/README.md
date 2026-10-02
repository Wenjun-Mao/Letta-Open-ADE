# Bounded D04 Behavioral Comparison

Status: Offline construction, scripted verification and independent manager readiness
review complete. No provider requests, live discovery, credentials, services or
databases were accessed. [Protocol](PROTOCOL.md) is prospective; provider outcomes
remain unrun. [ADR 0059](../../../../../../docs/adr/0059-bounded-d04-behavioral-comparison.md)
owns the narrow exception. This is not a selector or runtime retrieval change.

## Offline Preparation And Verification

Run from repository root, using the locked workspace:

```sh
PYTHONPATH=. uv run --locked python services/ade-api/tests/agent_runtime/story_behavioral_comparison.py
uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_behavioral_comparison.py workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/tests -q
uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_offline_capacity.py services/ade-api/tests/agent_runtime/test_story_correction_comparison.py services/ade-api/tests/agent_runtime/test_story_packet_comparison.py -q
```

The preparer alone imports runtime-owned packet mechanics. It freezes exactly
three independent request pairs and full-reserve reviewer requests in
[requests.json](requests.json), with source/order/hash/capacity receipts in
[preparation.json](preparation.json). Old builders and artifacts are unchanged.
Generation explicitly pins formerly omitted enabled/high thinking fields; the
generation input estimate includes those new bytes. The reviewer format and H are
unchanged. Reconstruct only before manager review; later drift fails closed.

| Arm | Generation estimate | Reviewer with full candidate reserve |
| --- | ---: | ---: |
| Literal-four | 1669 | 9200 |
| Repaired-four | 1680 | 9211 |
| Whole-pool | 2424 | 9993 |

These complete serialized byte/4 estimates fit 11213/11469. They do not measure
provider tokens or actual responses. Thinking pinning adds 14 estimated generation
tokens over the historical shape. Both calls retain their own 4096 output reserves.

Offline evidence at corrected readiness: 70 focused tests passed, plus 54 unchanged
historical packet/capacity tests (124 combined). The broader runtime/history suites
passed 586 tests with three expected skips for unavailable ignored H2/H4 evidence.
One existing Starlette/httpx deprecation
warning remains. Repository Ruff lint, changed-Python format, authored whitespace
and 50 local documentation links/anchors passed; the continuity plan remains 499
lines. Manager review reproduced all 124 focused/historical checks and separately
ran the complete runtime/router plus behavioral suites: 535 passed, 76 skipped
(database/private-evidence prerequisites unavailable), with the same warning.
Manager Ruff lint and changed-Python formatting also passed. No provider/database,
frontend, deployment or native verification was run.

## Later Launch — Manager Continuation Required

1. Review the diff, prospective rubric and scripted evidence. Commit the exact
   protocol/request freeze before provider outcomes; working tree must be clean.
2. Choose an unused loopback port and obtain credentials through the operator's
   existing secret process. Do not print credentials or reuse retained services.
   Verify effective settings locally without dumping secrets; repository `.env`
   and machine secret resolution can override expectations. Start a **new** router
   from that exact commit with only [router-sources.json](router-sources.json),
   reviewed profiles/manifest and 180-second upstream timeout. Example environment
   and process shape (not executed during readiness):

```sh
MODEL_ROUTER_SOURCES='[]' \
MODEL_ROUTER_SOURCES_FILE=workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/router-sources.json \
MODEL_ROUTER_MODEL_PROFILES_FILE=config/model-router/model-profiles.json \
MODEL_ROUTER_DEPLOYMENT_MANIFEST_FILE=config/model-router/deployment-manifest.json \
MODEL_ROUTER_REQUEST_TIMEOUT_SECONDS=180 \
MODEL_ROUTER_API_KEY_SECRET='' \
MODEL_ROUTER_API_KEY="$D04_ROUTER_TOKEN" \
uv run --locked uvicorn model_router.app:app --host 127.0.0.1 --port "$D04_ROUTER_PORT"
```

3. Startup discovery itself reaches the configured provider; only do this after
   continuation. Fresh authenticated catalog/credential preflight must show the
   exact canonical route/provider ID, `deepseek_openai`, official base URL, healthy
   source and enabled/high applied profile. The runner requests refresh and captures
   the complete catalog privately. A mismatch stops; no route/model substitution.
   Historical deployment qualification is not reused as this experiment's evidence.
4. Save a private configuration attestation under the ignored outputs directory,
   containing exactly `source_head` (current clean commit), `isolated_loopback:true`,
   `router_request_timeout_seconds:180`, `transport_retries:0`, and
   `configuration_sha256` copied from preparation. Verify those hashes against the
   actual process files. This attestation is operator evidence: the public catalog
   cannot prove a process's environment or timeout. No token or endpoint secret
   belongs in this JSON. Then execute once:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity.evidence_selection.behavioral.runner \
workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/outputs/d04-comparison \
--router-url "http://127.0.0.1:$D04_ROUTER_PORT" \
--configuration workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/outputs/configuration.json
```

5. Preserve the fixed launch directory. Its intents consume attempts; never remove,
   overwrite or resend. Fully captured prefix resume may run the same command;
   interrupted/transport/auth/routing/preflight stops refuse. Complete unusable
   output continues only the remaining predeclared arms and skips dependent review.
   `status(directory)` in [evidence.py](evidence.py) reports each stage as captured,
   unusable, skipped, stopped, uncertain-consumed or unrun. Private `stop.json`
   explains a capacity/catalog stop. It never changes request limits.
6. Audit captured reviewer JSON offline with the existing runtime schema/binder,
   even if a later attempt stopped or became uncertain. Audit validates the observed
   prefix and rejects tampering/non-prefix/post-stop artifacts. Its result separates
   `assessments`, per-stage `stages`, `execution_state` and any global `stop`. Earlier
   captured evidence remains auditable; execution still refuses to resume:

```sh
PYTHONPATH=. uv run --locked python services/ade-api/tests/agent_runtime/story_behavioral_comparison.py \
workflows/evals/character_memory_dev/story_continuity/evidence_selection/behavioral/outputs/d04-comparison
```

7. Assess visible answers manually using the frozen source-quoted rubric, naming
   the assessor and identifying whether human or AI, and quoting actual support.
   Codex manager assessment is AI-authored, not an independent human review.
   Preserve original raw/error/intent
   bytes privately. Publish only reviewed synthetic answers and redacted metadata;
   never reasoning, auth headers or sensitive endpoints. Stop only the isolated
   process you launched. No persistence, services on retained worktrees or native
   continuation is authorized.

Remaining launch prerequisites: manager continuation, clean committed freeze,
actual operator credentials and effective isolated-process
configuration, fresh provider catalog. Scripted verification cannot establish
availability, latency, provider token counts, behavior or reliability.
