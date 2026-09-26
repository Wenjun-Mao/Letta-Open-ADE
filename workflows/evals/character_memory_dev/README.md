# Character Memory Development

## Historical Recall Probe (H1–H3 Checkpoints)

The [frozen history contract](fixtures/history_recall/contract.json) belongs to
the approved bounded automatic-history versus empty-history probe. It is separate
from the historical Luna captures and earlier natural-memory matrices. The H2
reader is enabled only through `load_turn_state(..., include_history=True)`;
normal runtime turns do not send history to a model. It reads at most 128
complete succeeded exchanges from the accepted repeatable-read snapshot, with
whole-window omission when text or required source lineage exceeds the frozen
limits. Its omission counts and exact exchange/source IDs are mechanics evidence,
not dialogue-quality or release evidence.

H3 adds the evaluation-only `natural-user-assertions-v4-b-history-probe` binding.
Construct `AgentRuntimeWorker(..., history_probe=HistoryProbe(arm=...,
ranking_recipe=...))` only in an isolated evaluation runner. Both arms use that
binding; the empty arm supplies no H windows, and the automatic arm requires
one frozen H2 recipe or the earlier injected test selector. The native Qwen
path ranks the accepted snapshot in memory, checking exact source integrity
and subject generation immediately before each embedding dispatch. It uses
the configured Qwen route with a distinct transcript recipe. An absent selector
fails explicitly. Neither the native worker default nor public routes enable
history. See [ADR 0040](../../../docs/adr/0040-source-guarded-history-ranking.md).

The H3 packet is admitted against serialized generation and projected reviewer
capacity. Fresh source checks precede every H-bearing generation, continuation
and review request, and the success transaction checks the held sources again
even on a no-write turn. Genuine pre-exposure purge rebuilds the packet;
post-exposure loss fails the run. The successful attempt outcome records
`history_probe_status` and admitted run IDs. See [ADR 0039](../../../docs/adr/0039-history-probe-packet-and-commit-fence.md)
for the exact boundary and limits.

Run the reader and guard tests against a fresh disposable PostgreSQL database
migrated to head. Run the native worker tests in a separate idle database because
structural reader tests leave pending fixture runs; the worker intentionally
claims the oldest eligible run. These tests use only fake-router calls. The
[approved plan](../../../docs/plans/natural-history-recall.md) retains H2 live
ranking feasibility and H4/H5 scoring as later checkpoints.

The offline review correction added [typed case scripts](fixtures/history_recall/cases.json),
[ranking development scripts](fixtures/history_recall/ranking_development.json),
and deterministic fake-score tests. Development corpora have more candidates
than the top-four window limit, so a wrong ranking can lose needed evidence.
`history_fixture_contract.py` validates source quotes, lifecycle operation/reason
pairs, chronology, complete expected deltas and the finite control/follow-up
schedule. The finite H2 runner uses these frozen synthetic fixtures and labels
them as fixture-owned data; it does not claim a native database source check.

After the offline tests and exact route/artifact identity pass, run the finite
ranking schedule through the configured development router container. The
runner resolves the router credential inside that container and keeps it out
of command arguments, logs and saved artifacts. It saves every planned cell
and redacted embedding receipt under ignored `outputs/`. Run held-out cases
only if `development.json` selects an adequate recipe by the frozen rule:

```sh
uv run --project services/ade-api python -m workflows.evals.character_memory_dev.history_h2_probe \
  --phase development \
  --output workflows/evals/character_memory_dev/outputs/history-h2-ranking/development.json
uv run --project services/ade-api python -m workflows.evals.character_memory_dev.history_h2_probe \
  --phase heldout \
  --development-result workflows/evals/character_memory_dev/outputs/history-h2-ranking/development.json \
  --output workflows/evals/character_memory_dev/outputs/history-h2-ranking/heldout.json
```

The second command is conditional on an adequate development selection. Each
cell runs once; failed or unrun cells are retained without a reroll.
The 2026-09-26 finite schedule selected Qwen cosine and completed all four
held-out ranking cases. [Its finding](../../../docs/findings/natural-memory-consultation/history-h2-ranking-feasibility-2026-09-26.md)
records the full evidence and limits; H4 native dialogue scoring is pending
director review.

