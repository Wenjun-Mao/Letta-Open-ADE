# ADE Capability Inventory

Generated from [inventory.json](inventory.json); edit that source, not this view.
Reviewed: 2026-10-04. Source baseline: `f98c0ec6c78f1c6b30697fd49fe81a0b1f4a2189`.

Character-memory capabilities, their interfaces and supporting machinery; independent labs are registered as adjacent features. Not a file-by-file audit or deployed-state certification.

Status is implementation scope, not a claim that tests were rerun or behavior was released.
See the [entrypoint](README.md) for status definitions and authority boundaries.

## Character

### CHAR-01: Prompt and persona authoring
Owner: **Character / Persona Definition**. Implementation: **implemented**.
Input: Reviewed character-specific prompt/persona edits. Output: Versioned authored characterization including behavioral tendencies; no model invocation.
Code: [registry.py](../../../services/ade-api/src/ade_api/features/prompt_center/registry.py), [sqlite.py](../../../services/ade-api/src/ade_api/features/prompt_center/personas/sqlite.py), [personas.jsonl](../../../content/personas/personas.jsonl) Tests: [test_content_identity.py](../../../services/ade-api/src/ade_api/features/prompt_center/tests/test_content_identity.py), [test_persona_registry.py](../../../services/ade-api/src/ade_api/features/prompt_center/tests/test_persona_registry.py)
Evidence limit: Content ownership and identity tests exist; characterization quality is a separate judgment.
Known gap: A stored persona is not proof that models enact it consistently; ADE-wide rules are not personality attributes.
Next isolated check: Review coherent, distinguishable authored intent and character-specific contrasts, not a universal agreeable-assistant ideal (PC-12).

### CHAR-02: Immutable definition binding
Owner: **Character / Persona Definition**. Implementation: **implemented**.
Input: Content, deployment/policy snapshot, subject and selected version. Output: Conversation bound to an immutable definition version.
Code: [definition_service.py](../../../services/ade-api/src/ade_api/features/agent_runtime/definition_service.py), [definitions.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/definitions.py), [history_trial_api.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_trial_api.py) Tests: [test_resource_service.py](../../../services/ade-api/tests/agent_runtime/test_resource_service.py), [test_agent_studio_postgres.py](../../../services/ade-api/tests/agent_runtime/persistence/test_agent_studio_postgres.py)
Evidence limit: Definition/conversation mechanics and isolated version journeys are documented; ordinary version changes keep the character root (PC-03/04).
Known gap: Version-binding mechanics do not qualify cross-version story continuity.
Next isolated check: Trace the same character root through two versions with fixed historical evidence.

### CHAR-03: Evidence interpretation
Owner: **Character / Conversation Behavior**. Implementation: **partial**.
Input: Current exchange, bound characterization and actual delivered evidence with scope and qualifications. Output: Situational and evidence interpretation with warranted uncertainty within shared generation; no emitted intermediate or handoff.
Code: [executor.py](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py), [context.py](../../../services/ade-api/src/ade_api/features/agent_runtime/context.py), [history_admission.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_admission.py) Tests: [test_executor.py](../../../services/ade-api/tests/agent_runtime/test_executor.py), [test_story_behavioral_comparison.py](../../../services/ade-api/tests/agent_runtime/test_story_behavioral_comparison.py)
Evidence limit: D04 has bounded supported-answer and appropriate-uncertainty witnesses; no general interpretation certificate. Shares generation with CHAR-04; descriptions distinguish responsibilities, not internal stages (PC-12).
Known gap: Situational references, antecedents, ambiguity and correction qualifications are not generally qualified.
Next isolated check: Verify actual persona/evidence delivery and semantic sufficiency, then describe observable grounding outcomes without claiming an isolated internal failure.

