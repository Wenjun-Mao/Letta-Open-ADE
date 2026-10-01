# Offline Character Story Continuity

PC-11 preparation under PC-01/03/04/05/06/09/10 and ADR 0050. This directory is
the new workflow entrypoint; historical schedules, fixtures and hash gates are
unchanged. **All three readiness repairs are implemented offline.** The separate
[bounded native entrypoint](NATIVE.md) implements the subsequently approved live
probe; offline `prepare` and `OfflineADE` remain network-free. Scripted replies
and vectors prove mechanics, not model quality. Native assessment requires fresh
source/definition/catalog receipts and actual outcomes; offline-ready does not
mean live-qualified.

## Offline Retrieval Pressure Follow-Up

The [post-native diagnostic](../../../../docs/findings/natural-memory-consultation/character-story-retrieval-pressure-2026-09-30.md)
adds runtime-owned synthetic controls for faithful versus misleading echoes and
omitted corrections. Run without a database or providers:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime/test_story_retrieval_pressure.py -q
```

These tests deliberately expose unchanged selection limitations. Passing them
does not mean the limitation is fixed, prove model quality or reopen the native
probe. No ranking, admission, prompt, fixture or historical gate is changed.

The separate [source-diversity experiment](retrieval_diversity/README.md) now
compares a non-oracle novelty candidate with lexical top-four selection. Its
[findings](../../../../docs/findings/natural-memory-consultation/character-story-source-diversity-2026-09-30.md)
show better labeled evidence coverage but more unrelated admissions. The candidate
is evaluation-only and **not adopted**; passing its tests preserves that observed
tradeoff, not a claim of native quality or a completed retrieval fix.

The subsequent [review assessment](../../../../docs/findings/natural-memory-consultation/character-story-retrieval-review-assessment-2026-09-30.md)
shows that all five apparent coverage gains occur with only four distinct text
pairs for four slots. Source-group requirements also exceed demonstrated answer
needs in some cases. Keep the frozen scorecard; do not infer a general novelty
benefit or launch another selector before establishing query-relative sufficiency.

The [packet-sufficiency diagnostic](packet_sufficiency/READOUT.md) is complete
under the user's non-blind amendment after clean-session review proved unavailable.
Frozen Pro judgments precede new-control selection. The candidate recovers opposed
evidence in a varied-retelling case but fails the new antecedent case; all 68
packets fit unchanged limits. It remains unadopted. No native model quality or
successful blind audit is claimed, and that result did not authorize another probe.

The user separately approved the [matched correction-dependency measurement](correction_dependencies/READOUT.md).
Its six fresh cases and pre-selection author labels remain explicitly non-blind.
All 63 packets fit. The baseline loses the named referent in three matched pairs;
the novelty candidate does so in two, despite admitting each correction. This
supports a bounded design proposal, not selector adoption, a completed retrieval
fix or reopening native work. The workflow and exact reproduction commands are
in [correction_dependencies](correction_dependencies/README.md).

## Entrypoint And Freeze

From the retained primary checkout on `main`:

```sh
uv run --locked python -m workflows.evals.character_memory_dev.story_continuity prepare
uv run --locked python -m pytest workflows/evals/character_memory_dev/story_continuity/tests -q
```

The command only prints JSON. It takes no URL, credentials, database, environment
file or live flag, imports no runtime internals, and performs no network work.
`OfflineADE` accepts only injected in-process HTTP test transports; it has no
socket client fallback. Runtime tests own their explicit fake RouterTransport,
including catalog, chat and embeddings. No retained container is contacted.

`fixtures.json` is byte-frozen by `FIXTURE_SHA256` in `schedule.py`. Its ten prompts
are the exact proposed native ceiling, not ten authorized dispatches. Turn 4 alone
has a replacement-suggestion slot. All recall questions are fixed and receive no
diagnostic answers. A separate authorization must freeze actual model routes,
settings, source/definition identities and request envelope before any live run.

Preparation hashes the actual `.py` chat templates (including
`chat_v20260926.py`), persona seed, runtime source (including reviewer instructions,
Pydantic schema, ranking, policy and capacity), deployment manifest and workflow.
It checks required effective-input files exist. These hashes bind present source
bytes, including uncommitted changes; they do **not** assert that future immutable
database definitions already exist or that a running catalog matches these bytes.
No historical release fingerprint is rebound. The separate
`governed_source_fingerprint_v2` comes from `scripts/source_fingerprint.py` via
the current Python executable, covering tracked and unignored dirty governed
router/shared-parser/platform/migration source. `model_profiles_sha256` explicitly
binds `config/model-router/model-profiles.json`. These are source/configuration
hashes, not proof of a running router's effective settings. `prepare` reports
`offline_ready_live_approval_required` with provider dispatch unavailable.

## Human Rubric

Read the matched Mandarin controls with the same authored biography. Judge
meaning in context, not keywords, similarity scores, or whether a reviewer said
yes. The scripted fixture deliberately contains both correct and incorrect replies.

| Dimension | Record separately |
| --- | --- |
| Establishment | Concrete delivered solo-past assertion, explicit imagination, joke/metaphor, ambiguous, or no usable episode. A failed candidate establishes nothing. |
| Core continuity | Actual origin claims preserved, compatible elaboration, positive contradiction, or insufficient evidence. A present preference change need not contradict a past episode. |
| Disclosure | Newly revealed detail versus a supported or false claim of having told it earlier. |
| Correction | Identify the mistaken retelling and the retained earlier source/unchanged biography supporting correction; unsupported suggestions do not rewrite history. |
| Ownership | Character-only experience, faithful user-history recall, actual shared interaction, or invented user participation. |
| Naturalness | Warm/useful response, unnecessary refusal, mechanical policy lecture, gratuitous repetition, or awkward recall. No mandatory anecdote. |
| Evidence path | Corpus eligibility, selection, admission and omissions, faithful use, exact reviewer decision, terminal outcome, full persisted effects. |

Each judgment needs quoted evidence and a rationale; use `not_assessed` when
evidence is missing. Do not collapse semantic failure into structural success.
Faithful user-history recall and warm nonhistorical expression are positive
controls. All pure-story controls expect zero user-fact changes, but that alone
cannot prove safe memory behavior.

After turn 1 and before observing turn 2, annotate actual core details with exact
quotes, the establishment rationale and one replacement suggestion. After turn 3
and before turn 4, annotate an actual compatible new detail if one exists.
`freeze_annotation` binds the delivered reply/run and observation frontier;
`check_annotation` requires the previously frozen hash. This is an operator
chronology contract, not cryptographic proof of when a person read an outcome.
Annotations remain evaluator-side. No hardcoded expected native anecdote exists.
Without a committed usable origin, turns 3-10 are dependency-unassessable; turn 2
can still run. Without a usable turn-3 detail, turn 8 is unassessable. No rerolls.

Turn 7 archives **both** origin and callback chats before the new version/chat.
Its capture must admit the archived prior-version origin, not merely an
unarchived intermediate echo. No restore is performed. Combined archive/version
failure needs localization rather than assigning blame to one condition.

## Evidence And Ownership

`evidence.py` validates capture-v1 bytes plus the required versioned private
observations extension (ADR 0053), independent message readback,
terminal state, source hashes/roles, chronology and subject/root/workspace/purpose
scope. Rejected runs still have every available packet checked for structural
leakage. Early failures with no exposed packets remain unassessable. Missing,
stale, corrupt or truncated evidence stops assessment, never becomes a pass.
Historical capture consumers remain unchanged; old capture-v1 packets lacking
the extension are not enough for this workflow.

Public `SubjectMemoriesResponse` includes facts, fact-associated entity projection,
all nested revisions/source links and generation. It does **not** expose orphan
entities. Public equality is therefore insufficient. Runtime capture now reads
all persisted facts, entities, revisions, source links, predecessor edges and
generation before/after, independently of reviewer proposals. Before-state shares
the accepted-generation RR snapshot with history; after-state shares a separate
post-finalization RR snapshot with terminal receipts. Run/attempt/scope/definition/
policy/generation binding, snapshot and extension SHA-256 seals and bounded
same-subject run activity checks reject stale/concurrent evidence. The story test
compares both captured payloads against its independent SQL helper and retains
an orphan sentinel throughout the turns, invisible to the public projection.

`observations.py` requires complete state and equal before/after payloads for
pure stories and failed candidates. Missing tables/rows, generation drift,
overlapping activity or unavailable observation stops qualification, regardless
of run success. The existing isolated loopback/evaluation/development capture
gate remains. Disabled capture adds no SQL/provider dispatch. Each snapshot allows
512 rows per component and 600 KB; the complete private artifact stays under 2 MB.
Bound/error results are truncated/unavailable, not weakened complete snapshots.
Observation failure never rewrites authoritative runtime outcomes.

History coverage names the unchanged `scoped_completed_pairs` reader universe.
It records content/annotation omissions, the one known reader-capacity overflow
sentinel and the original `capacity_at_least` lower bound. Selection identifies
top-k, packet capacity, selector-not-selected and pre-exposure purges. Empty arms
are not-read; unavailable or truncated inventories stop PC-11 qualification.
Every known successful same-scope prior source must appear in the inventory with
an admission/omission reason. Foreign-scope and unsuccessful known ledger entries
are exclusions, not permission to query other users. No public history API,
ranking/prompt change or new memory schema is involved.

The runtime-owned integration test uses real ADE HTTP handlers, full unchanged
Xiaotang template/persona, worker, reviewer validation, captures, ranker and commit
path. Exact fixture vectors deliberately prioritize origin/detail documents;
this is a scripted admission control, **not retrieval-quality evidence**. A second
sequence returns invalid review output for the origin and verifies no committed
assistant history, no full persistence change, and dependent unassessable outcomes.

## Offline Readiness And Live Prerequisites

All three readiness items are resolved offline:

1. **Version provisioning (resolved, ADR 0051):** `OfflineADE.create_version` uses
   `POST /api/v3/history-trial/definitions/{root_id}/versions` with the generic
   definition request and required positive `expected_current_version`. The
   root/key must match an evaluation root in the active workspace; trial pins
   and capacity guards remain strict. The prior/current version must also pass
   the trial binding under workspace/root locks; an unrelated evaluation root
   cannot be converted into Xiaotang. The returned immutable version ID is bound
   through session HTTP. Turn 7 no longer calls a repository to create version 2.
   Session-created definitions still start at version 1. This proves lifecycle
   mechanics only, not native story quality.
2. **Catalog identity (resolved offline, ADR 0052):** workflow-local
   `deployment-manifest.json` binds the complete historical Qwen payload at
   `c549d7dc...` and current DeepSeek payload at `870ff4fb...`. The shared parser
   computes both hashes; the fake no longer overwrites any digest. Both entries
   are unqualified candidates with zero observed rounds. `sources.json` freezes
   only their adapters/endpoints, without endpoint environment overrides.
   `baseline.validate_catalog` rejects drift, missing or ambiguous routes and
   any substitution of the main manifest's newer `0f16a45a...` deployment.
   The shared vector-space ID is not deployment identity. `prepare` includes
   these files' hashes and source provenance as expected configuration, not a
   live catalog receipt. Runtime guards and retained trial configuration are
   unchanged. Before a separately approved native run, an isolated router must
   explicitly use these two files via its existing source/manifest settings;
   verify its actual catalog with this validator. Do not start `trial-stack.sh`
   against the retained human trial to prepare this new experiment.
3. **Full observation (resolved offline, ADR 0053):** runtime-owned capture-v1 now
   carries `private_observations` with contract
   `ade-private-evaluation-observations-v1`. Complete independent state and bounded
   omission coverage are mandatory PC-11 evidence, not unresolved native blockers
   or optional reviewer-approved substitutes. Integration uses the actual private
   capture with public messages and a prior-source ledger; no workflow DB import.

Native approval must still bind actual source/configuration, fresh owned database,
immutable definitions, observed catalog/settings and chronological human
annotations. Missing observations must never be inferred from reviewer approval
or scripted success. No live dispatch or deployment occurred during readiness.
Capture files belong in the existing ignored `../outputs/` area for any future
approved run; this test uses pytest temporary directories only.

## Disposable Database Verification

Use the parent workflow's documented fresh PostgreSQL/pgvector setup. The new
test rejects all but passwordless loopback `ade_owner` databases named
`ade_history_test_<hex>`. It requires an idle, exclusively owned, migrated DB;
never point it at a retained trial or production instance.

```sh
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:PORT/ade_history_test_HEX \
  uv run --locked python -m pytest \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py -q
