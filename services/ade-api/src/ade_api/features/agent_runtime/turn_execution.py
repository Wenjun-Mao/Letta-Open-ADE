from __future__ import annotations

import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings

from .compaction import plan_compaction
from .context import (
    conversation_history_metadata,
    context_budget_from_deployment,
    validate_current_user_message,
)
from .embeddings import (
    NATURAL_RETRIEVAL_POLICY_VERSION,
    RETRIEVAL_POLICY_VERSION,
    EmbeddingClient,
    embedding_space_key,
)
from .deployments import validate_definition_execution
from .errors import RuntimeValidationError
from .evaluation_tools import evaluation_tool_registry
from .executor import ConversationExecutor, curated_tools
from .history_admission import HistoryProbe
from .history_attempt import HistoryAttempt, HistoryBeforeExposure
from .memory_policy import prepare_memory_review
from .memory_policy_binding import require_executable_memory_policy
from .natural_attempt_evidence import capture_context, start_natural_capture
from .natural_evaluation_capacity import checked_checkpoint6_capacity
from .natural_context import (
    HISTORY_PROBE_POLICY,
    NATURAL_POLICY_BINDINGS,
    full_lifecycle_snapshot_fits,
)
from .natural_memory_reviewer import execute_natural_review
from .provider_tracing import AttemptTrace
from .release_policy import (
    ensure_agent_studio_release_ready,
    release_validation_kwargs,
)
from .reviewer import MemoryReviewer
from .router_transport import RouterTransport
from .turn_deployment import (
    deployment_adapter as _deployment_adapter,
    embedding_dimensions as _embedding_dimensions,
    max_model_requests as _max_model_requests,
    required_deployment as _required_deployment,
    reviewer_max_model_requests as _reviewer_max_model_requests,
)
from .turn_embedding_results import embed_review_operations
from .turn_memory_snapshot import (
    current_user_message as _current_user_message,
    load_turn_state,
)
from .turn_retrieval import search_memory_handler, select_automatic_facts
from .turn_context_selection import select_turn_context
from .turn_result import AttemptResult


