from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from ade_api.platform.settings import AdeApiSettings

from .compaction import ModelCompaction, plan_compaction
from .context import (
    BuiltContext,
    build_context,
    conversation_history_metadata,
    context_budget_from_deployment,
    validate_current_user_message,
)
from .embeddings import (
    AUTOMATIC_MAXIMUM_COSINE_DISTANCE,
    RETRIEVAL_POLICY_VERSION,
    EmbeddingClient,
    qwen_query_text,
)
from .deployments import validate_definition_execution
from .errors import RuntimeValidationError
from .executor import ConversationExecutor, ExecutorResult, curated_tools
from .memory_policy import PreparedMemoryReview, prepare_memory_review
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .provider_tracing import AttemptTrace
from .release_policy import (
    release_validation_kwargs,
)
from .reviewer import MemoryReviewer, ReviewerResult
from .router_transport import RouterTransport
from .tool_policy import resolve_tool_requirement


@dataclass(frozen=True)
class AttemptResult:
    assistant_text: str
    context: BuiltContext
    executor: ExecutorResult
    reviewer: ReviewerResult
    review: PreparedMemoryReview
    operation_embeddings: tuple[list[float] | None, ...]
    embedding_fingerprint: str
    embedding_dimensions: int
    retrieval_policy_version: str
    compaction: ModelCompaction | None