```

Without that variable the two integration cases explicitly skip. With it they
exercise ten scripted turns and a rejected-origin/two-attempted-turn sequence.
Existing history worker tests should run before reader tests because reader
fixtures intentionally leave pending rows. Cleanup only the newly created test
container/databases. Offline success does not qualify PC-11 or authorize delivery 3.

### Initial Offline Verification (Historical Checkpoint)

Retained checkout `/Users/wjmao/projects/HU/Letta-Open-ADE`, `main`, source HEAD
`90b72b435f2d54af00c3c44d413518a628ee94aa`. The original four consultation report
hashes still match the assessment. Ruff check and format check pass on all new
Python files. `prepare` returns `prepared_not_native_ready` with dispatch unavailable.

Exact final verification commands, from that checkout:

```sh
uv run --locked python -m pytest workflows/evals/character_memory_dev/story_continuity/tests workflows/evals/character_memory_dev/tests/test_attribution_contract.py workflows/evals/character_memory_dev/tests/test_fresh_conversation_generalization.py services/ade-api/tests/agent_runtime/test_history_admission.py -q
# 63 passed: 33 new portable checks plus 30 existing checks.

ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32769/ade_history_test_01a0f268b uv run --locked python -m pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py services/ade-api/tests/agent_runtime/persistence/test_postgres_history_worker.py -q
# 18 passed: 2 new full sequences plus 16 existing worker checks; no DB skips.

ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32769/ade_history_test_01a0f268b uv run --locked python -m pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_history_reader.py services/ade-api/tests/agent_runtime/persistence/test_postgres_history_lineage.py services/ade-api/tests/agent_runtime/persistence/test_postgres_history_guard.py -q
# 8 passed; no DB skips.

