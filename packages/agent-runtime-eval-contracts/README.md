# Agent Runtime Eval Contracts

This buildable package owns the runtime-neutral fixture, observation, scoring,
deployment-fingerprint, and qualification contracts shared by the historical
architecture study and the production-path v3 acceptance workflow.

It intentionally contains no ADE API, provider, database, or workflow adapter.
Each workflow translates its own evidence into these stable types, which keeps
the canonical cases and deterministic pass/fail rules identical without coupling
one runner to another.

```bash
uv run pytest packages/agent-runtime-eval-contracts/tests -q
```