H4's one-shot native runner is `python -m workflows.evals.character_memory_dev.history_h4_campaign`. It requires a fresh migrated passwordless loopback `ade_m2_memory_test_<hex>` database with pgvector in the `extensions` schema and an effective search path that resolves the vector cosine operator, the configured development ADE API container for the exact H2 Qwen fingerprint, and the official DeepSeek settings from `--env-file`. It accepts `--database-url`, `--env-file`, `--qwen-container`, and a new ignored `--output` directory. The runner rejects reuse of an output directory and never rerolls a cell.

The first H4 preflight stopped **before live dispatch**: its smallest H-capable request estimates 7,958 input tokens against the original 6,759 limit. The director-approved [H4 reviewer amendment](fixtures/history_recall/h4_reviewer_amendment.json) binds the unchanged H2-hashed contract, H2 result and H4 cases, and supplies an evaluation-only 16,384 context/4,096 output/11,469 input reviewer envelope to both arms and controls. See [the preflight diagnosis](../../../docs/findings/natural-memory-consultation/history-h4-preflight-blocker-2026-09-26.md). The runner still fails closed on the full candidate reserve. Optional older windows can be lost on long follow-ups; retain their capacity omissions as observations.

The first amended live run stopped when the `user_retraction` empty-arm turn exhausted the unchanged two-request conversation tool-step ceiling. The [partial H4/H5 finding](../../../docs/findings/natural-memory-consultation/history-h4-h5-partial-live-2026-09-26.md) records 10 committed, one rejected and 15 unrun cells. Its ignored output directory keeps the exact attempt packets, blind review packet, stage audit and independent database readback; do not resume that one-shot directory or reroll its failed cell.

The [offline interpretation correction](../../../docs/findings/natural-memory-consultation/history-h4-offline-review-correction-2026-09-26.md) distinguishes that verified bounded rejection from a source-integrity failure. H4 dispatch counters are observational; wrong routes still fail, and the per-turn request limits remain. The 15 unrun top-level targets and six dependent follow-ups are 21 unrun native turns. A separate review-only proposal lists them; no dispatch or replay is implied.

The separately authorized [remaining-turn run](../../../docs/findings/natural-memory-consultation/history-h4-remaining-stopped-2026-09-26.md) committed three targets, then stopped on an unequal `invalidated_ended` paired base packet. Its manifest and the original remain immutable. [ADR 0042](../../../docs/adr/0042-h4-paired-fixture-fact-chronology.md) records the offline fixture-order correction and native PostgreSQL regression; no product reviewer sort or retrospective packet normalization was made. Run `test_postgres_history_h4_campaign.py` with `ADE_TEST_DATABASE_URL` set to a migrated disposable PostgreSQL database before any newly authorized provider campaign. The [review-only 18-turn proposal](outputs/history-h4-offline-review-20260926/remaining-after-two-campaigns-proposal.json) excludes all 14 turns attempted across both campaigns and requires a new authorization before live dispatch.

The separately authorized [final remaining-turn campaign](../../../docs/findings/natural-memory-consultation/history-h4-final-remaining-live-2026-09-26.md) committed its 18 turns and matched all six new target base-packet pairs. Its stage audit and independent database readback confirm execution integrity, while five turns have exact expected memory-delta issues. Across the original 32-turn plan, 31 committed and one bounded rejection; the earlier `invalidated_ended` pair remains confounded and `user_retraction` remains one-sided. The blind answer packet awaits human scoring. No production history policy is selected by these counts.

The [offline H5 synthesis](../../../docs/findings/natural-memory-consultation/history-h5-offline-synthesis-2026-09-26.md) traces the ambiguous `h_only_referent` early write and the retained-dialogue miss in `removed_acknowledgment` without changing runtime or scorers. A separate [arm-neutral review companion](outputs/history-h4-offline-review-20260926/review-context-companion-v1.json) labels scope eligibility and fact lifecycle for all 11 cases while preserving the three original blind packets and keys.

