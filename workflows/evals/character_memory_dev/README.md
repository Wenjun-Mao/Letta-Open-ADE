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

The proposed local single-operator backend investigation, classified gaps, and
conditional live-call budget are recorded in
[ADR 0024](../../../docs/adr/0024-local-luna-agent-backend-feasibility.md).
The version-pinned `app_server_spike.py` is a no-generation stdio preflight,
not an ADE backend. It checks the installed CLI's ChatGPT login, initializes
the app-server in an empty temporary cwd, checks that the same invocation has
no enabled MCP servers, reads only filtered nonsecret config fields, and
terminates its process group. It never starts a thread or turn:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.app_server_spike
uv run --locked pytest -q workflows/evals/character_memory_dev/tests/test_app_server_spike.py
```

The fake-server tests exercise prospective dynamic-tool protocol handling;
the MCP inventory check covers only that layer. They do not establish that the
installed app-server exposes only ADE tools or that a Luna model call succeeds.
The user accepted unknown internal CLI transport retries for at most four
serial synthetic turn starts in this experiment only; no ADE/application
reroll or fallback is allowed. This is not a four-network-attempt guarantee,
and it does not qualify production or release behavior. No turn may begin
until exhaustive tool restriction or an independent host-isolation boundary
is established. The spike bounds each operation and total
captured messages, binds synthetic tool calls to one explicit thread/turn,
rejects duplicate call IDs, and terminates its process group. Requalify on
any CLI/schema version change.

The CLI has its own instruction context; role-labelled input is not equivalent
to Chat Completions role precedence. An empty temporary cwd and read-only sandbox
reduce accidental context access, but do not isolate hostile inputs from the host.
Use synthetic/trusted development data. Do not use this as a public service or
forward credentials/private transcripts. Captured prompts and output remain on
disk until the operator removes them.

## Verification

The bounded natural-memory implementation has a separate offline contract
matrix in `fixtures/natural_memory/` and
`tests/test_natural_memory_contract.py`. Run it without a provider account:

```sh
uv run pytest -q workflows/evals/character_memory_dev/tests/test_natural_memory_contract.py
uv run pytest -q services/ade-api/tests/agent_runtime/test_natural_context.py
```

The context tests use synthetic records at 0, 12, 48, 128 and 256 records,
short and long values, and check the first whole-request boundary at which
the full lifecycle snapshot fits. These are capacity and contract checks, not
evidence of useful model recall. The A/A0/B binding IDs are development-only;
under snapshot pressure A/A0 share the scoped current-memory fallback and
withhold prior narrative, while B alone admits the shared local suffix. The
A/A0 nonsummary equality assertion covers both full-snapshot and overflow cells.
The default product binding has not been changed. No live comparison or policy
selection is implied by this offline workflow.

The real-worker pressure test uses an exclusively idle disposable PostgreSQL
database, source-linked synthetic setup in a separate conversation, and a fake
router. It retains the actual A/A0/B generation and full reviewer requests,
then asserts 48 matching lifecycle targets, A/A0's identical withheld packets,
B's complete local exchanges, provider counts, token ceilings, and committed
outcomes. A second real-worker test generates a fake-model compaction from 68
source messages and verifies that an early afternoon interview detail reaches A
only through the generated summary; A0/B lack that detail in their final packets.
It checks the prefix boundary, A/A0 serialized nonsummary equality, and a
`search_memory` continuation against the second complete request. A third
real-worker test covers active Toronto residence during a Paris visit, ended
and invalidated assertions, and a forgotten relationship alongside attributed
old summary text. These are synthetic transport and state checks, not evidence
of real-model summary quality:

```sh
ADE_TEST_DATABASE_URL='postgresql+psycopg://ade_owner@127.0.0.1:32768/ade_m2_memory_test_<owned-id>' \
  uv run --locked pytest -q services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_packets.py services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_compaction_packets.py services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_state_packets.py
