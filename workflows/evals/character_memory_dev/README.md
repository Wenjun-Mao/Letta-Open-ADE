# Character Memory Development

Host-only experiments with the existing `chat_linxiaotang` (林小棠) persona,
using GPT-6 Luna through the installed Codex CLI and its ChatGPT login.
Run from the repository root on macOS/Linux. No Docker stack or Spark access
is required. This consumes the account's Codex allowance.

New development calls request `gpt-6-luna` with medium reasoning effort and the
default service tier. Three schema-enabled smoke calls passed on 2026-09-22:
dialogue, memory-review, and advisory judge. This verifies bounded task-shape
compatibility, not broad model quality or native runtime qualification. Frozen M1/M2
captures, matrices, manifests, and validators remain historical `gpt-5.6-luna`
evidence and must not be relabeled or mixed into GPT-6 comparisons.

## Run

New calls pass a task-specific `--output-schema` to the CLI and save its exact
JSON as `output-schema.json` beside the raw captures. The manifest records
`output_contract=json-schema-v1` and `runtime_qualification=schema_smoke_verified`.
Raw smoke records are in `outputs/gpt6-schema-{dialogue,review,judge}-20260922/`;
their launch-time qualification labels remain unchanged.
The first GPT-6 smoke returned plain text despite the prompt's JSON instruction;
its transport passed but task validation failed. That record is preserved.
Schemas constrain shape only: strict task/source validation still runs, with
no text wrapping, repair, or automatic retry. Historical GPT-5.6 captures used
prompt-only formatting and remain unchanged.

```sh
uv run python -m workflows.evals.character_memory_dev.run \
  --runtime luna-subscription --task dialogue \
  --input workflows/evals/character_memory_dev/fixtures/linxiaotang.json
```

Each invocation launches at most one generation session. Defaults: medium
reasoning, default service tier, 180-second generation timeout, no adapter
retries or fallback. Use `--timeout-seconds` to change the limit (maximum 600).
Run serially. Authentication and CLI availability are checked before generation.
API-key login is rejected; provider environment variables are not inherited.
Custom `CODEX_HOME` is not supported by this lane.

`--task memory-review` proposes source-linked user facts and shared experiences
from the same input format. `--task judge` requires a final assistant message
and nonempty `expectations`; its assessment is advisory.

Inputs contain `messages` with unique `id`, `role` (`user` or `assistant`), and
`content`, plus optional `memories` and `expectations` lists of strings. Supply
all relevant context explicitly. The workflow snapshots the actual persona
content into the captured prompt. It does not load Codex conversation history.

## Read The Result

An ignored `outputs/<unique-id>/` directory contains the prompt, raw stdout
events, stderr, final text, transport manifest, and task validation. Successful
task validation also produces `result.json`. Use `--output <new-directory>` for
a named run. Existing directories are rejected before launch, even after a
failed or interrupted run. There is no automatic resume or replay.

`transport_validated` in the manifest means the CLI returned one expected turn;
check `validation.json` separately for the task schema. A process crash can leave
`reserved` or `running`; these are incomplete records, never successful results.
Timeouts and post-launch failures are recorded as `uncertain_or_invalid` because
usage may have occurred. Raw evidence is preserved for inspection. Captures are
limited to 2 MB per output file (checked during execution); inputs to 64 KB.
CLI-version changes require rechecking the accepted event sequence.

Only requested model/effort and observable CLI metadata are recorded. One CLI
turn does not prove one internal network request or disable SDK-internal retries.
Missing usage remains unknown. Cache/reasoning tokens are subsets, not extras.

These experiments do not test ADE persistence, native provider tool calling,
embeddings, Qwen behavior, or release qualification. The sample supplies facts
in-context; correct recall is not evidence of long-term memory. Memory proposal
validation checks source IDs and author roles, not semantic truth. Review them
before any future use; this workflow never writes production memory.

The CLI has its own instruction context; role-labelled input is not equivalent
to Chat Completions role precedence. An empty temporary cwd and read-only sandbox
reduce accidental context access, but do not isolate hostile inputs from the host.
Use synthetic/trusted development data. Do not use this as a public service or
forward credentials/private transcripts. Captured prompts and output remain on
disk until the operator removes them.

## Verification

```sh
uv run pytest -q workflows/evals/character_memory_dev/tests
```

Tests use synthetic subprocesses and make no paid/subscription model calls.
Live experiments are explicit commands. No Luna endpoint is registered in Model
Router, and the native Chat Memory Eval remains unchanged.

## M2 Comparison Contract

[`fixtures/m2/comparison.json`](fixtures/m2/comparison.json) is the compact,
workflow-local comparison contract for M2. It fixes a common context budget and
the M1-linked, timestamped two-subject cases to use when comparing an ADE
extension with an external candidate. It specifies expected semantic state and
negative probes; it does not implement memory, call Hindsight, or make a
provider claim.

For a future candidate run, initialize fresh state for every `case_state_id`
and process that case's `conversation_ids` in their listed chronological order.
Do not retain future turns before an earlier probe. In the forgetting case,
store and successfully recall the milk-tea preference after `forget-origin`
before processing `forget-request`; its `forget-user` state is separate from
the corrected coffee/flower-tea preference case.

```sh
uv run pytest -q workflows/evals/character_memory_dev/tests/test_m2_comparison.py
```

The fixture test validates input references and shape only. Separate tests
exercise current ADE structural contracts where they exist: typed correction,
explicit forgetting, subject/status-scoped retrieval predicates, and context
assembly. They deliberately surface unsupported concern/promise/shared-event
semantics and active-profile distraction risk rather than simulating parity or
claiming memory-quality evidence.

## M2 Luna Development Matrix

[`fixtures/m2/luna_matrix.json`](fixtures/m2/luna_matrix.json) fixes a bounded
fourteen-session GPT-5.6 Luna development matrix: three source-transcript
`memory-review` calls and eleven dialogue calls. It uses the existing task
contract and is not a runner. The matrix keeps review criteria out of dialogue
inputs and labels all manually curated context as source-derived supplied
context, not retrieval.

```sh
uv run pytest -q workflows/evals/character_memory_dev/tests/test_m2_luna_matrix.py
```

Its ignored raw captures are development evidence only. A dialogue prompt with
omitted memory cannot prove forgetting or subject isolation; a valid
`memory-review` proposal is not a durable ADE fact.

### Review Claims, Not Vocabulary

Assess a factual-recall answer against the source it attributes: it must not
say the user remembered a more specific preference than the supplied evidence.
A recommendation may propose a subtype such as jasmine when presented as advice;
the word itself is not a false-memory claim. Likewise, a source-linked prose
proposal can preserve a resolved temporal story without supplying
machine-addressable lifecycle state, and a gentle callback is not automatically
repetitive. Record the exact assertion, source attribution, and uncertainty;
Luna samples alone do not justify a production or schema change.