### CHAR-04: Character expression and continuity
Owner: **Character / Conversation Behavior**. Implementation: **partial**.
Input: Authored characterization, current exchange, scoped evidence and ADE-wide requirements within the same generation as CHAR-03. Output: Observable candidate reply: choose an appropriate conversational action and express it in character, including continuity; not a style-only pass.
Code: [executor.py](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py), [personas.jsonl](../../../content/personas/personas.jsonl) Tests: [test_postgres_story_continuity.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_story_continuity.py)
Evidence limit: Shares the generation call with CHAR-03; story probes do not establish broad judgment, naturalness or personality quality. PC-12 clarifies assessment, not implementation or qualification.
Known gap: Character-relative conversational choices, distinct voice, non-repetitive memory use and long-run story continuity remain behavioral work.
Next isolated check: Assess grounding, conversational judgment and character fidelity separately on verified, sufficient inputs; cite persona intention, response passage and context, allowing multiple good or indeterminate outcomes (PC-11/12).

### CHAR-05: Curated tool choice and result use
Owner: **Character / Conversation Behavior**. Implementation: **implemented**.
Input: Available curated tools and model-issued arguments. Output: Validated invocation and actual result fed back to generation.
Code: [executor.py](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py), [tool_policy.py](../../../services/ade-api/src/ade_api/features/agent_runtime/tool_policy.py) Tests: [test_tool_policy.py](../../../services/ade-api/tests/agent_runtime/test_tool_policy.py), [test_executor.py](../../../services/ade-api/tests/agent_runtime/test_executor.py)
Evidence limit: Finite loop and structured tool contracts have tests; memory search remains a Memory capability even when tool-invoked.
Known gap: Discretionary tool choice is not guaranteed by transport conformance.
Next isolated check: Check appropriate invocation and truthful use of failed, empty and successful results.

## Memory

### MEM-01: Scope and eligibility
Owner: **Memory / Recall & Context**. Implementation: **partial**.
Input: Workspace, subject, character root, purpose and lifecycle state. Output: Eligible current facts and scoped original exchanges.
Code: [history.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py), [memory_source_read.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/memory_source_read.py), [turn_memory_views.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_memory_views.py) Tests: [test_postgres_history_reader.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_history_reader.py), [test_postgres_memory_lifecycle.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_memory_lifecycle.py)
Evidence limit: Fact isolation has code; historical reader is development/evaluation-bound. Facts and experiences have different scope (PC-02/03/10).
Known gap: Archived/versioned history eligibility is not general released historical recall.
Next isolated check: Inspect inclusion and exclusion receipts across user, root, version, archive and lifecycle boundaries.

### MEM-02: Candidate search
Owner: **Memory / Recall & Context**. Implementation: **partial**.
Input: Eligible state and current query. Output: Potentially relevant facts and original dialogue.
Code: [turn_retrieval.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_retrieval.py), [history_native_rank.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_native_rank.py), [history.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py) Tests: [test_embeddings.py](../../../services/ade-api/tests/agent_runtime/test_embeddings.py), [test_history_native_rank.py](../../../services/ade-api/tests/agent_runtime/test_history_native_rank.py)
Evidence limit: Fact search exists; history experiments use a bounded reader and source-guarded ranking. Reader considers newest 128 scoped completed pairs before exclusions.
Known gap: Absent candidates cannot be recovered by a better selector; larger-scale recovery is separate.
Next isolated check: Measure required-source availability before evaluating ranking or answers.

### MEM-03: Evidence selection
Owner: **Memory / Recall & Context**. Implementation: **experimental**.
Input: Fixed candidate pool and current question. Output: Chosen original source IDs, not canonical facts or an answer.
Code: [history_ranking.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_ranking.py), [history_admission.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_admission.py), [character-evidence-recovery.md](../../../docs/plans/character-evidence-recovery.md) Tests: [test_history_ranking_identity.py](../../../services/ade-api/tests/agent_runtime/test_history_ranking_identity.py), [test_story_correction_comparison.py](../../../services/ade-api/tests/agent_runtime/test_story_correction_comparison.py)
Evidence limit: Literal selection is measured; D04 loses an available antecedent. Neighborhood and joint model selection remain proposed, unimplemented.
Known gap: Material corrections/references can be omitted; six prior model witnesses are not selector reliability evidence.
Next isolated check: Map existing benchmark tasks to this boundary before adding custom semantic cases.

