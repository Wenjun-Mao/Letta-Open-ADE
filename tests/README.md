# Verification Layout

Tests live beside the behavior they protect whenever a service, package, feature,
or workflow owns that behavior. This root directory retains repository-wide
guardrails and shared live-check configuration.

## Test Homes

- `services/ade-api/tests/features/`: ADE API feature tests.
- `services/ade-api/tests/platform/`: API composition, auth, and OpenAPI tests.
- `services/model-router/tests/`: router catalog, profile, forwarding, and settings tests.
- `packages/model-catalog-contracts/tests/`: stable shared-contract tests.
- `apps/ade-web/src/**/*.test.*`: ADE Web unit and feature tests.
- `workflows/evals/<workflow>/tests/`: eval and provider-probe tests.
- `workflows/smoke/`: deliberate live stack checks.
- `tests/test_codebase_guardrails.py`: repository structure and architecture guardrails.

## Deterministic Checks

```text
uv run python -m pytest
uv run ruff check services packages workflows scripts tests
npm --prefix apps/ade-web run test
npm --prefix apps/ade-web run lint
```

Run a focused area by passing its owned test path to pytest, for example:

```text
uv run python -m pytest services/model-router/tests
uv run python -m pytest services/ade-api/tests/features/comment_lab
uv run python -m pytest workflows/evals/chat_memory_eval/tests
```

## Live Checks

Smoke checks require the Compose stack and model providers. Run them inside the
`ade-api` service through the Makefile so they use Compose-network addresses and
the configured service credentials:

```text
make smoke
make eval-chat-memory
make eval-comment-persona
```

Workflow outputs are run-scoped local artifacts. They are not pytest fixtures and
must stay out of source control.
