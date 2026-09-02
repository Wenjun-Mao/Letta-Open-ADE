# Agent Runtime Eval Contracts

This buildable package owns the runtime-neutral fixture, observation, scoring,
deployment-fingerprint, and qualification contracts shared by the historical
architecture study and the production-path v3 acceptance workflow.

It intentionally contains no ADE API, provider, database, or workflow adapter.
Each workflow translates its own evidence into these stable types, which keeps
the canonical cases and deterministic pass/fail rules identical without coupling
one runner to another.

`summary_through_sequence` describes the synthetic summary seeded by the
in-memory architecture-study world. Production-path workflows must instead prove
that the runtime emitted a valid, versioned, contiguous summary commitment and
preserved immutable raw history. They must not require a live token-dependent
compaction plan to land on the study world's synthetic sequence boundary.

```bash
uv run pytest packages/agent-runtime-eval-contracts/tests -q
```
