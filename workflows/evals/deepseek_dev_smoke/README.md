# Synthetic DeepSeek development probes

`probe.py` starts a loopback Model Router with the checked-in DeepSeek
source and exact-model allowlist. It reads `DEEPSEEK_API_KEY` and
`DEEPSEEK_API_BASE` from `--env-file`; `bind` and `native` also read the Spark host and
optional embedding key. It never prints credentials. Modes `tool`,
`reviewer`, `comment`, `label`, `bind`, and `native` each use only synthetic inputs. Tool mode
allows at most two generation requests including its continuation; reviewer
mode allows one and disables repair; each lab mode uses one with zero retries.
Each network request is capped at 180 seconds. A failed mode is not rerun
without separate authorization; record its attempt count in
`docs/findings/deepseek-development-smoke.md`.

From the repository root, after reserving the calls in the findings ledger:

```sh
uv run python workflows/evals/deepseek_dev_smoke/probe.py tool --env-file /absolute/path/to/main/.env
```

The other modes substitute `reviewer`, `comment`, or `label` for `tool`.
`bind` also requires `--database-url` pointing to an already migrated,
passwordless `ade_m2_memory_test_<hex>` database on loopback. It discovers
the authorized Spark embedding sidecar, checks database identity and migration
head, then creates one synthetic Agent Studio subject/conversation with an
immutable DeepSeek conversation/reviewer and Spark retriever binding. It does
not run a turn. The harness uses the Mac-reachable Spark host from the
environment file for read-only discovery; the checked-in source identity and
deployment fingerprint are unchanged.
`native` requires the same isolated database guard. It creates a fresh session
with no tools, accepts one synthetic fact turn through Agent Studio's HTTP API,
runs one real worker attempt, and checks the resulting run and memory through a
separate database connection. Its transport reserves at most two DeepSeek
generation and three Spark embedding requests before network calls; a third
generation or fourth embedding fails before sending. It does not touch the
release ledger or qualify the provider. The mode is not a background monitor
or an automated test-suite step. The authorized initial live budget has been
exhausted; do not run it again without a new explicit budget.

## M3 isolated UI/native acceptance host

`m3_host.py` starts the real ADE HTTP API, worker, and a loopback Model Router
against the same disposable database guard. It is an interactive diagnostic,
not a unit test or release route. Supply an explicit `--ledger` path: its SQLite
reservations are committed before each outbound generation or embedding request,
survive process/browser restarts, and fail closed at the explicit
`--generation-limit`/`--embedding-limit` ceilings (default 24 each, which was
the initial M3 authorization). Reopening a ledger with different limits fails.
Each request is capped at 180 seconds;
the host neither retries nor changes the application reviewer policy. Inspect
`calls` in that ledger before any continuation. Never delete or substitute a
ledger to reset the budget. The M3 run spent 22 generation and 14 embedding
requests; the remaining allowance is not a reason to rerun failed behavior.
The separately authorized post-fix regression used a **new** ledger with
explicit 6/6 limits and spent 4 generation plus 2 embedding requests, leaving
the original ledger frozen. Both are development diagnostics, not release
qualification.

The synthetic browser run used `ADE_API_BASE_URL` pointed at this host and a
separate Next development server. `seed_older_citation.py` is a one-shot,
identity-guarded pagination fixture for the exact synthetic source conversation:
it appends 125 explicitly labeled messages after six native messages so the
original citation falls beyond the latest 120. These rows have no native run
ID and are **not** behavioral evidence. The script refuses a second seed and
does not archive or restore the source. See the
[M3 acceptance finding](../../../docs/findings/m3-native-acceptance-2026-09-23.md)
for the model-call ledger, failed claims, and UI observations.
