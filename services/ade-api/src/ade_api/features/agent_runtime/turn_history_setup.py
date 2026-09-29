"""Bind one evaluated turn's snapshot, deployments and source-guarded selector."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncEngine

from .context import BuiltContext, ContextBudget
from .embeddings import EmbeddingClient
from .executor import CuratedTool
from .errors import RuntimeValidationError
from .history_admission import HistoryProbe
from .history_attempt import HistoryAttempt
from .history_native_rank import HISTORY_EMBEDDING_ROUTE, HISTORY_VECTOR_RECIPE
from .provider_tracing import AttemptTrace
from .router_transport import RouterTransport
from .turn_context_selection import TurnContextSelection


def validate_history_ranking_deployment(
    probe: HistoryProbe, retriever_deployment: dict[str, Any]
) -> None:
    if probe.ranking_recipe in {
        "probe_local_qwen_cosine",
        "probe_local_qwen_cosine_v2",
    }:
        payload = retriever_deployment.get("fingerprint_payload", {})
        sampling = payload.get("sampling_settings", {})
        if (
            retriever_deployment.get("route_alias") != HISTORY_EMBEDDING_ROUTE
            or retriever_deployment.get("fingerprint")
            != probe.expected_embedding_fingerprint
            or sampling.get("dimensions") != HISTORY_VECTOR_RECIPE["dimensions"]
            or payload.get("artifact_reference")
            != HISTORY_VECTOR_RECIPE["artifact_reference"]
            or payload.get("artifact_revision")
            != HISTORY_VECTOR_RECIPE["artifact_revision"]
        ):
            raise RuntimeValidationError(
                "H2 Qwen deployment identity differs before history ranking",
                detail_code="natural_history_selector_unavailable",
            )


async def prepare_history_turn(
    *,
    engine: AsyncEngine,
    probe: HistoryProbe,
    state: dict[str, Any],
    run: dict[str, Any],
    conversation: dict[str, Any],
    definition: dict[str, Any],
    current_user: dict[str, Any],
    selection: TurnContextSelection,
    conversation_deployment: dict[str, Any],
    reviewer_deployment: dict[str, Any],
    retriever_deployment: dict[str, Any],
    conversation_adapter: str,
    reviewer_adapter: str,
    generation_tools: dict[str, CuratedTool],
    budget: ContextBudget,
    deadline: float,
    trace: AttemptTrace,
    transport: RouterTransport,
) -> tuple[HistoryAttempt, BuiltContext]:
    validate_history_ranking_deployment(probe, retriever_deployment)
    attempt = HistoryAttempt(
        engine=engine,
        probe=probe,
        corpus=state.get("history", {}),
        run=run,
        conversation=conversation,
        definition=definition,
        current_user=current_user,
        source_messages=list(selection.natural_source_messages),
        facts=state["facts"],
        entities=state["entities"],
        base_context=selection.context,
        generation_model_key=str(conversation_deployment["route_alias"]),
        generation_adapter=conversation_adapter,
        generation_tools=generation_tools,
        generation_input_limit=budget.input_limit,
        generation_max_output_tokens=budget.max_output_tokens,
        reviewer_model_key=str(reviewer_deployment["route_alias"]),
        reviewer_adapter=reviewer_adapter,
        reviewer_input_limit=selection.reviewer_input_limit,
        reviewer_max_output_tokens=selection.reviewer_request_max_tokens,
        deadline=deadline,
        ranking_embeddings=EmbeddingClient(
            trace.transport(
                transport,
                stage="history_ranking",
                model_fingerprint=str(retriever_deployment["fingerprint"]),
            )
        ),
        ranking_model_key=str(retriever_deployment["route_alias"]),
    )
    return attempt, await attempt.prepare()
