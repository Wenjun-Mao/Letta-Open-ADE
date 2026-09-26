"""One evaluation turn's fixed history packet and awaited source authorization."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine

from .context import BuiltContext
from .errors import RuntimeValidationError
from .executor import CuratedTool
from .history_admission import HistoryProbe, admit_history, select_ranked_exchanges
from .persistence.history_guard import validate_admitted_history
from .persistence.metadata import memory_subjects


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
    ranked_exchanges: list[dict[str, Any]] = field(default_factory=list)
    admitted_exchanges: list[dict[str, Any]] = field(default_factory=list)
    context: BuiltContext | None = None
    exposed: bool = False
    status: str = "empty"

    def prepare(self) -> BuiltContext:
        if self.probe.arm == "automatic_history":
            if self.corpus.get("unavailable"):
                self.status = "unavailable"
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

    async def authorize_request(self, _payload: dict[str, Any]) -> None:
        if not self.admitted_exchanges:
            return
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeValidationError(
                "History authorization exceeded the attempt deadline",
                detail_code="natural_history_timeout",
            )

        async def check() -> set[str]:
            async with self.engine.connect() as connection:
                subject_id = str(self.conversation["memory_subject_id"])
                generation = await connection.scalar(
                    select(memory_subjects.c.memory_generation).where(
                        memory_subjects.c.id == subject_id,
                        memory_subjects.c.workspace_id
                        == str(self.conversation["workspace_id"]),
                    )
                )
                if generation != int(self.run["accepted_memory_generation"]):
                    raise RuntimeValidationError(
                        "Subject memory changed before history exposure",
                        detail_code="natural_history_stale_generation",
                    )
                return await validate_admitted_history(
                    connection,
                    exchanges=self.admitted_exchanges,
                    workspace_id=str(self.conversation["workspace_id"]),
                    subject_id=subject_id,
                    purpose=str(self.conversation["purpose"]),
                    definition_root_id=str(self.definition["agent_definition_id"]),
                    current_run_id=str(self.run["id"]),
                )

        try:
            missing = await asyncio.wait_for(check(), timeout=remaining)
        except (TimeoutError, asyncio.TimeoutError) as exc:
            raise RuntimeValidationError(
                "History authorization timed out",
                detail_code="natural_history_timeout",
            ) from exc
        except SQLAlchemyError as exc:
            if not self.exposed:
                raise HistoryBeforeExposure(
                    {str(item["run_id"]) for item in self.admitted_exchanges},
                    unavailable=True,
                ) from exc
            raise RuntimeValidationError(
                "Exposed history could not be revalidated",
                detail_code="natural_history_unavailable",
            ) from exc
        if missing:
            if not self.exposed:
                raise HistoryBeforeExposure(missing)
            raise RuntimeValidationError(
                "Exposed historical source was removed",
                detail_code="natural_history_missing",
            )
        self.exposed = True
