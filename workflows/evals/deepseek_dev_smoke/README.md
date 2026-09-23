# Synthetic DeepSeek development probes

`probe.py` starts a loopback Model Router with the checked-in DeepSeek
source and exact-model allowlist. It reads `DEEPSEEK_API_KEY` and
`DEEPSEEK_API_BASE` from `--env-file`; `bind` also reads the Spark host and
optional embedding key. It never prints credentials. Modes `tool`,
`reviewer`, `comment`, `label`, and `bind` each use only synthetic inputs. Tool mode
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
This workflow does not write memory facts, touch the release ledger, or qualify
the provider. It is not a background monitor or an automated test-suite step.
