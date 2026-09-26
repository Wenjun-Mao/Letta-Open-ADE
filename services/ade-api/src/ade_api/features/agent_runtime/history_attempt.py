"""One evaluation turn's fixed history packet and awaited source authorization."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from .context import BuiltContext
from .embeddings import EmbeddingClient
from .errors import RuntimeValidationError
from .executor import ConversationExecutor, CuratedTool, ExecutorResult
from .history_admission import HistoryProbe, admit_history, select_ranked_exchanges
from .history_native_rank import NativeHistoryRank, rank_native_history
from .persistence.history_guard import validate_history_before_dispatch


class HistoryBeforeExposure(Exception):
    def __init__(self, missing_run_ids: set[str], *, unavailable: bool = False) -> None:
        self.missing_run_ids = missing_run_ids
        self.unavailable = unavailable


@dataclass
class HistoryAttempt:
    engine: AsyncEngine
    probe: HistoryProbe
    corpus: dict[str, Any]
    run: dict[str, Any]
    conversation: dict[str, Any]
    definition: dict[str, Any]
    current_user: dict[str, Any]
    source_messages: list[dict[str, Any]]
    facts: list[dict[str, Any]]
    entities: list[dict[str, Any]]
    base_context: BuiltContext
    generation_model_key: str
    generation_adapter: str
    generation_tools: dict[str, CuratedTool]
    generation_input_limit: int
    generation_max_output_tokens: int
    reviewer_model_key: str
    reviewer_adapter: str
    reviewer_input_limit: int
    reviewer_max_output_tokens: int
    deadline: float
    ranking_embeddings: EmbeddingClient | None = None
    ranking_model_key: str | None = None
    ranked_exchanges: list[dict[str, Any]] = field(default_factory=list)
    admitted_exchanges: list[dict[str, Any]] = field(default_factory=list)
    context: BuiltContext | None = None
    exposed: bool = False
    ranking_exposed: bool = False
    rank_observation: NativeHistoryRank | None = None
    status: str = "empty"

    async def prepare(self) -> BuiltContext:
        if self.probe.arm == "automatic_history":
            if self.corpus.get("unavailable"):
                self.status = "unavailable"
            elif self.probe.ranking_recipe is not None:
                try:
                    self.rank_observation = await rank_native_history(
                        exchanges=self.corpus.get("exchanges", []),
                        current_user=str(self.current_user["content"]),
                        local_suffix=[
                            message
                            for message in self.source_messages
                            if str(message["id"]) != str(self.current_user["id"])
                        ],
                        recipe=self.probe.ranking_recipe,
                        embeddings=self.ranking_embeddings,
                        model_key=self.ranking_model_key,
                        deadline=self.deadline,
                        authorize_sources=self.authorize_ranking_sources,
                        mark_exposed=self.mark_ranking_exposed,
                    )
                except HistoryBeforeExposure as exc:
                    if not exc.unavailable:
                        raise
                    self.status = "unavailable"
                else:
                    self.ranked_exchanges = self.rank_observation.exchanges
                    if self.rank_observation.status == "purged":
                        self.status = "purged"
            else:
                self.ranked_exchanges = select_ranked_exchanges(
                    self.probe,
                    self.corpus.get("exchanges", []),
                    current_user=str(self.current_user["content"]),
                    local_suffix=[
                        message
                        for message in self.source_messages
                        if str(message["id"]) != str(self.current_user["id"])
                    ],
                )
        return self._admit()

    def _admit(self) -> BuiltContext:
        admission = admit_history(
            base=self.base_context,
            ranked_exchanges=self.ranked_exchanges,
            current_user=self.current_user,
            source_messages=self.source_messages,
            facts=self.facts,
            entities=self.entities,
            generation_model_key=self.generation_model_key,
            generation_adapter=self.generation_adapter,
            generation_tools=self.generation_tools,
            generation_input_limit=self.generation_input_limit,
            generation_max_output_tokens=self.generation_max_output_tokens,
            reviewer_model_key=self.reviewer_model_key,
            reviewer_adapter=self.reviewer_adapter,
            reviewer_input_limit=self.reviewer_input_limit,
            reviewer_max_output_tokens=self.reviewer_max_output_tokens,
        )
        self.context = admission.context
        self.admitted_exchanges = list(admission.exchanges)
        if self.status not in {"unavailable", "purged"}:
            self.status = (
                "admitted"
                if self.admitted_exchanges
                else "capacity_omitted"
                if admission.omitted_capacity
                else "empty"
            )
        return admission.context

    def omit_before_exposure(self, failure: HistoryBeforeExposure) -> BuiltContext:
        if self.exposed:
            raise RuntimeValidationError(
                "Exposed history cannot be rebuilt",
                detail_code="natural_history_integrity",
            )
        self.ranked_exchanges = (
            []
            if failure.unavailable
            else [
                exchange
                for exchange in self.ranked_exchanges
                if str(exchange["run_id"]) not in failure.missing_run_ids
            ]
        )
        self.status = "unavailable" if failure.unavailable else "purged"
        return self._admit()

    async def _validate_sources(
        self, exchanges: list[dict[str, Any]], *, exposed: bool
    ) -> set[str]:
        if not exchanges:
            return set()
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeValidationError(
                "History authorization exceeded the attempt deadline",
                detail_code="natural_history_timeout",
            )

        async def check() -> set[str]:
            async with self.engine.connect() as connection:
                subject_id = str(self.conversation["memory_subject_id"])
                return await validate_history_before_dispatch(
                    connection,
                    exchanges=exchanges,
                    workspace_id=str(self.conversation["workspace_id"]),
                    subject_id=subject_id,
                    purpose=str(self.conversation["purpose"]),
                    definition_root_id=str(self.definition["agent_definition_id"]),
                    current_run_id=str(self.run["id"]),
                    accepted_memory_generation=int(
                        self.run["accepted_memory_generation"]
                    ),
                )

        try:
            missing = await asyncio.wait_for(check(), timeout=remaining)
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise RuntimeValidationError(
                "History authorization timed out",
                detail_code="natural_history_timeout",
            ) from exc
        except SQLAlchemyError as exc:
            if not exposed:
                raise HistoryBeforeExposure(
                    {str(item["run_id"]) for item in exchanges},
                    unavailable=True,
                ) from exc
            raise RuntimeValidationError(
                "Exposed history could not be revalidated",
                detail_code="natural_history_unavailable",
            ) from exc
        return missing

    async def authorize_ranking_sources(
        self, exchanges: list[dict[str, Any]]
    ) -> set[str]:
        missing = await self._validate_sources(exchanges, exposed=self.ranking_exposed)
        if missing and self.ranking_exposed:
            raise RuntimeValidationError(
                "Exposed ranking source was removed",
                detail_code="natural_history_missing",
            )
        return missing

    def mark_ranking_exposed(self) -> None:
        self.ranking_exposed = True

    async def authorize_request(self, _payload: dict[str, Any]) -> None:
        if not self.admitted_exchanges:
            return
        missing = await self._validate_sources(
            self.admitted_exchanges, exposed=self.exposed
        )
        if missing:
            if not self.exposed:
                raise HistoryBeforeExposure(missing)
            raise RuntimeValidationError(
                "Exposed historical source was removed",
                detail_code="natural_history_missing",
            )
        self.exposed = True


async def execute_generation_with_history(
    *,
    executor: ConversationExecutor,
    context: BuiltContext,
    history_attempt: HistoryAttempt | None,
    model_key: str,
    max_output_tokens: int,
    max_model_requests: int,
    input_token_limit: int | None,
    tools: Mapping[str, CuratedTool],
    deadline: float,
    observe_request: Callable[[dict[str, Any]], None] | None,
) -> tuple[ExecutorResult, BuiltContext]:
    """Rebuild only before first H exposure; continuations keep the same packet."""
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("whole runtime attempt timed out")
        try:
            result = await executor.execute(
                model_key=model_key,
                messages=context.messages,
                timeout_seconds=remaining,
                max_output_tokens=max_output_tokens,
                max_model_requests=max_model_requests,
                input_token_limit=input_token_limit,
                observe_request=observe_request,
                authorize_request=(
                    history_attempt.authorize_request
                    if history_attempt is not None
                    else None
                ),
                tools=tools,
            )
            return result, context
        except HistoryBeforeExposure as exc:
            assert history_attempt is not None
            context = history_attempt.omit_before_exposure(exc)
