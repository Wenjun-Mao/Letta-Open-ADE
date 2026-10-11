# Hindsight Character Evaluation CLI

Evaluation-only contract `ade-hindsight-character-evaluation-v1`,
[ADR 0063](../../../../../../docs/adr/0063-hindsight-character-evaluation-boundary.md).
This feature owns scoped recall and final Character composition. The workflow
owns synthetic fixtures, ingestion, curation, isolated deployment/configuration
pins and semantic assessment. No native database, reviewer, run service,
finalizer, runtime worker or HTTP endpoint is constructed.

Use the CLI from the workspace or an installed `ade-api` package. Workflow code
must invoke this entrypoint as a subprocess rather than import its helpers.

```sh
uv run --locked python -m ade_api.features.agent_runtime.hindsight_evaluation scope \
  --workspace-id campaign-1 --subject-id subject-A --character-root-id xiaotang
```

`scope` is offline and prints workspace/subject/root, `bank_id`, `tags` and
`tags_match`. IDs must be 1-128 ASCII letters, digits, underscores or hyphens.
The bank is `ade-probe-` plus the first 32 lowercase hex characters of SHA256
over UTF-8 compact JSON `[workspace_id,subject_id]` (no spaces). For `W`/`S`, it
is `ade-probe-44c3cae52ae1985bc222da4433c70032`.
The tags are exactly `character:<character_root_id>` OR `kind:profile`, with
`any_strict`. Callers cannot supply arbitrary bank IDs, empty filters or modes.
Use a campaign/iteration-specific workspace ID for new candidate state; retain
it for continuity checks. Conversation, archive and persona-version changes do
not change scope. Another subject/workspace changes the bank; another root
changes the character tag within that bank (PC-02/03/04/10/11).

The workflow must assign `character:<root>` source tags, a narrow extracted
`kind:profile` label and character-local observation scopes. Never mark an entire
private source as profile-visible. Returned facts must match a requested tag;
observations must have exactly the current root among their character tags.
Profile-only and mixed-root observations fail closed. This is structural
admission, not proof that Hindsight correctly classified mixed factual meaning.

Create a synthetic JSON input using this shape (unknown input fields fail):

```json
{
  "contract": "ade-hindsight-character-evaluation-v1",
  "synthetic": true,
  "case_id": "solo-story",
  "scope": {
    "workspace_id": "campaign-1",
    "subject_id": "subject-A",
    "character_root_id": "xiaotang"
  },
  "model_key": "deepseek::deepseek-flash",
  "persona": "你是林小棠。",
  "dialogue": [{"role": "user", "content": "那次看海你是和谁一起去的？"}],
  "query": "小棠之前讲过的看海经历",
  "query_timestamp": "2026-10-11T12:00:00Z",
  "arms": ["hindsight", "empty", "adequate"],
  "adequate_memories": [{
    "id": "control-story-1",
    "text": "小棠说那次是独自去看海。",
    "type": "experience",
    "tags": ["character:xiaotang"],
    "document_id": "committed-exchange-1",
    "mentioned_at": "2026-10-01T12:00:00Z",
    "context": "A committed assistant solo story, not shared user history",
    "metadata": {"speaker": "assistant", "source_id": "exchange-1"}
  }]
}
```

`persona` is the workflow's exact frozen authored Character instruction text.
`dialogue` accepts only text-only user/assistant messages and must end in the
current user question. `query_timestamp` requires an ISO timestamp with timezone.
Arm names must be unique; each selected arm runs exactly one tool-free Character
generation. `hindsight` performs one scoped recall, `empty` deliberately injects
no memories without calling Hindsight, and `adequate` uses nonempty manually
supplied memories validated against the same scope. Omit `adequate_memories`
when not using that arm. Failed recall aborts, rather than substituting a control.

Optional frozen settings and defaults: `timeout_seconds=120.0` and
`recall_timeout_seconds=120.0` (positive, at most 180),
`max_output_tokens=2048`, `input_token_limit=8192`, `recall_max_tokens=2048`,
`recall_budget="mid"`, and
`recall_types=["world","experience","observation"]` (nonempty, unique).
Token integers must be positive; output/recall ceilings are 32768 and the input
ceiling is 131072. Admission checks the whole executor payload using the existing
UTF-8 token estimate, including memory metadata. It does not truncate an
oversized first recalled fact or prove provider-tokenizer capacity.