The [target-attribution diagnostic schedule](fixtures/history_recall/target_attribution_diagnostic.json) is a fresh seven-turn, four-subject follow-up for the reviewer contract in [ADR 0043](../../../docs/adr/0043-reviewer-target-attribution-before-mutation.md). It reuses the original source cases without modifying their fixtures or scorers: two independent ambiguous dog turns followed by opposite explicit clarifications, one immediate explicit rename, and a removed-jasmine history question followed by a fresh preference. The one-shot native runner is `python -m workflows.evals.character_memory_dev.history_target_diagnostic` with `--database-url`, `--env-file`, `--qwen-container`, and a new ignored `--output` directory. It binds a clean source revision/fingerprint, all three historical H4 manifest hashes, schedule and fixture hashes, exact DeepSeek/Qwen catalog fingerprints, the existing H4 capacity and per-turn limits, and a fresh migrated disposable database. pgvector must be in the `extensions` schema with the effective search path resolving its cosine operator. Four trajectories get independent subjects; a verified terminal rejection skips only its dependent followup. Missing or inconsistent native evidence stops the run. Score clarification in the delivered reply separately from mutation deferral, and judge entity, revision timing, source role, and historical testimony meaning rather than exact reply wording or citation substrings. Dispatch counts are observational; missing receipts mean incomplete counts. This diagnostic does not select a default policy.

