# Architecture Decision Index

Lifecycle review: 2026-09-25. Start with the [product contract](../product-contract.md)
for current product intent and [system status](../architecture/system-status.md)
for the stack. This index locates rationale; it does not create another contract.
Accepted design is not proof of implementation, behavioral acceptance, or release qualification.

## Current And Partially Superseded

"Partial" means the named surviving principle remains applicable; read the linked
record's status notice before applying its original execution details.

| ADR | Status and current scope |
| --- | --- |
| [0001](0001-local-only-access-boundary.md) | Current: local-only access boundary. |
| [0002](0002-router-transparent-retry-policy.md) | Current: one retry owner, transparent router. |
| [0003](0003-persona-source-and-runtime-storage.md) | Current persona-source/projection decision; SQLite here is not the native agent state store. |
| [0004](0004-frontend-same-origin-api-proxy.md) | Current: same-origin web proxy. |
| [0005](0005-incremental-feature-modularization.md) | Partial: modularization principles; repository rollout replaced by 0006. |
| [0006](0006-comprehension-first-service-and-feature-architecture.md) | Current: service/feature ownership and comprehension. |
| [0008](0008-test-center-evaluation-read-models.md) | Current: Test Center owns evaluation read models. |
| [0009](0009-ade-owned-agent-runtime.md) | Partial: ADE-owned foundation; stack, release, and reviewer details follow 0019/0027/0035. |
| [0010](0010-production-path-runtime-qualification.md) | Partial: production-path evidence; release route rules follow 0027. |
| [0011](0011-agent-runtime-operational-readiness.md) | Current: worker readiness and causal failure evidence. |
| [0012](0012-content-addressed-behavior-evaluation-decisions.md) | Current: content-addressed evaluation decisions. |
| [0014](0014-curated-tool-invocation-and-external-source-authority.md) | Partial: tool validation and source authority; phrase inference removed by 0036. |
| [0015](0015-model-scoped-tool-call-thinking-mode.md) | Current: model-scoped thinking policy; not a universal forced-tool guarantee. |
| [0018](0018-evaluation-cleanup-must-prove-absence.md) | Current: verified evaluation cleanup. |
| [0019](0019-ade-steady-state-runtime.md) | Current single native stack; release details amended by 0027. |
| [0020](0020-luna-character-development-workflow.md) | Retained development workflow, not the primary provider or qualified backend. |
| [0022](0022-incumbent-memory-first-product-slice.md) | Partial: ADE memory retained, external comparison deferred, shared subjects; later provider/removal contracts apply. |
| [0023](0023-agent-studio-intent-and-async-ownership.md) | Partial: async ownership and immutable-version guards; phrase intent selector removed by 0035. |
| [0025](0025-deepseek-development-lane.md) | Partial: provider integration retained; development-only scope extended by 0027, old smoke caps historical. |
| [0026](0026-memory-removal-reply-boundary.md) | Current: truthful capability/commit claims, not conversational privacy-policy enforcement. |
| [0027](0027-provider-neutral-release-and-embedding-space.md) | Current selected-route release and stable embedding-space contract; qualification pending. |
| [0029](0029-natural-memory-bounded-contract.md) | Partial: lifecycle and atomic generation guards; reviewer/accounting replaced by 0035. |
| [0030](0030-pending-lease-database-clock.md) | Current: database-clock lease expiry. |
| [0035](0035-compact-natural-review-and-observational-dispatch.md) | Current amended reviewer boundary and observational counting; no release qualification implied. |
| [0036](0036-discretionary-curated-tools-and-structured-requirements.md) | Current discretionary tools and explicit structured requirements. |
| [0037](0037-current-product-contract.md) | Current documentation authority and agreement maintenance. |

## Historical, Retired, Or On Hold

| ADR | Disposition |
| --- | --- |
| [0007](0007-router-authority-for-router-backed-models.md) | Superseded by 0019: no Letta handles/catalog dependency. |
| [0013](0013-narrow-native-runtime-product-pilot.md) | Completed pilot; separate native deployment retired by 0019. |
| [0016](0016-ade-native-agent-studio-cutover.md) | Completed cutover; transitional rollback retired by 0019. |
| [0017](0017-incumbent-baseline-does-not-veto-native-cutover.md) | Retired incumbent/Letta cutover gate under 0019. |
| [0021](0021-evidence-scoped-memory-and-affirmative-tools.md) | Semantic/tool phrase heuristics superseded by 0035/0036. |
| [0024](0024-local-luna-agent-backend-feasibility.md) | Investigation on hold, not a rejection of every future Luna integration. |
| [0028](0028-agent-runtime-qualification-request-ledger.md) | Spend enforcement retired; observational counters under 0035. |
| [0031](0031-natural-memory-evaluation-capacity.md) | Historical single-campaign capacity, not a production default. |
| [0032](0032-natural-reviewer-subject-binding-and-scope.md) | Historical diagnostic; interface replaced by 0035. |
| [0033](0033-natural-reviewer-output-diagnostic.md) | Historical bounded diagnostic, not standing run authority. |
| [0034](0034-natural-reviewer-current-user-authority.md) | Historical diagnostic; authority interface replaced by 0035. |

## Maintenance

When an approved decision replaces earlier behavior, update the old record's
status with a successor link and identify any surviving scope. Update this index
and the product contract in the same checkpoint when applicable. Preserve original
reasoning and evidence; do not silently rewrite old experiments as current policy.
Completed plans and paused investigations are not automatically superseded designs.
Keep historical paths stable rather than moving files merely to hide them.