### MEM-04: Context delivery
Owner: **Memory / Recall & Context**. Implementation: **partial**.
Input: Selected records, mandatory context, budgets and source bindings. Output: Actual serialized consumer requests with attributed admitted evidence.
Code: [natural_context.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_context.py), [history_admission.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_admission.py), [history_attempt.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_attempt.py), [turn_context_selection.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_context_selection.py) Tests: [test_natural_context.py](../../../services/ade-api/tests/agent_runtime/test_natural_context.py), [test_history_admission.py](../../../services/ade-api/tests/agent_runtime/test_history_admission.py), [test_story_offline_capacity.py](../../../services/ade-api/tests/agent_runtime/test_story_offline_capacity.py)
Evidence limit: Current admission is greedy; history probes bind supplied H. Exact whole-selection admission remains proposed in ADR 0060.
Known gap: Joint selections need a reviewed preservation contract; construction success does not prove semantic sufficiency.
Next isolated check: Compare selected IDs with actual generation/reviewer H, fit outcomes and source-loss receipts.

### MEM-05: Source capture
Owner: **Memory / Retention & Updates**. Implementation: **implemented**.
Input: Accepted user input and eventual candidate/committed reply. Output: Original messages, roles, hashes and run outcomes.
Code: [run_service.py](../../../services/ade-api/src/ade_api/features/agent_runtime/run_service.py), [conversations.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/conversations.py), [worker_finalization.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py) Tests: [test_run_service.py](../../../services/ade-api/tests/agent_runtime/test_run_service.py), [test_worker_finalization.py](../../../services/ade-api/tests/agent_runtime/test_worker_finalization.py)
Evidence limit: Input is persisted at acceptance before generation; completed assistant message is finalized later. Recording is not fact acceptance.
Known gap: Failed/pending input must not masquerade as a completed exchange.
Next isolated check: Trace accepted, cancelled, failed and completed turns without losing outcome attribution.

### MEM-06: Memory update review
Owner: **Memory / Retention & Updates**. Implementation: **partial**.
Input: Current user anchor, supplied references, fact state and reference-only candidate reply. Output: Supported proposed factual changes or no change.
Code: [reviewer.py](../../../services/ade-api/src/ade_api/features/agent_runtime/reviewer.py), [natural_memory_reviewer.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_reviewer.py), [natural_memory_review.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_review.py) Tests: [test_natural_memory_reviewer.py](../../../services/ade-api/tests/agent_runtime/test_natural_memory_reviewer.py), [test_natural_review_r5_contract.py](../../../services/ade-api/tests/agent_runtime/test_natural_review_r5_contract.py)
Evidence limit: Existing reviewer owns semantic interpretation (PC-05); natural variants are experimental. A valid citation is not semantic proof.
Known gap: Scope omissions, unsupported targets and output exhaustion remain observed limitations.
Next isolated check: Score false/missed updates and unjustified clarification against source-grounded expectations.

### MEM-07: Validation and commit
Owner: **Memory / Retention & Updates**. Implementation: **implemented**.
Input: Prepared review, source/version bindings and accepted generations. Output: Atomic permitted memory, assistant, summary and terminal run changes.
Code: [natural_memory_policy.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_policy.py), [natural_memory_commit.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_memory_commit.py), [worker_finalization.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py), [history_guard.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history_guard.py) Tests: [test_worker_finalization.py](../../../services/ade-api/tests/agent_runtime/test_worker_finalization.py), [test_postgres_natural_worker_fencing.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_worker_fencing.py)
Evidence limit: Structural validation, locks and finalization exist; ADE does not reinterpret meaning here (PC-05/07).
Known gap: Atomicity cannot repair a semantically wrong but structurally valid proposal.
Next isolated check: Check source/version drift and all-or-nothing assistant/memory finalization independently of reviewer quality.

### MEM-08: Index maintenance
Owner: **Memory / Organization & Maintenance**. Implementation: **implemented**.
Input: Prepared fact changes and embedding-space identity. Output: Revision-linked searchable representations committed with the facts.
Code: [turn_embedding_results.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_embedding_results.py), [embeddings.py](../../../services/ade-api/src/ade_api/features/agent_runtime/embeddings.py), [memory.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/memory.py) Tests: [test_embeddings.py](../../../services/ade-api/tests/agent_runtime/test_embeddings.py), [test_postgres_memory_lifecycle.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_memory_lifecycle.py)
Evidence limit: Fact embeddings are prepared before finalization, persisted atomically and bound to revisions/space; no general persistent dialogue graph is implied.
Known gap: Fresh/current representations still need retrieval-quality assessment.
Next isolated check: Verify obsolete revisions and incompatible embedding spaces cannot surface as current facts.

