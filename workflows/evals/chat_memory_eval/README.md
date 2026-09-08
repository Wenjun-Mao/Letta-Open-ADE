# Chat Memory Eval

Runs isolated native evaluation sessions through a fixed multi-turn conversation and
checks whether the selected model stays in persona while updating typed user memory.

## Quick Commands

Smoke one round:

```bash
uv run python workflows/evals/chat_memory_eval/run.py --config workflows/evals/chat_memory_eval/config.toml --rounds 1
```

Run the default matrix:

```bash
uv run python workflows/evals/chat_memory_eval/run.py --config workflows/evals/chat_memory_eval/config.toml
```

Outputs stream to `workflows/evals/chat_memory_eval/outputs/` as timestamped CSV, JSONL, summary JSON, and provenance JSON files. The JSONL preserves the full turn records, final memory, deterministic score, optional judge payload, and the run ID that binds it to the summary and provenance record.

## What It Checks

- The assistant does not self-disclose as an AI, bot, virtual assistant, or generated program.
- Typed subject memory changed from its initial value.
- Active memory facts contain `张伟`, `Rocky`, and `哈士奇/Husky`.
- Per-turn tool calls and committed memory operations are recorded from run events.

The optional LLM judge is diagnostic only. The process exit code uses deterministic checks.
The judge inherits `ADE_API_MODEL_ROUTER_BASE_URL`, which is
`http://model-router:8010` inside Compose. A direct host run falls back to
`http://127.0.0.1:8010`; set `model_router_base_url` in a local config when the
router is reachable elsewhere, or disable the advisory judge.

## Config

The default config is `workflows/evals/chat_memory_eval/config.toml`.

| Field | Default | Meaning |
| --- | --- | --- |
| `api_base_url` | `http://127.0.0.1:8000` | ADE API base URL. |
| `output_dir` | `workflows/evals/chat_memory_eval/outputs` | Directory for generated artifacts. |
| `fixture_key` | `recent_user_chat_turns` | Fixture JSON in `fixtures/`. |
| `rounds` | `3` | Number of isolated sessions to run. |
| `model` | `dgx_vllm::qwen3.6-35b-a3b-fp8` | Canonical Model Router key. |
| `prompt_key` | `chat_v20260516` | Chat prompt key. |
| `persona_key` | `chat_linxiaotang` | Chat persona key. |
| `embedding` | `dgx_embedding_sidecar::Qwen/Qwen3-Embedding-0.6B` | Canonical embedding route key. |
| `timeout_seconds` | `180` | Runtime timeout for each turn. |
| `retry_count` | `0` | Additional ADE-owned attempts for each idempotent turn. |
| `judge_enabled` | `true` | Run advisory router-backed LLM judge. |
| `judge_model_key` | blank | Router model key for judge; blank derives it from `model`. |

The evaluator makes exactly one HTTP attempt for every ADE API and advisory-judge
request. Each turn has a stable idempotency key; `retry_count` controls only the
additional attempts owned by the ADE runtime.

Each run captures immutable provenance: the requested run ID, prompt/persona snapshots, catalog deployment identities, every effective execution control, and `ADE_SOURCE_REVISION`, `ADE_SOURCE_DIRTY`, and `ADE_SOURCE_FINGERPRINT`. The configuration digest excludes the run ID and capture time, so equivalent runs remain comparable.

## Test Center

ADE Test Center can launch this workflow with a focused form. It passes its allocated `<run_id>` directory name through `--run-id`, and the workflow writes that same value into the provenance, summary, CSV, and every JSONL row. UI-launched runs write artifacts under `data/runtime/test-runs/<run_id>/` so the manifest, log, CSV, JSONL, summary, and provenance are all visible from the run artifact panel and survive an API restart. Direct CLI runs generate a run ID when `--run-id` is omitted.

## Troubleshooting

- If options validation fails, refresh ADE options and confirm the selected chat model, prompt, persona, and embedding are available.
- If judge calls fail but deterministic checks pass, inspect the JSONL `judge.error`; judge failures are advisory.
- Cleanup is idempotent. If a process is interrupted, delete its evaluation session
  through `DELETE /api/v3/evaluation-sessions/{conversation_id}`.
