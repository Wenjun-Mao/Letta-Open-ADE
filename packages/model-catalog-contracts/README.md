# Model Catalog Contracts

## Purpose

This package contains the small, stable data contract shared by model discovery
and provider-probe workflows. It currently resolves checked-in allowlist report
locations and validates report metadata. It is not a general ADE utility package.

## Boundaries

- Owns only versioned, cross-service model-catalog artifact contracts.
- Has no network, FastAPI, provider SDK, ADE API, or UI dependency.
- Must not accumulate feature helpers. A type belongs here only when at least two
  independently deployed or operator-run components need the same stable contract.

## Source And Tests

- Source: `src/model_catalog_contracts/`
- Tests: `tests/`
- Checked-in reports: `content/model-catalog/`

```bash
uv run python -m pytest packages/model-catalog-contracts/tests -q
uv run ruff check packages/model-catalog-contracts
```