### MEM-09: Conversation compaction
Owner: **Memory / Organization & Maintenance**. Implementation: **implemented**.
Input: Older local messages and current context pressure. Output: Source-linked versioned summary proposal and working context.
Code: [turn_compaction.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_compaction.py), [compaction.py](../../../services/ade-api/src/ade_api/features/agent_runtime/compaction.py), [executor.py](../../../services/ade-api/src/ade_api/features/agent_runtime/executor.py), [worker_finalization.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py) Tests: [test_compaction.py](../../../services/ade-api/tests/agent_runtime/test_compaction.py), [test_postgres_natural_compaction_packets.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_natural_compaction_packets.py)
Evidence limit: Existing compaction is not a future optional addition. Its summary proposal is prepared before generation and finalized with the turn.
Known gap: A summary is not independent factual authority or proof of source-level recall.
Next isolated check: Compare source qualifiers with supplied summaries and count meaningful omissions.

### MEM-10: Additional derived views
Owner: **Memory / Organization & Maintenance**. Implementation: **deferred**.
Input: Source-linked committed records, if an extension is justified. Output: Optional compact view, not a new truth store.
Code: None; no implementation is implied. Tests: None; no implementation is implied.
Evidence limit: Placeholder for possible timelines/consolidated views; not implemented or approved. Existing summaries remain MEM-09.
Known gap: No demonstrated need for another derived representation (PC-09).
Next isolated check: Reopen only after measured search/context gaps justify its maintenance and distortion costs.

## Interface

### UI-01: Conversation workspace
Owner: **Interface / Conversation UI**. Implementation: **implemented**.
Input: User messages, selections and run events. Output: Session lifecycle, replies, cancellation and state refresh.
Code: [agent-studio-view.tsx](../../../apps/ade-web/src/features/agent-studio/agent-studio-view.tsx), [use-agent-studio.ts](../../../apps/ade-web/src/features/agent-studio/use-agent-studio.ts) Tests: [agent-studio-view.test.tsx](../../../apps/ade-web/src/features/agent-studio/agent-studio-view.test.tsx), [use-agent-studio.async.test.tsx](../../../apps/ade-web/src/features/agent-studio/use-agent-studio.async.test.tsx)
Evidence limit: Browser owns presentation; providers are accessed only behind ADE API.
Known gap: A working UI is not evidence of personality or historical-recall quality.
Next isolated check: Follow one immutable version/subject selection through an asynchronous turn.

### UI-02: Memory and lineage display
Owner: **Interface / Conversation UI**. Implementation: **implemented**.
Input: Subject facts, revisions, source links and conversation summaries. Output: Operator-visible state and explicit lifecycle actions.
Code: [agent-studio-view.tsx](../../../apps/ade-web/src/features/agent-studio/agent-studio-view.tsx), [resource_service.py](../../../services/ade-api/src/ade_api/features/agent_runtime/resource_service.py) Tests: [agent-studio-view.test.tsx](../../../apps/ade-web/src/features/agent-studio/agent-studio-view.test.tsx), [test_resource_service.py](../../../services/ade-api/tests/agent_runtime/test_resource_service.py)
Evidence limit: Facts and conversation binding are exposed explicitly; removal is an operator action, not a conversational consent feature (PC-06/07).
Known gap: Displayed fact state must not hide terminal lifecycle outcomes.
Next isolated check: Match UI state to committed lineage after correct/end/remove operations.

### UI-03: Turn activity inspection
Owner: **Interface / Inspection & Evaluation UI**. Implementation: **implemented**.
Input: Retained dispatch, tool and context metadata. Output: Observed counts, admitted IDs, source-chat links and incompleteness labels.
Code: [turn-activity-view.tsx](../../../apps/ade-web/src/features/agent-studio/turn-activity-view.tsx), [turn_activity.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_activity.py) Tests: [turn-activity-view.test.tsx](../../../apps/ade-web/src/features/agent-studio/turn-activity-view.test.tsx), [test_turn_activity.py](../../../services/ade-api/tests/agent_runtime/test_turn_activity.py)
Evidence limit: Existing inspector reports evidence availability, not causal model thinking. It is not a full candidate-to-packet trace.
Known gap: Candidate, selected and delivered source differences are not all visible here.
Next isolated check: Inventory missing boundary artifacts before extending this view.