For the approved [native generation follow-up](../../../docs/plans/natural-history-recall.md#proposed-follow-up-native-generation-contract-alignment), the same runner now explicitly binds `chat_v20260926` through [its separate generation binding](fixtures/history_recall/generation_contract_diagnostic.json). That binding pins the unchanged persona, reviewer and schema, prior seven-turn manifest, provider routes, schedule, and hashes for the candidate plus shared generation instruction owners. Existing default and prior prompt snapshots remain bound to `chat_v20260516`. The next run requires a new clean source commit and separate output directory. It records admitted source-text and capacity-omission comparisons against the prior seven turns; a difference means the context is not matched. The [offline instruction review](../../../docs/findings/natural-memory-consultation/native-generation-contract-offline-2026-09-26.md) covers assembled packets and the limits of the preflight. No provider rerun is part of that offline checkpoint.

To reproduce the structural database checks, use an isolated PostgreSQL 15
instance with pgvector and a passwordless loopback `ade_owner` database named
`ade_history_test_<hex>`. On a host with Docker, for example:

```sh
docker run -d --name ade-history-check -e POSTGRES_USER=ade_owner \
  -e POSTGRES_DB=ade_history_test_01a0dbe2b -e POSTGRES_HOST_AUTH_METHOD=trust \
  -p 127.0.0.1::5432 pgvector/pgvector:0.8.1-pg15
docker port ade-history-check 5432
# Substitute the reported port for PORT below.
docker exec ade-history-check psql -U ade_owner -d ade_history_test_01a0dbe2b \
  -c 'CREATE SCHEMA ade; CREATE EXTENSION IF NOT EXISTS vector;'
ADE_DATABASE_MIGRATION_URL=postgresql+psycopg://ade_owner@127.0.0.1:PORT/ade_history_test_01a0dbe2b \
  uv run --project services/ade-api alembic -c services/ade-api/alembic.ini upgrade head
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:PORT/ade_history_test_01a0dbe2b \
  uv run python -m pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_history_reader.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_history_lineage.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_history_guard.py -q
# The reader tests leave pending fixture runs. Create an independent idle DB
# for worker claiming; use the same mapped PORT reported above.
docker exec ade-history-check createdb -U ade_owner ade_history_test_01a0dbe2c
docker exec ade-history-check psql -U ade_owner -d ade_history_test_01a0dbe2c \
  -c 'CREATE SCHEMA ade; CREATE EXTENSION IF NOT EXISTS vector;'
ADE_DATABASE_MIGRATION_URL=postgresql+psycopg://ade_owner@127.0.0.1:PORT/ade_history_test_01a0dbe2c \
  uv run --project services/ade-api alembic -c services/ade-api/alembic.ini upgrade head
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:PORT/ade_history_test_01a0dbe2c \
  uv run python -m pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_history_worker.py -q
docker rm -f ade-history-check
```

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
to that same subject. Pass `--enable-search-memory` to expose the subject-bound
tool for a discretionary invocation regression. It writes a private fixture
receipt under `outputs/`.
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

The tool-policy-v2 browser replay is retained privately in
`outputs/natural-browser-20260924-tool-v2/browser-evidence.json`. With
`search_memory` enabled, a free-form request to search completed without a
forced requirement or a scripted tool call. The same v4 conversation then
committed a Toronto location fact with its source citation. This checks current
dispatch and persistence wiring; the fake router does not measure whether a
real model chooses a useful tool call.

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

### Authorized factual-continuity diagnostic (2026-09-24)

The user authorized a new, bounded live diagnostic after the revision-5
responsibility cleanup. Its immutable eleven-turn, four-subject schedule is
[`fixtures/natural_memory/factual_live_diagnostic.json`](fixtures/natural_memory/factual_live_diagnostic.json).
Three independent subjects establish morning coffee through natural dialogue,
then test a morning-tea correction and cross-conversation recall, a distinct
evening-tea addition and recall, or uncertainty followed by drinking behavior
and recall. A fourth subject probes non-transfer. Each row declares its full
fact/revision/generation delta and answer boundary before provider calls.
The same natural-v4 B context, DeepSeek Flash high-thinking profile, Qwen
embedding route and 4,096-token reviewer output envelope are held throughout.
This is one declared context variant, not an A/B policy selection.

`natural_factual_live.py` requires a clean source commit and a fresh, migrated,
passwordless disposable loopback PostgreSQL database with zero runs. It starts
an isolated loopback router using the approved official DeepSeek and Spark
routes, performs one native attempt per scheduled turn with zero application
retries, records dispatch observations and private captures, and stops on a
rejected review or structural/evidence failure. It never resumes an output
directory. Private attempts, full subject readback, conversation state and
per-turn captures live under the ignored output path. Semantic misses in
committed turns remain evidence; no scorer or prompt changes occur during the
run. The known release-policy fingerprint freshness gate remains unwaived.

This authorization excludes the older 30-cell comparison, release promotion,
fingerprint rebind, deployment and production data. The output requires an
independent semantic review of every committed delta and reply before findings
are reported; an empty or rejected first-cell write is not a successful setup.

The first preflight created its private output and stopped with zero provider
dispatches because the local Spark IP changed the router catalog's base URL,
so it no longer matched the deployment's pinned `dgx-spark` URL. The runner
now resolves that exact alias to the configured IPv4 address inside its own
process while retaining the pinned URL in the catalog and outbound request.
This local DNS bridge matches Compose's `extra_hosts` mapping; it does not
change the provider route, deployment fingerprint, or model fallback policy.
The first native turn then stopped after one failed embedding dispatch because
async HTTPX passed the pinned alias as bytes. The bridge now handles both
string and byte forms, with a focused regression test and a read-only async
catalog check. The turn was not retried. See the
[stopped factual diagnostic](../../../docs/findings/natural-memory-factual-live-diagnostic-2026-09-24.md).
After director review, one fresh binding under the existing user `go` reached
five turns: four committed, including a correct morning-tea recall in a new
conversation, and the fifth rejected atomically when the reviewer tried to
reassert an active fact. Six scheduled turns stayed unrun. The linked finding
records the exact deltas, dispatches and private evidence identities; it is
partial development evidence, not a policy or release qualification.
An offline wire review then found that the request exposed F1 as active but
did not describe `reassert` as inactive-only or say to omit unchanged active
facts. The existing prompt/schema now state those lifecycle rules, with
serialized-request and atomic-rejection tests. No further live turns were
sent under this clarification.
The director then selected one bounded eight-turn follow-up under the user's
existing `go`, recorded in
[`fixtures/natural_memory/factual_live_followup.json`](fixtures/natural_memory/factual_live_followup.json).
`natural_factual_live.py --follow-up-eight` selects only the three frozen
case branches named there. The two first turns are independent subject setup;
the remaining six were unrun or rejected in the previous binding. The
selection keeps their exact source texts and complete-delta expectations,
the v4 B context, DeepSeek Flash high-thinking and Spark Qwen routes,
4,096-token reviewer output, one attempt per turn, and early structural stop.
It requires a new clean source commit, fresh migrated disposable database and
new output path. This is not permission to reroll any earlier committed turn,
modify the scorer midrun, or run the original 30-cell comparison.
The [follow-up finding](../../../docs/findings/natural-memory-factual-followup-2026-09-24.md)
records five commits and one stopped turn: the evening addition and recall
worked, a separate setup lost morning scope, uncertain tea deferred, and the
habit reviewer truncated at 4,096 output tokens. Two scheduled probes were
unrun. No midrun repair or reroll was made.

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
