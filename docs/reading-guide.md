# ADE Maintainer Reading Guide

Read these pages in order when joining the project:

Start with the [current product contract](product-contract.md) for settled
behavior, exclusions, and genuinely open decisions. Plans and product reviews
reference its PC IDs; historical design documents are not competing current rules.

For delivery priorities, consult the [roadmap](product-roadmap.md) and
[project tracker](project-tracker.md) before choosing work.

1. [System status](architecture/system-status.md) for the current authority.
2. [Architecture overview](architecture/overview.md) for service and data boundaries.
3. [Request flows](architecture/request-flows.md) for a product request end to end.
4. [Codebase map](codebase-map.md) to find the owner of a change.
5. The local README for the feature or workflow you will change.

Keep this model in mind:

- `apps/ade-web` owns browser behavior and the same-origin proxy.
- `services/ade-api` owns product APIs and the native Agent Studio runtime.
- `services/model-router` owns provider protocols and canonical model identities.
- PostgreSQL owns persistent runtime state.
- `content/` is reviewed product material; `workflows/` is executable evaluation
  and operational work.

When a change crosses a boundary, start with the owning feature README. Do not
create compatibility aliases, duplicate product paths, or generic shared folders
to avoid deciding ownership.

Historical ADRs and the replacement study explain why the current runtime was
chosen. They are provenance, not onboarding instructions. Use the
[decision lifecycle index](adr/README.md) to distinguish current, partially
superseded, retired, and paused decisions. Start with
[ADR 0019](adr/0019-ade-steady-state-runtime.md) for the stack and
[ADR 0027](adr/0027-provider-neutral-release-and-embedding-space.md) for release policy.