### UI-04: Private evaluation artifact inspection
Owner: **Interface / Inspection & Evaluation UI**. Implementation: **experimental**.
Input: Bounded development/evaluation captures and readbacks. Output: Inspectable source/state/packet evidence with explicit unavailable states.
Code: [natural_attempt_evidence.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_attempt_evidence.py), [natural_evidence_readback.py](../../../services/ade-api/src/ade_api/features/agent_runtime/natural_evidence_readback.py), [history_observations.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_observations.py), [README.md](../../../workflows/evals/character_memory_dev/story_continuity/README.md) Tests: [test_natural_attempt_evidence.py](../../../services/ade-api/tests/agent_runtime/test_natural_attempt_evidence.py), [test_history_observations.py](../../../services/ade-api/tests/agent_runtime/test_history_observations.py)
Evidence limit: Isolated capture exists; full artifacts are private and not a newly implemented public inspection UI.
Known gap: Inspection has to preserve access, capture limits and missing-evidence distinctions.
Next isolated check: Trace an already-recorded case across candidate, selection, actual packet and commit evidence.

### UI-05: Prompt and persona editor
Owner: **Interface / Configuration UI**. Implementation: **implemented**.
Input: Operator content edits. Output: Reviewed authoring requests and rendered content state.
Code: [README.md](../../../apps/ade-web/src/features/prompt-center/README.md), [use-prompt-center.ts](../../../apps/ade-web/src/features/prompt-center/use-prompt-center.ts) Tests: [helpers.test.ts](../../../apps/ade-web/src/features/prompt-center/helpers.test.ts)
Evidence limit: Prompt Center edits content, not running agents or providers.
Known gap: Authoring changes do not rewrite already-bound conversation versions.
Next isolated check: Verify editor state and immutable runtime binding remain distinct.

### UI-06: Model catalog interface
Owner: **Interface / Configuration UI**. Implementation: **implemented**.
Input: Canonical model options and scenario selections. Output: User-visible model/capability selection.
Code: [README.md](../../../apps/ade-web/src/features/model-catalog/README.md), [api.py](../../../services/ade-api/src/ade_api/features/model_catalog/api.py) Tests: [test_identity.py](../../../services/ade-api/src/ade_api/features/model_catalog/tests/test_identity.py)
Evidence limit: The backend catalog adapts Model Router identity rather than inventing another model registry.
Known gap: Availability and selected-route qualification are not equivalent.
Next isolated check: Check displayed options against canonical identities and release-qualified selections.

### UI-07: Schema editor
Owner: **Interface / Configuration UI**. Implementation: **implemented**.
Input: Reviewed label-schema edits. Output: Schema authoring UI and validated schema records.
Code: [README.md](../../../apps/ade-web/src/features/schema-center/README.md), [api.py](../../../services/ade-api/src/ade_api/features/schema_center/api.py) Tests: [helpers.test.ts](../../../apps/ade-web/src/features/schema-center/helpers.test.ts), [test_registry.py](../../../services/ade-api/src/ade_api/features/schema_center/tests/test_registry.py)
Evidence limit: Existing schema tooling supports the adjacent Label Lab; it is not a character memory schema redesign.
Known gap: Keep task schemas distinct from native memory contracts.
Next isolated check: Trace a label-schema edit through its own owning feature.

### UI-08: Test Center and artifact viewer
Owner: **Interface / Inspection & Evaluation UI**. Implementation: **implemented**.
Input: Named workflow launches and rooted run artifacts. Output: Run state, cancellation and bounded artifact presentation.
Code: [test-center-view.tsx](../../../apps/ade-web/src/features/test-center/test-center-view.tsx), [run-artifact-viewer.tsx](../../../apps/ade-web/src/features/test-center/run-artifact-viewer.tsx), [run_descriptors.py](../../../services/ade-api/src/ade_api/features/test_center/run_descriptors.py) Tests: [launchers.test.ts](../../../apps/ade-web/src/features/test-center/launchers.test.ts), [tests](../../../services/ade-api/src/ade_api/features/test_center/tests)
Evidence limit: Maintains three named workflows; private character-development workflows are not automatically registered here.
Known gap: UI launchability is not behavior or release acceptance.
Next isolated check: Check artifact provenance and rooted access before adding a new inspection capability.