Supply credentials only through the process environment:

- `ADE_EVAL_ROUTER_BASE_URL`: experiment router `/v1` URL.
- `ADE_EVAL_ROUTER_API_KEY`: experiment router bearer key, required.
- `ADE_EVAL_HINDSIGHT_BASE_URL`: self-hosted server origin, without `/v1`.
- `ADE_EVAL_HINDSIGHT_API_KEY`: Hindsight bearer key, required for that arm.

URLs reject embedded credentials, query strings and fragments. The Hindsight
client follows no redirects and performs no retries. Router transport retains
its existing one-attempt contract. Do not supply live credentials at P0.

```sh
uv run --locked python -m ade_api.features.agent_runtime.hindsight_evaluation run \
  --input workflows/evals/hindsight_memory_probe/fixtures/case.json \
  --output-directory workflows/evals/hindsight_memory_probe/outputs/case-unique
```

The output parent must exist and the final directory must be new. Existing
directories/receipts are never overwritten. Exit 0 plus `completion.json`, with
no `failure.json`, means all requested arms and captures completed. A nonzero
exit or failure receipt invalidates completion; preserve partial receipts and
use a new directory on a justified retry. Finishing does not qualify semantic
behavior, infrastructure, full reranking or live provider compatibility.

Receipts (directory 0700, files 0600, exclusive writes with fsync):

- `input.json`, `binding.json`: frozen synthetic inputs, derived scope, pinned
  Hindsight identity and selected router model/profile fingerprint.
- `<arm>.context.json`: admitted attributed memories, recall status/path/payload,
  recall latency/count or explicitly identified control status.
- `hindsight.recall-request.json`: actual scope/payload captured before dispatch;
  capture failure prevents recall as well as Character generation.
- `hindsight.recall-failure.json`: safe HTTP/transport failure metadata, without
  error bodies, headers or exception text; timeouts retain the request receipt.
- `hindsight.recall.json`: actual recall request/status/latency and original-value
  result projection, captured before schema/scope admission so rejected candidates
  survive. Keeps the pinned result fields plus scores/chunk IDs; excludes
  attachments, unknown fields and metadata outside attribution. Arbitrary HTTP
  error bodies are never stored.
- `hindsight.recall-trace.json`: actual upstream trace, required for recall;
  never injected into Character. Retrieval candidate text may exceed admitted
  context. The workflow checks complete reranking using trace score components,
  phase metrics and candidate configuration/server evidence; HTTP 200 alone is
  insufficient. The pinned trace's reranking metric does not identify the served
  provider. No chunks, global entity views or source-fact bundles are requested.
- `<arm>.request.json`: the actual final executor payload sent to Model Router,
  captured through awaited authorization before dispatch. It is not a guessed
  reconstruction or a capture of Model Router's downstream adapted wire request.
- `<arm>.result.json`: final assistant text, numeric usage, finish reason,
  provider request IDs, one-request count, latency and captured request hash.
  A non-`stop` finish preserves this receipt but fails completion.
- `completion.json` last, or `failure.json` with a safe code, scope and elapsed
  time. Raw provider errors, authorization headers and private reasoning are
  excluded. Metadata projects only speaker/source/time/subject/root/version.

The CLI freezes persona, dialogue, route and limits across arms and requires an
applied router profile. It checks selected catalog settings before and after
each generation and aborts observed drift. The workflow must also bind an
immutable experiment router release/configuration; catalog checks cannot prevent
concurrent reconfiguration or capture its upstream serialization. No provider
sampling overrides or independent serializer are added to the native executor.

The HTTP path and models were inspected at Hindsight 0.10.3 source
`eb6df499d35300e5b2f3f029b2e6adda04ed90f8`:
[server request/result definitions](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/api/http.py),
[generated recall client](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-clients/python/hindsight_client_api/api/memory_api.py),
and [trace schema](https://github.com/vectorize-io/hindsight/blob/eb6df499d35300e5b2f3f029b2e6adda04ed90f8/hindsight-api-slim/hindsight_api/engine/search/trace.py).
Fake HTTP tests prove offline mechanics. Pinned-image provider serialization,
authentication, extraction, Chinese retrieval and semantic qualification remain
workflow acceptance work under the activated experiment plan.