class TurnExecution:
    def __init__(
        self,
        *,
        engine: AsyncEngine,
        transport: RouterTransport,
        settings: AdeApiSettings,
    ) -> None:
        self.engine = engine
        self.transport = transport
        self.settings = settings

    async def execute(
        self,
        run: dict[str, Any],
        *,
        deadline: float,
        trace: AttemptTrace,
    ) -> AttemptResult:
        state = await self._load_state(run)
        definition = state["definition"]
        catalog = await trace.transport(self.transport, stage="catalog").catalog(
            timeout_seconds=min(
                _remaining(deadline),
                self.settings.model_discovery_timeout_seconds,
            )
        )
        validate_definition_execution(
            definition,
            catalog,
            mode=self.settings.agent_runtime_v3_mode,
            **release_validation_kwargs(self.settings.agent_runtime_v3_mode),
        )
        conversation = state["conversation"]
        subject_id = str(conversation["memory_subject_id"])
        deployments = {
            str(item["role"]): item for item in definition["deployment_snapshot"]
        }
        conversation_deployment = _required_deployment(deployments, "conversation")
        reviewer_deployment = _required_deployment(deployments, "reviewer")
        retriever_deployment = _required_deployment(deployments, "retriever")
        conversation_executor = ConversationExecutor(
            trace.transport(
                self.transport,
                stage="conversation",
                model_fingerprint=str(conversation_deployment["fingerprint"]),
            )
        )
        compaction_executor = ConversationExecutor(
            trace.transport(
                self.transport,
                stage="compaction",
                model_fingerprint=str(conversation_deployment["fingerprint"]),
            )
        )
        reviewer = MemoryReviewer(
            trace.transport(
                self.transport,
                stage="reviewer",
                model_fingerprint=str(reviewer_deployment["fingerprint"]),
            )
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
        budget = context_budget_from_deployment(conversation_deployment)
        try:
            validate_current_user_message(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                content=str(current_user["content"]),
                budget=budget,
            )
        except ValueError as exc:
            raise RuntimeValidationError(str(exc)) from exc
        compaction_plan = plan_compaction(
            messages=state["messages"],
            current_user_message_id=str(current_user["id"]),
            summary=summary,
            recent_token_budget=budget.recent_tokens,
            compaction_input_token_budget=budget.input_limit,
        )
        compaction = (
            await compaction_executor.compact(
                model_key=str(conversation_deployment["route_alias"]),
                model_fingerprint=str(conversation_deployment["fingerprint"]),
                plan=compaction_plan,
                timeout_seconds=_remaining(deadline),
                max_output_tokens=budget.max_output_tokens,
                summary_token_budget=budget.summary_tokens,
            )
            if compaction_plan is not None
            else None
        )

        query_vector = (
            await retrieval_embeddings.embed(
                model_key=str(retriever_deployment["route_alias"]),
                inputs=[qwen_query_text(str(current_user["content"]))],
                timeout_seconds=_remaining(deadline),
            )
        )[0]
        retrieved = await self._search(
            subject_id=subject_id,
            query_vector=query_vector,
            fingerprint=str(retriever_deployment["fingerprint"]),
            limit=8,
            maximum_distance=AUTOMATIC_MAXIMUM_COSINE_DISTANCE,
        )
        active_facts = sorted(
            state["active_facts"],
            key=lambda item: (item["updated_at"], str(item["id"])),
            reverse=True,
        )
        summary_boundary = int(summary["through_sequence"]) if summary else 0
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
        try:
            built_context = build_context(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                active_facts=[_context_fact(item) for item in active_facts[:12]],
                conversation_summary=summary_content,
                history_metadata=conversation_history_metadata(
                    messages=state["messages"],
                    current_sequence=current_sequence,
                    summary_through_sequence=summary_boundary,
                ),
                retrieved_facts=[_context_fact(item) for item in retrieved],
                recent_messages=recent_messages,
                current_user_content=str(current_user["content"]),
                budget=budget,
            )
        except ValueError as exc:
            raise RuntimeValidationError(str(exc)) from exc
        if built_context.omitted_message_ids:
            raise RuntimeValidationError(
                "Context construction omitted unsummarized conversation history"
            )

        async def search_memory(query: str, limit: int) -> list[dict[str, Any]]:
            vector = (
                await tool_embeddings.embed(
                    model_key=str(retriever_deployment["route_alias"]),
                    inputs=[qwen_query_text(query)],
                    timeout_seconds=_remaining(deadline),
                )
            )[0]
            rows = await self._search(
                subject_id=subject_id,
                query_vector=vector,
                fingerprint=str(retriever_deployment["fingerprint"]),
                limit=limit,
                maximum_distance=None,
            )
            return [_tool_fact(item) for item in rows]

        enabled_tool_names = tuple(str(name) for name in definition["tool_names"])
        tool_requirement = resolve_tool_requirement(
            str(current_user["content"]), enabled_tool_names
        )
        if tool_requirement is not None:
            trace.record_tool_requirement_resolved(tool_requirement)
        try:
            executor_result = await conversation_executor.execute(
                model_key=str(conversation_deployment["route_alias"]),
                messages=built_context.messages,
                timeout_seconds=_remaining(deadline),
                max_output_tokens=budget.max_output_tokens,
                max_model_requests=_max_model_requests(conversation_deployment),
                tools=curated_tools(
                    enabled_tool_names,
                    search_memory=search_memory,
                ),
                tool_requirement=tool_requirement,
            )
        except RuntimeValidationError as exc:
            if tool_requirement is not None and exc.detail_code in {
                "conversation_required_tool_missing",
                "conversation_required_tool_mismatch",
                "conversation_tool_call_malformed",
                "conversation_tool_not_enabled",
                "conversation_tool_arguments_invalid_json",
                "conversation_tool_arguments_not_object",
                "curated_tool_arguments_invalid",
                "curated_tool_requirement_invalid",
            }:
                trace.record_tool_requirement_unmet(
                    tool_requirement, detail_code=exc.detail_code
                )
            raise
        if tool_requirement is not None:
            if not executor_result.tool_requirement_satisfied:
                raise RuntimeValidationError(
                    "Conversation executor lost its required tool outcome",
                    detail_code="conversation_required_tool_missing",
                )
            trace.record_tool_requirement_satisfied(tool_requirement)
        recent_users = [
            message
            for message in state["messages"]
            if message["role"] == "user" and int(message["sequence"]) < current_sequence
        ][-8:]
        reviewer_result = await reviewer.review(
            model_key=str(reviewer_deployment["route_alias"]),
            current_user_message=current_user,
            recent_user_messages=recent_users,
            active_facts=active_facts,
            entities=state["entities"],
            timeout_seconds=_remaining(deadline),
            validate_decision=lambda decision: _validate_review_decision(
                decision=decision,
                subject_id=subject_id,
                current_user=current_user,
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
        embeddable = [
            operation
            for operation in prepared.operations
            if operation.value is not None
        ]
        vectors = await memory_embeddings.embed(
            model_key=str(retriever_deployment["route_alias"]),
            inputs=[_fact_document(item) for item in embeddable],
            timeout_seconds=_remaining(deadline),
        )
        vector_iterator = iter(vectors)
        operation_embeddings = tuple(
            None if operation.value is None else next(vector_iterator)
            for operation in prepared.operations
        )
        expected_dimensions = _embedding_dimensions(retriever_deployment)
        dimensions = len(vectors[0]) if vectors else expected_dimensions
        if expected_dimensions and vectors and dimensions != expected_dimensions:
            raise RuntimeValidationError(
                "Embedding dimensions do not match the deployment fingerprint"
            )
        return AttemptResult(
            assistant_text=executor_result.assistant_text,
            context=built_context,
            executor=executor_result,
            reviewer=reviewer_result,
            review=prepared,
            operation_embeddings=operation_embeddings,
            embedding_fingerprint=str(retriever_deployment["fingerprint"]),
            embedding_dimensions=dimensions,
            retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
            compaction=compaction,
        )

    async def _load_state(self, run: dict[str, Any]) -> dict[str, Any]:
        async with self.engine.connect() as connection:
            conversations = ConversationRepository(connection)
            memory = MemoryRepository(connection)
            conversation = await conversations.get(str(run["conversation_id"]))
            definition = await DefinitionVersionRepository(connection).get(
                str(conversation["agent_definition_version_id"])
            )
            subject_id = str(conversation["memory_subject_id"])
            return {
                "conversation": conversation,
                "definition": definition,
                "messages": await conversations.list_messages(str(conversation["id"])),
                "summary": await conversations.latest_summary(str(conversation["id"])),
                "active_facts": await memory.list_active_facts(subject_id),
                "entities": await memory.list_entities(subject_id),
            }

    async def _search(
        self,
        *,
        subject_id: str,
        query_vector: list[float],
        fingerprint: str,
        limit: int,
        maximum_distance: float | None,
    ) -> list[dict[str, Any]]:
        async with self.engine.connect() as connection:
            return await MemoryRepository(connection).search_active_facts(
                subject_id=subject_id,
                query_embedding=query_vector,
                model_fingerprint=fingerprint,
                retrieval_policy_version=RETRIEVAL_POLICY_VERSION,
                limit=limit,
                maximum_distance=maximum_distance,
            )


def _required_deployment(
    deployments: dict[str, dict[str, Any]], role: str
) -> dict[str, Any]:
    try:
        return deployments[role]
    except KeyError as exc:
        raise RuntimeValidationError(
            f"Agent definition has no {role} deployment snapshot"
        ) from exc


def _current_user_message(
    messages: list[dict[str, Any]], run_id: str
) -> dict[str, Any]:
    matches = [
        message
        for message in messages
        if message["role"] == "user" and str(message.get("run_id")) == run_id
    ]
    if len(matches) != 1:
        raise RuntimeValidationError(
            "Accepted run must reference exactly one immutable user message"
        )
    return matches[0]


def _max_model_requests(deployment: dict[str, Any]) -> int:
    context = dict(deployment.get("fingerprint_payload", {})).get(
        "context_settings", {}
    )
    if not isinstance(context, dict):
        return 6
    return max(1, min(8, int(context.get("max_model_requests") or 6)))


def _embedding_dimensions(deployment: dict[str, Any]) -> int:
    sampling = dict(deployment.get("fingerprint_payload", {})).get(
        "sampling_settings", {}
    )
    if not isinstance(sampling, dict):
        return 0
    return max(0, int(sampling.get("dimensions") or 0))


def _context_fact(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(fact["id"]),
        "key": str(fact["normalized_key"]),
        "value": fact["value"],
        "version": int(fact["version"]),
    }


def _tool_fact(fact: dict[str, Any]) -> dict[str, Any]:
    return {
        **_context_fact(fact),
        "fact_type": fact["fact_type"],
        "qualifier": fact["qualifier"],
        "distance": float(fact["distance"]),
    }


def _fact_document(operation) -> str:
    return (
        f"fact_type: {operation.fact_type}\n"
        f"qualifier: {operation.qualifier or ''}\n"
        f"value: {operation.value or ''}"
    )


def _validate_review_decision(
    *,
    decision,
    subject_id: str,
    current_user: dict[str, Any],
    active_facts: list[dict[str, Any]],
    entities: list[dict[str, Any]],
) -> None:
    prepare_memory_review(
        decision=decision,
        subject_id=subject_id,
        current_user_message=current_user,
        active_facts=active_facts,
        entities=entities,
    )


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("whole runtime attempt timed out")
    return remaining