### UI-09: Dashboard and documentation
Owner: **Interface / Workspace Navigation**. Implementation: **implemented**.
Input: Feature routes and maintained documentation. Output: Workspace navigation and feature reading surfaces.
Code: [README.md](../../../apps/ade-web/src/features/dashboard/README.md), [README.md](../../../apps/ade-web/src/features/documentation/README.md) Tests: None; no implementation is implied.
Evidence limit: Existing feature homes are registered; this inventory did not qualify navigation behavior anew.
Known gap: Documentation and navigation must not present experimental behavior as released.
Next isolated check: Cross-check links and status language against the current contracts.

## External Tools

### EXT-01: External information and actions
Owner: **External Tools / External Information & Actions**. Implementation: **deferred**.
Input: A future concrete, permitted outside-information/action request. Output: Actual outside result for Character to interpret.
Code: None; no implementation is implied. Tests: None; no implementation is implied.
Evidence limit: No generic external tool platform is proposed. Memory search is CHAR-05/MEM-02; synthetic weather/failure tools are evaluation fixtures.
Known gap: A concrete capability and execution/authority contract are required before expansion.
Next isolated check: Reopen for a named user need, not because this placeholder exists.

## Platform Support / Supporting Register

Cross-cutting platform responsibilities with their existing owners.

### SUP-01: Turn orchestration and worker
Owner: **Platform Support / Supporting Register / Runtime Coordination**. Implementation: **implemented**.
Input: Accepted run, deadline, lease and immutable bindings. Output: One coordinated attempt, tools/review, cancellation/retry and final outcome.
Code: [turn_execution.py](../../../services/ade-api/src/ade_api/features/agent_runtime/turn_execution.py), [worker.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker.py), [run_service.py](../../../services/ade-api/src/ade_api/features/agent_runtime/run_service.py), [retry.py](../../../services/ade-api/src/ade_api/features/agent_runtime/retry.py) Tests: [test_worker.py](../../../services/ade-api/tests/agent_runtime/test_worker.py), [test_retry.py](../../../services/ade-api/tests/agent_runtime/test_retry.py)
Evidence limit: Owns sequencing and atomic finalization; capability boxes are not independent post-reply hooks (PC-08/09).
Known gap: The chart is not a deployment or retry-policy change.
Next isolated check: Trace acceptance through failure/cancellation/success with existing receipts.

### SUP-02: PostgreSQL and migrations
Owner: **Platform Support / Supporting Register / State & Storage**. Implementation: **implemented**.
Input: Transactions, schema migrations and locked identities. Output: Native state, revisions, summaries, runs and events.
Code: [metadata.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/metadata.py), [database.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/database.py), [migrations](../../../services/ade-api/migrations) Tests: [test_metadata.py](../../../services/ade-api/tests/agent_runtime/persistence/test_metadata.py), [test_postgres_migration.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_migration.py)
Evidence limit: PostgreSQL is native state authority; persona authoring SQLite is separate from immutable runtime snapshots.
Known gap: Storage correctness is not semantic memory correctness.
Next isolated check: Verify schema and transaction invariants using isolated database tests.

### SUP-03: Model Router and catalog adapters
Owner: **Platform Support / Supporting Register / Model Access**. Implementation: **implemented**.
Input: Canonical route, capability profile and request. Output: One-attempt provider response or explicit failure.
Code: [forwarding.py](../../../services/model-router/src/model_router/forwarding.py), [profiles.py](../../../services/model-router/src/model_router/profiles.py), [router_transport.py](../../../services/ade-api/src/ade_api/features/agent_runtime/router_transport.py), [README.md](../../../services/ade-api/src/ade_api/features/model_catalog/README.md) Tests: [test_app.py](../../../services/model-router/tests/test_app.py), [test_profiles.py](../../../services/model-router/tests/test_profiles.py)
Evidence limit: Router owns identity/discovery/forwarding; ADE owns turn retry and product behavior.
Known gap: Provider availability does not qualify persona or memory behavior.
Next isolated check: Verify request/profile identity independently of product scoring.