class TurnExecution:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        transport: RouterTransport,
        settings: AdeApiSettings,
        history_probe: HistoryProbe | None = None,
    ) -> None:
        self.engine = engine
        self.transport = transport
        self.settings = settings
        self.history_probe = history_probe

    async def execute(
        self,
        run: dict[str, Any],
        *,
        deadline: float,
        trace: AttemptTrace,
    ) -> AttemptResult:
        state = await self._load_state(run)
        definition = state["definition"]
        conversation = state["conversation"]
        if conversation.get("purpose") == "agent_studio":
            ensure_agent_studio_release_ready(self.settings.agent_runtime_mode)
        natural_variant = NATURAL_POLICY_BINDINGS.get(
            definition["memory_policy_version"]
        )
        require_executable_memory_policy(
            str(definition["memory_policy_version"]),
            purpose=str(conversation.get("purpose") or ""),
            runtime_mode=self.settings.agent_runtime_mode,
        )
        natural_mode = natural_variant is not None
        history_probe_enabled = (
            definition["memory_policy_version"] == HISTORY_PROBE_POLICY
        )
        if history_probe_enabled != (self.history_probe is not None) or (
            history_probe_enabled and conversation.get("purpose") != "evaluation"
        ):
            raise RuntimeValidationError(
                "History probe requires its evaluation-only policy and arm binding",
                detail_code="natural_history_binding",
            )
        if natural_mode and self.settings.agent_runtime_mode != "development":
            raise RuntimeValidationError(
                "Experimental natural-memory bindings cannot run in release mode"
            )
        if natural_mode:
            trace.natural_evidence = start_natural_capture(
                database_url=self.settings.database_url,
                runtime_mode=self.settings.agent_runtime_mode,
                purpose=str(conversation.get("purpose") or ""),
                run_id=str(run["id"]),
                attempt=trace.attempt,
                policy_binding=str(definition["memory_policy_version"]),
            )
        catalog = await trace.transport(self.transport, stage="catalog").catalog(
            timeout_seconds=min(
                _remaining(deadline),
                self.settings.model_discovery_timeout_seconds,
            )
        )
        validate_definition_execution(
            definition,
            catalog,
            mode=self.settings.agent_runtime_mode,
            **release_validation_kwargs(self.settings.agent_runtime_mode),
        )
        evaluation_capacity = checked_checkpoint6_capacity(
            definition,
            purpose=str(conversation.get("purpose") or ""),
            natural_variant=natural_variant,
        )
        subject_id = str(conversation["memory_subject_id"])
        deployments = {
            str(item["role"]): item for item in definition["deployment_snapshot"]
        }
        conversation_deployment = _required_deployment(deployments, "conversation")
        reviewer_deployment = _required_deployment(deployments, "reviewer")
        retriever_deployment = _required_deployment(deployments, "retriever")
        retriever_space_key = embedding_space_key(retriever_deployment)
        conversation_adapter = _deployment_adapter(catalog, conversation_deployment)
        reviewer_adapter = _deployment_adapter(catalog, reviewer_deployment)
        conversation_executor = ConversationExecutor(
            trace.transport(
                self.transport,
                stage="conversation",
                model_fingerprint=str(conversation_deployment["fingerprint"]),
            ),
            provider_adapter=conversation_adapter,
        )
        compaction_executor = ConversationExecutor(
            trace.transport(
                self.transport,
                stage="compaction",
                model_fingerprint=str(conversation_deployment["fingerprint"]),
            ),
            provider_adapter=conversation_adapter,
        )
        reviewer = MemoryReviewer(
            trace.transport(
                self.transport,
                stage="reviewer",
                model_fingerprint=str(reviewer_deployment["fingerprint"]),
            ),
            provider_adapter=reviewer_adapter,
        )
        retrieval_embeddings = EmbeddingClient(
            trace.transport(
                self.transport,
                stage="retrieval_query",
                model_fingerprint=str(retriever_deployment["fingerprint"]),
            )
        )
        tool_embeddings = EmbeddingClient(
            trace.transport(
                self.transport,
                stage="tool_retrieval",
                model_fingerprint=str(retriever_deployment["fingerprint"]),
            )
        )
        memory_embeddings = EmbeddingClient(
            trace.transport(
                self.transport,
                stage="memory_embeddings",
                model_fingerprint=str(retriever_deployment["fingerprint"]),
            )
        )
        current_user = _current_user_message(state["messages"], str(run["id"]))
        current_sequence = int(current_user["sequence"])
        summary = state["summary"]
        budget = (
            evaluation_capacity.conversation
            if evaluation_capacity is not None
            else context_budget_from_deployment(conversation_deployment)
        )
        try:
            validate_current_user_message(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                content=str(current_user["content"]),
                budget=budget,
            )
        except ValueError as exc:
            raise RuntimeValidationError(str(exc)) from exc
        compaction_plan = (
            None
            if natural_variant == "B"
            else plan_compaction(
                messages=state["messages"],
                current_user_message_id=str(current_user["id"]),
                summary=summary,
                recent_token_budget=budget.recent_tokens,
                compaction_input_token_budget=budget.input_limit,
            )
        )
        summary_boundary = int(summary["through_sequence"]) if summary else 0
        if natural_variant in {"A", "A0"} and compaction_plan is not None:
            planned_history = conversation_history_metadata(
                messages=state["messages"],
                current_sequence=current_sequence,
                summary_through_sequence=compaction_plan.through_sequence,
            )
            if not full_lifecycle_snapshot_fits(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                current_user_content=str(current_user["content"]),
                lifecycle_facts=state["facts"],
                history_metadata=planned_history,
                input_limit=budget.input_limit,
            ):
                # Narrative is ineligible for both A and A0 on this turn.
                # Do not spend a compaction call on content the bundle withholds.
                compaction_plan = None
        compaction = (
            await compaction_executor.compact(
                model_key=str(conversation_deployment["route_alias"]),
                model_fingerprint=str(conversation_deployment["fingerprint"]),
                plan=compaction_plan,
                timeout_seconds=_remaining(deadline),
                max_output_tokens=budget.max_output_tokens,
                summary_token_budget=budget.summary_tokens,
                observe_request=(
                    trace.natural_evidence.capture_compaction_request
                    if trace.natural_evidence is not None
                    else None
                ),
            )
            if compaction_plan is not None
            else None
        )

        if compaction is not None and trace.natural_evidence is not None:
            trace.natural_evidence.capture_compaction_result(compaction)

        summary_content = str(summary["content"]) if summary else ""
        if compaction is not None:
            summary_boundary = compaction.plan.through_sequence
            summary_content = compaction.content
        recent_messages = [
            message
            for message in state["messages"]
            if int(message["sequence"]) > summary_boundary
            and int(message["sequence"]) < current_sequence
        ]
        history = conversation_history_metadata(
            messages=state["messages"],
            current_sequence=current_sequence,
            summary_through_sequence=summary_boundary,
        )
        selective_retrieval = natural_variant not in {"A", "A0"}
        if natural_variant in {"A", "A0"}:
            selective_retrieval = not full_lifecycle_snapshot_fits(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                current_user_content=str(current_user["content"]),
                lifecycle_facts=state["facts"],
                history_metadata=history,
                input_limit=budget.input_limit,
            )
        expected_dimensions = _embedding_dimensions(retriever_deployment)
        retrieved: list[dict[str, Any]] = []
        if selective_retrieval:
            retrieved = await select_automatic_facts(
                engine=self.engine,
                embeddings=retrieval_embeddings,
                deployment=retriever_deployment,
                current_user_content=str(current_user["content"]),
                subject_id=subject_id,
                fingerprint=retriever_space_key,
                expected_dimensions=expected_dimensions,
                accepted_memory_generation=int(run["accepted_memory_generation"]),
                natural=natural_mode,
                deadline=deadline,
            )
        selection = select_turn_context(
            state=state,
            definition=definition,
            current_user=current_user,
            recent_messages=recent_messages,
            retrieved=retrieved,
            summary_content=summary_content,
            history_metadata=history,
            budget=budget,
            natural_variant=natural_variant,
            evaluation_capacity=evaluation_capacity,
            reviewer_deployment=reviewer_deployment,
            reviewer_adapter=reviewer_adapter,
            history_capable=history_probe_enabled,
        )
        built_context = selection.context
        natural_source_messages = selection.natural_source_messages
        active_facts = selection.active_facts
        reviewer_input_limit = selection.reviewer_input_limit
        reviewer_request_max_tokens = selection.reviewer_request_max_tokens

        enabled_tool_names = tuple(str(name) for name in definition["tool_names"])
        generation_tools = curated_tools(
            enabled_tool_names,
            search_memory=search_memory_handler(
                engine=self.engine,
                embeddings=tool_embeddings,
                deployment=retriever_deployment,
                subject_id=subject_id,
                fingerprint=retriever_space_key,
                expected_dimensions=expected_dimensions,
                accepted_memory_generation=int(run["accepted_memory_generation"]),
                natural=natural_mode,
                deadline=deadline,
            ),
            additional_tools=(
                evaluation_tool_registry()
                if conversation.get("purpose") == "evaluation"
                else None
            ),
        )
        history_attempt: HistoryAttempt | None = None
        if self.history_probe is not None:
            history_attempt = HistoryAttempt(
                engine=self.engine,
                probe=self.history_probe,
                corpus=state.get("history", {}),
                run=run,
                conversation=conversation,
                definition=definition,
                current_user=current_user,
                source_messages=list(natural_source_messages),
                facts=state["facts"],
                entities=state["entities"],
                base_context=built_context,
                generation_model_key=str(conversation_deployment["route_alias"]),
                generation_adapter=conversation_adapter,
                generation_tools=generation_tools,
                generation_input_limit=budget.input_limit,
                generation_max_output_tokens=budget.max_output_tokens,
                reviewer_model_key=str(reviewer_deployment["route_alias"]),
                reviewer_adapter=reviewer_adapter,
                reviewer_input_limit=reviewer_input_limit,
                reviewer_max_output_tokens=reviewer_request_max_tokens,
                deadline=deadline,
            )
            built_context = history_attempt.prepare()

        while True:
            try:
                executor_result = await conversation_executor.execute(
                    model_key=str(conversation_deployment["route_alias"]),
                    messages=built_context.messages,
                    timeout_seconds=_remaining(deadline),
                    max_output_tokens=budget.max_output_tokens,
                    max_model_requests=(
                        evaluation_capacity.conversation_requests
                        if evaluation_capacity is not None
                        else _max_model_requests(conversation_deployment)
                    ),
                    input_token_limit=budget.input_limit if natural_mode else None,
                    observe_request=(
                        trace.natural_evidence.capture_generation_request
                        if trace.natural_evidence is not None
                        else None
                    ),
                    authorize_request=(
                        history_attempt.authorize_request
                        if history_attempt is not None
                        else None
                    ),
                    tools=generation_tools,
                )
                break
            except HistoryBeforeExposure as exc:
                assert history_attempt is not None
                built_context = history_attempt.omit_before_exposure(exc)
        try:
            capture_context(
                trace.natural_evidence,
                context=built_context,
                source_messages=natural_source_messages,
                input_limit=budget.input_limit,
            )
        except Exception:
            pass
        if trace.natural_evidence is not None:
            try:
                trace.natural_evidence.capture_candidate(
                    executor_result.assistant_text, executor_result.tool_evidence
                )
            except Exception:
                pass
        recent_users = [
            message
            for message in state["messages"]
            if message["role"] == "user" and int(message["sequence"]) < current_sequence
        ][-8:]
        natural_source_message_ids: tuple[str, ...] = ()
        if natural_mode:
            source_messages = list(natural_source_messages)
            natural_source_message_ids = tuple(
                str(message["id"]) for message in source_messages
            )
            reviewer_result, prepared = await execute_natural_review(
                trace=trace,
                transport=self.transport,
                reviewer_deployment=reviewer_deployment,
                provider_adapter=reviewer_adapter,
                subject_id=subject_id,
                current_user_message=current_user,
                source_messages=source_messages,
                facts=state["facts"],
                entities=state["entities"],
                candidate_reply=executor_result.assistant_text,
                timeout_seconds=_remaining(deadline),
                input_token_limit=reviewer_input_limit,
                max_output_tokens=reviewer_request_max_tokens,
                history_exchanges=(
                    history_attempt.admitted_exchanges
                    if history_attempt is not None
                    else []
                ),
                history_capable=history_probe_enabled,
                authorize_request=(
                    history_attempt.authorize_request
                    if history_attempt is not None
                    else None
                ),
            )
        else:
            reviewer_result = await reviewer.review(
                model_key=str(reviewer_deployment["route_alias"]),
                current_user_message=current_user,
                recent_user_messages=recent_users,
                active_facts=active_facts,
                entities=state["entities"],
                timeout_seconds=_remaining(deadline),
                max_model_requests=_reviewer_max_model_requests(reviewer_deployment),
                validate_decision=lambda decision: prepare_memory_review(
                    decision=decision,
                    subject_id=subject_id,
                    current_user_message=current_user,
                    active_facts=active_facts,
                    entities=state["entities"],
                ),
            )
            prepared = prepare_memory_review(
                decision=reviewer_result.decision,
                subject_id=subject_id,
                current_user_message=current_user,
                active_facts=active_facts,
                entities=state["entities"],
            )
        operation_embeddings, dimensions = await embed_review_operations(
            client=memory_embeddings,
            deployment=retriever_deployment,
            review=prepared,
            expected_dimensions=expected_dimensions,
            timeout_seconds=_remaining(deadline),
            evidence=trace.natural_evidence,
        )
        return AttemptResult(
            assistant_text=executor_result.assistant_text,
            context=built_context,
            executor=executor_result,
            reviewer=reviewer_result,
            review=prepared,
            operation_embeddings=operation_embeddings,
            embedding_fingerprint=retriever_space_key,
            embedding_dimensions=dimensions,
            retrieval_policy_version=(
                NATURAL_RETRIEVAL_POLICY_VERSION
                if natural_mode
                else RETRIEVAL_POLICY_VERSION
            ),
            compaction=compaction,
            natural_source_message_ids=natural_source_message_ids,
            admitted_history_exchanges=(
                tuple(history_attempt.admitted_exchanges)
                if history_attempt is not None
                else ()
            ),
            history_deadline=(
                deadline
                if history_attempt is not None and history_attempt.admitted_exchanges
                else None
            ),
            history_probe_status=(
                history_attempt.status if history_attempt is not None else None
            ),
        )

    async def _load_state(self, run: dict[str, Any]) -> dict[str, Any]:
        return await load_turn_state(
            self.engine,
            run,
            include_history=self.history_probe is not None
            and self.history_probe.arm == "automatic_history",
        )


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("whole runtime attempt timed out")
    return remaining