env -u ADE_TEST_DATABASE_URL uv run --locked python -m pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py -q
# 2 explicit skips without database configuration, not qualification evidence.
```

The database ran in the newly created `ade-pc11-offline-01a0f268` container using
`pgvector/pgvector:0.8.1-pg15`, loopback-only port 32769, `ade_owner`, trust auth.
Both fresh test databases were migrated with the repository Alembic head; the
second database separated final worker checks from pending reader fixtures in
the first. The disposable container is removed after verification. No retained
trial data, provider connection, deployment, commit or push was used.

### Readiness Item 1 Verification (2026-09-30)

ADR 0051 adds supported version creation only. Exact commands in the retained
primary checkout, with fake router responses only:

```sh
uv run --locked pytest services/ade-api/tests/agent_runtime/test_history_trial.py workflows/evals/character_memory_dev/story_continuity/tests workflows/evals/character_memory_dev/tests/test_attribution_contract.py workflows/evals/character_memory_dev/tests/test_fresh_conversation_generalization.py services/ade-api/tests/agent_runtime/test_history_admission.py -q
# 68 passed; one existing Starlette/httpx deprecation warning.
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32770/ade_history_test_01a0f2a4 uv run --locked pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py services/ade-api/tests/agent_runtime/persistence/test_postgres_history_worker.py -q
# 18 passed, no skips. Turn 7 uses public HTTP, including version-contract checks.
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32770/ade_history_test_01a0f2a4 uv run --locked pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_history_reader.py services/ade-api/tests/agent_runtime/persistence/test_postgres_history_lineage.py services/ade-api/tests/agent_runtime/persistence/test_postgres_history_guard.py -q
# 8 passed, no skips.
env -u ADE_TEST_DATABASE_URL uv run --locked pytest services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py -q
# 2 explicit database skips.
```

Fresh container `ade-pc11-versions-01a0f2a4` used
`pgvector/pgvector:0.8.1-pg15`, passwordless loopback-only port 32770, and the
repository migration head (`uv run --locked --project services/ade-api alembic
-c services/ade-api/alembic.ini upgrade head`, with `ADE_DATABASE_MIGRATION_URL`
set to the disposable URL above). It was removed after verification. Ruff check
and format check passed for the eight changed Python files. The story suite also
rejects unrelated evaluation persona/policy roots without inserting a version or
advancing their pointers. No retained service
or database was used. That checkpoint covered item 1 only; items 2-3 are now
implemented as described above, without changing its historical results.

### Readiness Items 2-3 Final Verification (2026-09-30)

Primary `main` checkout, no commit/push/deploy/provider or retained-trial access.
The scripted story sequence exercises the parsed ADR 0052 catalog and ADR 0051
HTTP version-2 path together with required ADR 0053 observations. Native semantic
quality and future deployment/catalog receipts remain unmeasured.

Final portable command (190 passed, 3 explicit historical-private-evidence skips):

```sh
uv run --locked python -m pytest \
  workflows/evals/character_memory_dev/story_continuity/tests \
  workflows/evals/character_memory_dev/tests/test_attribution_contract.py \
  workflows/evals/character_memory_dev/tests/test_fresh_conversation_generalization.py \
  services/ade-api/tests/agent_runtime/test_natural_attempt_evidence.py \
  services/ade-api/tests/agent_runtime/test_history_admission.py \
  services/ade-api/tests/agent_runtime/test_history_capacity.py \
  services/ade-api/tests/agent_runtime/test_history_h4_remaining.py \
  services/ade-api/tests/agent_runtime/test_history_native_rank.py \
  services/ade-api/tests/agent_runtime/test_history_observations.py \
  services/ade-api/tests/agent_runtime/test_history_ranking_identity.py \
  services/ade-api/tests/agent_runtime/test_history_trial.py \
  services/ade-api/tests/agent_runtime/test_compaction.py \
  services/ade-api/tests/agent_runtime/test_context.py \
  services/ade-api/tests/agent_runtime/test_natural_context.py \
  services/ade-api/tests/agent_runtime/test_provider_tracing.py -q -rs