### SUP-04: Evaluation workflows and fixtures
Owner: **Platform Support / Supporting Register / Evaluation**. Implementation: **implemented**.
Input: Tracked fixtures, explicit environment binding and any separately authorized run. Output: Offline checks, diagnostic artifacts or exact qualification evidence.
Code: [README.md](../../../workflows/evals/character_memory_dev/README.md), [README.md](../../../workflows/evals/character_memory_dev/story_continuity/README.md), [README.md](../../../workflows/evals/chat_memory_eval/README.md), [README.md](../../../workflows/evals/agent_runtime_acceptance/README.md), [evaluation_tools.py](../../../services/ade-api/src/ade_api/features/agent_runtime/evaluation_tools.py) Tests: [tests](../../../workflows/evals/character_memory_dev/tests), [test_postgres_native_story_runner.py](../../../services/ade-api/tests/agent_runtime/persistence/test_postgres_native_story_runner.py)
Evidence limit: Offline, private replay, live diagnosis and release gates remain distinct. This map launches none of them.
Known gap: Reuse of named public memory benchmarks has not yet been mapped to these boundaries.
Next isolated check: Map reusable tasks to subsystem measures; keep only uncovered ADE regression cases.

### SUP-05: Dispatch and source observations
Owner: **Platform Support / Supporting Register / Observability**. Implementation: **implemented**.
Input: Actual boundary events and bounded evaluation capture. Output: Counts, completeness, hashes, omission receipts and before/after state.
Code: [provider_tracing.py](../../../services/ade-api/src/ade_api/features/agent_runtime/provider_tracing.py), [request_counts.py](../../../services/ade-api/src/ade_api/features/agent_runtime/request_counts.py), [history_observations.py](../../../services/ade-api/src/ade_api/features/agent_runtime/history_observations.py), [evaluation_observations.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/evaluation_observations.py) Tests: [test_provider_tracing.py](../../../services/ade-api/tests/agent_runtime/test_provider_tracing.py), [test_request_counts.py](../../../services/ade-api/tests/agent_runtime/test_request_counts.py), [test_history_observations.py](../../../services/ade-api/tests/agent_runtime/test_history_observations.py)
Evidence limit: Public metadata and restricted full-state capture have different access and completeness contracts; neither exposes private model reasoning.
Known gap: Observed availability cannot identify which source caused a reply.
Next isolated check: Distinguish unavailable, truncated and observed-empty boundary artifacts.

### SUP-06: Release gates, smoke and recovery
Owner: **Platform Support / Supporting Register / Release & Operations**. Implementation: **implemented**.
Input: Exact source/build/policy identity and approved evidence. Output: Release decision, operational checks and documented rollback.
Code: [release_policy.py](../../../services/ade-api/src/ade_api/features/agent_runtime/release_policy.py), [check_agent_studio_release_gate.py](../../../scripts/check_agent_studio_release_gate.py), [ade_api_e2e_check.py](../../../workflows/smoke/ade_api_e2e_check.py), [agent-studio-release.md](../../../docs/operations/agent-studio-release.md) Tests: [test_release_evidence.py](../../../services/ade-api/tests/agent_runtime/test_release_evidence.py), [test_agent_studio_release_scripts.py](../../../scripts/tests/test_agent_studio_release_scripts.py)
Evidence limit: Gate machinery exists; this inventory neither checks live deployment nor qualifies changed policies.
Known gap: Historical qualification cannot be inherited by new source/policy hashes.
Next isolated check: Audit exact ledger bindings only when a release decision is requested.