```

The private `outputs/natural-worker-cases-20260924/manifest.json` indexes 19
retained, SHA-256-bound real-worker attempts: A/A0/B pressure and long history,
B tool continuation, and four A/A0/B lifecycle/narrative states. Each packet includes exact
serialized sections, source IDs and roles, selected lifecycle views, omissions,
token estimates, provider counts, and terminal readback. The separate
`outputs/natural-failure-20260924/manifest.json` indexes committed and
confirmed-rejection attempt packets. Both manifests are synthetic evidence;
they do not qualify a live comparison.

`test_natural_matrix_packets.py` executes all 30 expanded frozen cells through
the same generation and reviewer serializers with a scripted router, asserting
exact source-bundle parity and paired A/A0 and A0/B controls. Mutation cells
there are packet-only receipts; they do not claim a database write or a correct
model proposal. `test_natural_packet_grid.py` retains 30 additional serialized
0/12/48/128/256 short/long A/A0/B packets and measures full reviewer overflow
separately without clipping targets. The private
`outputs/natural-matrix-packets-20260924/manifest.json` maps every cell and
grid input to its exact request artifact and hash. The ten
`test_full_snapshot_whole_request_boundary` cases independently locate the
first whole-generation-request fit and assert both sides for each count and
size. Existing focused lifecycle policy and PostgreSQL tests check the write
contracts; fake replies do not
establish usefulness. Run the packet layer with:

```sh
uv run --locked pytest -q workflows/evals/character_memory_dev/tests/test_natural_matrix_packets.py workflows/evals/character_memory_dev/tests/test_natural_packet_grid.py
```

For the local Agent Studio journey, `offline_natural_router.py` supplies only
scripted catalog, chat, review, and embedding responses on loopback. Run it
with `uv run --locked python -m workflows.evals.character_memory_dev.offline_natural_router --port 8130`.
`offline_natural_browser_setup.py` provisions a natural-policy fixture in an
existing migrated, passwordless `ade_m2_memory_test_<owned-id>` database. Pass
`--existing-subject-id` to provision an archived old-policy conversation bound
to that same subject. It writes a private fixture receipt under `outputs/`.
The API and worker must both point to that isolated database and the fake
router base URL. Browser observations from this setup do not measure provider
quality or authorize live calls. The 2026-09-24 in-app browser replay and
PostgreSQL readback are retained privately in
`outputs/natural-browser-20260924-round2/browser-evidence.json`: fresh turn,
shared subject readback in an archived old-policy conversation, disabled old
composer, inline removal cancel, exact confirmation, forgotten audit lineage,
and memory generation 2 to 3. Its sibling `manifest.json` hashes the fixture
receipts and observed action/readback note.

The revision-5 offline replay is retained in
`outputs/natural-browser-20260924-v3/browser-evidence.json`. The scripted fake
router covers scoped addition/correction, unresolved deferral, user-antecedent
resolution with distinct source roles, and atomic rejection of bare-name
endorsement. The same isolated UI and database show archived old-policy
readback, source citation, exact removal, and historical revision retention.
These observations establish integration mechanics only.

Opt-in natural-memory attempt evidence is available only when
`ADE_NATURAL_MEMORY_CAPTURE=1` is set on a development worker connected to a
loopback database named `ade_*_test_*` and the conversation purpose is
`evaluation`. It writes one private JSON artifact per run attempt under the
ignored `outputs/natural-memory-attempts/` directory. The artifact retains
visible generation requests (including tool continuations), optional compaction
request/result and source boundary, source bundle,
candidate reply, typed reviewer decision, absent stages and authoritative
run/attempt readback. Authentication, provider wire bodies, private reasoning
and raw exception text are excluded. A missing or `unconfirmed` artifact is
unscorable and must stop the synthetic campaign; artifact failure does not
rewrite an already committed run. This switch does not authorize provider calls.

```sh
uv run pytest -q workflows/evals/character_memory_dev/tests
```

Tests use synthetic subprocesses and make no paid/subscription model calls.
Live experiments are explicit commands. No Luna endpoint is registered in Model
Router, and the native Chat Memory Eval remains unchanged.

## Natural-Memory Offline Contract (Checkpoint 1)

The frozen checkpoint-1 matrix and former checkpoint-6 campaign describe a
historical reviewer contract. Its no-save cell and comparison schedule do not
qualify the current reviewer/ADE boundary amended on 2026-09-24. Preserve the
hash-bound inputs and prior evidence; design a new factual-continuity matrix
before any future live campaign. The frozen natural-v3 binding is read-only;
fresh offline natural sessions use natural-v4.

[`fixtures/natural_memory/cases.json`](fixtures/natural_memory/cases.json)
contains isolated, chronological branches for all 22 worked design arcs. Each
branch names source roles, state checkpoints, a useful reply criterion, forbidden
claims, and unsupported scope. Operator-labelled turns in these synthetic
branches are control actions, never fabricated user messages or citations.

[`fixtures/natural_memory/matrix.json`](fixtures/natural_memory/matrix.json)
freezes the proposed A/A0/B comparison cells, numerical generation and reviewer
allocations, pressure grid, positive actual-compaction assertion, stop classes,
and a proposed 96-generation/160-embedding ceiling. It is a checkpoint-1
offline contract, not evidence that the
entire 30-cell campaign has passed database writes or live semantic quality,
and not a selected product policy. All 30 cells now have executed serializer
packets; the representative high-risk states have separate real-worker packets.
The user authorized one bounded live checkpoint-6 campaign on 2026-09-24,
subject to the plan's pre-request route, ledger, source, database, and evidence
guards. Provider-backed scoring and release qualification remain unrun.

The proposed schedule expands to 30 turn cells, each allowing at most one
conversation continuation and one reviewer call, plus two actual-compaction
calls: 92 reserved generation requests, with four unallocated under the ceiling.
The embedding ceiling allocates 40 to scripted setup/indexing and 120 to all
turn-level query, write, and tool paths. Conditional calls consume only actual
pre-request reservations; unused allocation is not evidence of execution. If
setup or continuation needs more than its allocation, the campaign is incomplete
until a newly reviewed schedule is approved. No rerolls or reviewer repair are
included. A0 is diagnostic only; neither A nor B may win on incomplete mandatory
coverage or safe but unhelpful abstention.

```sh
uv run pytest -q workflows/evals/character_memory_dev/tests/test_natural_memory_contract.py
```

This test only validates fixtures and accounting; it makes zero outbound calls.

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

## M2 ADE PostgreSQL Context-Conditioning Slice

This bounded development slice connects committed state from the existing ADE
PostgreSQL typed-fact path to the Luna dialogue task. It uses one fresh
synthetic case in the explicitly disposable local database only. The workflow
creates source records and writes typed add/correct/forget operations through
the existing Pydantic review validation, `prepare_memory_review`, and
`commit_memory_review` path. These operations are scripted setup, not
model-generated extraction and not evidence that prose is automatically
converted into typed facts.

The exact serial chronology is: (1) commit Subject One's scripted drink
preference and probe; (2) correct it in a distinct Subject One conversation,
commit, and probe; (3) forget the corrected fact, commit, and probe; (4) add a
different explicit preference for Subject Two, commit, and probe. Each probe
reads the current subject's active facts through `MemoryRepository` only after
the preceding transaction commits. Its dialogue input includes those active
fact values and one new recall question. It excludes source/origin, correction,
and forget transcripts and expected answers. The separate-subject output is
not post-filtered: the repository query is scoped to Subject Two before its
facts are passed to the prompt. Raw model calls, exact prompt contexts, and
source fact/revision IDs are retained together in the ignored output folder.

The four calls are limited to the existing Luna subscription adapter, medium
effort, default tier, 180-second timeout, JSON Schema dialogue contract, and
zero adapter retries/fallbacks. Calls run serially and once; a failed or
uncertain call is not retried. This is database-backed context-conditioning
development evidence only—not semantic retrieval quality, extraction quality,
native runtime behavior, a security proof, or a head-to-head Hindsight result.
Review exact claims and source attribution, specifically whether the forgotten
preference is resurrected and whether Subject One's preference is attributed
to Subject Two; distinguish pass, fail, and uncertain rather than grading
vocabulary alone.

After applying the checked-in ADE migrations to the named disposable local DB,
run the case once with a passwordless loopback `ADE_TEST_DATABASE_URL` for
`ade_m2_memory_test_01a0ca1b`:

```sh
ADE_TEST_DATABASE_URL='postgresql+psycopg://ade_owner@127.0.0.1:<mapped-port>/ade_m2_memory_test_01a0ca1b' \
  uv run --locked python -m workflows.evals.character_memory_dev.m2_postgres_luna
```

The angle-bracket port is the local Docker mapping, not a value to copy
literally. The workflow verifies the connected database and role before any
case write. It does not migrate, drop, truncate, or clean up the database. The
new case IDs are random; the case manifest and per-call captures are written
under ignored `outputs/m2-postgres-luna-<case-id>/`.

### Review Claims, Not Vocabulary

Assess a factual-recall answer against the source it attributes: it must not
say the user remembered a more specific preference than the supplied evidence.
A recommendation may propose a subtype such as jasmine when presented as advice;
the word itself is not a false-memory claim. Likewise, a source-linked prose
proposal can preserve a resolved temporal story without supplying
machine-addressable lifecycle state, and a gentle callback is not automatically
repetitive. Record the exact assertion, source attribution, and uncertainty;
Luna samples alone do not justify a production or schema change.