```

The new workflow alone passes 89 tests. Skips are one absent ignored H2 result
and two absent ignored H4 schedule-evidence checks; no private fixture was read
from a retained service or rebound. One existing Starlette/httpx deprecation
warning remains. Ruff check and format check passed (29 changed/new Python files
in the formatting check); `git diff --check` passed.

Final disposable-PostgreSQL commands (33 + 14 passed, **zero DB skips**):

```sh
ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32771/ade_history_test_01a0f2b3 \
uv run --locked python -m pytest \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_observation_worker.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_history_worker.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_evidence.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_worker.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_worker_fencing.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_compaction_packets.py -q

ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32771/ade_history_test_01a0f2b3 \
uv run --locked python -m pytest \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_evaluation_observations.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_history_reader.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_history_lineage.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_history_guard.py -q

env -u ADE_TEST_DATABASE_URL uv run --locked python -m pytest \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_observation_worker.py \
  services/ade-api/tests/agent_runtime/persistence/test_postgres_evaluation_observations.py -q -rs
# 15 explicit skips without DB configuration, separately verified.
```

New container `ade-pc11-observations-01a0f2b1` used
`pgvector/pgvector:0.8.1-pg15`, loopback port 32771, `ade_owner`, trust auth.
Three new databases (`ade_history_test_01a0f2b1`, `...b2`, `...b3`) separated
iteration/final worker passes from reader fixtures. Each used `CREATE SCHEMA ade;
CREATE EXTENSION IF NOT EXISTS vector;` and repository Alembic head via
`ADE_DATABASE_MIGRATION_URL=... uv run --locked --project services/ade-api alembic
-c services/ade-api/alembic.ini upgrade head`. Only this owned container is
removed after verification; no retained container was touched.

DB coverage includes actual 129-candidate reader overflow, content/annotation
omissions, no extra disabled SQL, before/history same-RR coherence, independent
after visibility and concurrent-activity rejection, full inactive/orphan/lineage
readback, successful user-fact writes, SQL failures at each snapshot, all bounds,
and identical fake-provider dispatches under disabled/failing observations.

### Independent Manager Audit (2026-09-30)

After implementation stopped, the manager independently reviewed all three
contracts, reproduced the historical Qwen payload with the shared manifest parser,
and reran the final source:

```sh
uv run --locked python -m pytest services/ade-api/tests/agent_runtime workflows/evals/character_memory_dev/story_continuity/tests --ignore=services/ade-api/tests/agent_runtime/persistence -q -rs
# 383 passed; 3 historical-evidence skips (one H2, two H4); existing deprecation warning.
git ls-files --modified --others --exclude-standard -z -- '*.py' | xargs -0 uv run --locked ruff format --check
# 34 files formatted; explicit Ruff check of all changed/new Python also passed.
git diff --check
```

Both PostgreSQL command groups immediately above were rerun with
`ADE_TEST_DATABASE_URL=postgresql+psycopg://ade_owner@127.0.0.1:32772/ade_history_test_01a0f2cf`:
**33 + 14 passed, no skips**. The independently created
`ade-pc11-audit-01a0f2cf` container used the same pgvector image, loopback-only
port, schema/extension setup and migration head. It was removed after verification.
`prepare` returns `offline_ready_live_approval_required` with provider dispatch
unavailable. This accepts all three offline repairs, not native behavior or release.
