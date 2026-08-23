# August 2026 Maintenance Cleanup Record

This record closes the repository simplification work identified by the August
2026 audit. Use [the codebase map](codebase-map.md) for current ownership and
[ADR 0005](adr/0005-incremental-feature-modularization.md) for the rule that
future splits follow behavior boundaries rather than arbitrary line counts.

## Completed Boundaries

- `apps/ade-web/app/agent-studio/page.tsx` is now a composition root. Feature-local
  hooks own agent creation, lifecycle and selection, chat execution, inspection,
  execution traces, and notices. Pure selection, history, creation-settings, and
  tool-catalog rules have focused tests. Request identity, cancellation, and
  model-selection behavior remain explicit.
- Persona persistence is separated into a SQLite store, record mapping, domain
  rules, and transactional seed projection. Seed synchronization preserves
  runtime-only records, rejects duplicate keys, removes only stale managed seed
  records, and rolls back atomically on failure.
- Comment Lab and Label Lab services remain feature orchestrators while local
  request builders and response mappers own provider payloads and diagnostics.
  Retry ownership stays request-scoped in each service; the model router performs
  exactly one upstream attempt.
- Test Center run types are declared by one backend descriptor registry that owns
  accepted fields, command construction, and artifact discovery. The frontend has
  separate launch, view, copy, and artifact-viewer modules.
- Model-router HTTP forwarding, authentication, streaming cleanup, and response
  mapping live in `model_router/forwarding.py`; catalog discovery and profile
  enrichment remain independent.

## Repository Cleanup

- Retired direct-Letta learning scripts, obsolete notebooks, and the bundled
  MemGPT PDF were removed. [Authoritative references](references.md) replace the
  stale copies, and guardrail tests prevent those retired paths from returning.
- The unused notebook dependency group was removed. Python dependencies are
  locked with `uv`, and Letta client/server versions are kept explicit.
- Local Letta now requires `LETTA_ENCRYPTION_KEY`; the Compose contract and manual
  document how to generate it without committing secrets.
- CI verifies Ruff lint and changed-file formatting, Python tests, OpenAPI drift,
  frontend tests, lint, audit and build, Compose rendering, and all first-party
  image builds.
- Container builds use copy-mode `uv` installation, avoiding host-dependent
  hard-link behavior.

## Verification Record

The completed cleanup was validated with the full Python suite, frontend unit
tests, Ruff lint and changed-file formatting, OpenAPI export checks, Chinese
OpenAPI generation, frontend production build, both Compose render modes, all
first-party image builds, API E2E, ADE smoke E2E, and desktop/mobile browser
checks. The rebuilt
OrbStack stack exposes ADE on `3000`, Letta on `8283`, the Agent Platform API on
`8284`, and the model router on `8290`; the backend root and `/static` remain
unserved.

## Deliberate Holds

- Keep the Chinese OpenAPI generator cohesive until a behavior boundary, not its
  line count, justifies extraction.
- Keep formatter-only churn separate from behavioral changes. CI rejects newly
  changed Python files that are not Ruff-formatted without rewriting the older
  formatting baseline inside an unrelated feature diff.
- Stay on ESLint 9 until the Next.js plugin dependency tree declares ESLint 10
  support. Treat the package-manager support notice as an upstream watch item,
  not a reason to bypass peer constraints.
- Track Letta's organization-scoped provider-listing startup warnings separately.
  The local stack is pinned to the tested release, encrypted-secret storage is
  active, and no downstream workaround should hide upstream warnings.

## Future Extraction Triggers

Add another module only when a current owner acquires a second independent
responsibility, a contract needs isolated tests, or a new implementation must be
swappable. A split is complete only when the former owner no longer owns that
behavior; forwarding-only facades and catch-all helper modules are not acceptable
substitutes.
