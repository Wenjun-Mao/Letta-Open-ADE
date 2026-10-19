# Architecture Decision Index

Stage-1 index reconciliation: 2026-10-19. Start with the [product contract](../product-contract.md)
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
| [0019](0019-ade-steady-state-runtime.md) | Current incumbent stack; release details amended by 0027; planned Hindsight data-authority split under 0068. |
| [0020](0020-luna-character-development-workflow.md) | Retained development workflow, not the primary provider or qualified backend. |
| [0022](0022-incumbent-memory-first-product-slice.md) | Historical incumbent slice; Hindsight adoption and character-local learned-memory ownership supersede its default and subject-wide sharing direction under 0068. |
| [0023](0023-agent-studio-intent-and-async-ownership.md) | Partial: async ownership and immutable-version guards; phrase intent selector removed by 0035. |
| [0025](0025-deepseek-development-lane.md) | Partial: provider integration retained; development-only scope extended by 0027, old smoke caps historical. |
| [0026](0026-memory-removal-reply-boundary.md) | Truthful capability/commit claims remain; manual removal is deferred for the first Hindsight integration under 0068. |
| [0027](0027-provider-neutral-release-and-embedding-space.md) | Current selected-route release and stable embedding-space contract; qualification pending. |
| [0029](0029-natural-memory-bounded-contract.md) | Partial: lifecycle and atomic generation guards; reviewer/accounting replaced by 0035. |
| [0030](0030-pending-lease-database-clock.md) | Current: database-clock lease expiry. |
| [0035](0035-compact-natural-review-and-observational-dispatch.md) | Incumbent reviewer boundary and observational counting; native reviewer/atomic-Memory requirements replaced for the planned Hindsight path under 0068. |
| [0036](0036-discretionary-curated-tools-and-structured-requirements.md) | Current discretionary tools and explicit structured requirements. |
| [0037](0037-current-product-contract.md) | Current documentation authority and agreement maintenance. |
| [0038](0038-bounded-history-probe-source-contract.md) | Isolated historical-recall probe source and snapshot contract; no production selection. |
| [0043](0043-reviewer-target-attribution-before-mutation.md) | Bounded reviewer target-attribution correction; no general semantic acceptance. |
| [0044](0044-native-generation-memory-contract-candidate.md) | Explicit chat candidate and shared generation instruction alignment; no default adoption. |
| [0045](0045-isolated-history-trial-composition.md) | Running development-only browser trial composition; no release qualification. |
| [0046](0046-current-turn-weighted-history-trial-ranking.md) | Versioned ranking selected for the isolated trial; no production/default qualification. |
| [0047](0047-recalled-dialogue-attribution.md) | Shared generation source fidelity and grounded H-speaker conflicts; no general answer verifier or live acceptance. |
| [0048](0048-mainline-development.md) | Main is the ongoing development baseline; source integration is not deployment or release qualification. |
| [0049](0049-portable-offline-evidence-checks.md) | Portable synthetic mechanics checks remain separate from exact private historical replay and release evidence. |
| [0050](0050-consistent-improvised-character-history.md) | Accepted product intent: consistent improvised solo episodes are scoped to each user-character relationship, with common authored biography; implementation remains open. |
| [0051](0051-evaluation-immutable-definition-versions.md) | Evaluation-owned immutable next versions through the gated history-trial API; no live qualification. |
| [0052](0052-isolated-story-probe-deployment-binding.md) | Source-backed isolated story-probe deployment configuration, with computed fingerprints and no inherited qualification. |
| [0053](0053-private-evaluation-observations.md) | Versioned private full-state and bounded history-omission observations; required for PC-11 evidence, not a public API or live qualification. |
| [0054](0054-bounded-native-story-probe.md) | Separate approved native PC-11 runner: clean source, owned services, immutable one-attempt receipts and human annotation frontiers. |
| [0055](0055-nonblind-packet-sufficiency-diagnostic.md) | Existing exposed-context Pro reports may support a bounded non-blind offline diagnostic, not blind or runtime qualification. |
| [0056](0056-matched-correction-dependency-measurement.md) | Pre-outcome matched correction pairs with explicit non-blind author labels and single-dialogue topology; unchanged selectors and no runtime adoption. |
| [0057](0057-model-assisted-evidence-selection-investigation.md) | Agreed investigation design: bounded semantic source selection, fresh shared final evidence and uncertain incomplete recall; no implementation, model run or adoption. |
| [0058](0058-offline-packet-capacity-and-qualifications.md) | Approved D04-only eight-source offline capacity diagnostic and whole-packet qualification rubric; no runtime count change or provider calls. |
| [0061](0061-capability-responsibility-map.md) | Domain/Subsystem/Module inventory, authored-characterization versus contextual-application boundary, and repeatable case/run/review assessment with three overlapping lenses; no new runtime phases or release qualification. |
| [0062](0062-self-hosted-hindsight.md) | Self-hosting and historical isolated OCI campaign direction; adoption-deferred status superseded by 0068, with integration/cutover still separate. |
| [0063](0063-hindsight-character-evaluation-boundary.md) | Evaluation-only CLI owns strict scoped recall, frozen Character comparison arms and fail-closed durable captures; workflow owns ingestion/curation and qualification, with incumbent execution unchanged. |
| [0064](0064-isolated-hindsight-infrastructure.md) | Offline isolated deployment, fail-closed actual-wire observation, detached deadline/safety guard, release-scoped P4 restart evidence and terminal process receipts; OCI/image/semantic qualification remains pending. |
| [0065](0065-post-restore-snapshot-failure-recovery.md) | Registered child exit-mm handling and a separate, finite, exact-resource recovery path for the failed P4 post-restore snapshot; captured state remains failed evidence, not restore success. |
| [0066](0066-canonical-persisted-schema-snapshots.md) | Shared P4 schema capture excludes only numeric PostgreSQL temporary namespaces; durable schema, owner, extension, migration and data drift remain exact mismatches. |
| [0067](0067-hindsight-revision-five-activation-clock.md) | Revision-5 source-pinned clock and activation-scoped registry/capture paths; old admissions and receipts are never renewed, and tests use a declared synthetic clock. |
| [0068](0068-hindsight-default-memory.md) | Hindsight default, character-local ownership, fresh scope and separate data authorities; scoped development flow observed, no production transition or general quality acceptance. |
| [0069](0069-offline-character-assessment-kit.md) | Immutable Mandarin case/run/review kit; the Stage-1 collector adds six mechanically complete captures, not a human-calibrated quality baseline. |
| [0070](0070-hindsight-message-delivery.md) | Immutable per-message identities, attributed antecedents and native reconciliation/retry; scoped native and ADE observations, not general semantic qualification. |
| [0071](0071-private-wire-observations-and-activation-leases.md) | Actual final-send capture and finite owned leases with permanent closure; isolated checks are not deployment authority. |
| [0072](0072-hindsight-outbox-and-saved-input-retry.md) | Atomic ADE source/outbox intent, independent delivery and saved-input pause/Retry, with application-role SQL and representative product proof. |
| [0073](0073-hindsight-reply-runtime.md) | Required scoped recall and the normal Character reply path replace native reviewer/fact obligations. |
| [0074](0074-relationship-memory-inspection.md) | Authorized relationship inspection and fallible Memory reads independent of chat/run loading. |
| [0075](0075-product-memory-and-request-observations.md) | Exact committed-source, recall, component and actual Character-request joins; private capture is not semantic acceptance. |
| [0076](0076-isolated-product-actor-and-provenance.md) | Product-established synthetic history and source-bound six-slot actor, isolated from incumbent services. |
| [0077](0077-database-wall-clock-lease-fences.md) | Wall-clock ownership checks and final release fencing reject expired blocked finalizers. |
| [0078](0078-candidate-authoring-asset-seed.md) | Candidate-private authored-asset copies preserve source/image ownership without modifying incumbent content. |
| [0079](0079-cpu-bounded-http-health-probe.md) | Bounded readiness uses a cheap same-timeout HTTP probe instead of expensive imports. |
| [0080](0080-native-processing-pagination.md) | Native operation pagination respects the pinned API limit and rejects incomplete readbacks. |
| [0081](0081-owned-safety-observation-controllers.md) | Eight representative owned-stack safety cases and source-bound checkpoint controls; failures remain retained. |
| [0082](0082-candidate-web-authoring-role.md) | Private trusted authoring web uses the required admin role without exposing credentials or weakening API roles. |
| [0083](0083-stopped-health-and-checkpoint-recovery.md) | Live health is state-aware; closed-point recovery uses verified read-only originals and new database copies, not a reopened lease or restore qualification. |
| [0084](0084-workflow-local-configuration.md) | Workflow defaults stay local; explicit bound credentials replace process-global dotenv side effects. |
| [0085](0085-revision-bound-historical-architecture.md) | Native architecture maps remain visibly historical and validate exact recorded source, separately from today's Hindsight guide. |
| [0086](0086-stage1-review-repair-contracts.md) | Lookup database outages pause saved input; compaction/composition preserve complete dialogue; versioned serial tool capture binds exact per-call native rows. |

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
