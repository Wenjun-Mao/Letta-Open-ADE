# Mainline Integration: 2026-09-30

Status: integrated locally and verified with the audit limitation below;
not deployment or release qualification.

The user requested merging character-continuity work to `main` and staying there.
The primary checkout was clean at `e1395c31032233c0e1bdfdca129b7e9a345fbecf`.
The development branch was 147 commits ahead with no divergence; 43 of those
commits were not yet on its GitHub branch. The consultation draft was committed
as `46402dd`, then `main` was fast-forwarded without conflict. ADR 0048 records
the continuing mainline workflow. Existing trial worktrees/services were retained.

## Clean-Checkout Corrections

- Five changed Python files needed standard Ruff formatting. No behavior change.
- Four H4 checks depended on ignored historical output files. ADR 0049 separates
  portable contract/synthetic schedule tests from optional exact historical
  replay. Missing/corrupt live evidence still fails closed; no artifacts were
  fabricated, copied into the checkout or published.
- A candidate-policy test assumed old hashes were current. It now verifies the
  retained candidates are historical/unqualified and rejected for release.
  Deployment manifests, historical release evidence and frozen fixtures remain
  unchanged; no release rebind or weaker runtime check was introduced.
- Canonical OpenAPI output omitted the existing turn-activity endpoint and its
  four response schemas. The established generators regenerated both language
  artifacts; explicit translation entries cover the new observation terms.

## Verification

`uv run --locked python -m pytest -q -rs`: **780 passed, 63 skipped** in 37.11s.
The skips are 58 disposable-database checks and five private historical-evidence
checks. The existing Starlette/httpx deprecation warning remains. Portable H4
schedule/envelope checks and missing/corrupt evidence guards passed.

Frontend: **85 tests across 24 files passed**; ESLint and the Next.js production
build passed. Python fatal-error lint and changed-file formatting passed (232
Python files checked); AST comparisons confirmed the five formatting-only files
are semantically unchanged. Canonical English OpenAPI checks passed, Chinese
generation reports zero missing translations, Compose configuration validates,
and `git diff --check` passes. Locked dependency installation completed; no
lockfile update was made. Local container builds were not repeated.

No live provider calls, database migration, service rebuild/restart or runtime
adoption is part of this integration. Formatting changes governed source bytes,
so the running trial's earlier source-bound evidence does not qualify the new
mainline tree. The consultation remains pinned to its earlier exact source.

## Open Dependency Audit

`npm audit --audit-level=high` failed against the locked frontend dependencies.
The audit reported 17 affected package entries: seven low, two moderate, seven
high and one critical. The report includes Next.js 16.3.2, sharp, brace-expansion,
js-yaml, and transitive Scalar/Vitest dependencies. This is audit output, not a
confirmed exploitability assessment of ADE; counts may change with advisory data.

Follow-up: review the advisory paths and compatible fixes, update the lockfile
deliberately, and rerun audit/tests/lint/build before treating the dependency gate
as clear. Do not run `npm audit fix --force`, suppress advisories, or call this
integration fully green. GitHub's unchanged frontend audit step may fail until
that separate dependency work is completed. No dependency upgrade is included.
