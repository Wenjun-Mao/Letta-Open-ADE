from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from .compaction import ModelCompaction, plan_compaction
from .context import BuiltContext, ContextBudget, build_context
from .embeddings import (
    AUTOMATIC_MAXIMUM_COSINE_DISTANCE,
    RETRIEVAL_POLICY_VERSION,
    EmbeddingClient,
    qwen_query_text,
)
from .errors import RuntimeValidationError
from .executor import ConversationExecutor, ExecutorResult, curated_tools
from .memory_policy import PreparedMemoryReview, prepare_memory_review
from .persistence.conversations import ConversationRepository
from .persistence.definitions import DefinitionVersionRepository
from .persistence.memory import MemoryRepository
from .reviewer import MemoryReviewer, ReviewerResult
from .router_transport import RouterTransport


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
    def __init__(self, *, engine: AsyncEngine, transport: RouterTransport) -> None:
        self.engine = engine
        self.transport = transport
        self.embeddings = EmbeddingClient(transport)
        self.executor = ConversationExecutor(transport)
        self.reviewer = MemoryReviewer(transport)

    async def execute(self, run: dict[str, Any], *, deadline: float) -> AttemptResult:
        state = await self._load_state(run)
        definition = state["definition"]
        conversation = state["conversation"]
        subject_id = str(conversation["memory_subject_id"])
        deployments = {
            str(item["role"]): item for item in definition["deployment_snapshot"]
        }
        conversation_deployment = _required_deployment(deployments, "conversation")
        reviewer_deployment = _required_deployment(deployments, "reviewer")
        retriever_deployment = _required_deployment(deployments, "retriever")
        current_user = _current_user_message(state["messages"], str(run["id"]))

        query_vector = (
            await self.embeddings.embed(
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
        summary = state["summary"]
        summary_boundary = int(summary["through_sequence"]) if summary else 0
        recent_messages = [
            message
            for message in state["messages"]
            if int(message["sequence"]) > summary_boundary
            and str(message["id"]) != str(current_user["id"])
        ]
        budget = _context_budget(conversation_deployment)
        try:
            built_context = build_context(
                system_prompt=str(definition["prompt_content"]),
                persona=str(definition["persona_content"]),
                active_facts=[_context_fact(item) for item in active_facts[:12]],
                conversation_summary=str(summary["content"]) if summary else "",
                retrieved_facts=[_context_fact(item) for item in retrieved],
                recent_messages=recent_messages,
                current_user_content=str(current_user["content"]),
                budget=budget,
            )
        except ValueError as exc:
            raise RuntimeValidationError(str(exc)) from exc

        async def search_memory(query: str, limit: int) -> list[dict[str, Any]]:
            vector = (
                await self.embeddings.embed(
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

        executor_result = await self.executor.execute(
            model_key=str(conversation_deployment["route_alias"]),
            messages=built_context.messages,
            timeout_seconds=_remaining(deadline),
            max_output_tokens=budget.max_output_tokens,
            max_model_requests=_max_model_requests(conversation_deployment),
            tools=curated_tools(
                tuple(str(name) for name in definition["tool_names"]),
                search_memory=search_memory,
            ),
        )
        recent_users = [
            message
            for message in state["messages"]
            if message["role"] == "user" and message["id"] != current_user["id"]
        ][-8:]
        reviewer_result = await self.reviewer.review(
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
            if operation.proposal.value is not None
        ]
        vectors = await self.embeddings.embed(
            model_key=str(retriever_deployment["route_alias"]),
            inputs=[_fact_document(item) for item in embeddable],
            timeout_seconds=_remaining(deadline),
        )
        vector_iterator = iter(vectors)
        operation_embeddings = tuple(
            None if operation.proposal.value is None else next(vector_iterator)
            for operation in prepared.operations
        )
        expected_dimensions = _embedding_dimensions(retriever_deployment)
        dimensions = len(vectors[0]) if vectors else expected_dimensions
        if expected_dimensions and vectors and dimensions != expected_dimensions:
            raise RuntimeValidationError(
                "Embedding dimensions do not match the deployment fingerprint"
            )
        compaction_plan = plan_compaction(
            messages=state["messages"],
            current_user_message_id=str(current_user["id"]),
            summary=summary,
            omitted_message_ids=built_context.omitted_message_ids,
        )
        compaction = (
            await self.executor.compact(
                model_key=str(conversation_deployment["route_alias"]),
                plan=compaction_plan,
                timeout_seconds=_remaining(deadline),
                max_output_tokens=budget.max_output_tokens,
            )
            if compaction_plan is not None
            else None
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


def _context_budget(deployment: dict[str, Any]) -> ContextBudget:
    context = dict(deployment.get("fingerprint_payload", {})).get(
        "context_settings", {}
    )
    if not isinstance(context, dict):
        context = {}
    context_window = int(
        context.get("total_tokens") or context.get("context_tokens") or 16_384
    )
    max_output = int(
        context.get("max_output_tokens")
        or context.get("response_reserve_tokens")
        or 4_096
    )
    return ContextBudget(
        context_window=max(2_048, context_window),
        max_output_tokens=max(256, min(max_output, context_window // 2)),
        tool_schema_tokens=256,
    )


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
        f"fact_type: {operation.proposal.fact_type}\n"
        f"qualifier: {operation.proposal.qualifier or ''}\n"
        f"value: {operation.proposal.value or ''}"
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