### SUP-07: App composition and authentication
Owner: **Platform Support / Supporting Register / Application Boundary**. Implementation: **implemented**.
Input: Same-origin requests and server-side configuration/credentials. Output: Composed product API and authenticated feature access.
Code: [app.py](../../../services/ade-api/src/ade_api/platform/app.py), [auth.py](../../../services/ade-api/src/ade_api/platform/auth.py) Tests: [test_native_app.py](../../../services/ade-api/tests/agent_runtime/test_native_app.py)
Evidence limit: Application wiring and credential handling retain their existing platform owner.
Known gap: Not every infrastructure concern is a Character or Memory module.
Next isolated check: Keep public feature contracts and server-only credentials at their existing boundaries.

### SUP-08: Reviewed task schemas
Owner: **Platform Support / Supporting Register / Schema Content**. Implementation: **implemented**.
Input: Reviewed schema edits and Label Lab selection. Output: Validated task schemas through Schema Center's public contract.
Code: [registry.py](../../../services/ade-api/src/ade_api/features/schema_center/registry.py), [label-schemas](../../../content/label-schemas) Tests: [test_api.py](../../../services/ade-api/src/ade_api/features/schema_center/tests/test_api.py), [test_registry.py](../../../services/ade-api/src/ade_api/features/schema_center/tests/test_registry.py)
Evidence limit: Schema Center and its content registry exist; task-label schemas are not Memory facts.
Known gap: Task schema evolution must not silently change native memory contracts.
Next isolated check: Trace schema identity through the owning task instead of the character-memory pipeline.

## Independent Labs / Adjacent Features

Independent Comment and Label labs with their existing owners.

### ADJ-01: Comment Lab
Owner: **Independent Labs / Adjacent Features / Independent Labs**. Implementation: **implemented**.
Input: Task-specific comment, persona and model options. Output: Router-backed comment result under the lab contract.
Code: [README.md](../../../services/ade-api/src/ade_api/features/comment_lab/README.md), [README.md](../../../apps/ade-web/src/features/comment-lab/README.md) Tests: [test_request_response_mappers.py](../../../services/ade-api/src/ade_api/features/comment_lab/tests/test_request_response_mappers.py)
Evidence limit: Independent existing feature, not silently reassigned to the character-memory runtime.
Known gap: This inventory does not re-evaluate its task behavior.
Next isolated check: Use its owning workflow if Comment Lab work is requested.

### ADJ-02: Label Lab
Owner: **Independent Labs / Adjacent Features / Independent Labs**. Implementation: **implemented**.
Input: Task text, selected schema and model options. Output: Validated labeling result under the lab contract.
Code: [README.md](../../../services/ade-api/src/ade_api/features/label_lab/README.md), [README.md](../../../apps/ade-web/src/features/label-lab/README.md) Tests: [test_service.py](../../../services/ade-api/src/ade_api/features/label_lab/tests/test_service.py)
Evidence limit: Independent existing feature using Schema Center and Model Catalog; not character conversational behavior.
Known gap: This inventory does not re-evaluate labeling quality.
Next isolated check: Use its own task cases rather than character-memory fixtures.

## Stored Records

Records are not processing modules.

### REC-DIALOGUE: Original dialogue
Evidence of what was said, with roles and run outcomes; not automatic fact acceptance
Sources: [conversations.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/conversations.py), [history.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/history.py)

### REC-FACTS: Facts and revisions
Maintained subject-owned state, lifecycle, sources and revisions
Sources: [memory.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/memory.py)

### REC-SUMMARY: Conversation summaries
Source-linked versioned working context; not independent factual authority
Sources: [compaction.py](../../../services/ade-api/src/ade_api/features/agent_runtime/compaction.py), [worker_finalization.py](../../../services/ade-api/src/ade_api/features/agent_runtime/worker_finalization.py)

### REC-DEFINITION: Definition snapshots
Immutable prompt/persona/deployment/policy binding for a conversation
Sources: [definitions.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/definitions.py)

### REC-INDEX: Fact search representations
Revision/space-linked derived access, not a second truth store
Sources: [embeddings.py](../../../services/ade-api/src/ade_api/features/agent_runtime/embeddings.py), [memory.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/memory.py)

### REC-RUNS: Runs, attempts and events
Observed processing/outcome metadata; completeness must be stated
Sources: [runs.py](../../../services/ade-api/src/ade_api/features/agent_runtime/persistence/runs.py), [provider_tracing.py](../../../services/ade-api/src/ade_api/features/agent_runtime/provider_tracing.py)
